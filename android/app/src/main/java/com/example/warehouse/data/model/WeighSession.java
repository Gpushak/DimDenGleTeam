package com.example.warehouse.data.model;

import com.google.gson.annotations.SerializedName;

public class WeighSession {
    @SerializedName("session_id")
    public long sessionId;

    @SerializedName("gross")
    public double gross;

    @SerializedName("tare")
    public double tare;

    @SerializedName("net")
    public double net;

    @SerializedName("stable")
    public boolean stable;

    @SerializedName("status")
    public String status;
}