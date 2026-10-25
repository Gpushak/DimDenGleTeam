package com.example.warehouse.data.api;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

/**
 * PATCH должен содержать только изменённые поля. Иначе сервер воспринимает
 * null как «вынуть из контейнера» и «сменить тип».
 */
public class ItemUpdateBodyTest {

    @Test
    public void quantityOmitsBoxAndType() {
        assertEquals(
                "{\"quantity\":3}",
                ItemUpdateBody.gson().toJson(ItemUpdateBody.quantity(3)));
    }

    @Test
    public void moveSendsOnlyBoxId() {
        assertEquals(
                "{\"box_id\":8}",
                ItemUpdateBody.gson().toJson(ItemUpdateBody.moveTo(8)));
    }

    @Test
    public void unboxSendsNullBoxId() {
        assertEquals(
                "{\"box_id\":null}",
                ItemUpdateBody.gson().toJson(ItemUpdateBody.moveTo(null)));
    }

    @Test
    public void typeChangeSendsOnlyType() {
        assertEquals(
                "{\"item_type_id\":2}",
                ItemUpdateBody.gson().toJson(ItemUpdateBody.itemType(2)));
    }
}
