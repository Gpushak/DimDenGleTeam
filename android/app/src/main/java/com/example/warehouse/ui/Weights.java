package com.example.warehouse.ui;

import android.content.Context;

import com.example.warehouse.R;

/** Вес в граммах или килограммах на языке интерфейса. */
public final class Weights {

    private Weights() {
    }

    public static String format(Context context, long grams) {
        if (grams >= 1000) {
            return context.getString(R.string.weight_kg, grams / 1000.0);
        }
        return context.getString(R.string.weight_g, grams);
    }

    public static String format(Context context, Integer grams) {
        if (grams == null) {
            return "—";
        }
        return format(context, grams.longValue());
    }
}
