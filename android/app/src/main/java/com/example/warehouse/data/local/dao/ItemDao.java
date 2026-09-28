package com.example.warehouse.data.local.dao;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;

import com.example.warehouse.data.local.entity.ItemEntity;

import java.util.List;

@Dao
public interface ItemDao {

    @Query("SELECT * FROM items WHERE listId = :listId")
    List<ItemEntity> getByList(String listId);

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    void insertAll(List<ItemEntity> items);

    @Query("DELETE FROM items WHERE listId = :listId")
    void clearByList(String listId);

    @Query("DELETE FROM items WHERE id = :id")
    void deleteById(String id);
}