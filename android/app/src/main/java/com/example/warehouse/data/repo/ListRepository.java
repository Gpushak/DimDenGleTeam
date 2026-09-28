package com.example.warehouse.data.repo;

import android.content.Context;

import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.local.AppDatabase;
import com.example.warehouse.data.model.InventoryItem;
import com.example.warehouse.data.model.InventoryList;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class ListRepository {

    public interface ListsCallback {
        void onData(List<InventoryList> lists, boolean fromCache);
    }

    public interface ItemsCallback {
        void onData(List<InventoryItem> items, boolean fromCache);
    }

    private final AppDatabase db;
    private final ExecutorService io = Executors.newSingleThreadExecutor();

    public ListRepository(Context ctx) {
        db = AppDatabase.get(ctx);
    }

    public void loadLists(ListsCallback cb) {
        ApiClient.api().getLists().enqueue(new Callback<List<InventoryList>>() {
            @Override
            public void onResponse(Call<List<InventoryList>> call, Response<List<InventoryList>> response) {
                if (response.isSuccessful() && response.body() != null) {
                    final List<InventoryList> fresh = response.body();
                    io.execute(() -> {
                        List<com.example.warehouse.data.local.entity.ListEntity> entities = new ArrayList<>();
                        for (InventoryList l : fresh) entities.add(Mappers.toEntity(l));
                        db.listDao().clear();
                        db.listDao().insertAll(entities);
                    });
                    cb.onData(fresh, false);
                } else {
                    loadListsFromCache(cb);
                }
            }

            @Override
            public void onFailure(Call<List<InventoryList>> call, Throwable t) {
                loadListsFromCache(cb);
            }
        });
    }

    private void loadListsFromCache(ListsCallback cb) {
        io.execute(() -> {
            List<InventoryList> cached = Mappers.toListModel(db.listDao().getAll());
            cb.onData(cached, true);
        });
    }

    public void loadItems(long listId, ItemsCallback cb) {
        ApiClient.api().getListItems(listId).enqueue(new Callback<List<InventoryItem>>() {
            @Override
            public void onResponse(Call<List<InventoryItem>> call, Response<List<InventoryItem>> response) {
                if (response.isSuccessful() && response.body() != null) {
                    final List<InventoryItem> fresh = response.body();
                    io.execute(() -> {
                        List<com.example.warehouse.data.local.entity.ItemEntity> entities = new ArrayList<>();
                        for (InventoryItem i : fresh) entities.add(Mappers.toEntity(i, listId));
                        db.itemDao().clearByList(String.valueOf(listId));
                        db.itemDao().insertAll(entities);
                    });
                    cb.onData(fresh, false);
                } else {
                    loadItemsFromCache(listId, cb);
                }
            }

            @Override
            public void onFailure(Call<List<InventoryItem>> call, Throwable t) {
                loadItemsFromCache(listId, cb);
            }
        });
    }

    private void loadItemsFromCache(long listId, ItemsCallback cb) {
        io.execute(() -> {
            List<InventoryItem> cached = Mappers.toItemModel(db.itemDao().getByList(String.valueOf(listId)));
            cb.onData(cached, true);
        });
    }

    public void deleteItemFromCache(long itemId) {
        io.execute(() -> db.itemDao().deleteById(String.valueOf(itemId)));
    }
}