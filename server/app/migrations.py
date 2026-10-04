"""Схема БД и её миграции.

Схема хранится в `db/schema.sql` и применяется только к ПУСТОЙ базе — это
базовая версия `SCHEMA_VERSION`. Дальнейшие изменения схемы оформляются как
миграции в `MIGRATIONS`: словарь {версия_до: [SQL-выражения]}, где ключ —
текущая версия базы, а список — шаги, которые применяются последовательно,
после чего версия увеличивается на 1.

Текущая версия базы хранится в `PRAGMA user_version`, что позволяет применять
миграции к уже существующей БД, а не пересоздавать её.
"""
from __future__ import annotations

import sqlite3

#: Версия схемы, создаваемой из db/schema.sql.
SCHEMA_VERSION = 1

#: Миграции: {версия_до -> [шаги SQL]}. Пустой словарь означает, что изменений
#: после базовой схемы ещё не было. Каждый список применяется в одной транзакции.
MIGRATIONS: dict[int, list[str]] = {}


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def is_initialized(db: sqlite3.Connection) -> bool:
    """Есть ли в базе таблицы проекта (то есть она не совсем пустая)."""
    return _table_exists(db, "box_type")


def get_version(db: sqlite3.Connection) -> int:
    row = db.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row is not None else 0


def _apply_base_schema(db: sqlite3.Connection, schema_sql: str) -> None:
    db.executescript(schema_sql)


def apply_schema(db: sqlite3.Connection, schema_sql: str) -> None:
    """Готовит базу к работе: создаёт схему (если пустая) и применяет миграции.

    Идемпотентна — безопасно вызывать при каждом старте приложения.
    """
    if not is_initialized(db):
        _apply_base_schema(db, schema_sql)
        db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        return

    version = get_version(db)

    # База могла быть создана прошлой версией кода, где user_version не
    # выставлялся. Считаем её базовой и сразу проставляем версию.
    if version == 0:
        db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        return

    while version < SCHEMA_VERSION:
        steps = MIGRATIONS.get(version, [])
        for step in steps:
            db.execute(step)
        version += 1
        db.execute(f"PRAGMA user_version = {version}")
