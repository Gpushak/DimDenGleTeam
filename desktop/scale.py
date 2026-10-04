"""Чтение весового модуля с Serial и публикация в API /scale.

Работает в двух режимах:

* **Serial** — если задан `SERIAL_PORT` и установлен pyserial, читаем строки
  от Arduino и публикуем распарсенный вес;
* **опрос API** — иначе раз в секунду берём последнее показание из
  `GET /scale`. Это позволяет видеть вес, опубликованный эмулятором
  весов из Docker или другим клиентом.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from typing import Callable, Iterator, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared.protocol import SERIAL_BAUD, parse_weight_line  # noqa: E402

from api_client import ApiClient, ApiError  # noqa: E402

#: Пауза перед повторным открынием порта после обрыва.
_RECONNECT_DELAY = 1.5
#: Период опроса GET /scale, когда Serial недоступен.
_POLL_INTERVAL = 1.0


class ScaleMonitor:
    """Читает веса и сообщает о каждом новом показании."""

    def __init__(self, client: ApiClient, port: str = "",
                 on_weight: Optional[Callable[[float], None]] = None):
        self.client = client
        self.port = port
        self.on_weight = on_weight
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_weight: Optional[float] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="scale-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    # ───────────────────────────────────────────────────── внутреннее

    def _read_serial(self) -> Iterator[float]:
        """Генератор показаний с Serial; переподключается при обрыве."""
        import serial  # type: ignore — опциональная зависимость

        while not self._stop.is_set():
            try:
                with serial.Serial(self.port, SERIAL_BAUD, timeout=1) as device:
                    while not self._stop.is_set():
                        raw = device.readline()
                        if not raw:
                            continue
                        line = raw.decode("utf-8", errors="replace").strip()
                        weight = parse_weight_line(line)
                        if weight is not None:
                            self._publish(weight, line)
            except Exception:  # noqa: BLE001 — любой обрыв переподключаем
                time.sleep(_RECONNECT_DELAY)

    def _poll_api(self) -> None:
        """Забирает последнее показание из API (когда Serial не настроен)."""
        try:
            state = self.client.get("/scale")
            weight = state.get("weight_g") if isinstance(state, dict) else None
            if weight is not None:
                self.last_weight = float(weight)
                if self.on_weight:
                    self.on_weight(self.last_weight)
        except ApiError:
            # Сервер может быть недоступен (или перезапускается) — это
            # не повод останавливать поток, просто ждём следующего цикла.
            pass

    def _publish(self, weight: float, line: str) -> None:
        self.last_weight = weight
        if self.on_weight:
            self.on_weight(weight)
        try:
            self.client.post("/scale", {"weight_g": weight, "line": line})
        except ApiError:
            pass

    def _run(self) -> None:
        if self.port and self._has_pyserial():
            self._read_serial()
            return

        while not self._stop.is_set():
            self._poll_api()
            self._stop.wait(_POLL_INTERVAL)

    @staticmethod
    def _has_pyserial() -> bool:
        try:
            import serial  # noqa: F401
        except ImportError:
            return False
        return True
