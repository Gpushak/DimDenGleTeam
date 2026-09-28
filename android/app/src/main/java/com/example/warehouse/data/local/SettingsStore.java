package com.example.warehouse.data.local;

import android.content.Context;
import android.content.SharedPreferences;

import com.example.warehouse.BuildConfig;

public class SettingsStore {
    private static final String PREF = "warehouse_settings";
    private static final String KEY_BASE_URL = "base_url";

    private final SharedPreferences prefs;

    public SettingsStore(Context ctx) {
        prefs = ctx.getApplicationContext().getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    public String getBaseUrl() {
        return prefs.getString(KEY_BASE_URL, BuildConfig.API_BASE_URL);
    }

    public void setBaseUrl(String url) {
        if (url == null) return;
        url = url.trim();
        if (!url.endsWith("/")) url += "/";
        prefs.edit().putString(KEY_BASE_URL, url).apply();
    }
}