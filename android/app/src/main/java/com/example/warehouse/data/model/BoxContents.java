package com.example.warehouse.data.model;

import com.google.gson.annotations.SerializedName;

import java.util.ArrayList;
import java.util.List;

/**
 * Содержимое ячейки (ответ GET /boxes/{id}/contents).
 */
public class BoxContents {
    public int box_id;
    public List<ItemRow> items = new ArrayList<>();
    public List<ChildBox> child_boxes = new ArrayList<>();

    public static class ItemRow {
        /**
         * Ключи {@code /boxes/{id}/contents} и {@code /items/{id}} различаются:
         * в первом позиция названа {@code item_id}, во втором — {@code id}.
         * Gson умеет сопоставлять полю несколько имён через alternate, поэтому
         * один класс читает оба ответа.
         */
        @SerializedName(value = "item_id", alternate = {"id"})
        public int item_id;
        public int item_type_id;
        public String item_type_name;
        public Integer weight_g;
        public int quantity;
        public Integer total_weight_g;
        /** В ответе /boxes/{id}/contents отсутствует — там позиция всегда в этой коробке. */
        public Integer box_id;
        /** Только в ответе /items/{id}: имя контейнера, где лежит позиция. */
        public String box_name;
    }

    public static class ChildBox {
        public int id;
        public String name;
        public int box_type_id;
        public String box_type_name;
    }
}
