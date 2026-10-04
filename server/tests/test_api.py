"""Тесты REST API склада.

Покрывают контракт, который используют десктоп и Android: справочники,
дерево коробок, предметы, показание весов и QR-lookup.
"""
import time


def test_health_reports_schema_version(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["schema_version"] == body["schema_version_expected"]


# ─────────────────────────── Типы коробок ───────────────────────────

def test_box_types_crud(client):
    created = client.post("/box-types", json={"name": "Паллетный бокс"})
    assert created.status_code == 200
    box_type_id = created.json()["id"]

    assert client.get("/box-types").status_code == 200
    assert client.get(f"/box-types/{box_type_id}").json()["name"] == "Паллетный бокс"

    # Дубликат имени → 409, без сырого текста SQLite в ответе.
    duplicate = client.post("/box-types", json={"name": "Паллетный бокс"})
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]

    assert client.delete(f"/box-types/{box_type_id}").status_code == 200
    assert client.get(f"/box-types/{box_type_id}").status_code == 404


def test_delete_used_box_type_conflicts(client):
    box_type_id = client.get("/box-types").json()[0]["id"]
    assert client.delete(f"/box-types/{box_type_id}").status_code == 409


# ─────────────────────────── Типы предметов ───────────────────────────

def test_item_type_patch_can_clear_weight(client):
    item_type_id = client.post("/item-types", json={"name": "Гайка", "weight_g": 12}).json()["id"]

    # Явный null должен сбрасывать вес, а не игнорироваться.
    cleared = client.patch(f"/item-types/{item_type_id}", json={"weight_g": None})
    assert cleared.status_code == 200
    assert cleared.json()["weight_g"] is None

    # Пустой PATCH → 400 (нечего обновлять).
    assert client.patch(f"/item-types/{item_type_id}", json={}).status_code == 400

    # Опечатка в имени поля → 422, а не тихий игнор.
    assert client.patch(f"/item-types/{item_type_id}", json={"weight": 5}).status_code == 422


# ─────────────────────────────── Коробки ───────────────────────────────

def test_box_tree_and_move_cycle(client):
    types = {b["name"]: b["id"] for b in client.get("/box-types").json()}
    main = client.post("/boxes", json={"name": "Корень", "box_type_id": types["Склад"]}).json()
    child = client.post("/boxes", json={"name": "Сын", "box_type_id": types["Ячейка"], "parent_id": main["id"]}).json()
    grand = client.post("/boxes", json={"name": "Внук", "box_type_id": types["Ячейка"], "parent_id": child["id"]}).json()

    # Дерево: корни → дети → внуки.
    tree = client.get("/boxes/tree").json()
    root_node = next(b for b in tree if b["id"] == main["id"])
    child_node = root_node["children"][0]
    assert child_node["id"] == child["id"]
    assert child_node["children"][0]["id"] == grand["id"]

    # Нельзя перенести коробку в собственного потомка.
    conflict = client.post(f"/boxes/{main['id']}/move", json={"parent_id": grand["id"]})
    assert conflict.status_code == 409

    # Нельзя в саму себя.
    assert client.post(f"/boxes/{main['id']}/move", json={"parent_id": main["id"]}).status_code == 409

    # Корректный перенос в корень.
    moved = client.post(f"/boxes/{grand['id']}/move", json={"parent_id": None})
    assert moved.status_code == 200
    assert moved.json()["parent_id"] is None


