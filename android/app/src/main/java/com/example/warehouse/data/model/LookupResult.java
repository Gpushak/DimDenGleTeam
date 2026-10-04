package com.example.warehouse.data.model;

/**
 * Ответ GET /lookup по QR-коду {@code qwentory:<kind>:<id>}.
 *
 * Эндпоинт полиморфный: в зависимости от {@code kind} заполнено ровно одно
 * из полей {@link #item}, {@link #item_type} или {@link #box} (+ {@link #contents}
 * для коробки). Незаполненные поля остаются null.
 */
public class LookupResult {
    /** item | type | box */
    public String kind;

    /** При kind=item — сама позиция товара. */
    public ItemSummary item;

    /** При kind=type — справочная запись типа товара. */
    public ItemTypeSummary item_type;

    /** При kind=box — контейнер. */
    public BoxSummary box;

    /** При kind=box — содержимое контейнера. */
    public BoxContents contents;
}