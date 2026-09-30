import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_db


router = APIRouter(
    prefix="/boxes",
    tags=["Boxes"]
)


class BoxCreate(BaseModel):
    name: str
    box_type_id: int
    parent_id: int | None = None


class BoxUpdate(BaseModel):
    name: str | None = None
    box_type_id: int | None = None


class BoxMove(BaseModel):
    parent_id: int | None = None


@router.get("")
def get_boxes():
    with get_db() as db:
        rows = db.execute(
            """
            SELECT
                b.box_id,
                b.box_name,
                b.box_type_id,
                bt.box_type_name,
                b.parent_id
            FROM box b
            JOIN box_type bt ON bt.box_type_id = b.box_type_id
            ORDER BY b.box_id
            """
        ).fetchall()

    return [
        {
            "id": row["box_id"],
            "name": row["box_name"],
            "box_type_id": row["box_type_id"],
            "box_type_name": row["box_type_name"],
            "parent_id": row["parent_id"]
        }
        for row in rows
    ]


BOX_TREE_SELECT = """
SELECT
    b.box_id,
    b.box_name,
    b.box_type_id,
    bt.box_type_name,
    b.parent_id
FROM box b
JOIN box_type bt ON bt.box_type_id = b.box_type_id
"""


def get_box_or_404(db, box_id: int):
    row = db.execute(
        BOX_TREE_SELECT + " WHERE b.box_id = ?",
        (box_id,)
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Box not found"
        )

    return row


# ВАЖНО: маршрут /tree должен быть объявлен до /{box_id},
# иначе "tree" будет воспринят как box_id.
@router.get("/tree")
def get_box_tree():
    with get_db() as db:
        rows = db.execute(
            BOX_TREE_SELECT + " ORDER BY b.box_id"
        ).fetchall()

    nodes = {
        row["box_id"]: {
            "id": row["box_id"],
            "name": row["box_name"],
            "box_type_id": row["box_type_id"],
            "box_type_name": row["box_type_name"],
            "parent_id": row["parent_id"],
            "children": []
        }
        for row in rows
    }

    roots = []

    for node in nodes.values():
        parent = nodes.get(node["parent_id"])

        if parent is not None:
            parent["children"].append(node)
        else:
            roots.append(node)

    return roots


@router.get("/{box_id}")
def get_box(box_id: int):
    with get_db() as db:
        row = db.execute(
            """
            SELECT
                b.box_id,
                b.box_name,
                b.box_type_id,
                bt.box_type_name,
                b.parent_id
            FROM box b
            JOIN box_type bt ON bt.box_type_id = b.box_type_id
            WHERE b.box_id = ?
            """,
            (box_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Box not found"
        )

    return {
        "id": row["box_id"],
        "name": row["box_name"],
        "box_type_id": row["box_type_id"],
        "box_type_name": row["box_type_name"],
        "parent_id": row["parent_id"]
    }


@router.post("")
def create_box(box: BoxCreate):
    try:
        with get_db() as db:

            # Проверяем существование типа коробки
            type_exists = db.execute(
                """
                SELECT 1
                FROM box_type
                WHERE box_type_id = ?
                """,
                (box.box_type_id,)
            ).fetchone()

            if type_exists is None:
                raise HTTPException(
                    status_code=404,
                    detail="Box type not found"
                )

            # Если указана родительская коробка,
            # проверяем её существование
            if box.parent_id is not None:
                parent_exists = db.execute(
                    """
                    SELECT 1
                    FROM box
                    WHERE box_id = ?
                    """,
                    (box.parent_id,)
                ).fetchone()

                if parent_exists is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Parent box not found"
                    )

            cursor = db.execute(
                """
                INSERT INTO box (
                    box_name,
                    box_type_id,
                    parent_id
                )
                VALUES (?, ?, ?)
                """,
                (
                    box.name,
                    box.box_type_id,
                    box.parent_id
                )
            )

            box_id = cursor.lastrowid

    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    return {
        "id": box_id,
        "name": box.name,
        "box_type_id": box.box_type_id,
        "parent_id": box.parent_id
    }


