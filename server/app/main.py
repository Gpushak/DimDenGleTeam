from pathlib import Path

from fastapi import FastAPI

from app.database import get_db
from app.routers.box_types import router as box_types_router
from app.routers.item_types import router as item_types_router
from app.routers.boxes import router as boxes_router
from app.routers.items import router as items_router


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "warehouse.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"


app = FastAPI(
    title="Warehouse Management API",
    description="Backend для АСУ складского учёта",
    version="0.1.0",
)


def init_db():
    if DB_PATH.exists():
        return

    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_db() as db:
        db.executescript(schema)


init_db()

app.include_router(box_types_router)
app.include_router(item_types_router)
app.include_router(boxes_router)
app.include_router(items_router)


@app.get("/")
def root():
    return {
        "message": "Warehouse API is running"
    }


@app.get("/health")
def health():
    with get_db() as db:
        db.execute("SELECT 1")

    return {
        "status": "ok",
        "database": "ok"
    }