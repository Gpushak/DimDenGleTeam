package com.example.warehouse.data.repo;

import com.example.warehouse.data.local.entity.ItemEntity;
import com.example.warehouse.data.local.entity.ListEntity;
import com.example.warehouse.data.model.InventoryItem;
import com.example.warehouse.data.model.InventoryList;

import java.util.ArrayList;
import java.util.List;

public class Mappers {

    public static ListEntity toEntity(InventoryList l) {
        ListEntity e = new ListEntity();
        e.id = String.valueOf(l.id);
        e.name = l.name;
        e.status = l.status;
        e.createdAt = l.createdAt;
        e.itemsCount = l.itemsCount;
        return e;
    }

    public static List<InventoryList> toListModel(List<ListEntity> entities) {
        List<InventoryList> result = new ArrayList<>();
        if (entities == null) return result;
        for (ListEntity e : entities) {
            InventoryList l = new InventoryList();
            try { l.id = Long.parseLong(e.id); } catch (Exception ex) { l.id = 0; }
            l.name = e.name;
            l.status = e.status;
            l.createdAt = e.createdAt;
            l.itemsCount = e.itemsCount;
            result.add(l);
        }
        return result;
    }

    public static ItemEntity toEntity(InventoryItem i, long listId) {
        ItemEntity e = new ItemEntity();
        e.id = String.valueOf(i.id);
        e.listId = String.valueOf(listId);
        e.productId = i.productId;
        e.productName = i.productName;
        e.sku = i.sku;
        e.grossWeight = i.grossWeight;
        e.tareWeight = i.tareWeight;
        e.netWeight = i.netWeight;
        e.status = i.status;
        return e;
    }

    public static List<InventoryItem> toItemModel(List<ItemEntity> entities) {
        List<InventoryItem> result = new ArrayList<>();
        if (entities == null) return result;
        for (ItemEntity e : entities) {
            InventoryItem i = new InventoryItem();
            try { i.id = Long.parseLong(e.id); } catch (Exception ex) { i.id = 0; }
            try { i.listId = Long.parseLong(e.listId); } catch (Exception ex) { i.listId = 0; }
            i.productId = e.productId;
            i.productName = e.productName;
            i.sku = e.sku;
            i.grossWeight = e.grossWeight;
            i.tareWeight = e.tareWeight;
            i.netWeight = e.netWeight;
            i.status = e.status;
            result.add(i);
        }
        return result;
    }
}