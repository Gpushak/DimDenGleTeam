package com.example.warehouse.data.api;

import com.example.warehouse.data.model.InventoryItem;
import com.example.warehouse.data.model.InventoryList;
import com.example.warehouse.data.model.LoginRequest;
import com.example.warehouse.data.model.LoginResponse;

import java.util.List;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.DELETE;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;

public interface ApiService {

    @POST("auth/login")
    Call<LoginResponse> login(@Body LoginRequest request);

    @GET("inventory/lists")
    Call<List<InventoryList>> getLists();

    @GET("inventory/lists/{id}/items")
    Call<List<InventoryItem>> getListItems(@Path("id") long listId);

    @DELETE("inventory/items/{id}")
    Call<Void> deleteItem(@Path("id") long itemId);
}