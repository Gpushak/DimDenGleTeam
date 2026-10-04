"""Протокол весов и QR.

Раньше здесь была копия логики `shared/protocol.py` — она разошлась с оригиналом
(в копии не было `format_weight_line`/`make_qr_payload`). Теперь это тонкая
обёртка: единственный источник истины — пакет `shared/`, а настоящая копия
осталась только в `firmware/weight_module/emulator.py`, где она действительно
необходима (контекст сборки образа — firmware/, пакета shared/ там нет).
"""
import sys
from pathlib import Path


def _locate_shared_package() -> Path | None:
    """Каталог, в котором лежит пакет `shared`.

    Ищем вверх от этого файла, а не считаем фиксированный уровень: раскладка
    разная. Локально — `<repo>/server/app/protocol.py` (корень на 2 уровня
    выше), в Docker — `/app/app/protocol.py` и `shared/` рядом с `/app`
    (корень на 1 уровень выше, и там же работает `PYTHONPATH=/app`).
    """
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "shared" / "protocol.py").is_file():
            return candidate
    return None


# Пакет `shared` лежит вне папки `server/`. В Docker это уже решено через
# `ENV PYTHONPATH=/app`, а здесь добавляем корень в пути импорта, чтобы тот же
# импорт работал при локальном запуске из папки `server/`
# (`uvicorn app.main:app`) без ручной настройки переменных окружения.
_shared_root = _locate_shared_package()
if _shared_root is not None and str(_shared_root) not in sys.path:
    sys.path.insert(0, str(_shared_root))

from shared.protocol import (  # noqa: E402  (импорт после настройки sys.path)
    QR_KINDS,
    QR_SCHEME,
    SERIAL_BAUD,
    WEIGHT_PREFIX,
    format_weight_line,
    make_qr_payload,
    parse_qr_payload,
    parse_weight_line,
)

__all__ = [
    "QR_KINDS",
    "QR_SCHEME",
    "SERIAL_BAUD",
    "WEIGHT_PREFIX",
    "format_weight_line",
    "make_qr_payload",
    "parse_qr_payload",
    "parse_weight_line",
]