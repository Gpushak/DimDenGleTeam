PRAGMA foreign_keys = ON;

CREATE TABLE box_type (
    box_type_id   INTEGER PRIMARY KEY,
    box_type_name TEXT NOT NULL UNIQUE
);

CREATE TABLE box (
    box_id       INTEGER PRIMARY KEY,
    box_name     TEXT NOT NULL,
    box_type_id  INTEGER NOT NULL REFERENCES box_type(box_type_id) ON DELETE RESTRICT,
    parent_id    INTEGER REFERENCES box(box_id) ON DELETE CASCADE,
    CHECK (parent_id IS NULL OR parent_id <> box_id),
    UNIQUE (parent_id, box_name)
);

CREATE UNIQUE INDEX ux_box_root_name
    ON box(box_name)
    WHERE parent_id IS NULL;

CREATE INDEX idx_box_parent ON box(parent_id);
CREATE INDEX idx_box_type   ON box(box_type_id);

CREATE TABLE item_type (
    item_type_id   INTEGER PRIMARY KEY,
    item_type_name TEXT NOT NULL UNIQUE,
    weight_g       INTEGER CHECK (weight_g IS NULL OR weight_g >= 0)
);

CREATE TABLE item (
    item_id      INTEGER PRIMARY KEY,
    item_type_id INTEGER NOT NULL REFERENCES item_type(item_type_id) ON DELETE RESTRICT,
    box_id       INTEGER REFERENCES box(box_id) ON DELETE SET NULL,
    quantity     INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE (box_id, item_type_id)
);

CREATE UNIQUE INDEX ux_item_unboxed
    ON item(item_type_id)
    WHERE box_id IS NULL;

CREATE INDEX idx_item_type ON item(item_type_id);
CREATE INDEX idx_item_box  ON item(box_id);

CREATE TRIGGER trg_box_no_cycle
BEFORE UPDATE OF parent_id ON box
FOR EACH ROW
WHEN NEW.parent_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'box: cycle in tree is not allowed')
    WHERE EXISTS (
        WITH RECURSIVE descendants(id) AS (
            SELECT box_id FROM box WHERE parent_id = NEW.box_id
            UNION ALL
            SELECT b.box_id
            FROM box b
            JOIN descendants d ON b.parent_id = d.id
        )
        SELECT 1 FROM descendants WHERE id = NEW.parent_id
    );
END;