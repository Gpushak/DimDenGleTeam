package com.example.warehouse.data.api;

import com.example.warehouse.data.model.BoxContents;
import com.example.warehouse.data.model.BoxNode;
import com.example.warehouse.data.model.LookupResult;

import java.util.List;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Path;
import retrofit2.http.Query;

/**
 * Сервер работает без аутентификации, поэтому запросы отправляются без токена.
 */
public interface ApiService {

    @GET("boxes/tree")
    Call<List<BoxNode>> getBoxTree();

    @GET("boxes/{boxId}/contents")
    Call<BoxContents> getBoxContents(@Path("boxId") int boxId);

    /**
     * Разбор QR-кода вида {@code qwentory:item:<id>}, {@code qwentory:type:<id>}
     * или {@code qwentory:box:<id>}.
     *
     * @param code полное содержимое QR-кода
     */
    @GET("lookup")
    Call<LookupResult> lookup(@Query("code") String code);
}