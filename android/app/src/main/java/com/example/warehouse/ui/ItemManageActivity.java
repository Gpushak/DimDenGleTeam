package com.example.warehouse.ui;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Toast;

import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.api.ItemUpdateBody;
import com.example.warehouse.data.model.BoxNode;
import com.example.warehouse.data.model.ItemSummary;
import com.example.warehouse.data.model.ItemTypeSummary;
import com.example.warehouse.databinding.ActivityItemManageBinding;

import java.util.ArrayList;
import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * Экран редактирования позиции товара: изменение количества, смена типа,
 * перемещение в другой контейнер и удаление.
 *
 * Данные приходят из {@link MainActivity} (тап-эндой или долгое нажатие на
 * строку товара). После изменения количества или удаления ставится
 * {@link #RESULT_CHANGED} — главный экран при возврате обновляет содержимое
 * контейнера. Перемещение и смена типа результат не помечают: позиция после
 * них может покинуть открытый контейнер, но список всё равно актуален до
 * явного обновления (пользователь увидит корректные данные по «Назад»).
 */
public class ItemManageActivity extends AppCompatActivity {

    public static final String EXTRA_ITEM_ID = "extra_item_id";
    public static final String EXTRA_BOX_ID = "extra_box_id";
    /** Ставится, если позиция изменилась так, что список надо перечитать. */
    public static final String RESULT_CHANGED = "result_changed";

    private ActivityItemManageBinding binding;

    private int itemId;
    /** Контейнер, из которого открыли позицию (0 — позиция вне контейнера). */
    private int originBoxId;
    /** Актуальная запись позиции после последнего успешного PATCH. */
    private ItemSummary item;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityItemManageBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        ApiClient.init(this);

        itemId = getIntent().getIntExtra(EXTRA_ITEM_ID, 0);
        originBoxId = getIntent().getIntExtra(EXTRA_BOX_ID, 0);

        binding.btnMinus.setOnClickListener(v -> stepQuantity(-1));
        binding.btnPlus.setOnClickListener(v -> stepQuantity(1));
        binding.btnSaveQuantity.setOnClickListener(v -> saveQuantity());
        binding.btnChangeType.setOnClickListener(v -> showChangeTypeDialog());
        binding.btnMove.setOnClickListener(v -> showMoveDialog());
        binding.btnDelete.setOnClickListener(v -> confirmDelete());

        loadItem();
    }

    /** Подтягивает актуальную запись позиции — сервер источник истины. */
    private void loadItem() {
        setLoading(true);
        ApiClient.api().getItem(itemId).enqueue(new Callback<ItemSummary>() {
            @Override
            public void onResponse(Call<ItemSummary> call,
                                   Response<ItemSummary> response) {
                setLoading(false);
                if (response.isSuccessful() && response.body() != null) {
                    item = response.body();
                    bindItem();
                } else {
                    toast("Ошибка загрузки товара: " + response.code());
                }
            }

            @Override
            public void onFailure(Call<ItemSummary> call, Throwable t) {
                setLoading(false);
                toast("Сеть недоступна: " + t.getMessage());
            }
        });
    }

    private void bindItem() {
        binding.tvTitle.setText(item.item_type_name);

        StringBuilder info = new StringBuilder();
        info.append("Позиция #").append(item.id);
        if (item.weight_g != null) {
            info.append(" · вес единицы: ").append(formatWeight(item.weight_g));
        }
        if (item.total_weight_g != null) {
            info.append(" · общий вес: ").append(formatWeight(item.total_weight_g));
        }
        if (item.box_name != null) {
            info.append("\nКонтейнер: ").append(item.box_name);
        } else {
            info.append("\nБез контейнера");
        }
        binding.tvInfo.setText(info);

        binding.etQuantity.setText(String.valueOf(item.quantity));
    }

    private void stepQuantity(int delta) {
        int current = parseQuantity();
        int next = Math.max(1, current + delta);
        binding.etQuantity.setText(String.valueOf(next));
    }

    private int parseQuantity() {
        try {
            return Integer.parseInt(binding.etQuantity.getText().toString().trim());
        } catch (NumberFormatException e) {
            return item != null ? item.quantity : 1;
        }
    }

    private void saveQuantity() {
        if (item == null) {
            return;
        }
        int quantity = parseQuantity();
        if (quantity < 1) {
            toast("Количество должно быть не меньше 1");
            return;
        }
        if (quantity == item.quantity) {
            toast("Количество не изменилось");
            return;
        }
        patch(ItemUpdateBody.quantity(quantity), true);
    }

    /** Диалог смены типа товара: список справочника GET /item-types. */
    private void showChangeTypeDialog() {
        if (item == null) {
            return;
        }
        setLoading(true);
        ApiClient.api().getItemTypes().enqueue(new Callback<List<ItemTypeSummary>>() {
            @Override
            public void onResponse(Call<List<ItemTypeSummary>> call,
                                   Response<List<ItemTypeSummary>> response) {
                setLoading(false);
                if (!response.isSuccessful() || response.body() == null) {
                    toast("Ошибка загрузки типов: " + response.code());
                    return;
                }
                List<ItemTypeSummary> types = response.body();
                if (types.isEmpty()) {
                    toast("Справочник типов пуст");
                    return;
                }
                CharSequence[] labels = new CharSequence[types.size()];
                for (int i = 0; i < types.size(); i++) {
                    ItemTypeSummary t = types.get(i);
                    labels[i] = t.weight_g != null
                            ? t.name + " (" + formatWeight(t.weight_g) + ")"
                            : t.name;
                }
                new AlertDialog.Builder(ItemManageActivity.this)
                        .setTitle("Новый тип товара")
                        .setItems(labels, (dialog, which) ->
                                patch(ItemUpdateBody.itemType(types.get(which).id), true))
                        .setNegativeButton("Отмена", null)
                        .show();
            }

            @Override
            public void onFailure(Call<List<ItemTypeSummary>> call, Throwable t) {
                setLoading(false);
                toast("Сеть недоступна: " + t.getMessage());
            }
        });
    }

    /**
     * Диалог перемещения: выбор из дерева контейнеров (GET /boxes/tree) плюс
     * пункт «Вынуть из контейнера» (PATCH c box_id = null).
     */
    private void showMoveDialog() {
        if (item == null) {
            return;
        }
        setLoading(true);
        ApiClient.api().getBoxTree().enqueue(new Callback<List<BoxNode>>() {
            @Override
            public void onResponse(Call<List<BoxNode>> call,
                                   Response<List<BoxNode>> response) {
                setLoading(false);
                if (!response.isSuccessful() || response.body() == null) {
                    toast("Ошибка загрузки дерева: " + response.code());
                    return;
                }
                List<BoxNode> flat = new ArrayList<>();
                flatten(response.body(), "", flat);

                // +1 пункт «без контейнера» в начале списка.
                CharSequence[] labels = new CharSequence[flat.size() + 1];
                labels[0] = "⟶ Вынуть из контейнера";
                for (int i = 0; i < flat.size(); i++) {
                    BoxNode node = flat.get(i);
                    boolean here = item.box_id != null && item.box_id == node.id;
                    labels[i + 1] = node.name + (here ? "  (текущий)" : "");
                }

                new AlertDialog.Builder(ItemManageActivity.this)
                        .setTitle("Переместить в контейнер")
                        .setItems(labels, (dialog, which) -> {
                            Integer targetBoxId = which == 0 ? null : flat.get(which - 1).id;
                            patch(ItemUpdateBody.moveTo(targetBoxId), false);
                        })
                        .setNegativeButton("Отмена", null)
                        .show();
            }

            @Override
            public void onFailure(Call<List<BoxNode>> call, Throwable t) {
                setLoading(false);
                toast("Сеть недоступна: " + t.getMessage());
            }
        });
    }

    /** Обход дерева в плоский список с путями в названиях для читаемости. */
    private static void flatten(List<BoxNode> nodes, String prefix, List<BoxNode> out) {
        if (nodes == null) {
            return;
        }
        for (BoxNode node : nodes) {
            out.add(node);
            flatten(node.children, prefix + node.name + " / ", out);
        }
    }

    private void confirmDelete() {
        if (item == null) {
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("Удалить товар?")
                .setMessage(item.item_type_name + " (" + item.quantity + " шт., позиция #"
                        + item.id + ") будет удалена без возможности восстановления.")
                .setPositiveButton("Удалить", (dialog, which) -> deleteItem())
                .setNegativeButton("Отмена", null)
                .show();
    }

    private void deleteItem() {
        setLoading(true);
        ApiClient.api().deleteItem(itemId).enqueue(new Callback<Void>() {
            @Override
            public void onResponse(Call<Void> call, Response<Void> response) {
                setLoading(false);
                if (response.isSuccessful()) {
                    toast("Товар удалён");
                    Intent data = new Intent();
                    data.putExtra(RESULT_CHANGED, true);
                    setResult(RESULT_OK, data);
                    finish();
                } else {
                    toast("Ошибка удаления: " + response.code());
                }
            }

            @Override
            public void onFailure(Call<Void> call, Throwable t) {
                setLoading(false);
                toast("Сеть недоступна: " + t.getMessage());
            }
        });
    }

    /**
     * Отправка PATCH /items/{id}. При успехе перечитываем позицию и ставим
     * RESULT_CHANGED, если список родителя нужно обновить (changed == true:
     * менялись количество или тип — они видны в текущем контейнере; при
     * перемещении позиция уходит в другой контейнер, changed == false).
     */
    private void patch(ItemUpdateBody body, boolean changed) {
        setLoading(true);
        ApiClient.api().updateItem(itemId, body).enqueue(new Callback<ItemSummary>() {
            @Override
            public void onResponse(Call<ItemSummary> call,
                                   Response<ItemSummary> response) {
                setLoading(false);
                if (response.isSuccessful() && response.body() != null) {
                    item = response.body();
                    bindItem();
                    if (changed) {
                        setResult(RESULT_OK, new Intent().putExtra(RESULT_CHANGED, true));
                    }
                    toast("Сохранено");
                } else {
                    toast(readError(response));
                }
            }

            @Override
            public void onFailure(Call<ItemSummary> call, Throwable t) {
                setLoading(false);
                toast("Сеть недоступна: " + t.getMessage());
            }
        });
    }

    /** Извлекает detail из тела ошибки FastAPI (409/404 и т.п.), иначе код. */
    private static String readError(Response<?> response) {
        try {
            if (response.errorBody() != null) {
                String json = response.errorBody().string();
                int idx = json.indexOf("\"detail\"");
                if (idx >= 0) {
                    int start = json.indexOf('"', json.indexOf(':', idx) + 1) + 1;
                    int end = json.indexOf('"', start);
                    if (start > 0 && end > start) {
                        return "Ошибка: " + json.substring(start, end);
                    }
                }
            }
        } catch (Exception ignored) {
            // Не удалось разобрать тело — вернём код ниже.
        }
        return "Ошибка запроса: " + response.code();
    }

    private static String formatWeight(long grams) {
        if (grams >= 1000) {
            return String.format("%.3f кг", grams / 1000.0);
        }
        return grams + " г";
    }

    private void setLoading(boolean loading) {
        // Прогресс-индикатора на экране нет — на время запроса блокируем кнопки
        // и показываем статус в информационном тексте.
        binding.btnMinus.setEnabled(!loading);
        binding.btnPlus.setEnabled(!loading);
        binding.btnSaveQuantity.setEnabled(!loading);
        binding.btnChangeType.setEnabled(!loading);
        binding.btnMove.setEnabled(!loading);
        binding.btnDelete.setEnabled(!loading);

        if (loading) {
            binding.tvInfo.setText("Выполняется запрос…");
        } else if (item != null) {
            bindItem();
        }
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }
}
