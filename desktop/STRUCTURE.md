# Структура Python-проекта

## Файлы

```
python_app/
├── main.py              # Точка входа
├── models.py            # SQLAlchemy модели (BoxType, Box, ItemType, Item)
├── database.py          # Инициализация БД, сессии, демо-данные
├── crud.py              # CRUD операции для всех сущностей
├── ui/
│   ├── __init__.py
│   ├── main_window.py   # Главное окно с деревом и таблицей
│   └── dialogs.py       # Модальные диалоги (BoxDialog, ItemTypeDialog, ItemDialog)
├── requirements.txt     # SQLAlchemy>=2.0
└── README.md            # Документация
```

## Запуск

```bash
cd python_app
pip install -r requirements.txt
python main.py
```

При первом запуске создаётся `warehouse.db` с демо-данными.

## Технологии

- **customtkinter** — современный GUI с тёмной темой
- **SQLAlchemy 2.0+** — ORM для работы с БД
- **SQLite** — встроенная база данных

## Схема БД

Соответствует требованиям:
- `box_type` (box_type_id, box_type_name)
- `box` (box_id, box_name, box_type_id FK, parent_id FK self)
- `item_type` (item_type_id, item_type_name, weight_g)
- `item` (item_id, item_type_id FK, box_id FK nullable, quantity, date)

## Функциональность

✓ CRUD для контейнеров (дерево с иерархией)
✓ CRUD для типов товаров
✓ CRUD для товаров
✓ Поиск по типу и расположению
✓ При удалении контейнера товары остаются с box_id=NULL
✓ Разделы "Все товары" и "Без расположения"
✓ Демо-данные при первом запуске
