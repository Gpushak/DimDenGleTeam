package com.example.warehouse.data.model;

import java.util.ArrayList;
import java.util.List;

/**
 * Узел дерева складов (ответ {@code GET /boxes/tree}).
 *
 * Поле {@code children} заполняется Gson из вложенного JSON и используется
 * для обхода дерева и подсчёта вложенных контейнеров.
 */
public class BoxNode {
    public int id;
    public String name;
    public Integer box_type_id;
    public String box_type_name;
    public List<BoxNode> children = new ArrayList<>();

    public int childrenCount() {
        return children == null ? 0 : children.size();
    }
}