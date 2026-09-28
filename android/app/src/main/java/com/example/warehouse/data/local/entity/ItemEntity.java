package com.example.warehouse.data.local.entity;

import androidx.annotation.NonNull;
import androidx.room.Entity;
import androidx.room.PrimaryKey;

@Entity(tableName = "items")
public class ItemEntity {
    @PrimaryKey
    @NonNull
    public String id;

    public String listId;
    public long productId;
    public String productName;
    public String sku;
    public double grossWeight;
    public double tareWeight;
    public double netWeight;
    public String status;
}