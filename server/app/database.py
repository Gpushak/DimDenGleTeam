import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


BASE_DIR = Path(__file__).resolve().parent.parent

# Путь к БД можно переопределить переменной окружения WAREHOUSE_DB
# (используется docker-compose для монтирования volume с данными).
DB_PATH = Path(os.getenv("WAREHOUSE_DB", str(BASE_DIR / "data" / "warehouse.db")))
DB_DIR = DB_PATH.parent


def get_db() -> sqlite3.Connection:
    """Открывает новое соединение с БД.

    Вызывающий обязан сам закрыть соединение — проще всего через
    `db_session()` ниже. Оставлено публичным для тех мест, где нужно
    удерживать соединение дольше одной операции (миграции).
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """Соединение с БД на время операции: коммит при успехе, откат при ошибке,
    закрытие — в любом случае.

    Почему не `with get_db() as db:`: контекст-менеджер самого `sqlite3.Connection`
    управляет ТРАНЗАКЦИЕЙ (коммит/откат), но не ЗАКРЫВАЕТ соединение. Закрытие
    тогда происходит лишь потому, что CPython освобождает объект по счётчику
    ссылок — а при исключении живой трейсбек удерживает фрейк вместе с
    соединением (логгер, очередь задач, обработчик ошибок), и соединение
    вместе с файловым дескриптором живёт дольше, чем нужно. Здесь соединение
    закрывается в `finally` явно, независимо от сценария.
    """
    connection = get_db()
    try:
        yield connection
    except BaseException:
        connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        connection.close()
