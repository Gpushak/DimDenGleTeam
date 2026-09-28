package com.example.warehouse.data.model;

import com.google.gson.annotations.SerializedName;

public class InventoryList {
    @SerializedName("id")
    public long id;

    @SerializedName("name")
    public String name;

    @SerializedName("status")
    public String status;

    @SerializedName("created_at")
    public String createdAt;

    @SerializedName("items_count")
    public int itemsCount;
}