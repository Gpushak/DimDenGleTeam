"""Соединения с БД должны закрываться, в том числе при исключениях.

Контекст-менеджер `sqlite3.Connection` управляет ТРАНЗАКЦИЕЙ (коммит/откат),
но не закрывает соединение. В простом (безошибочном) сценарии это не заметно:
CPython освобождает объект по счётчику ссылок. Настоящая проблема возникает при
исключениях — живой трейсбек удерживает фрейк, а вместе с ним и соединение
(вместе с файловым дескриптором), и оно живёт дольше, чем нужно.

`db_session()` закрывает соединение в `finally`, поэтому число действительно
ОТКРЫТЫХ соединений не растёт по мере выполнения операций.

Важно: считаем только открытые соединения. Закрытый, но ещё не собранный
объект `sqlite3.Connection` продолжает существовать, пока на него держит ссылку
(например, трейсбек), поэтому простое «сколько объектов Connection» даёт ложные
срабатывания. Открытость проверяем попыткой выполнить запрос.
"""
import gc
import sqlite3

from app import database


def _open_connection_count() -> int:
    """Сколько соединений СУЩЕСТВЕННО открыто (пригодно к работе)."""
    gc.collect()
    count = 0
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            try:
                obj.execute("SELECT 1")
            except sqlite3.ProgrammingError:
                continue  # закрыто — не считаем
            except sqlite3.Error:
                count += 1
            else:
                count += 1
    return count


def test_connections_do_not_grow_on_success(tmp_path, monkeypatch):
    db_path = tmp_path / "ok.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(database, "DB_DIR", db_path.parent)

    for _ in range(5):  # прогрев
        with database.db_session() as db:
            db.execute("SELECT 1")

    before = _open_connection_count()
    for _ in range(60):
        with database.db_session() as db:
            db.execute("SELECT 1")
    after = _open_connection_count()

    assert after <= before, (
        f"открытые соединения накапливаются: было {before}, стало {after} "
        f"после 60 операций"
    )


def test_connections_do_not_grow_on_error(tmp_path, monkeypatch):
    db_path = tmp_path / "errors.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(database, "DB_DIR", db_path.parent)

    def boom():
        with database.db_session() as db:
            db.execute("SELECT 1")
            raise ValueError("имитация сбоя обработчика")

    for _ in range(5):  # прогрев
        try:
            boom()
        except ValueError:
            pass
    before = _open_connection_count()

    # Теперь держим трейсбеки живыми — как это делает логгер/очередь задач.
    held = []
    for _ in range(60):
        try:
            boom()
        except ValueError as exc:
            held.append(exc)

    after = _open_connection_count()

    assert after <= before, (
        f"ошибки приводят к утечке открытых соединений: было {before}, стало "
        f"{after} после 60 удерживаемых трейсбеков"
    )
