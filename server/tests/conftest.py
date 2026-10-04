"""Общие фикстуры тестов сервера.

Каждый тест получает СВОЮ временную БД: путь подменяется в модуле
`app.database` до вызова `init_db()`, поэтому состояние между тестами не течёт,
а демо-данные засеваются один раз на тест (как в реальном «первом запуске»).
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Корень папки server/ в sys.path — чтобы `import app...` работал без
# установки пакета и без PYTHONPATH.
SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import database
    from app.main import app, init_db

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(database, "DB_DIR", db_path.parent)

    init_db()

    with TestClient(app) as test_client:
        yield test_client
