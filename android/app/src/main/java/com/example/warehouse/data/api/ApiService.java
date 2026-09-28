package com.example.warehouse.data.api;

import com.example.warehouse.data.model.CreateListRequest;
import com.example.warehouse.data.model.InventoryItem;
import com.example.warehouse.data.model.InventoryList;
import com.example.warehouse.data.model.LoginRequest;
import com.example.warehouse.data.model.LoginResponse;
import com.example.warehouse.data.model.ScanRequest;
import com.example.warehouse.data.model.ScanResponse;
import com.example.warehouse.data.model.WeighSession;

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

    @POST("inventory/lists")
    Call<InventoryList> createList(@Body CreateListRequest request);

    @GET("inventory/lists/{id}/items")
    Call<List<InventoryItem>> getListItems(@Path("id") long listId);

    @DELETE("inventory/items/{id}")
    Call<Void> deleteItem(@Path("id") long itemId);

    @POST("inventory/scan")
    Call<ScanResponse> scan(@Body ScanRequest request);

    @GET("weigh/session/{id}")
    Call<WeighSession> getWeighSession(@Path("id") long sessionId);

    @POST("weigh/confirm")
    Call<Void> confirmWeigh(@Body WeighSession session);
}