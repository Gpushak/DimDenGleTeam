package com.example.warehouse;

import android.app.Application;

import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.sync.SyncScheduler;

public class WarehouseApp extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        ApiClient.init(this);
        SyncScheduler.schedulePeriodic(this);
    }
}