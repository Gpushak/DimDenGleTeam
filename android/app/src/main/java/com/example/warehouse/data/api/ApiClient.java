package com.example.warehouse.data.api;

import android.content.Context;

import com.example.warehouse.data.local.SettingsStore;

import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class ApiClient {
    private static Retrofit retrofit;
    private static String currentBaseUrl;
    private static Context appContext;

    public static void init(Context ctx) {
        appContext = ctx.getApplicationContext();
    }

    public static Retrofit get() {
        String baseUrl = appContext != null
                ? new SettingsStore(appContext).getBaseUrl()
                : "http://10.0.2.2:8000/";

        if (retrofit == null || !baseUrl.equals(currentBaseUrl)) {
            currentBaseUrl = baseUrl;

            HttpLoggingInterceptor log = new HttpLoggingInterceptor();
            log.setLevel(HttpLoggingInterceptor.Level.BODY);

            OkHttpClient client = new OkHttpClient.Builder()
                    .addInterceptor(log)
                    .connectTimeout(15, TimeUnit.SECONDS)
                    .readTimeout(15, TimeUnit.SECONDS)
                    .build();

            retrofit = new Retrofit.Builder()
                    .baseUrl(baseUrl)
                    .client(client)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build();
        }
        return retrofit;
    }

    public static ApiService api() {
        return get().create(ApiService.class);
    }
}