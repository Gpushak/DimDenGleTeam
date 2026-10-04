from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import db_session, DB_PATH
from app.migrations import apply_schema, get_version, SCHEMA_VERSION
from app.routers.box_types import router as box_types_router
from app.routers.item_types import router as item_types_router
from app.routers.boxes import router as boxes_router
from app.routers.items import router as items_router
from app.routers.scale import router as scale_router
from app.routers.lookup import router as lookup_router
from app.seed import seed_demo_data


BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"


def init_db() -> None:
    """Создаёт/обновляет схему БД и наполняет её демо-данными при первом запуске.

    Идемпотентна: схема применяется только к пустой базе, а существующая
    обновляется через миграции (app/migrations.py). Демо-данные добавляются
    только в базу, где ещё нет ни одного типа коробки.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with db_session() as db:
        apply_schema(db, SCHEMA_PATH.read_text(encoding="utf-8"))

        empty = db.execute("SELECT COUNT(*) AS n FROM box_type").fetchone()["n"] == 0
        if empty:
            seed_demo_data(db)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Инициализация БД выполняется при старте приложения, а не при импорте
    # модуля: иначе uvicorn --reload пересоздавал бы БД на каждое
    # изменении файла, а любой тестовый импорт запускал бы побочный эффект.
    init_db()
    yield


app = FastAPI(
    title="Warehouse Management API",
    description="Backend для АСУ складского учёта. Один источник данных для десктопа, Android и весового модуля.",
    version="0.2.0",
    lifespan=lifespan,
)

# Сервер работает без аутентификации и обслуживает мобильный клиент и
# десктоп из локальной сети, поэтому CORS открыт для любых источников.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(box_types_router)
app.include_router(item_types_router)
app.include_router(boxes_router)
app.include_router(items_router)
app.include_router(scale_router)
app.include_router(lookup_router)


@app.get("/")
def root():
    return {
        "message": "Warehouse API is running",
        "qr": "qwentory:item:<id> | qwentory:type:<id> | qwentory:box:<id>",
        "scale": "GET/POST /scale, serial line WEIGHT:<grams>",
    }


@app.get("/health")
def health():
    with db_session() as db:
        db.execute("SELECT 1")
        schema_version = get_version(db)

    return {
        "status": "ok",
        "database": "ok",
        "database_path": str(DB_PATH),
        "schema_version": schema_version,
        "schema_version_expected": SCHEMA_VERSION,
    }
