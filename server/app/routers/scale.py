import math
from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.protocol import parse_weight_line


router = APIRouter(prefix="/scale", tags=["Scale"])

#: Сколько секунд показание считается «свежим». Клиент может ориентироваться на
#: поле `stale` в ответе, чтобы не принять старое значение за текущее.
FRESH_TTL_SECONDS = 5.0

#: Последнее показание весов. Хранится в памяти, а не в БД: это текущее
#: состояние, а не история взвешиваний.
#:
#: Синхронные обработчики FastAPI выполняются в пуле потоков, поэтому
#: обращение к общему состоянию защищено блокировкой.
#:
#: ОГРАНИЧЕНИЕ (осознанное): состояние живёт в памяти одного процесса, поэтому
#: (а) теряется при перезапуске и (а) рассыпается при нескольких воркерах
#: uvicorn (`--workers N > 1`). Поэтому в docker-compose сервис запускается
#: одним воркером. Если понадобится несколько — состояние надо вынести в
#: Redis/БД (это отдельная задача, не часть прототипа).
_latest: dict | None = None
_lock = Lock()


class ScaleReading(BaseModel):
    weight_g: float | None = None
    line: str | None = None


class ScaleState(BaseModel):
    weight_g: float | None = None
    updated_at: datetime | None = None
    source: str = "none"
    stale: bool = True


def _to_state(latest: dict | None) -> ScaleState:
    if not latest:
        return ScaleState()

    updated_at = latest["updated_at"]
    age = (datetime.now(timezone.utc) - updated_at).total_seconds()
    return ScaleState(
        weight_g=latest["weight_g"],
        updated_at=updated_at,
        source=latest["source"],
        stale=age > FRESH_TTL_SECONDS,
    )


@router.get("", response_model=ScaleState)
def get_scale():
    with _lock:
        latest = _latest
    return _to_state(latest)


@router.post("", response_model=ScaleState)
def post_scale(reading: ScaleReading):
    global _latest

    # Приоритет у явного weight_g; иначе пытаемся разобрать строку Serial.
    weight = reading.weight_g
    if weight is None and reading.line:
        weight = parse_weight_line(reading.line)

    if weight is None:
        raise HTTPException(
            status_code=400,
            detail="Provide weight_g or a parseable serial line",
        )

    # Нефизичные значения (NaN/±Inf) отбрасываем: они не проходят проверки
    # формата ни в одном клиенте и только засоряют состояние.
    if not math.isfinite(weight):
        raise HTTPException(
            status_code=400,
            detail="weight_g must be a finite number",
        )

    state = {
        "weight_g": float(weight),
        "updated_at": datetime.now(timezone.utc),
        # Источник «serial» означает, что вес пришёл строкой от Arduino,
        # а не прямым числом от клиента.
        "source": "serial" if reading.line else "api",
    }
    with _lock:
        _latest = state

    return _to_state(state)


@router.delete("")
def clear_scale():
    global _latest
    with _lock:
        _latest = None
    return {"message": "Scale reading cleared"}
