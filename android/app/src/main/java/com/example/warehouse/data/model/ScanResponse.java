package com.example.warehouse.data.model;

import com.google.gson.annotations.SerializedName;

public class ScanResponse {
    @SerializedName("session_id")
    public long sessionId;

    @SerializedName("product_id")
    public long productId;

    @SerializedName("product_name")
    public String productName;
}