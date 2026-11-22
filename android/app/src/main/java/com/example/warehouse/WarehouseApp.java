package com.example.warehouse;

import android.app.Application;

import com.example.warehouse.data.AppSettings;

/** Применяет сохранённые тему и язык до открытия любого экрана. */
public class WarehouseApp extends Application {

    @Override
    public void onCreate() {
        super.onCreate();
        AppSettings.apply(this);
    }
}
