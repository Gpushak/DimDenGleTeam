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
import com.example.warehouse.data.repo.ListRepository;
import com.example.warehouse.data.sync.SyncScheduler;
import com.example.warehouse.databinding.ActivityListsBinding;

public class ListsActivity extends AppCompatActivity {

    private ActivityListsBinding binding;
    private ListAdapter adapter;
    private ListRepository repo;

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

        repo = new ListRepository(this);

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
        if (item.getItemId() == R.id.action_refresh) {
            SyncScheduler.runNow(this);
            binding.getRoot().postDelayed(this::loadLists, 1500);
            Toast.makeText(this, "Синхронизация запущена", Toast.LENGTH_SHORT).show();
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
        repo.loadLists((lists, fromCache) -> runOnUiThread(() -> {
            setLoading(false);
            adapter.setData(lists);
            if (fromCache && lists.isEmpty()) {
                Toast.makeText(this, "Нет данных и нет сети", Toast.LENGTH_SHORT).show();
            }
        }));
    }

    private void setLoading(boolean loading) {
        binding.progress.setVisibility(loading ? View.VISIBLE : View.GONE);
    }
}