package com.example.warehouse;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

import com.example.warehouse.data.model.LoginRequest;
import com.example.warehouse.data.model.LoginResponse;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;
import retrofit2.Response;

public class ApiServiceTest {

    private MockWebServer server;

    @Before
    public void setUp() throws IOException {
        server = new MockWebServer();
        server.start();
    }

    @After
    public void tearDown() throws IOException {
        server.shutdown();
    }

    @Test
    public void login_returnsToken() throws IOException {
        server.enqueue(new MockResponse()
                .setResponseCode(200)
                .setBody("{\"token\":\"abc123\",\"role\":\"admin\"}"));

        Retrofit retrofit = new Retrofit.Builder()
                .baseUrl(server.url("/"))
                .addConverterFactory(GsonConverterFactory.create())
                .build();

        com.example.warehouse.data.api.ApiService api =
                retrofit.create(com.example.warehouse.data.api.ApiService.class);

        Response<LoginResponse> response = api
                .login(new LoginRequest("user", "pass"))
                .execute();

        assertEquals(200, response.code());
        assertNotNull(response.body());
        assertEquals("abc123", response.body().token);
        assertEquals("admin", response.body().role);
    }
}