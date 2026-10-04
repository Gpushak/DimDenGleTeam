"""Демо-данные склада — те же сущности, что видят десктоп и Android."""


def seed_demo_data(db) -> None:
    box_types = [
        "Склад",
        "Стеллаж",
        "Полка",
        "Ячейка",
        "Зона",
        "Помещение",
        "Контейнер",
        "Коробка",
    ]
    for name in box_types:
        db.execute("INSERT INTO box_type (box_type_name) VALUES (?)", (name,))

    type_ids = {
        row["box_type_name"]: row["box_type_id"]
        for row in db.execute("SELECT box_type_id, box_type_name FROM box_type")
    }

    def add_box(name, type_name, parent_id=None):
        cur = db.execute(
            "INSERT INTO box (box_name, box_type_id, parent_id) VALUES (?, ?, ?)",
            (name, type_ids[type_name], parent_id),
        )
        return cur.lastrowid

    main_wh = add_box("Основной склад", "Склад")
    # Второй корень без товаров — как в десктопном демо.
    add_box("Склад ГСМ", "Склад")
    rack_a = add_box("Стеллаж A", "Стеллаж", main_wh)
    rack_b = add_box("Стеллаж B", "Стеллаж", main_wh)
    shelf_a1 = add_box("Полка 1", "Полка", rack_a)
    shelf_a2 = add_box("Полка 2", "Полка", rack_a)
    shelf_b1 = add_box("Полка 1", "Полка", rack_b)
    cell_a1_1 = add_box("Ячейка A1-1", "Ячейка", shelf_a1)
    cell_a1_2 = add_box("Ячейка A1-2", "Ячейка", shelf_a1)
    cell_a2_1 = add_box("Ячейка A2-1", "Ячейка", shelf_a2)

    materials = [
        ("Болт M10x50", 45),
        ("Гайка M10", 12),
        ("Шайба 10мм", 5),
        ("Краска белая", 1200),
        ("Кисть малярная", 150),
        ("Масло моторное 5W-30", 1000),
        ("Антифриз", 1100),
        ("Винт M8x30", 18),
    ]
    for name, weight in materials:
        db.execute(
            "INSERT INTO item_type (item_type_name, weight_g) VALUES (?, ?)",
            (name, weight),
        )

    type_by_name = {
        row["item_type_name"]: row["item_type_id"]
        for row in db.execute("SELECT item_type_id, item_type_name FROM item_type")
    }

    items = [
        (type_by_name["Болт M10x50"], cell_a1_1, 500),
        (type_by_name["Гайка M10"], cell_a1_1, 300),
        (type_by_name["Шайба 10мм"], cell_a1_2, 1000),
        (type_by_name["Краска белая"], cell_a2_1, 25),
        (type_by_name["Кисть малярная"], shelf_b1, 50),
        (type_by_name["Масло моторное 5W-30"], None, 10),
        (type_by_name["Антифриз"], None, 15),
        (type_by_name["Винт M8x30"], cell_a1_1, 200),
    ]
    for item_type_id, box_id, qty in items:
        db.execute(
            "INSERT INTO item (item_type_id, box_id, quantity) VALUES (?, ?, ?)",
            (item_type_id, box_id, qty),
        )
