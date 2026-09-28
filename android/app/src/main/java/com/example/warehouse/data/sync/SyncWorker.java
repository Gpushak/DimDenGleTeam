package com.example.warehouse.data.sync;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.local.AppDatabase;
import com.example.warehouse.data.local.entity.ListEntity;
import com.example.warehouse.data.model.InventoryList;
import com.example.warehouse.data.repo.Mappers;

import java.util.ArrayList;
import java.util.List;

import retrofit2.Response;

public class SyncWorker extends Worker {

    public static final String WORK_NAME = "warehouse_sync";

    public SyncWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        try {
            Response<List<InventoryList>> response = ApiClient.api().getLists().execute();
            if (!response.isSuccessful() || response.body() == null) {
                return Result.retry();
            }

            List<ListEntity> entities = new ArrayList<>();
            for (InventoryList l : response.body()) {
                entities.add(Mappers.toEntity(l));
            }

            AppDatabase db = AppDatabase.get(getApplicationContext());
            db.listDao().clear();
            db.listDao().insertAll(entities);

            return Result.success();
        } catch (Exception e) {
            return Result.retry();
        }
    }
}