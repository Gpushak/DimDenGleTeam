package com.example.warehouse.data.model;

import com.google.gson.annotations.SerializedName;

public class ScanRequest {
    @SerializedName("qr_code")
    public String qrCode;

    @SerializedName("list_id")
    public long listId;

    public ScanRequest(String qrCode, long listId) {
        this.qrCode = qrCode;
        this.listId = listId;
    }
}