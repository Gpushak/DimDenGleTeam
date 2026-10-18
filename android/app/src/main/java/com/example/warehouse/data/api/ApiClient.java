package com.example.warehouse.data.api;

import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

import com.google.gson.Gson;

/**
 * Единая точка доступа к REST API сервера.
 * Базовый адрес берётся из {@link ServerConfig} и может быть изменён
 * в рантайме (после этого Retrofit пересоздаётся).
 */
public class ApiClient {
    private static volatile Retrofit retrofit;
    private static volatile String currentBaseUrl;

    /** Должен вызываться при старте приложения, чтобы задать контекст. */
    public static void init(android.content.Context context) {
        synchronized (ApiClient.class) {
            String url = ServerConfig.getBaseUrl(context);
            if (retrofit == null || !url.equals(currentBaseUrl)) {
                currentBaseUrl = url;
                retrofit = buildRetrofit(url);
            }
        }
    }

    public static Retrofit get() {
        Retrofit r = retrofit;
        if (r == null) {
            throw new IllegalStateException(
                    "ApiClient.init(context) must be called before using the API");
        }
        return r;
    }

    public static ApiService api() {
        return get().create(ApiService.class);
    }

    /** Сбрасывает кэш Retrofit — используется при смене адреса сервера. */
    public static void reset() {
        synchronized (ApiClient.class) {
            retrofit = null;
            currentBaseUrl = null;
        }
    }

    private static Retrofit buildRetrofit(String baseUrl) {
        HttpLoggingInterceptor log = new HttpLoggingInterceptor();
        log.setLevel(HttpLoggingInterceptor.Level.BODY);

        OkHttpClient client = new OkHttpClient.Builder()
                .addInterceptor(log)
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
                .build();

        // serializeNulls нужен для PATCH /items/{id}: null в box_id означает
        // «вынуть позицию из контейнера», и это поле должно попасть в JSON.
        Gson gson = new Gson().newBuilder().serializeNulls().create();

        return new Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create(gson))
                .build();
    }
}
