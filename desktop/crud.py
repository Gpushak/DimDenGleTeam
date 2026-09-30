"""CRUD операции для работы с БД."""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from models import BoxType, Box, ItemType, Item


# ===== BoxType =====
def get_all_box_types(session: Session) -> List[BoxType]:
    return session.query(BoxType).order_by(BoxType.box_type_name).all()


def add_box_type(session: Session, name: str) -> BoxType:
    bt = BoxType(box_type_name=name)
    session.add(bt)
    session.commit()
    session.refresh(bt)
    return bt


def update_box_type(session: Session, box_type_id: int, name: str) -> None:
    bt = session.get(BoxType, box_type_id)
    if bt:
        bt.box_type_name = name
        session.commit()


def delete_box_type(session: Session, box_type_id: int) -> None:
    bt = session.get(BoxType, box_type_id)
    if bt:
        session.delete(bt)
        session.commit()


# ===== Box =====
def get_all_boxes(session: Session) -> List[Box]:
    return session.query(Box).options(joinedload(Box.box_type)).all()


def get_root_boxes(session: Session) -> List[Box]:
    return session.query(Box).filter(Box.parent_id.is_(None)).options(joinedload(Box.box_type)).all()


def get_child_boxes(session: Session, parent_id: Optional[int]) -> List[Box]:
    if parent_id is None:
        return get_root_boxes(session)
    return session.query(Box).filter(Box.parent_id == parent_id).options(joinedload(Box.box_type)).all()


def get_box_by_id(session: Session, box_id: int) -> Optional[Box]:
    return session.get(Box, box_id)


def add_box(session: Session, name: str, box_type_id: int, parent_id: Optional[int]) -> Box:
    box = Box(box_name=name, box_type_id=box_type_id, parent_id=parent_id)
    session.add(box)
    session.commit()
    session.refresh(box)
    return box


def update_box(session: Session, box_id: int, name: str, box_type_id: int, parent_id: Optional[int]) -> None:
    box = session.get(Box, box_id)
    if box:
        box.box_name = name
        box.box_type_id = box_type_id
        box.parent_id = parent_id
        session.commit()


def delete_box(session: Session, box_id: int) -> int:
    """Удалить контейнер и всех потомков. Товары остаются с box_id=None.
    Возвращает количество затронутых товаров."""
    box = session.query(Box).get(box_id)
    if not box:
        return 0

    # Собираем все ID потомков
    affected_count = 0
    ids_to_delete = _collect_descendant_ids(session, box_id)
    ids_to_delete.append(box_id)

    # Обнуляем box_id у товаров
    items = session.query(Item).filter(Item.box_id.in_(ids_to_delete)).all()
    affected_count = len(items)
    for item in items:
        item.box_id = None

    # Удаляем контейнеры
    session.query(Box).filter(Box.box_id.in_(ids_to_delete)).delete(synchronize_session=False)
    session.commit()
    return affected_count


def _collect_descendant_ids(session: Session, parent_id: int) -> List[int]:
    result = []
    children = session.query(Box).filter(Box.parent_id == parent_id).all()
    for child in children:
        result.append(child.box_id)
        result.extend(_collect_descendant_ids(session, child.box_id))
    return result


def get_box_full_path(session: Session, box_id: Optional[int]) -> str:
    if box_id is None:
        return 'Без расположения'
    box = session.get(Box, box_id)
    if not box:
        return 'Без расположения'
    return box.full_path


# ===== ItemType =====
def get_all_item_types(session: Session) -> List[ItemType]:
    return session.query(ItemType).order_by(ItemType.item_type_name).all()


def add_item_type(session: Session, name: str, weight_g: Optional[int]) -> ItemType:
    it = ItemType(item_type_name=name, weight_g=weight_g)
    session.add(it)
    session.commit()
    session.refresh(it)
    return it


def update_item_type(session: Session, item_type_id: int, name: str, weight_g: Optional[int]) -> None:
    it = session.get(ItemType, item_type_id)
    if it:
        it.item_type_name = name
        it.weight_g = weight_g
        session.commit()


def delete_item_type(session: Session, item_type_id: int) -> None:
    it = session.get(ItemType, item_type_id)
    if it:
        session.delete(it)
        session.commit()


# ===== Item =====
def get_all_items(session: Session) -> List[Item]:
    return session.query(Item).options(
        joinedload(Item.item_type),
        joinedload(Item.box).joinedload(Box.box_type)
    ).all()


def get_items_by_box(session: Session, box_id: int, include_children: bool = True) -> List[Item]:
    if not include_children:
        return session.query(Item).filter(Item.box_id == box_id).options(
            joinedload(Item.item_type),
            joinedload(Item.box).joinedload(Box.box_type)
        ).all()

    ids = [box_id] + _collect_descendant_ids(session, box_id)
    return session.query(Item).filter(Item.box_id.in_(ids)).options(
        joinedload(Item.item_type),
        joinedload(Item.box).joinedload(Box.box_type)
    ).all()


def get_items_without_box(session: Session) -> List[Item]:
    return session.query(Item).filter(Item.box_id.is_(None)).options(
        joinedload(Item.item_type),
        joinedload(Item.box).joinedload(Box.box_type)
    ).all()


def add_item(session: Session, item_type_id: int, box_id: Optional[int], quantity: int) -> Item:
    item = Item(item_type_id=item_type_id, box_id=box_id, quantity=quantity)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def update_item(session: Session, item_id: int, item_type_id: int, box_id: Optional[int], quantity: int) -> None:
    item = session.get(Item, item_id)
    if item:
        item.item_type_id = item_type_id
        item.box_id = box_id
        item.quantity = quantity
        session.commit()


def delete_item(session: Session, item_id: int) -> None:
    item = session.get(Item, item_id)
    if item:
        session.delete(item)
        session.commit()


def search_items(session: Session, query: str) -> List[Item]:
    """Поиск по названию типа товара и расположению."""
    q = f'%{query.lower()}%'
    items = session.query(Item).options(
        joinedload(Item.item_type),
        joinedload(Item.box).joinedload(Box.box_type)
    ).all()

    result = []
    for item in items:
        type_name = item.item_type.item_type_name.lower() if item.item_type else ''
        location = get_box_full_path(session, item.box_id).lower()
        if q.strip('%') in type_name or q.strip('%') in location:
            result.append(item)
    return result
