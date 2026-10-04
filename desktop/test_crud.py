"""Тесты десктопного приложения без запуска графического оболочки.

Проверяется логика, а не виджеты: разбор путей контейнеров и фильтрация
товаров. Запуск (из корня репозитория):

    python -m unittest discover -s desktop -t desktop

Для тестов нужен только стандартный библиотечный unittest — mock-объект
подменяет сетевой клиент, поэтому API поднимать не нужно.
"""
import sys
import unittest
from pathlib import Path

# Модули десктопа (api_client, crud, models) лежат рядом с этим файлом
# и импортируются как верхнеуровневые, поэтому добавляем папку в sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crud import NO_LOCATION, BoxIndex, search_items  # noqa: E402
from models import Box, Item  # noqa: E402


def make_box(box_id: int, name: str, parent_id=None, type_id: int = 1) -> Box:
    return Box(
        box_id=box_id,
        box_name=name,
        box_type_id=type_id,
        parent_id=parent_id,
        box_type_name="Полка",
    )


def make_item(item_id: int, box_id, type_name: str, quantity: int = 1,
              weight_g: int = None) -> Item:
    return Item.from_api({
        "id": item_id,
        "item_type_id": 7,
        "box_id": box_id,
        "quantity": quantity,
        "weight_g": weight_g,
        "item_type_name": type_name,
        "total_weight_g": None if weight_g is None else weight_g * quantity,
    })


class FakeClient:
    """Минимальная заглушка ApiClient для одного эндпоинта."""

    def __init__(self, boxes=None, items=None):
        self._boxes = boxes or []
        self._items = items or []

    def get(self, path, params=None):
        if path == "/boxes":
            return [
                {"id": b.box_id, "name": b.box_name,
                 "box_type_id": b.box_type_id, "box_type_name": b.box_type_name,
                 "parent_id": b.parent_id}
                for b in self._boxes
            ]
        if path == "/items":
            return [
                {"id": i.item_id, "item_type_id": i.item_type_id,
                 "box_id": i.box_id, "quantity": i.quantity,
                 "weight_g": i.weight_g,
                 "item_type_name": i.item_type.item_type_name,
                 "total_weight_g": i.total_weight_g_from_api}
                for i in self._items
            ]
        raise AssertionError(f"неожиданный запрос: {path}")


class BoxIndexTest(unittest.TestCase):
    def setUp(self):
        self.boxes = [
            make_box(1, "Основной склад"),
            make_box(2, "Стеллаж A", parent_id=1),
            make_box(3, "Полка 1", parent_id=2),
            make_box(4, "Стеллаж B", parent_id=1),
            make_box(5, "Склад ГСМ"),
        ]
        self.index = BoxIndex(self.boxes)

    def test_links_parent_references(self):
        self.assertIs(self.index.get(2).parent, self.index.get(1))
        self.assertIsNone(self.index.get(1).parent)

    def test_full_path_of_nested_box(self):
        self.assertEqual(
            self.index.full_path(3),
            "Основной склад / Стеллаж A / Полка 1",
        )

    def test_full_path_of_root(self):
        self.assertEqual(self.index.full_path(1), "Основной склад")

    def test_full_path_of_missing_box(self):
        self.assertEqual(self.index.full_path(999), NO_LOCATION)

    def test_full_path_without_box(self):
        self.assertIsNone(self.index.get(None))
        self.assertEqual(self.index.full_path(None), NO_LOCATION)

    def test_children_of(self):
        self.assertEqual(
            sorted(b.box_id for b in self.index.children_of(1)),
            [2, 4],
        )

    def test_children_of_root_level(self):
        self.assertEqual(
            sorted(b.box_id for b in self.index.children_of(None)),
            [1, 5],
        )

    def test_children_of_leaf_is_empty(self):
        self.assertEqual(self.index.children_of(3), [])

    def test_cycle_does_not_hang(self):
        """Повреждённые данные (цикл) не должны подвешивать интерфейс."""
        cyclic = [make_box(1, "A", parent_id=2), make_box(2, "B", parent_id=1)]
        path = BoxIndex(cyclic).full_path(1)
        self.assertIn("A", path)
        self.assertIn("B", path)

    def test_load_parses_api_rows(self):
        index = BoxIndex.load(FakeClient(self.boxes))
        self.assertEqual(index.full_path(3), "Основной склад / Стеллаж A / Полка 1")


class SearchItemsTest(unittest.TestCase):
    def setUp(self):
        self.items = [
            make_item(1, 1, "Болт M10x50", quantity=500, weight_g=45),
            make_item(2, 3, "Краска белая", quantity=25, weight_g=1200),
            make_item(3, None, "Антифриз", quantity=15, weight_g=1100),
        ]
        self.index = BoxIndex([
            make_box(1, "Основной склад"),
            make_box(2, "Стеллаж A", parent_id=1),
            make_box(3, "Полка 1", parent_id=2),
        ])
        self.client = FakeClient(items=self.items)

    def test_matches_by_item_type(self):
        found = search_items(self.client, "болт", self.index)
        self.assertEqual([i.item_id for i in found], [1])

    def test_matches_by_location(self):
        found = search_items(self.client, "полка", self.index)
        self.assertEqual([i.item_id for i in found], [2])

    def test_matches_unlocated_item(self):
        found = search_items(self.client, "антифриз", self.index)
        self.assertEqual([i.item_id for i in found], [3])

    def test_is_case_insensitive(self):
        self.assertEqual(len(search_items(self.client, "БОЛТ", self.index)), 1)

    def test_empty_query_returns_nothing(self):
        self.assertEqual(search_items(self.client, "   ", self.index), [])

    def test_no_match_returns_empty(self):
        self.assertEqual(search_items(self.client, "несуществующее", self.index), [])


class ItemModelTest(unittest.TestCase):
    def test_total_weight_from_api(self):
        item = make_item(1, 1, "Болт", quantity=10, weight_g=5)
        self.assertEqual(item.total_weight_g, 50)

    def test_total_weight_zero_without_weight(self):
        item = make_item(1, 1, "Болт", quantity=10)
        self.assertEqual(item.total_weight_g, 0)

    def test_parses_contents_shape_with_item_id(self):
        """Содержимое контейнера отдаёт item_id, а /items — id."""
        item = Item.from_api({
            "item_id": 42,
            "item_type_id": 1,
            "quantity": 3,
            "weight_g": 10,
            "item_type_name": "Гайка",
            "total_weight_g": 30,
        })
        self.assertEqual(item.item_id, 42)
        self.assertEqual(item.total_weight_g, 30)
        self.assertEqual(item.item_type.item_type_name, "Гайка")

    def test_missing_item_type_name_falls_back(self):
        item = Item.from_api({
            "id": 1, "item_type_id": 1, "quantity": 1,
        })
        self.assertEqual(item.item_type.item_type_name, "—")


if __name__ == "__main__":
    unittest.main(verbosity=2)