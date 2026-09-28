package com.example.warehouse.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;

import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.model.InventoryItem;
import com.example.warehouse.data.model.ScanRequest;
import com.example.warehouse.data.model.ScanResponse;
import com.example.warehouse.data.repo.ListRepository;
import com.example.warehouse.databinding.ActivityListDetailBinding;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class ListDetailActivity extends AppCompatActivity {

    private ActivityListDetailBinding binding;
    private ItemAdapter adapter;
    private ListRepository repo;
    private long listId;

    private final ActivityResultLauncher<Intent> scanLauncher =
            registerForActivityResult(
                    new ActivityResultContracts.StartActivityForResult(),
                    result -> {
                        if (result.getResultCode() == RESULT_OK && result.getData() != null) {
                            String qr = result.getData().getStringExtra(ScanActivity.EXTRA_QR);
                            if (qr != null) postScan(qr);
                        }
                    });

    private final ActivityResultLauncher<Intent> weighLauncher =
            registerForActivityResult(
                    new ActivityResultContracts.StartActivityForResult(),
                    result -> {
                        if (result.getResultCode() == RESULT_OK) loadItems();
                    });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityListDetailBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        repo = new ListRepository(this);

        listId = getIntent().getLongExtra("list_id", -1);
        String listName = getIntent().getStringExtra("list_name");

        setTitle(listName != null ? listName : "Список");
        binding.tvTitle.setText(listName != null ? listName : "Список");

        adapter = new ItemAdapter(item -> confirmDelete(item));
        binding.rvItems.setLayoutManager(new LinearLayoutManager(this));
        binding.rvItems.setAdapter(adapter);

        binding.btnScan.setOnClickListener(v -> {
            Intent intent = new Intent(this, ScanActivity.class);
            scanLauncher.launch(intent);
        });

        loadItems();
    }

    private void postScan(String qr) {
        setLoading(true);
        ApiClient.api().scan(new ScanRequest(qr, listId)).enqueue(new Callback<ScanResponse>() {
            @Override
            public void onResponse(Call<ScanResponse> call, Response<ScanResponse> response) {
                setLoading(false);
                if (response.isSuccessful() && response.body() != null) {
                    ScanResponse sr = response.body();
                    Intent i = new Intent(ListDetailActivity.this, WeighActivity.class);
                    i.putExtra(WeighActivity.EXTRA_SESSION_ID, sr.sessionId);
                    i.putExtra(WeighActivity.EXTRA_PRODUCT_NAME,
                            sr.productName != null ? sr.productName : ("Товар #" + sr.productId));
                    weighLauncher.launch(i);
                } else {
                    Toast.makeText(ListDetailActivity.this,
                            "Ошибка сканирования: " + response.code(), Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<ScanResponse> call, Throwable t) {
                setLoading(false);
                Toast.makeText(ListDetailActivity.this,
                        "Сеть недоступна: " + t.getMessage(), Toast.LENGTH_LONG).show();
            }
        });
    }

    private void loadItems() {
        setLoading(true);
        repo.loadItems(listId, (items, fromCache) -> runOnUiThread(() -> {
            setLoading(false);
            adapter.setData(items);
            if (fromCache && items.isEmpty()) {
                Toast.makeText(this, "Нет данных и нет сети", Toast.LENGTH_SHORT).show();
            }
        }));
    }

    private void confirmDelete(InventoryItem item) {
        new AlertDialog.Builder(this)
                .setTitle("Удалить позицию?")
                .setMessage(item.productName != null ? item.productName : ("Товар #" + item.productId))
                .setPositiveButton("Удалить", (d, w) -> deleteItem(item))
                .setNegativeButton("Отмена", null)
                .show();
    }

    private void deleteItem(InventoryItem item) {
        ApiClient.api().deleteItem(item.id).enqueue(new Callback<Void>() {
            @Override
            public void onResponse(Call<Void> call, Response<Void> response) {
                if (response.isSuccessful()) {
                    adapter.removeItem(item);
                    repo.deleteItemFromCache(item.id);
                    Toast.makeText(ListDetailActivity.this, "Удалено", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(ListDetailActivity.this,
                            "Ошибка удаления: " + response.code(), Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<Void> call, Throwable t) {
                Toast.makeText(ListDetailActivity.this,
                        "Сеть недоступна: " + t.getMessage(), Toast.LENGTH_LONG).show();
            }
        });
    }

    private void setLoading(boolean loading) {
        binding.progress.setVisibility(loading ? View.VISIBLE : View.GONE);
    }
}