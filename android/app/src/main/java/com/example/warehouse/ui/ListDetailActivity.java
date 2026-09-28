package com.example.warehouse.ui;

import android.os.Bundle;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

public class ListDetailActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        long listId = getIntent().getLongExtra("list_id", -1);
        String listName = getIntent().getStringExtra("list_name");
        Toast.makeText(this, "Список: " + listName + " (#" + listId + ")", Toast.LENGTH_SHORT).show();
        finish();
    }
}