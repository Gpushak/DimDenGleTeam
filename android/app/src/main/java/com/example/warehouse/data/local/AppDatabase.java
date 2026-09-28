package com.example.warehouse.data.local;

import android.content.Context;

import androidx.room.Database;
import androidx.room.Room;
import androidx.room.RoomDatabase;

import com.example.warehouse.data.local.dao.ItemDao;
import com.example.warehouse.data.local.dao.ListDao;
import com.example.warehouse.data.local.entity.ItemEntity;
import com.example.warehouse.data.local.entity.ListEntity;

@Database(
        entities = {ListEntity.class, ItemEntity.class},
        version = 1,
        exportSchema = false
)
public abstract class AppDatabase extends RoomDatabase {

    private static volatile AppDatabase INSTANCE;

    public abstract ListDao listDao();
    public abstract ItemDao itemDao();

    public static AppDatabase get(Context ctx) {
        if (INSTANCE == null) {
            synchronized (AppDatabase.class) {
                if (INSTANCE == null) {
                    INSTANCE = Room.databaseBuilder(
                                    ctx.getApplicationContext(),
                                    AppDatabase.class,
                                    "warehouse.db")
                            .fallbackToDestructiveMigration()
                            .build();
                }
            }
        }
        return INSTANCE;
    }
}