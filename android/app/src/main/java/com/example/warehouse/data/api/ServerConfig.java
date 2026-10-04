package com.example.warehouse.data.api;

import android.content.Context;
import android.content.SharedPreferences;

import com.example.warehouse.BuildConfig;

/**
 * Хранит базовый адрес API. По умолчанию берётся из BuildConfig
 * (http://10.0.2.2:8000/ — хост-машина для эмулятора Android),
 * но может быть переопределён пользователем (например, IP компьютера
 * в локальной сети для реального телефона).
 */
public final class ServerConfig {

    private static final String PREFS = "server";
    private static final String KEY_BASE_URL = "base_url";

    private ServerConfig() {
    }

    public static String getBaseUrl(Context context) {
        String saved = prefs(context).getString(KEY_BASE_URL, null);
        return (saved != null && !saved.isEmpty()) ? normalize(saved) : BuildConfig.API_BASE_URL;
    }

    public static void setBaseUrl(Context context, String url) {
        prefs(context).edit().putString(KEY_BASE_URL, normalize(url)).apply();
        ApiClient.reset();
    }

    /** Убирает сохранённый адрес — приложение вернётся к значению из BuildConfig. */
    public static void clearBaseUrl(Context context) {
        prefs(context).edit().remove(KEY_BASE_URL).apply();
        ApiClient.reset();
    }

    /** Приводит адрес к виду scheme://host[:port]/ — Retrofit требует завершающий «/». */
    public static String normalize(String url) {
        String trimmed = url.trim();
        if (trimmed.isEmpty()) {
            return trimmed;
        }
        if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
            trimmed = "http://" + trimmed;
        }
        if (!trimmed.endsWith("/")) {
            trimmed = trimmed + "/";
        }
        return trimmed;
    }

    private static SharedPreferences prefs(Context context) {
        return context.getApplicationContext()
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }
}
