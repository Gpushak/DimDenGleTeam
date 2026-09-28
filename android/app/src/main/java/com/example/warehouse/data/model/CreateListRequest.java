package com.example.warehouse.data.model;

import com.google.gson.annotations.SerializedName;

public class CreateListRequest {
    @SerializedName("name")
    public String name;

    public CreateListRequest(String name) {
        this.name = name;
    }
}