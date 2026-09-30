import os
from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent

# Путь к БД можно переопределить переменной окружения WAREHOUSE_DB
# (используется docker-compose для монтирования volume с данными).
DB_PATH = Path(os.getenv("WAREHOUSE_DB", str(BASE_DIR / "data" / "warehouse.db")))
DB_DIR = DB_PATH.parent


def get_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection