package com.example.warehouse.ui;

import android.content.DialogInterface;
import android.content.Intent;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.widget.EditText;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

import com.example.warehouse.BuildConfig;
import com.example.warehouse.adapter.WarehouseAdapter;
import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.api.ServerConfig;
import com.example.warehouse.data.model.BoxContents;
import com.example.warehouse.data.model.BoxNode;
import com.example.warehouse.databinding.ActivityMainBinding;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * Главный экран приложения. Регистрация и аутентификация не используются —
 * приложение сразу открывает структуру склада, сервер доступен без токена.
 */
public class MainActivity extends AppCompatActivity {

    private ActivityMainBinding binding;
    private WarehouseAdapter adapter;

    /** Корень дерева складов (кэш ответа /boxes/tree). */
    private List<BoxNode> treeRoots;

    /** Путь от корня к текущей ячейке (включая саму текущую). */
    private final Deque<BoxNode> path = new ArrayDeque<>();

    /** Запуск QR-сканера и реакция на его результат. */
    private final ActivityResultLauncher<Intent> scanLauncher =
            registerForActivityResult(new ActivityResultContracts.StartActivityForResult(),
                    result -> {
                        if (result.getResultCode() != RESULT_OK
                                || result.getData() == null) {
                            return;
                        }
                        int boxId = result.getData().getIntExtra(ScanActivity.RESULT_BOX_ID, 0);
                        int itemId = result.getData().getIntExtra(ScanActivity.RESULT_ITEM_ID, 0);
                        onScanned(itemId, boxId);
                    });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        ApiClient.init(this);

        adapter = new WarehouseAdapter(this);
        binding.list.setAdapter(adapter);

        binding.btnRefresh.setOnClickListener(v -> loadTree());
        binding.btnUp.setOnClickListener(v -> goUp());
        binding.btnServer.setOnClickListener(v -> showServerDialog());
        binding.btnScan.setOnClickListener(
                v -> scanLauncher.launch(new Intent(this, ScanActivity.class)));
        binding.swipeRefresh.setOnRefreshListener(this::loadTree);

        binding.list.setOnItemClickListener((parent, view, position, id) -> {
            WarehouseAdapter.Row row = adapter.getItem(position);
            if (row != null && row.isBox) {
                openBox(row.box);
            }
        });

