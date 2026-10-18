package com.example.warehouse.data.api;

/**
 * Тело запроса PATCH /items/{id}.
 *
 * Сервер (app/routers/items.py, ItemUpdate) принимает quantity, box_id и
 * item_type_id; пропущенные поля не меняются. Отправка box_id == null
 * вынимает позицию из контейнера — чтобы Gson сериализовал null, в
 * {@link ApiClient} включён serializeNulls и поле объявлено как Integer.
 */
public class ItemUpdateBody {

    public Integer quantity;
    public Integer box_id;
    public Integer item_type_id;

    public static ItemUpdateBody quantity(int value) {
        ItemUpdateBody body = new ItemUpdateBody();
        body.quantity = value;
        return body;
    }

    /** Перемещение позиции в контейнер (boxId == null — вынуть из контейнера). */
    public static ItemUpdateBody moveTo(Integer boxId) {
        ItemUpdateBody body = new ItemUpdateBody();
        body.box_id = boxId;
        return body;
    }

    /** Смена типа товара позиции. */
    public static ItemUpdateBody itemType(int itemTypeId) {
        ItemUpdateBody body = new ItemUpdateBody();
        body.item_type_id = itemTypeId;
        return body;
    }
}
