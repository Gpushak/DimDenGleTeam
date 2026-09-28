package com.example.warehouse.data.model;

import com.google.gson.annotations.SerializedName;

public class Product {
    @SerializedName("id")
    public long id;

    @SerializedName("sku")
    public String sku;

    @SerializedName("name")
    public String name;

    @SerializedName("tare_weight")
    public double tareWeight;

    @SerializedName("unit")
    public String unit;
}