def test_delete_box_cascades_and_unboxes_items(client):
    types = {b["name"]: b["id"] for b in client.get("/box-types").json()}
    item_type_id = client.post("/item-types", json={"name": "Болт", "weight_g": 5}).json()["id"]

    parent = client.post("/boxes", json={"name": "Внешний", "box_type_id": types["Коробка"]}).json()
    child = client.post("/boxes", json={"name": "Внутренняя", "box_type_id": types["Коробка"], "parent_id": parent["id"]}).json()

    # Два одинаковых предмета: один во вложенной коробке, один «без коробки».
    client.post("/items", json={"item_type_id": item_type_id, "box_id": child["id"], "quantity": 3})
    client.post("/items", json={"item_type_id": item_type_id, "quantity": 2})

    deleted = client.delete(f"/boxes/{parent['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["unboxed"] == 1  # один предмет «вынут» из вложенной коробки

    # Вложенная коробка удалена каскадом.
    assert client.get(f"/boxes/{child['id']}").status_code == 404

    # Количества слились: было 2 (без коробки) + 3 (из удалённой) = 5.
    # Фильтруем по своему типу: на пустой БД засеваются демо-данные, где тоже
    # есть предметы «без коробки».
    merged = [i for i in client.get("/items", params={"unboxed": True}).json()
              if i["item_type_id"] == item_type_id]
    assert len(merged) == 1
    assert merged[0]["quantity"] == 5


# ─────────────────────────────── Предметы ───────────────────────────────

def test_item_lifecycle(client):
    item_type_id = client.post("/item-types", json={"name": "Шуруп", "weight_g": 3}).json()["id"]
    box_id = client.get("/boxes").json()[0]["id"]

    created = client.post("/items", json={"item_type_id": item_type_id, "box_id": box_id, "quantity": 4})
    assert created.status_code == 200
    item = created.json()
    assert item["total_weight_g"] == 12  # 4 * 3

    # Дубль «коробка + тип» → 409.
    duplicate = client.post("/items", json={"item_type_id": item_type_id, "box_id": box_id})
    assert duplicate.status_code == 409

    # Перенос в «без коробки»: box_id = null.
    moved = client.patch(f"/items/{item['id']}", json={"box_id": None})
    assert moved.status_code == 200
    assert moved.json()["box_id"] is None

    assert client.delete(f"/items/{item['id']}").status_code == 200
    assert client.get(f"/items/{item['id']}").status_code == 404


def test_items_include_children(client):
    types = {b["name"]: b["id"] for b in client.get("/box-types").json()}
    item_type_id = client.post("/item-types", json={"name": "Гайка", "weight_g": 2}).json()["id"]
    parent = client.post("/boxes", json={"name": "R", "box_type_id": types["Стеллаж"]}).json()
    child = client.post("/boxes", json={"name": "C", "box_type_id": types["Ячейка"], "parent_id": parent["id"]}).json()

    client.post("/items", json={"item_type_id": item_type_id, "box_id": parent["id"], "quantity": 1})
    client.post("/items", json={"item_type_id": item_type_id, "box_id": child["id"], "quantity": 1})

    only_parent = client.get("/items", params={"box_id": parent["id"]}).json()
    assert len(only_parent) == 1

    with_children = client.get(
        "/items", params={"box_id": parent["id"], "include_children": True}
    ).json()
    assert len(with_children) == 2


# ──────────────────────────────── Весы ────────────────────────────────

def test_scale_post_get_delete(client):
    posted = client.post("/scale", json={"weight_g": 1234.5})
    assert posted.status_code == 200
    assert posted.json()["weight_g"] == 1234.5
    assert posted.json()["source"] == "api"
    assert posted.json()["stale"] is False

    # Serial-строка от Arduino помечается источником serial.
    serial = client.post("/scale", json={"line": "WEIGHT:500.00"})
    assert serial.json()["source"] == "serial"
    assert serial.json()["weight_g"] == 500.0

    # Нечитаемое значение → 400.
    assert client.post("/scale", json={"line": "hello"}).status_code == 400

    # Нечисловой вес → 422 (валидация Pydantic).
    assert client.post("/scale", json={"weight_g": "abc"}).status_code == 422

    assert client.delete("/scale").status_code == 200
    assert client.get("/scale").json()["weight_g"] is None


def test_scale_stale_flag_after_ttl(client):
    # Подменяем TTL на 0 секунд, чтобы не ждать в тесте.
    from app.routers import scale as scale_module

    original = scale_module.FRESH_TTL_SECONDS
    scale_module.FRESH_TTL_SECONDS = 0.0
    try:
        client.post("/scale", json={"weight_g": 10})
        time.sleep(0.01)
        assert client.get("/scale").json()["stale"] is True
    finally:
        scale_module.FRESH_TTL_SECONDS = original


# ──────────────────────────────── Lookup ────────────────────────────────

def test_lookup_by_qr(client):
    types = {b["name"]: b["id"] for b in client.get("/box-types").json()}
    box_id = client.post("/boxes", json={"name": "Полка QR", "box_type_id": types["Полка"]}).json()["id"]
    item_type_id = client.post("/item-types", json={"name": "Мат", "weight_g": 900}).json()["id"]

    box_lookup = client.get("/lookup", params={"code": f"qwentory:box:{box_id}"})
    assert box_lookup.status_code == 200
    assert box_lookup.json()["kind"] == "box"
    assert box_lookup.json()["box"]["id"] == box_id
    assert "contents" in box_lookup.json()

    type_lookup = client.get("/lookup", params={"code": f"qwentory:type:{item_type_id}"})
    assert type_lookup.json()["kind"] == "type"
    assert type_lookup.json()["item_type"]["id"] == item_type_id

    # Некорректный/чужой QR → 400.
    assert client.get("/lookup", params={"code": "some-other-app:x:1"}).status_code == 400
    assert client.get("/lookup", params={"code": "qwentory:item:abc"}).status_code == 400
