package com.example.warehouse.ui;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.warehouse.data.local.SettingsStore;
import com.example.warehouse.data.local.TokenStore;
import com.example.warehouse.databinding.ActivitySettingsBinding;

public class SettingsActivity extends AppCompatActivity {

    private ActivitySettingsBinding binding;
    private SettingsStore settingsStore;
    private TokenStore tokenStore;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivitySettingsBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        settingsStore = new SettingsStore(this);
        tokenStore = new TokenStore(this);

        binding.etBaseUrl.setText(settingsStore.getBaseUrl());

        binding.btnSave.setOnClickListener(v -> {
            String url = binding.etBaseUrl.getText().toString().trim();
            if (url.isEmpty()) {
                Toast.makeText(this, "Введите адрес", Toast.LENGTH_SHORT).show();
                return;
            }
            settingsStore.setBaseUrl(url);
            Toast.makeText(this, "Сохранено. Адрес применится при следующем запросе.",
                    Toast.LENGTH_LONG).show();
        });

        binding.btnLogout.setOnClickListener(v -> {
            tokenStore.clear();
            Intent i = new Intent(this, LoginActivity.class);
            i.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(i);
            finish();
        });
    }
}