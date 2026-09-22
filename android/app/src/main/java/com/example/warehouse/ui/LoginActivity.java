package com.example.warehouse.ui;

import android.os.Bundle;
import android.view.View;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.local.TokenStore;
import com.example.warehouse.data.model.LoginRequest;
import com.example.warehouse.data.model.LoginResponse;
import com.example.warehouse.databinding.ActivityLoginBinding;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class LoginActivity extends AppCompatActivity {

    private ActivityLoginBinding binding;
    private TokenStore tokenStore;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityLoginBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        tokenStore = new TokenStore(this);

        if (tokenStore.isLoggedIn()) {
            goToMain();
            return;
        }

        binding.btnLogin.setOnClickListener(v -> doLogin());
    }

    private void doLogin() {
        String user = binding.etUsername.getText().toString().trim();
        String pass = binding.etPassword.getText().toString().trim();

        if (user.isEmpty() || pass.isEmpty()) {
            Toast.makeText(this, "Введите логин и пароль", Toast.LENGTH_SHORT).show();
            return;
        }

        setLoading(true);

        ApiClient.api().login(new LoginRequest(user, pass))
                .enqueue(new Callback<LoginResponse>() {
                    @Override
                    public void onResponse(Call<LoginResponse> call, Response<LoginResponse> response) {
                        setLoading(false);
                        if (response.isSuccessful() && response.body() != null) {
                            tokenStore.save(response.body().token, response.body().role);
                            goToMain();
                        } else {
                            Toast.makeText(LoginActivity.this,
                                    "Ошибка входа: " + response.code(), Toast.LENGTH_SHORT).show();
                        }
                    }

                    @Override
                    public void onFailure(Call<LoginResponse> call, Throwable t) {
                        setLoading(false);
                        Toast.makeText(LoginActivity.this,
                                "Сеть недоступна: " + t.getMessage(), Toast.LENGTH_LONG).show();
                    }
                });
    }

    private void setLoading(boolean loading) {
        binding.progress.setVisibility(loading ? View.VISIBLE : View.GONE);
        binding.btnLogin.setEnabled(!loading);
    }

    private void goToMain() {
        Toast.makeText(this, "Успешный вход", Toast.LENGTH_SHORT).show();
    }
}