@router.delete("/{box_id}")
def delete_box(box_id: int):
    with get_db() as db:
        cursor = db.execute(
            """
            DELETE FROM box
            WHERE box_id = ?
            """,
            (box_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Box not found"
            )

    return {
        "message": "Box deleted"
    }


@router.get("/{box_id}/children")
def get_box_children(box_id: int):
    with get_db() as db:
        get_box_or_404(db, box_id)

        rows = db.execute(
            BOX_TREE_SELECT + " WHERE b.parent_id = ? ORDER BY b.box_id",
            (box_id,)
        ).fetchall()

    return [
        {
            "id": row["box_id"],
            "name": row["box_name"],
            "box_type_id": row["box_type_id"],
            "box_type_name": row["box_type_name"],
            "parent_id": row["parent_id"]
        }
        for row in rows
    ]


@router.get("/{box_id}/contents")
def get_box_contents(box_id: int):
    with get_db() as db:
        get_box_or_404(db, box_id)

        items = db.execute(
            """
            SELECT
                i.item_id,
                i.item_type_id,
                it.item_type_name,
                it.weight_g,
                i.quantity
            FROM item i
            JOIN item_type it ON it.item_type_id = i.item_type_id
            WHERE i.box_id = ?
            ORDER BY i.item_id
            """,
            (box_id,)
        ).fetchall()

        children = db.execute(
            """
            SELECT
                b.box_id,
                b.box_name,
                b.box_type_id,
                bt.box_type_name
            FROM box b
            JOIN box_type bt ON bt.box_type_id = b.box_type_id
            WHERE b.parent_id = ?
            ORDER BY b.box_id
            """,
            (box_id,)
        ).fetchall()

    return {
        "box_id": box_id,
        "items": [
            {
                "item_id": row["item_id"],
                "item_type_id": row["item_type_id"],
                "item_type_name": row["item_type_name"],
                "weight_g": row["weight_g"],
                "quantity": row["quantity"],
                "total_weight_g": (
                    row["quantity"] * row["weight_g"]
                    if row["weight_g"] is not None
                    else None
                )
            }
            for row in items
        ],
        "child_boxes": [
            {
                "id": row["box_id"],
                "name": row["box_name"],
                "box_type_id": row["box_type_id"],
                "box_type_name": row["box_type_name"]
            }
            for row in children
        ]
    }


@router.patch("/{box_id}")
def update_box(box_id: int, update: BoxUpdate):
    if update.name is None and update.box_type_id is None:
        raise HTTPException(
            status_code=400,
            detail="Nothing to update: provide name and/or box_type_id"
        )

    try:
        with get_db() as db:
            current = get_box_or_404(db, box_id)

            new_name = (
                update.name
                if update.name is not None
                else current["box_name"]
            )

            new_type_id = (
                update.box_type_id
                if update.box_type_id is not None
                else current["box_type_id"]
            )

            if update.box_type_id is not None:
                type_exists = db.execute(
                    "SELECT 1 FROM box_type WHERE box_type_id = ?",
                    (update.box_type_id,)
                ).fetchone()

                if type_exists is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Box type not found"
                    )

            cursor = db.execute(
                """
                UPDATE box
                SET box_name = ?,
                    box_type_id = ?
                WHERE box_id = ?
                """,
                (new_name, new_type_id, box_id)
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Box not found"
                )

    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    return get_box(box_id)


@router.post("/{box_id}/move")
def move_box(box_id: int, move: BoxMove):
    try:
        with get_db() as db:
            get_box_or_404(db, box_id)

            if move.parent_id is not None:
                get_box_or_404(db, move.parent_id)

            # Проверка циклов: нельзя переместить коробку
            # в саму себя или в одного из своих потомков.
            if move.parent_id == box_id:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot move a box into itself"
                )

            descendant = db.execute(
                """
                WITH RECURSIVE subtree(id) AS (
                    SELECT box_id
                    FROM box
                    WHERE box_id = ?

                    UNION ALL

                    SELECT b.box_id
                    FROM box b
                    JOIN subtree s ON b.parent_id = s.id
                )
                SELECT 1
                FROM subtree
                WHERE id = ?
                LIMIT 1
                """,
                (box_id, move.parent_id)
            ).fetchone()

            if move.parent_id is not None and descendant is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot move a box into its own descendant"
                )

            db.execute(
                "UPDATE box SET parent_id = ? WHERE box_id = ?",
                (move.parent_id, box_id)
            )

    except sqlite3.IntegrityError as error:
        # Здесь срабатывает триггер trg_box_no_cycle
        # и ограничение UNIQUE(parent_id, box_name).
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    return get_box(box_id)
