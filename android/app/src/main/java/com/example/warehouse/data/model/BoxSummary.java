package com.example.warehouse.data.model;

/**
 * Контейнер в ответе GET /lookup (kind=box).
 *
 * В отличие от {@link BoxContents.ChildBox} содержит {@code parent_id} —
 * его возвращает эндпоинт GET /boxes/{id}, а не содержимое контейнера.
 */
public class BoxSummary {
    public int id;
    public String name;
    public int box_type_id;
    public String box_type_name;
    public Integer parent_id;
}