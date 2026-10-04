"""CRUD поверх REST API Warehouse.

Модуль не знает про HTTP-детали: вызывающий код работает с моделями из
`models.py`, а сетевые ошибки приходят как `ApiError`.

Загрузка контейнеров
--------------------
Получить путь контейнера (`Box.full_path`) можно только зная всю цепочку
родителей, поэтому для этого нужен весь список `/boxes`. Чтобы не делать
по одному запросу на каждую строку таблицы, вводится `BoxIndex` — кэш
контейнеров на одну операцию перерисовки:

    boxes = crud.BoxIndex.load(client)
    location = boxes.full_path(item.box_id)

Каждый метод ниже, которому нужны контейнеры, принимает готовый `BoxIndex`
либо загружает свой (однократно) — но никогда не делает запрос на позицию.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from api_client import ApiClient, ApiError
from models import Box, BoxType, Item, ItemType

NO_LOCATION = "Без расположения"


class BoxIndex:
    """Контейнеры и пути к ним, загруженные одним запросом к /boxes."""

    def __init__(self, boxes: List[Box]):
        self._boxes: Dict[int, Box] = {box.box_id: box for box in boxes}

        # Проставляем ссылки на родителей, чтобы `Box.full_path` работал
        # и в crud, и в диалогах (им нужен путь до корня).
        for box in boxes:
            if box.parent_id is not None:
                box.parent = self._boxes.get(box.parent_id)

        self._paths: Dict[int, str] = {}

    @classmethod
    def load(cls, client: ApiClient) -> "BoxIndex":
        return cls([Box.from_api(row) for row in client.get("/boxes")])

    def get(self, box_id: Optional[int]) -> Optional[Box]:
        return self._boxes.get(box_id) if box_id is not None else None

    def all(self) -> List[Box]:
        return list(self._boxes.values())

    def children_of(self, box_id: Optional[int]) -> List[Box]:
        """Непосредственные потомки контейнера (None — корневые контейнеры)."""
        return [box for box in self._boxes.values() if box.parent_id == box_id]

    def full_path(self, box_id: Optional[int]) -> str:
        """Путь «Склад / Стеллаж A / Полка 1» либо «Без расположения»."""
        if box_id is None:
            return NO_LOCATION
        cached = self._paths.get(box_id)
        if cached is not None:
            return cached

        # Путь собираем с защитой от цикла: сервер запрещает зацикливание,
        # но повреждённые данные не должны подвешивать UI.
        parts: List[str] = []
        seen = set()
        current: Optional[Box] = self._boxes.get(box_id)
        while current is not None and current.box_id not in seen:
            seen.add(current.box_id)
            parts.append(current.box_name)
            current = current.parent

        path = " / ".join(reversed(parts)) if parts else NO_LOCATION
        self._paths[box_id] = path
        return path


# ──────────────────────────────────────────────────────────── контейнеры

def get_all_box_types(client: ApiClient) -> List[BoxType]:
    return [BoxType.from_api(row) for row in client.get("/box-types")]


def add_box_type(client: ApiClient, name: str) -> BoxType:
    return BoxType.from_api(client.post("/box-types", {"name": name}))


def get_all_boxes(client: ApiClient) -> List[Box]:
    """Все контейнеры со связанными родителями (нужно для диалогов)."""
    return BoxIndex.load(client).all()


def get_box_by_id(client: ApiClient, box_id: int) -> Optional[Box]:
    try:
        return Box.from_api(client.get(f"/boxes/{box_id}"))
    except ApiError as error:
        if error.status == 404:
            return None
        raise


def add_box(client: ApiClient, name: str, box_type_id: int, parent_id: Optional[int]) -> Box:
    return Box.from_api(client.post("/boxes", {
        "name": name,
        "box_type_id": box_type_id,
        "parent_id": parent_id,
    }))


def update_box(
    client: ApiClient,
    box_id: int,
    name: str,
    box_type_id: int,
    parent_id: Optional[int],
) -> None:
    """Обновляет контейнер: сначала реквизиты, затем родителя (отдельный эндпоинт)."""
    client.patch(f"/boxes/{box_id}", {"name": name, "box_type_id": box_type_id})
    client.post(f"/boxes/{box_id}/move", {"parent_id": parent_id})


def delete_box(client: ApiClient, box_id: int) -> int:
    """Удаляет контейнер; возвращает, сколько позиций осталось без расположения."""
    result = client.delete(f"/boxes/{box_id}") or {}
    return int(result.get("unboxed") or 0)


# ──────────────────────────────────────────────────────── типы товаров

def get_all_item_types(client: ApiClient) -> List[ItemType]:
    return [ItemType.from_api(row) for row in client.get("/item-types")]


def add_item_type(client: ApiClient, name: str, weight_g: Optional[int]) -> ItemType:
    return ItemType.from_api(client.post("/item-types", {"name": name, "weight_g": weight_g}))


def update_item_type(client: ApiClient, item_type_id: int, name: str, weight_g: Optional[int]) -> None:
    client.patch(f"/item-types/{item_type_id}", {"name": name, "weight_g": weight_g})


# ──────────────────────────────────────────────────────────────── товары

def get_item_by_id(client: ApiClient, item_id: int) -> Optional[Item]:
    try:
        return Item.from_api(client.get(f"/items/{item_id}"))
    except ApiError as error:
        if error.status == 404:
            return None
        raise


def get_all_items(client: ApiClient) -> List[Item]:
    return [Item.from_api(row) for row in client.get("/items")]


def get_items_by_box(
    client: ApiClient,
    box_id: int,
    include_children: bool = True,
) -> List[Item]:
    return [
        Item.from_api(row)
        for row in client.get("/items", {
            "box_id": box_id,
            "include_children": str(include_children).lower(),
        })
    ]


def get_items_without_box(client: ApiClient) -> List[Item]:
    return [Item.from_api(row) for row in client.get("/items", {"unboxed": "true"})]


def add_item(client: ApiClient, item_type_id: int, box_id: Optional[int], quantity: int) -> Item:
    return Item.from_api(client.post("/items", {
        "item_type_id": item_type_id,
        "box_id": box_id,
        "quantity": quantity,
    }))


def update_item(
    client: ApiClient,
    item_id: int,
    item_type_id: int,
    box_id: Optional[int],
    quantity: int,
) -> None:
    client.patch(f"/items/{item_id}", {
        "item_type_id": item_type_id,
        "box_id": box_id,
        "quantity": quantity,
    })


def delete_item(client: ApiClient, item_id: int) -> None:
    client.delete(f"/items/{item_id}")


# ──────────────────────────────────────────────────────────────── поиск

def search_items(client: ApiClient, query: str, boxes: BoxIndex) -> List[Item]:
    """Фильтрует товары по типу товара или по расположению."""
    needle = query.lower().strip()
    if not needle:
        return []

    return [
        item for item in get_all_items(client)
        if needle in _item_type_name(item).lower()
        or needle in boxes.full_path(item.box_id).lower()
    ]


def _item_type_name(item: Item) -> str:
    return item.item_type.item_type_name if item.item_type else ""