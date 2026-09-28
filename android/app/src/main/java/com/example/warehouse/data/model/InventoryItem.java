package com.example.warehouse.data.model;

import com.google.gson.annotations.SerializedName;

public class InventoryItem {
    @SerializedName("id")
    public long id;

    @SerializedName("list_id")
    public long listId;

    @SerializedName("product_id")
    public long productId;

    @SerializedName("product_name")
    public String productName;

    @SerializedName("sku")
    public String sku;

    @SerializedName("gross_weight")
    public double grossWeight;

    @SerializedName("tare_weight")
    public double tareWeight;

    @SerializedName("net_weight")
    public double netWeight;

    @SerializedName("status")
    public String status;
}