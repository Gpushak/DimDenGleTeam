package com.example.warehouse.data.api;

import com.example.warehouse.data.model.BoxContents;
import com.example.warehouse.data.model.BoxNode;
import com.example.warehouse.data.model.ItemSummary;
import com.example.warehouse.data.model.ItemTypeSummary;
import com.example.warehouse.data.model.LookupResult;

import java.util.List;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.DELETE;
import retrofit2.http.GET;
import retrofit2.http.PATCH;
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

    /** Полная запись позиции (ответ совпадает с форматом GET /items/{id}). */
    @GET("items/{itemId}")
    Call<ItemSummary> getItem(@Path("itemId") int itemId);

    /**
     * Частичное обновление позиции: количество и/или контейнер.
     * Сервер принимает только ненулевые поля тела {@link ItemUpdateBody}.
     */
    @PATCH("items/{itemId}")
    Call<ItemSummary> updateItem(@Path("itemId") int itemId,
                                 @Body ItemUpdateBody body);

    @DELETE("items/{itemId}")
    Call<Void> deleteItem(@Path("itemId") int itemId);

    /** Справочник типов товаров — нужен для выбора типа при перемещении. */
    @GET("item-types")
    Call<List<ItemTypeSummary>> getItemTypes();
}