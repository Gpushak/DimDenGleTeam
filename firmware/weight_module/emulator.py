"""Эмулятор весового модуля: Serial (Arduino/HX711) → POST /scale.

Нужен, чтобы тестировать весовой контур без физического железа.

Два режима работы (выбираются автоматически):

* **serial** — если задан `SERIAL_PORT` (и установлен pyserial), читаем строки
  от Arduino и публикуем распарсенный вес. Строка отправляется в API как есть,
  поэтому сервер помечает источник как `serial`.
* **simulation** — если порт не задан или недоступен, генерируем правдоподобный
  вес: значения «ложатся на весы», стабилизируются с шумом, затем уходят в ноль.

Скрипт использует только стандартную библиотеку, чтобы образ Docker оставался
минимальным. `pyserial` — опциональная зависимость для работы с реальным портом.
"""
from __future__ import annotations

import json
import os
import random
import signal
import sys
import time
from typing import Iterator, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# --------------------------------------------------------------------------
# Настройки (переопределяются переменными окружения)
# --------------------------------------------------------------------------

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000").rstrip("/")

# Физический порт. Пусто (по умолчанию) — работа в режиме симуляции.
SERIAL_PORT = os.getenv("SERIAL_PORT", "")

# Baud- rate Arduino/HX711-модуля. Должен совпадать с shared/protocol.py.
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "9600"))

# Интервал публикации в секундах.
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", "1.0"))

# Границы «правдоподобного» веса для симуляции.
SIM_MIN_WEIGHT = float(os.getenv("SIM_MIN_WEIGHT", "0"))
SIM_MAX_WEIGHT = float(os.getenv("SIM_MAX_WEIGHT", "2500"))


def log(message: str) -> None:
    """Печать в stdout с временной меткой (важно для `docker compose logs`)."""
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


# --------------------------------------------------------------------------
# Протокол (продублирован намеренно — образ не должен зависеть от ../../shared)
# --------------------------------------------------------------------------

WEIGHT_PREFIX = "WEIGHT:"


def format_weight_line(weight_g: float) -> str:
    """Строка того же формата, что шлёт прошивка Arduino."""
    return f"{WEIGHT_PREFIX}{weight_g:.2f}"


# --------------------------------------------------------------------------
# Источники данных о весе
# --------------------------------------------------------------------------


def simulate_weights() -> Iterator[float]:
    """Генерирует правдоподобную последовательность весов.

    Сценарий имитирует работу кладовщика: груз выставляется, стабилизируется
    с небольшим шумом, затем снимается (вес возвращается к нулю).
    """
    state = "idle"
    current = 0.0
    target = 0.0
    settle_left = 0

    while True:
        if state == "idle":
            if random.random() < 0.05:
                target = random.uniform(SIM_MIN_WEIGHT, SIM_MAX_WEIGHT)
                settle_left = random.randint(3, 8)
                state = "settling"
                log(f"груз выставлен: ~{target:.0f} г")
            current = 0.0

        elif state == "settling":
            settle_left -= 1
            if settle_left <= 0:
                state = "weighing"
                current = target
                log("груз стабилизирован")

        elif state == "weighing":
            # Небольшой дрейф вокруг целевого значения — как у реальных тензодатчиков.
            current = max(0.0, target + random.gauss(0, target * 0.005 + 0.5))

        # Плавный переход к новому состоянию, чтобы значение не прыгало.
        yield current

        if state == "weighing" and random.random() < 0.03:
            state = "idle"
            log("груз снят")


def read_serial(port: str, baud: int) -> Iterator[float]:
    """Читает веса с реального Serial-порта Arduino.

    `pyserial` импортируется лениво: без него скрипт всё равно работает,
    но переходит в режим симуляции (см. `main`).
    """
    import serial  # type: ignore  # noqa: PLC0415  (опциональная зависимость)

    log(f"открываю Serial {port} @ {baud}")
    while True:
        try:
            with serial.Serial(port, baud, timeout=1) as device:
                while True:
                    raw = device.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace").strip()
                    weight = _parse_weight_line(line)
                    if weight is not None:
                        yield weight
        except Exception as error:  # noqa: BLE001 — переподключаемся при обрыве
            log(f"Serial недоступен ({error}), переподключение через 2 с")
            time.sleep(2)


def _parse_weight_line(line: str) -> Optional[float]:
    """Разбирает строку прошивки. Дублирует shared/protocol.py."""
    import re  # noqa: PLC0415

    patterns = (
        re.compile(r"^WEIGHT:(-?\d+(?:\.\d+)?)\s*$", re.IGNORECASE),
        re.compile(r"^Weight:\s*(-?\d+(?:\.\d+)?)\s*g", re.IGNORECASE),
        re.compile(r"^(-?\d+(?:\.\d+)?)\s*g\s*$", re.IGNORECASE),
    )
    for pattern in patterns:
        match = pattern.match(line)
        if match:
            return float(match.group(1))
    return None


# --------------------------------------------------------------------------
# Публикация в API
# --------------------------------------------------------------------------


def publish(weight_g: float, line: str, timeout: float = 5.0) -> bool:
    """Отправляет показание в POST /scale.

    Передаём и `weight_g`, и исходную `line`: сервер помечает источник как
    `serial`, если `line` задан, иначе как `api`.
    """
    payload = json.dumps({"weight_g": round(weight_g, 2), "line": line}).encode("utf-8")
    request = Request(
        f"{API_BASE_URL}/scale",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            response.read()
        return True
    except HTTPError as error:
        log(f"API отклонил показание: {error.code} {error.reason}")
    except URLError as error:
        log(f"API недоступен ({error.reason}) — повторю позже")
    return False


# --------------------------------------------------------------------------
# Точка входа
# --------------------------------------------------------------------------


_running = True


def _handle_signal(signum, _frame) -> None:
    """Корректное завершение по SIGTERM/SIGINT (важно для `docker stop`)."""
    global _running
    log(f"получен сигнал {signum}, завершаюсь")
    _running = False


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    log(f"API: {API_BASE_URL}")

    source = None
    if SERIAL_PORT:
        try:
            import serial  # noqa: F401  — проверяем доступность до старта

            source = read_serial(SERIAL_PORT, SERIAL_BAUD)
            log(f"режим: реальный Serial ({SERIAL_PORT})")
        except ImportError:
            log("pyserial не установлен — переключаюсь на симуляцию")
            source = simulate_weights()
    else:
        log("SERIAL_PORT не задан — режим симуляции (тестовые веса)")
        source = simulate_weights()

    published = 0
    while _running:
        started = time.monotonic()

        try:
            weight = next(source)
        except StopIteration:
            time.sleep(PUBLISH_INTERVAL)
            continue

        line = format_weight_line(weight)
        if publish(weight, line):
            published += 1
            if published % 10 == 0:
                log(f"опубликовано показаний: {published} (последнее: {weight:.2f} г)")

        # Вычитаем время чтения/публикации из интервала, чтобы темп был стабилен.
        elapsed = time.monotonic() - started
        remaining = PUBLISH_INTERVAL - elapsed
        if remaining > 0:
            time.sleep(remaining)

    log(f"остановлено, всего опубликовано показаний: {published}")
    return 0


if __name__ == "__main__":
    sys.exit(main())