package com.example.warehouse.data.model;

/**
 * Справочная запись типа товара в ответе GET /lookup (kind=type).
 *
 * Внимание: имена полей здесь {@code id} и {@code name}, а не
 * {@code item_type_id}/{@code item_type_name}, как у позиции товара —
 * так отдаёт серверный эндпоинт GET /item-types.
 */
public class ItemTypeSummary {
    public int id;
    public String name;
    public Integer weight_g;
}