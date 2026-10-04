from fastapi import APIRouter, HTTPException

from app.database import db_session
from app.protocol import parse_qr_payload
from app.routers.boxes import BOX_SELECT, _row_to_dict, get_box_contents_payload
from app.routers.item_types import ITEM_TYPE_SELECT_BY_ID
from app.routers.items import ITEM_SELECT, item_row_to_dict


router = APIRouter(tags=["Lookup"])


@router.get("/lookup")
def lookup(code: str):
    parsed = parse_qr_payload(code)
    if parsed is None:
        raise HTTPException(
            status_code=400,
            detail="QR must look like qwentory:item:<id>, qwentory:type:<id> or qwentory:box:<id>",
        )

    kind, entity_id = parsed

    # Один endpoint — одно соединение с БД: сущность и (для коробки) её
    # содержимое читаются в рамках одной сессии, а не в нескольких.
    with db_session() as db:
        if kind == "item":
            row = db.execute(
                ITEM_SELECT + " WHERE i.item_id = ?",
                (entity_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Item not found")
            return {"kind": "item", "item": item_row_to_dict(row)}

        if kind == "type":
            row = db.execute(ITEM_TYPE_SELECT_BY_ID, (entity_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Item type not found")
            return {
                "kind": "type",
                "item_type": {
                    "id": row["item_type_id"],
                    "name": row["item_type_name"],
                    "weight_g": row["weight_g"],
                },
            }

        box_row = db.execute(
            BOX_SELECT + " WHERE b.box_id = ?",
            (entity_id,),
        ).fetchone()
        if box_row is None:
            raise HTTPException(status_code=404, detail="Box not found")
        return {
            "kind": "box",
            "box": _row_to_dict(box_row),
            "contents": get_box_contents_payload(db, entity_id),
        }
