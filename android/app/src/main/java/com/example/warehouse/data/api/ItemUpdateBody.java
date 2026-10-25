package com.example.warehouse.data.api;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonSerializationContext;
import com.google.gson.JsonSerializer;

import java.lang.reflect.Type;

/**
 * Тело запроса PATCH /items/{id}.
 *
 * Сервер меняет только те поля, которые реально пришли в JSON. Поэтому
 * незаданное поле нельзя сериализовать как null: иначе смена количества
 * заодно обнулит контейнер и тип. Исключение — «вынуть из контейнера»:
 * {@code box_id: null} отправляется только когда это запрошено явно.
 */
public class ItemUpdateBody {

    public Integer quantity;
    public Integer box_id;
    public Integer item_type_id;

    /** true — поле box_id входит в JSON, даже если оно null. */
    public transient boolean includeBox;
    /** true — поле item_type_id входит в JSON. */
    public transient boolean includeType;

    public static ItemUpdateBody quantity(int value) {
        ItemUpdateBody body = new ItemUpdateBody();
        body.quantity = value;
        return body;
    }

    /** Перемещение позиции в контейнер (boxId == null — вынуть из контейнера). */
    public static ItemUpdateBody moveTo(Integer boxId) {
        ItemUpdateBody body = new ItemUpdateBody();
        body.box_id = boxId;
        body.includeBox = true;
        return body;
    }

    /** Смена типа товара позиции. */
    public static ItemUpdateBody itemType(int itemTypeId) {
        ItemUpdateBody body = new ItemUpdateBody();
        body.item_type_id = itemTypeId;
        body.includeType = true;
        return body;
    }

    public static Gson gson() {
        // serializeNulls нужен, чтобы явное box_id: null дожило до строки.
        // Сериализатор сам не кладёт поля, которые менять не просили, поэтому
        // смена количества по-прежнему уходит как {"quantity": N}.
        return new GsonBuilder()
                .serializeNulls()
                .registerTypeAdapter(ItemUpdateBody.class, new Serializer())
                .create();
    }

    static final class Serializer implements JsonSerializer<ItemUpdateBody> {
        @Override
        public JsonElement serialize(ItemUpdateBody src, Type typeOfSrc,
                                     JsonSerializationContext context) {
            JsonObject object = new JsonObject();
            if (src.quantity != null) {
                object.addProperty("quantity", src.quantity);
            }
            if (src.includeBox) {
                if (src.box_id == null) {
                    object.add("box_id", JsonNull.INSTANCE);
                } else {
                    object.addProperty("box_id", src.box_id);
                }
            }
            if (src.includeType && src.item_type_id != null) {
                object.addProperty("item_type_id", src.item_type_id);
            }
            return object;
        }
    }
}
