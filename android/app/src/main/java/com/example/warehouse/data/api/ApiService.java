package com.example.warehouse.data.api;

import com.example.warehouse.data.model.LoginRequest;
import com.example.warehouse.data.model.LoginResponse;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.POST;

public interface ApiService {
    @POST("auth/login")
    Call<LoginResponse> login(@Body LoginRequest request);
}