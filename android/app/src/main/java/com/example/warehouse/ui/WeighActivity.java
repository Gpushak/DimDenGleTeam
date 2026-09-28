package com.example.warehouse.ui;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.model.WeighSession;
import com.example.warehouse.databinding.ActivityWeighBinding;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class WeighActivity extends AppCompatActivity {

    public static final String EXTRA_SESSION_ID = "session_id";
    public static final String EXTRA_PRODUCT_NAME = "product_name";

    private ActivityWeighBinding binding;
    private long sessionId;
    private WeighSession current;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean polling = false;

    private final Runnable pollTask = new Runnable() {
        @Override
        public void run() {
            if (!polling) return;
            fetchSession();
            handler.postDelayed(this, 1500);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityWeighBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        sessionId = getIntent().getLongExtra(EXTRA_SESSION_ID, -1);
        String productName = getIntent().getStringExtra(EXTRA_PRODUCT_NAME);

        binding.tvProduct.setText(productName != null ? productName : "Взвешивание");
        binding.btnConfirm.setEnabled(false);

        binding.btnConfirm.setOnClickListener(v -> confirm());
    }

    @Override
    protected void onResume() {
        super.onResume();
        polling = true;
        handler.post(pollTask);
    }

    @Override
    protected void onPause() {
        super.onPause();
        polling = false;
        handler.removeCallbacks(pollTask);
    }

    private void fetchSession() {
        ApiClient.api().getWeighSession(sessionId).enqueue(new Callback<WeighSession>() {
            @Override
            public void onResponse(Call<WeighSession> call, Response<WeighSession> response) {
                if (response.isSuccessful() && response.body() != null) {
                    current = response.body();
                    render(current);
                } else {
                    binding.tvStatus.setText("Ошибка: " + response.code());
                }
            }

            @Override
            public void onFailure(Call<WeighSession> call, Throwable t) {
                binding.tvStatus.setText("Сеть недоступна: " + t.getMessage());
            }
        });
    }

    private void render(WeighSession s) {
        binding.tvGross.setText(String.format("Брутто: %.3f кг", s.gross));
        binding.tvTare.setText(String.format("Тара: %.3f кг", s.tare));
        binding.tvNet.setText(String.format("Нетто: %.3f кг", s.net));

        if (s.stable) {
            binding.tvStatus.setText("Вес стабилен");
            binding.btnConfirm.setEnabled(true);
        } else {
            binding.tvStatus.setText("Ожидание стабильного веса...");
            binding.btnConfirm.setEnabled(false);
        }
    }

    private void confirm() {
        if (current == null) return;
        setLoading(true);

        ApiClient.api().confirmWeigh(current).enqueue(new Callback<Void>() {
            @Override
            public void onResponse(Call<Void> call, Response<Void> response) {
                setLoading(false);
                if (response.isSuccessful()) {
                    Toast.makeText(WeighActivity.this, "Операция сохранена", Toast.LENGTH_SHORT).show();
                    setResult(RESULT_OK);
                    finish();
                } else {
                    Toast.makeText(WeighActivity.this,
                            "Ошибка: " + response.code(), Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<Void> call, Throwable t) {
                setLoading(false);
                Toast.makeText(WeighActivity.this,
                        "Сеть недоступна: " + t.getMessage(), Toast.LENGTH_LONG).show();
            }
        });
    }

    private void setLoading(boolean loading) {
        binding.progress.setVisibility(loading ? View.VISIBLE : View.GONE);
        binding.btnConfirm.setEnabled(!loading && current != null && current.stable);
    }
}