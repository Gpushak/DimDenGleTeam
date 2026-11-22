package com.example.warehouse.data;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.res.Configuration;

import androidx.appcompat.app.AppCompatDelegate;
import androidx.core.os.LocaleListCompat;

/**
 * Тема и язык интерфейса. Значения читаются при старте {@link com.example.warehouse.WarehouseApp}
 * и сразу применяются ко всему приложению.
 */
public final class AppSettings {

    private static final String PREFS = "settings";
    private static final String KEY_DARK = "dark_theme";
    private static final String KEY_LANG = "language";

    public static final String LANG_RU = "ru";
    public static final String LANG_EN = "en";

    private AppSettings() {
    }

    public static void apply(Context context) {
        applyNightMode(context);
        AppCompatDelegate.setApplicationLocales(
                LocaleListCompat.forLanguageTags(getLanguage(context)));
    }

    public static boolean hasThemePreference(Context context) {
        return prefs(context).contains(KEY_DARK);
    }

    /** Сохранённый выбор. Если его ещё не было — совпадает с текущей системной темой. */
    public static boolean isDarkTheme(Context context) {
        if (!hasThemePreference(context)) {
            return isNightNow(context);
        }
        return prefs(context).getBoolean(KEY_DARK, false);
    }

    public static void setDarkTheme(Context context, boolean dark) {
        prefs(context).edit().putBoolean(KEY_DARK, dark).commit();
        AppCompatDelegate.setDefaultNightMode(dark
                ? AppCompatDelegate.MODE_NIGHT_YES
                : AppCompatDelegate.MODE_NIGHT_NO);
    }

    public static boolean isNightNow(Context context) {
        int night = context.getResources().getConfiguration().uiMode
                & Configuration.UI_MODE_NIGHT_MASK;
        return night == Configuration.UI_MODE_NIGHT_YES;
    }

    public static String getLanguage(Context context) {
        String saved = prefs(context).getString(KEY_LANG, LANG_RU);
        return LANG_EN.equals(saved) ? LANG_EN : LANG_RU;
    }

    public static void setLanguage(Context context, String language) {
        String lang = LANG_EN.equals(language) ? LANG_EN : LANG_RU;
        prefs(context).edit().putString(KEY_LANG, lang).commit();
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(lang));
    }

    private static void applyNightMode(Context context) {
        if (!hasThemePreference(context)) {
            AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM);
            return;
        }
        AppCompatDelegate.setDefaultNightMode(isDarkTheme(context)
                ? AppCompatDelegate.MODE_NIGHT_YES
                : AppCompatDelegate.MODE_NIGHT_NO);
    }

    private static SharedPreferences prefs(Context context) {
        return context.getApplicationContext()
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }
}
