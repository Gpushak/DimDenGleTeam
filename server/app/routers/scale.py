from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.protocol import parse_weight_line


router = APIRouter(prefix="/scale", tags=["Scale"])

#: Последнее показание весов. Хранится в памяти, а не в БД: это текущее
#: состояние, а не история взвешиваний.
#:
#: Синхронные обработчики FastAPI выполняются в пуле потоков, поэтому
#: обращение к общему состоянию защищено блокировкой.
_latest: dict | None = None
_lock = Lock()


class ScaleReading(BaseModel):
    weight_g: float | None = None
    line: str | None = None


class ScaleState(BaseModel):
    weight_g: float | None = None
    updated_at: datetime | None = None
    source: str = "none"


@router.get("", response_model=ScaleState)
def get_scale():
    with _lock:
        latest = _latest
    return ScaleState(**latest) if latest else ScaleState()


@router.post("", response_model=ScaleState)
def post_scale(reading: ScaleReading):
    # Приоритет у явного weight_g; иначе пытаемся разобрать строку Serial.
    weight = reading.weight_g
    if weight is None and reading.line:
        weight = parse_weight_line(reading.line)

    if weight is None:
        raise HTTPException(
            status_code=400,
            detail="Provide weight_g or a parseable serial line",
        )

    state = {
        "weight_g": float(weight),
        "updated_at": datetime.now(timezone.utc),
        # Источник «serial» означает, что вес пришёл строкой от Arduino,
        # а не прямым числом от клиента.
        "source": "serial" if reading.line else "api",
    }
    with _lock:
        global _latest
        _latest = state

    return ScaleState(**state)


@router.delete("")
def clear_scale():
    global _latest
    with _lock:
        _latest = None
    return {"message": "Scale reading cleared"}
