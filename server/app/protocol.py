"""Протокол весов и QR.

Раньше здесь была копия логики `shared/protocol.py` — она разошлась с оригиналом
(в копии не было `format_weight_line`/`make_qr_payload`). Теперь это тонкая
обёртка: единственный источник истины — пакет `shared/`, а настоящая копия
осталась только в `firmware/weight_module/emulator.py`, где она действительно
необходима (контекст сборки образа — firmware/, пакета shared/ там нет).
"""
from shared.protocol import (
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