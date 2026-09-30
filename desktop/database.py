"""Инициализация базы данных и управление сессиями."""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models import Base, BoxType, Box, ItemType, Item

DB_PATH = Path(__file__).parent / 'warehouse.db'
DATABASE_URL = f'sqlite:///{DB_PATH}'

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Создать таблицы и заполнить демо-данными при первом запуске."""
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        # Если база пуста — заполняем демо-данными
        if session.query(BoxType).count() == 0:
            _seed_demo_data(session)
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Session:
    """Получить новую сессию."""
    return SessionLocal()


def _seed_demo_data(session: Session) -> None:
    """Заполнить БД демо-данными."""
    # Box types
    bt_warehouse = BoxType(box_type_name='Склад')
    bt_rack = BoxType(box_type_name='Стеллаж')
    bt_shelf = BoxType(box_type_name='Полка')
    bt_cell = BoxType(box_type_name='Ячейка')
    bt_zone = BoxType(box_type_name='Зона')
    bt_room = BoxType(box_type_name='Помещение')
    bt_container = BoxType(box_type_name='Контейнер')
    bt_box = BoxType(box_type_name='Коробка')

    session.add_all([bt_warehouse, bt_rack, bt_shelf, bt_cell, bt_zone, bt_room, bt_container, bt_box])
    session.flush()

    # Boxes (hierarchy)
    main_warehouse = Box(box_name='Основной склад', box_type_id=bt_warehouse.box_type_id)
    fuel_warehouse = Box(box_name='Склад ГСМ', box_type_id=bt_warehouse.box_type_id)
    session.add_all([main_warehouse, fuel_warehouse])
    session.flush()

    rack_a = Box(box_name='Стеллаж A', box_type_id=bt_rack.box_type_id, parent_id=main_warehouse.box_id)
    rack_b = Box(box_name='Стеллаж B', box_type_id=bt_rack.box_type_id, parent_id=main_warehouse.box_id)
    session.add_all([rack_a, rack_b])
    session.flush()

    shelf_a1 = Box(box_name='Полка 1', box_type_id=bt_shelf.box_type_id, parent_id=rack_a.box_id)
    shelf_a2 = Box(box_name='Полка 2', box_type_id=bt_shelf.box_type_id, parent_id=rack_a.box_id)
    shelf_b1 = Box(box_name='Полка 1', box_type_id=bt_shelf.box_type_id, parent_id=rack_b.box_id)
    session.add_all([shelf_a1, shelf_a2, shelf_b1])
    session.flush()

    cell_a1_1 = Box(box_name='Ячейка A1-1', box_type_id=bt_cell.box_type_id, parent_id=shelf_a1.box_id)
    cell_a1_2 = Box(box_name='Ячейка A1-2', box_type_id=bt_cell.box_type_id, parent_id=shelf_a1.box_id)
    cell_a2_1 = Box(box_name='Ячейка A2-1', box_type_id=bt_cell.box_type_id, parent_id=shelf_a2.box_id)
    session.add_all([cell_a1_1, cell_a1_2, cell_a2_1])
    session.flush()

    # Item types
    it_bolt = ItemType(item_type_name='Болт M10x50', weight_g=45)
    it_nut = ItemType(item_type_name='Гайка M10', weight_g=12)
    it_washer = ItemType(item_type_name='Шайба 10мм', weight_g=5)
    it_paint = ItemType(item_type_name='Краска белая', weight_g=1200)
    it_brush = ItemType(item_type_name='Кисть малярная', weight_g=150)
    it_oil = ItemType(item_type_name='Масло моторное 5W-30', weight_g=1000)
    it_antifreeze = ItemType(item_type_name='Антифриз', weight_g=1100)
    it_screw = ItemType(item_type_name='Винт M8x30', weight_g=18)
    session.add_all([it_bolt, it_nut, it_washer, it_paint, it_brush, it_oil, it_antifreeze, it_screw])
    session.flush()

    # Items
    items = [
        Item(item_type_id=it_bolt.item_type_id, box_id=cell_a1_1.box_id, quantity=500),
        Item(item_type_id=it_nut.item_type_id, box_id=cell_a1_1.box_id, quantity=300),
        Item(item_type_id=it_washer.item_type_id, box_id=cell_a1_2.box_id, quantity=1000),
        Item(item_type_id=it_paint.item_type_id, box_id=cell_a2_1.box_id, quantity=25),
        Item(item_type_id=it_brush.item_type_id, box_id=shelf_b1.box_id, quantity=50),
        Item(item_type_id=it_oil.item_type_id, box_id=None, quantity=10),
        Item(item_type_id=it_antifreeze.item_type_id, box_id=None, quantity=15),
        Item(item_type_id=it_screw.item_type_id, box_id=cell_a1_1.box_id, quantity=200),
    ]
    session.add_all(items)
