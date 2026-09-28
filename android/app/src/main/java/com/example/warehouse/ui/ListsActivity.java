package com.example.warehouse.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;

import com.example.warehouse.R;
import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.model.InventoryList;
import com.example.warehouse.databinding.ActivityListsBinding;

import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class ListsActivity extends AppCompatActivity {

    private ActivityListsBinding binding;
    private ListAdapter adapter;

    private final ActivityResultLauncher<Intent> createLauncher =
            registerForActivityResult(
                    new ActivityResultContracts.StartActivityForResult(),
                    result -> {
                        if (result.getResultCode() == RESULT_OK) loadLists();
                    });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityListsBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        adapter = new ListAdapter(list -> {
            Intent i = new Intent(this, ListDetailActivity.class);
            i.putExtra("list_id", list.id);
            i.putExtra("list_name", list.name);
            startActivity(i);
        });

        binding.rvLists.setLayoutManager(new LinearLayoutManager(this));
        binding.rvLists.setAdapter(adapter);

        binding.fabAdd.setOnClickListener(v ->
                createLauncher.launch(new Intent(this, CreateListActivity.class)));

        loadLists();
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        getMenuInflater().inflate(R.menu.menu_lists, menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(@NonNull MenuItem item) {
        if (item.getItemId() == R.id.action_settings) {
            startActivity(new Intent(this, SettingsActivity.class));
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    @Override
    protected void onResume() {
        super.onResume();
        loadLists();
    }

    private void loadLists() {
        setLoading(true);
        ApiClient.api().getLists().enqueue(new Callback<List<InventoryList>>() {
            @Override
            public void onResponse(Call<List<InventoryList>> call, Response<List<InventoryList>> response) {
                setLoading(false);
                if (response.isSuccessful() && response.body() != null) {
                    adapter.setData(response.body());
                } else {
                    Toast.makeText(ListsActivity.this,
                            "Ошибка загрузки: " + response.code(), Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<List<InventoryList>> call, Throwable t) {
                setLoading(false);
                Toast.makeText(ListsActivity.this,
                        "Сеть недоступна: " + t.getMessage(), Toast.LENGTH_LONG).show();
            }
        });
    }

    private void setLoading(boolean loading) {
        binding.progress.setVisibility(loading ? View.VISIBLE : View.GONE);
    }
}