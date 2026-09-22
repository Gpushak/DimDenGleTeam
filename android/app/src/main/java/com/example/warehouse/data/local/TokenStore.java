package com.example.warehouse.data.local;

import android.content.Context;
import android.content.SharedPreferences;

public class TokenStore {
    private static final String PREF = "warehouse_prefs";
    private static final String KEY_TOKEN = "jwt";
    private static final String KEY_ROLE = "role";

    private final SharedPreferences prefs;

    public TokenStore(Context ctx) {
        prefs = ctx.getApplicationContext().getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    public void save(String token, String role) {
        prefs.edit().putString(KEY_TOKEN, token).putString(KEY_ROLE, role).apply();
    }

    public String getToken() { return prefs.getString(KEY_TOKEN, null); }
    public String getRole() { return prefs.getString(KEY_ROLE, null); }
    public boolean isLoggedIn() { return getToken() != null; }
    public void clear() { prefs.edit().clear().apply(); }
}