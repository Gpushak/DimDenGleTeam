package com.example.warehouse.data.model;

/**
 * Позиция товара в ответе GET /lookup (kind=item).
 *
 * Имена полей соответствуют JSON сервера: там позиция товара возвращается
 * с ключом {@code id}, а не {@code item_id} (в отличие от
 * {@link BoxContents.ItemRow}). Поэтому это отдельный класс, а не переиспользование.
 */
public class ItemSummary {
    public int id;
    public int item_type_id;
    public String item_type_name;
    public Integer weight_g;
    public Integer box_id;
    public String box_name;
    public int quantity;
    public Integer total_weight_g;
}