"""SQLAlchemy модели для складского учёта."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, UniqueConstraint,
    CheckConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class BoxType(Base):
    """Тип контейнера (Склад, Стеллаж, Полка, Ячейка и т.д.)."""
    __tablename__ = 'box_type'

    box_type_id = Column(Integer, primary_key=True)
    box_type_name = Column(String, nullable=False, unique=True)

    boxes = relationship('Box', back_populates='box_type', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<BoxType {self.box_type_name!r}>'


class Box(Base):
    """Контейнер (коробка, стеллаж, полка и т.д.) с иерархией."""
    __tablename__ = 'box'

    box_id = Column(Integer, primary_key=True)
    box_name = Column(String, nullable=False)
    box_type_id = Column(Integer, ForeignKey('box_type.box_type_id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('box.box_id'), nullable=True)

    box_type = relationship('BoxType', back_populates='boxes')
    parent = relationship('Box', remote_side=[box_id], backref='children')
    items = relationship('Item', back_populates='box')

    def __repr__(self):
        return f'<Box {self.box_name!r}>'

    @property
    def full_path(self) -> str:
        """Полный путь контейнера через иерархию."""
        parts = []
        current = self
        visited = set()
        while current is not None:
            if current.box_id in visited:
                break
            visited.add(current.box_id)
            parts.append(current.box_name)
            current = current.parent
        return ' / '.join(reversed(parts))


class ItemType(Base):
    """Тип товара с весом."""
    __tablename__ = 'item_type'

    item_type_id = Column(Integer, primary_key=True)
    item_type_name = Column(String, nullable=False, unique=True)
    weight_g = Column(Integer, nullable=True)

    items = relationship('Item', back_populates='item_type', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ItemType {self.item_type_name!r}>'


class Item(Base):
    """Запись о товаре в контейнере."""
    __tablename__ = 'item'

    item_id = Column(Integer, primary_key=True)
    item_type_id = Column(Integer, ForeignKey('item_type.item_type_id'), nullable=False)
    box_id = Column(Integer, ForeignKey('box.box_id'), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('quantity >= 1', name='check_quantity_positive'),
    )

    item_type = relationship('ItemType', back_populates='items')
    box = relationship('Box', back_populates='items')

    def __repr__(self):
        return f'<Item {self.item_type_id} qty={self.quantity}>'

    @property
    def total_weight_g(self) -> int:
        """Общий вес записи (вес типа × количество)."""
        if self.item_type and self.item_type.weight_g:
            return self.item_type.weight_g * self.quantity
        return 0
