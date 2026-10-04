"""Модели склада. Поля соответствуют ответам Warehouse REST API.

Модели — тонкие датаклассы: разбор JSON (`from_api`) и вычисляемые свойства.
Никакой бизнес-логики и обращений к сети здесь нет.

Замечание о поле `parent`: ссылки между контейнерами проставляет `crud.BoxIndex`
либо список, полученный из `get_all_boxes`. Одиночный ответ `/boxes/{id}` не
содержит родителя, поэтому путь (`full_path`) считается по локальному кэшу.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BoxType:
    box_type_id: int
    box_type_name: str

    @classmethod
    def from_api(cls, row: dict) -> "BoxType":
        return cls(box_type_id=row["id"], box_type_name=row["name"])


@dataclass
class Box:
    box_id: int
    box_name: str
    box_type_id: int
    parent_id: Optional[int] = None
    box_type_name: str = ""

    #: Ссылка на родителя; проставляется из полного списка контейнеров.
    parent: Optional["Box"] = None

    @classmethod
    def from_api(cls, row: dict) -> "Box":
        return cls(
            box_id=row["id"],
            box_name=row["name"],
            box_type_id=row["box_type_id"],
            parent_id=row.get("parent_id"),
            box_type_name=row.get("box_type_name") or "",
        )

    @property
    def full_path(self) -> str:
        """«Склад / Стеллаж A / Полка 1»; защищено от зацикливания."""
        parts = []
        seen = set()
        current: Optional[Box] = self
        while current is not None and current.box_id not in seen:
            seen.add(current.box_id)
            parts.append(current.box_name)
            current = current.parent
        return " / ".join(reversed(parts))


@dataclass
class ItemType:
    item_type_id: int
    item_type_name: str
    weight_g: Optional[int] = None

    @classmethod
    def from_api(cls, row: dict) -> "ItemType":
        return cls(
            item_type_id=row["id"],
            item_type_name=row["name"],
            weight_g=row.get("weight_g"),
        )


@dataclass
class Item:
    item_id: int
    item_type_id: int
    box_id: Optional[int]
    quantity: int
    weight_g: Optional[int] = None
    box_name: Optional[str] = None
    total_weight_g_from_api: Optional[int] = None
    item_type: Optional[ItemType] = None

    @classmethod
    def from_api(cls, row: dict) -> "Item":
        """Собирает позицию из строки /items или /boxes/{id}/contents.

        Имена ключей у этих эндпоинтов различаются (`id` против `item_id`),
        поэтому оба варианта поддерживаются явно.
        """
        item = cls(
            item_id=row.get("id") or row.get("item_id"),
            item_type_id=row["item_type_id"],
            box_id=row.get("box_id"),
            quantity=row["quantity"],
            weight_g=row.get("weight_g"),
            box_name=row.get("box_name"),
            total_weight_g_from_api=row.get("total_weight_g"),
        )
        item.item_type = ItemType(
            item_type_id=item.item_type_id,
            item_type_name=row.get("item_type_name") or "—",
            weight_g=item.weight_g,
        )
        return item

    @property
    def total_weight_g(self) -> int:
        """Суммарный вес позиции; 0, если вес единицы неизвестен."""
        if self.total_weight_g_from_api is not None:
            return self.total_weight_g_from_api
        if self.item_type and self.item_type.weight_g:
            return self.item_type.weight_g * self.quantity
        return 0