        loadTree();
    }

    private void loadTree() {
        setLoading(true);

        ApiClient.api().getBoxTree().enqueue(new Callback<List<BoxNode>>() {
            @Override
            public void onResponse(Call<List<BoxNode>> call, Response<List<BoxNode>> response) {
                setLoading(false);
                binding.swipeRefresh.setRefreshing(false);

                if (response.isSuccessful() && response.body() != null) {
                    treeRoots = response.body();
                    path.clear();
                    renderLevel();
                } else {
                    toast("Ошибка загрузки дерева: " + response.code());
                }
            }

            @Override
            public void onFailure(Call<List<BoxNode>> call, Throwable t) {
                setLoading(false);
                binding.swipeRefresh.setRefreshing(false);
                toast("Сеть недоступна: " + t.getMessage());
            }
        });
    }

    private void openBox(BoxNode box) {
        path.addLast(box);
        loadContents(box);
    }

    /**
     * Реакция на результат QR-сканирования.
     *
     * Если распознан контейнер — переходим в него и подсвечиваем отсканированную
     * позицию в списке. Для типа товара навигации нет: просто сообщаем, что
     * код относится к справочной записи.
     *
     * @param itemId идентификатор позиции товара (0 — если не товар)
     * @param boxId  идентификатор контейнера (0 — если неизвестен)
     */
    private void onScanned(int itemId, int boxId) {
        if (boxId > 0) {
            BoxNode target = findNode(treeRoots, boxId);
            if (target != null) {
                // Пересобираем путь от корня до найденного контейнера,
                // чтобы кнопка «Вверх» вела по иерархии, а не в пустоту.
                path.clear();
                collectPath(treeRoots, boxId, path);
                loadContents(target);
                if (itemId > 0) {
                    highlightItem(itemId);
                }
                return;
            }
            toast("Контейнер не найден в загруженном дереве — обновите");
            return;
        }

        if (itemId > 0) {
            toast("Позиция товара найдена (ID " + itemId + ")");
        } else {
            toast("Отсканирован тип товара — см. сведения в сканере");
        }
    }

    /** Ищет контейнер по id в дереве, загруженном из /boxes/tree. */
    private static BoxNode findNode(List<BoxNode> nodes, int boxId) {
        if (nodes == null) {
            return null;
        }
        for (BoxNode node : nodes) {
            if (node.id == boxId) {
                return node;
            }
            BoxNode found = findNode(node.children, boxId);
            if (found != null) {
                return found;
            }
        }
        return null;
    }

    /** Собирает путь от корня до контейнера (для кнопки «Вверх»). */
    private static boolean collectPath(List<BoxNode> nodes, int boxId, Deque<BoxNode> out) {
        if (nodes == null) {
            return false;
        }
        for (BoxNode node : nodes) {
            if (node.id == boxId) {
                out.addLast(node);
                return true;
            }
            if (collectPath(node.children, boxId, out)) {
                out.addFirst(node);
                return true;
            }
        }
        return false;
    }

    /**
     * Сообщает пользователю позицию товара в открытом контейнере.
     *
     * Список в адаптере плоский, а {@code item_id} в {@link WarehouseAdapter.Row}
     * не хранится, поэтому программно выделить строку нельзя. Вместо этого
     * показываем понятное уведомление с номером позиции.
     */
    private void highlightItem(int itemId) {
        toast("Позиция #" + itemId + " — в открытом контейнере");
    }

    private void goUp() {
        if (!path.isEmpty()) {
            path.removeLast();
            renderLevel();
        }
    }

    /**
     * Верхний уровень: показываем корневые ячейки.
     */
    private void renderLevel() {
        updatePathLabel();

        if (path.isEmpty()) {
            List<WarehouseAdapter.Row> rows = new ArrayList<>();
            if (treeRoots != null) {
                for (BoxNode node : treeRoots) {
                    rows.add(WarehouseAdapter.Row.ofBox(node));
                }
            }
            adapter.setRows(rows);
            return;
        }

        loadContents(path.peekLast());
    }

    /**
     * Содержимое конкретной ячейки: вложенные коробки + товары.
     */
    private void loadContents(BoxNode current) {
        updatePathLabel();
        setLoading(true);

        ApiClient.api().getBoxContents(current.id)
                .enqueue(new Callback<BoxContents>() {
                    @Override
                    public void onResponse(Call<BoxContents> call,
                                           Response<BoxContents> response) {
                        setLoading(false);
                        binding.swipeRefresh.setRefreshing(false);

                        if (response.isSuccessful() && response.body() != null) {
                            BoxContents contents = response.body();
                            List<WarehouseAdapter.Row> rows = new ArrayList<>();

                            for (BoxContents.ChildBox child : contents.child_boxes) {
                                rows.add(WarehouseAdapter.Row.ofBox(toNode(child)));
                            }
                            for (BoxContents.ItemRow item : contents.items) {
                                rows.add(WarehouseAdapter.Row.ofItem(item));
                            }
                            adapter.setRows(rows);
                        } else {
                            toast("Ошибка загрузки содержимого: " + response.code());
                        }
                    }

                    @Override
                    public void onFailure(Call<BoxContents> call, Throwable t) {
                        setLoading(false);
                        binding.swipeRefresh.setRefreshing(false);
                        toast("Сеть недоступна: " + t.getMessage());
                    }
                });
    }

    private static BoxNode toNode(BoxContents.ChildBox child) {
        BoxNode node = new BoxNode();
        node.id = child.id;
        node.name = child.name;
        node.box_type_id = child.box_type_id;
        node.box_type_name = child.box_type_name;
        return node;
    }

    private void updatePathLabel() {
        binding.btnUp.setEnabled(!path.isEmpty());

        StringBuilder sb = new StringBuilder("Склад");
        for (BoxNode node : path) {
            sb.append(" / ").append(node.name);
        }
        binding.tvPath.setText(sb);
    }

    private void setLoading(boolean loading) {
        binding.progress.setVisibility(loading ? View.VISIBLE : View.GONE);
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }

    /** Диалог настройки адреса сервера (для реального телефона — IP компьютера в LAN). */
    private void showServerDialog() {
        EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setText(ServerConfig.getBaseUrl(this));
        input.setSelection(input.getText().length());

        new AlertDialog.Builder(this)
                .setTitle("Адрес сервера")
                .setMessage("Например: http://192.168.1.50:8000\n"
                        + "Для эмулятора Android хост-машина доступна по 10.0.2.2")
                .setView(input)
                .setPositiveButton("Сохранить", (DialogInterface dialog, int which) -> {
                    String url = ServerConfig.normalize(input.getText().toString());
                    if (url.isEmpty()) {
                        toast("Адрес не может быть пустым");
                        return;
                    }
                    ServerConfig.setBaseUrl(this, url);
                    toast("Сервер: " + url);
                    loadTree();
                })
                .setNeutralButton("Сбросить", (DialogInterface dialog, int which) -> {
                    ServerConfig.clearBaseUrl(this);
                    ApiClient.init(this);
                    toast("Использован адрес по умолчанию: "
                            + BuildConfig.API_BASE_URL);
                    loadTree();
                })
                .setNegativeButton("Отмена", null)
                .show();
    }
}
