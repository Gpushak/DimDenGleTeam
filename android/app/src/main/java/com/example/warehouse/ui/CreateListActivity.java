package com.example.warehouse.ui;

import android.os.Bundle;
import android.view.View;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.model.CreateListRequest;
import com.example.warehouse.data.model.InventoryList;
import com.example.warehouse.databinding.ActivityCreateListBinding;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class CreateListActivity extends AppCompatActivity {

    private ActivityCreateListBinding binding;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityCreateListBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        binding.btnCreate.setOnClickListener(v -> create());
    }

    private void create() {
        String name = binding.etName.getText().toString().trim();
        if (name.isEmpty()) {
            Toast.makeText(this, "Введите название", Toast.LENGTH_SHORT).show();
            return;
        }

        setLoading(true);
        ApiClient.api().createList(new CreateListRequest(name))
                .enqueue(new Callback<InventoryList>() {
                    @Override
                    public void onResponse(Call<InventoryList> call, Response<InventoryList> response) {
                        setLoading(false);
                        if (response.isSuccessful()) {
                            Toast.makeText(CreateListActivity.this, "Список создан", Toast.LENGTH_SHORT).show();
                            setResult(RESULT_OK);
                            finish();
                        } else {
                            Toast.makeText(CreateListActivity.this,
                                    "Ошибка: " + response.code(), Toast.LENGTH_SHORT).show();
                        }
                    }

                    @Override
                    public void onFailure(Call<InventoryList> call, Throwable t) {
                        setLoading(false);
                        Toast.makeText(CreateListActivity.this,
                                "Сеть недоступна: " + t.getMessage(), Toast.LENGTH_LONG).show();
                    }
                });
    }

    private void setLoading(boolean loading) {
        binding.progress.setVisibility(loading ? View.VISIBLE : View.GONE);
        binding.btnCreate.setEnabled(!loading);
    }
}