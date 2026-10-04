import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.database import db_session


router = APIRouter(
    prefix="/boxes",
    tags=["Boxes"]
)


class BoxCreate(BaseModel):
    name: str
    box_type_id: int
    parent_id: int | None = None


class BoxUpdate(BaseModel):
    # extra="forbid" — опечатка в поле даёт 422, а не молчаливый игнор.
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    box_type_id: int | None = None


class BoxMove(BaseModel):
    parent_id: int | None = None


BOX_SELECT = """
SELECT
    b.box_id,
    b.box_name,
    b.box_type_id,
    bt.box_type_name,
    b.parent_id
FROM box b
JOIN box_type bt ON bt.box_type_id = b.box_type_id
"""


def _row_to_dict(row) -> dict:
    """Единое представление контейнера для всех эндпоинтов."""
    return {
        "id": row["box_id"],
        "name": row["box_name"],
        "box_type_id": row["box_type_id"],
        "box_type_name": row["box_type_name"],
        "parent_id": row["parent_id"],
    }


def _fetch_box_row(db, box_id: int):
    return db.execute(
        BOX_SELECT + " WHERE b.box_id = ?",
        (box_id,),
    ).fetchone()


def get_box_or_404(db, box_id: int):
    """Загружает контейнер или выбрасывает 404. Используется и как сериализатор."""
    row = _fetch_box_row(db, box_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Box not found")

    return _row_to_dict(row)


def _ensure_box_type_exists(db, box_type_id: int) -> None:
    if db.execute(
        "SELECT 1 FROM box_type WHERE box_type_id = ?",
        (box_type_id,),
    ).fetchone() is None:
        raise HTTPException(status_code=404, detail="Box type not found")


@router.get("")
def get_boxes():
    with db_session() as db:
        rows = db.execute(BOX_SELECT + " ORDER BY b.box_id").fetchall()

    return [_row_to_dict(row) for row in rows]


# ВАЖНО: маршрут /tree должен быть объявлен до /{box_id},
# иначе "tree" будет воспринят как box_id.
@router.get("/tree")
def get_box_tree():
    with db_session() as db:
        rows = db.execute(BOX_SELECT + " ORDER BY b.box_id").fetchall()

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
    with db_session() as db:
        return get_box_or_404(db, box_id)


@router.post("")
def create_box(box: BoxCreate):
    try:
        with db_session() as db:
            # Тип контейнера должен существовать — иначе клиент узнает
            # об ошибке сразу, а не из сообщения про нарушение FK.
            _ensure_box_type_exists(db, box.box_type_id)

            # Если указана родительская коробка, проверяем её существование
            if box.parent_id is not None:
                get_box_or_404(db, box.parent_id)

            cursor = db.execute(
                """
                INSERT INTO box (box_name, box_type_id, parent_id)
                VALUES (?, ?, ?)
                """,
                (box.name, box.box_type_id, box.parent_id),
            )
            box_id = cursor.lastrowid
            assert box_id is not None, "INSERT в box не вернул идентификатор"

            # Возвращаем коробку в том же соединении — так не открывается
            # второе подключение (и не возникает read-your-writes гонки).
            result = get_box_or_404(db, box_id)

    except sqlite3.IntegrityError:
        # Нарушен UNIQUE(parent_id, box_name) / ux_box_root_name.
        raise HTTPException(
            status_code=409,
            detail="A box with this name already exists at the same level",
        )

    # Тот же формат, что и GET /boxes/{id} — в том числе box_type_name.
    return result


@router.delete("/{box_id}")
def delete_box(box_id: int):
    with db_session() as db:
        exists = db.execute(
            "SELECT 1 FROM box WHERE box_id = ?",
            (box_id,),
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="Box not found")

        subtree = db.execute(
            """
            WITH RECURSIVE subtree(id) AS (
                SELECT ?
                UNION ALL
                SELECT b.box_id FROM box b JOIN subtree s ON b.parent_id = s.id
            )
            SELECT id FROM subtree
            """,
            (box_id,),
        ).fetchall()
        box_ids = [row["id"] for row in subtree]
        placeholders = ",".join("?" * len(box_ids))

        items = db.execute(
            f"SELECT item_id, item_type_id, quantity FROM item WHERE box_id IN ({placeholders})",
            box_ids,
        ).fetchall()

        unboxed_count = 0
        for item in items:
            # Если такой тип уже лежит без коробки, сливаем количества,
            # иначе просто «вынимаем» предмет из удаляемой коробки.
            existing = db.execute(
                """
                SELECT item_id
                FROM item
                WHERE box_id IS NULL AND item_type_id = ?
                """,
                (item["item_type_id"],),
            ).fetchone()
            if existing is not None:
                db.execute(
                    "UPDATE item SET quantity = quantity + ? WHERE item_id = ?",
                    (item["quantity"], existing["item_id"]),
                )
                db.execute("DELETE FROM item WHERE item_id = ?", (item["item_id"],))
            else:
                db.execute(
                    "UPDATE item SET box_id = NULL WHERE item_id = ?",
                    (item["item_id"],),
                )
            unboxed_count += 1

        # ON DELETE CASCADE схемы удалит и вложенные коробки.
        db.execute("DELETE FROM box WHERE box_id = ?", (box_id,))

    return {
        "message": "Box deleted",
        "unboxed": unboxed_count,
    }


@router.get("/{box_id}/children")
def get_box_children(box_id: int):
    with db_session() as db:
        get_box_or_404(db, box_id)

        rows = db.execute(
            BOX_SELECT + " WHERE b.parent_id = ? ORDER BY b.box_id",
            (box_id,),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_box_contents_payload(db, box_id: int):
    """Содержимое коробки (предметы + вложенные коробки) по готовому соединению.

    Вынесено отдельно от эндпоинта, чтобы /lookup переиспользовал его в том же
    соединении, не открывая второе подключение."""
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


@router.get("/{box_id}/contents")
def get_box_contents(box_id: int):
    with db_session() as db:
        get_box_or_404(db, box_id)
        return get_box_contents_payload(db, box_id)


@router.patch("/{box_id}")
def update_box(box_id: int, update: BoxUpdate):
    # model_fields_set, а не `is None`: так «поле не передали» отличается от
    # «передали null» и PATCH ведёт себя предсказуемо.
    if not update.model_fields_set:
        raise HTTPException(
            status_code=400,
            detail="Nothing to update: provide name and/or box_type_id"
        )

    try:
        with db_session() as db:
            current = get_box_or_404(db, box_id)

            new_name = (
                update.name
                if "name" in update.model_fields_set and update.name is not None
                else current["name"]
            )

            new_type_id = (
                update.box_type_id
                if "box_type_id" in update.model_fields_set and update.box_type_id is not None
                else current["box_type_id"]
            )

            if (
                "box_type_id" in update.model_fields_set
                and update.box_type_id is not None
            ):
                _ensure_box_type_exists(db, update.box_type_id)

            db.execute(
                """
                UPDATE box
                SET box_name = ?,
                    box_type_id = ?
                WHERE box_id = ?
                """,
                (new_name, new_type_id, box_id)
            )

            result = get_box_or_404(db, box_id)

    except sqlite3.IntegrityError:
        # Нарушен UNIQUE(parent_id, box_name) / ux_box_root_name.
        raise HTTPException(
            status_code=409,
            detail="A box with this name already exists at the same level",
        )

    return result


@router.post("/{box_id}/move")
def move_box(box_id: int, move: BoxMove):
    try:
        with db_session() as db:
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

                if descendant is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="Cannot move a box into its own descendant"
                    )

            db.execute(
                "UPDATE box SET parent_id = ? WHERE box_id = ?",
                (move.parent_id, box_id)
            )

            result = get_box_or_404(db, box_id)

    except sqlite3.IntegrityError:
        # Здесь срабатывает триггер trg_box_no_cycle
        # и ограничение UNIQUE(parent_id, box_name).
        raise HTTPException(
            status_code=409,
            detail="Cannot move a box into its own descendant"
        )

    return result
