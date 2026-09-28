package com.example.warehouse.data.local.entity;

import androidx.annotation.NonNull;
import androidx.room.Entity;
import androidx.room.PrimaryKey;

@Entity(tableName = "lists")
public class ListEntity {
    @PrimaryKey
    @NonNull
    public String id;

    public String name;
    public String status;
    public String createdAt;
    public int itemsCount;
}