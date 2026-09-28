package com.example.warehouse.data.local.dao;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;

import com.example.warehouse.data.local.entity.ListEntity;

import java.util.List;

@Dao
public interface ListDao {

    @Query("SELECT * FROM lists")
    List<ListEntity> getAll();

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    void insertAll(List<ListEntity> lists);

    @Query("DELETE FROM lists")
    void clear();
}