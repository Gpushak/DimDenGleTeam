"""Протокол весов и QR — единственный источник истины для всего проекта.

Используется сервером (`GET /lookup`, `POST /scale`), десктопом и десктопным
генератором QR-этикеток.

Вес по Serial (9600 8N1), одна строка:
    WEIGHT:<граммы>
Дополнительно принимаются человекочитаемые строки Arduino:
    Weight: 12.34 g
    12.34 g

QR-этикетка:
    qwentory:item:<item_id>
    qwentory:type:<item_type_id>
    qwentory:box:<box_id>

ПРИ ИЗМЕНЕНИИ ЗДЕСЬ: проверьте, что правка не требует обновления
`firmware/weight_module/emulator.py` — там протокол продублирован намеренно,
чтобы образ эмулятора не зависел от этого пакета.
"""
from __future__ import annotations

import re
from typing import Optional

QR_SCHEME = "qwentory"
SERIAL_BAUD = 9600
WEIGHT_PREFIX = "WEIGHT:"

#: Допустимые значения второго сегмента QR-кода.
QR_KINDS = frozenset({"item", "type", "box"})

_WEIGHT_PATTERNS = (
    re.compile(r"^WEIGHT:(-?\d+(?:\.\d+)?)\s*$", re.IGNORECASE),
    re.compile(r"^Weight:\s*(-?\d+(?:\.\d+)?)\s*g", re.IGNORECASE),
    re.compile(r"^(-?\d+(?:\.\d+)?)\s*g\s*$", re.IGNORECASE),
)


def parse_weight_line(line: str) -> Optional[float]:
    """Вес в граммах из строки Serial или None, если строка не про вес."""
    text = (line or "").strip()
    if not text:
        return None
    for pattern in _WEIGHT_PATTERNS:
        match = pattern.match(text)
        if match:
            return float(match.group(1))
    return None


def format_weight_line(weight_g: float) -> str:
    """Строка Serial, которую шлёт прошивка Arduino."""
    return f"{WEIGHT_PREFIX}{weight_g:.2f}"


def make_qr_payload(kind: str, entity_id: int) -> str:
    """Содержимое QR-этикетки для сущности заданного вида."""
    if kind not in QR_KINDS:
        raise ValueError(f"Unknown QR kind: {kind}")
    return f"{QR_SCHEME}:{kind}:{int(entity_id)}"


def parse_qr_payload(code: str) -> Optional[tuple[str, int]]:
    """Разбирает `qwentory:<kind>:<id>` в пару (kind, id) либо None.

    Идентификатор должен быть положительным целым: это соответствует
    проверке на стороне Android (data/model/QrCode.java).
    """
    text = (code or "").strip()
    parts = text.split(":")
    if len(parts) != 3 or parts[0] != QR_SCHEME:
        return None
    kind, raw_id = parts[1], parts[2]
    if kind not in QR_KINDS:
        return None
    try:
        entity_id = int(raw_id)
    except ValueError:
        return None
    return (kind, entity_id) if entity_id > 0 else None