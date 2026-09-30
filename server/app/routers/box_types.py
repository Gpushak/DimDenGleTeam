import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_db


router = APIRouter(
    prefix="/box-types",
    tags=["Box types"]
)


class BoxTypeCreate(BaseModel):
    name: str


@router.get("")
def get_box_types():
    with get_db() as db:
        rows = db.execute(
            """
            SELECT box_type_id, box_type_name
            FROM box_type
            ORDER BY box_type_id
            """
        ).fetchall()

    return [
        {
            "id": row["box_type_id"],
            "name": row["box_type_name"]
        }
        for row in rows
    ]


@router.get("/{box_type_id}")
def get_box_type(box_type_id: int):
    with get_db() as db:
        row = db.execute(
            """
            SELECT box_type_id, box_type_name
            FROM box_type
            WHERE box_type_id = ?
            """,
            (box_type_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Box type not found"
        )

    return {
        "id": row["box_type_id"],
        "name": row["box_type_name"]
    }


@router.post("")
def create_box_type(box_type: BoxTypeCreate):
    try:
        with get_db() as db:
            cursor = db.execute(
                """
                INSERT INTO box_type (box_type_name)
                VALUES (?)
                """,
                (box_type.name,)
            )

            box_type_id = cursor.lastrowid

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    return {
        "id": box_type_id,
        "name": box_type.name
    }


@router.delete("/{box_type_id}")
def delete_box_type(box_type_id: int):
    try:
        with get_db() as db:
            cursor = db.execute(
                """
                DELETE FROM box_type
                WHERE box_type_id = ?
                """,
                (box_type_id,)
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Box type not found"
                )

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Box type is used by a box"
        )

    return {
        "message": "Box type deleted"
    }