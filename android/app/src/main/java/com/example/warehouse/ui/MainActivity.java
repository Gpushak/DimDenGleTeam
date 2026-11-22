package com.example.warehouse.ui;

import android.content.DialogInterface;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

import com.example.warehouse.BuildConfig;
import com.example.warehouse.R;
import com.example.warehouse.adapter.WarehouseAdapter;
import com.example.warehouse.data.AppSettings;
import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.api.ServerConfig;
import com.example.warehouse.data.model.BoxContents;
import com.example.warehouse.data.model.BoxNode;
import com.example.warehouse.data.model.ItemSummary;
import com.example.warehouse.databinding.ActivityMainBinding;
import com.google.android.material.button.MaterialButtonToggleGroup;
import com.google.android.material.materialswitch.MaterialSwitch;
import com.google.android.material.textfield.TextInputEditText;

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

    /** После смены темы или языка активность пересоздаётся — диалог открываем снова. */
    private static final String EXTRA_OPEN_SETTINGS = "extra_open_settings";

    private ActivityMainBinding binding;
    private WarehouseAdapter adapter;

    /** Корень дерева складов (кэш ответа /boxes/tree). */
    private List<BoxNode> treeRoots;

    /** Путь от корня к текущей ячейке (включая саму текущую). */
    private final Deque<BoxNode> path = new ArrayDeque<>();

    /** Отбрасывает устаревший ответ «товары без контейнера», если корень уже ушли. */
    private int unboxedGeneration;

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

    /** Экран редактирования/удаления товара: при возврате перечитываем контейнер. */
    private final ActivityResultLauncher<Intent> itemManageLauncher =
            registerForActivityResult(new ActivityResultContracts.StartActivityForResult(),
                    result -> {
                        if (result.getResultCode() == RESULT_OK
                                && result.getData() != null
                                && result.getData().getBooleanExtra(
                                        ItemManageActivity.RESULT_CHANGED, false)) {
                            refreshCurrentLevel();
                        }
                    });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        ApiClient.init(this);

        adapter = new WarehouseAdapter(this);
        binding.list.setAdapter(adapter);

        binding.btnRefresh.setOnClickListener(v -> refresh());
        binding.btnUp.setOnClickListener(v -> goUp());
        binding.btnServer.setOnClickListener(v -> showServerDialog());
        binding.btnSettings.setOnClickListener(v -> showSettingsDialog());
        binding.btnScan.setOnClickListener(
                v -> scanLauncher.launch(new Intent(this, ScanActivity.class)));
        binding.swipeRefresh.setOnRefreshListener(this::refresh);

        binding.list.setOnItemClickListener((parent, view, position, id) -> {
            WarehouseAdapter.Row row = adapter.getItem(position);
            if (row == null) {
                return;
            }
            if (row.isBox) {
                openBox(row.box);
            } else {
                openItemEditor(row.item.item_id);
            }
        });

        // Долгое нажатие — быстрый доступ к удалению без входа в редактор.
        binding.list.setOnItemLongClickListener((parent, view, position, id) -> {
            WarehouseAdapter.Row row = adapter.getItem(position);
            if (row != null && !row.isBox) {
                confirmDeleteFromList(row.item);
                return true;
            }
            return false;
        });

        updatePathLabel();
        loadTree();

        if (getIntent().getBooleanExtra(EXTRA_OPEN_SETTINGS, false)) {
            getIntent().removeExtra(EXTRA_OPEN_SETTINGS);
            binding.getRoot().post(this::showSettingsDialog);
        }
    }

    /**
     * «Обновить» и свайп: заново читает дерево и текущий уровень.
     * Открытый контейнер сохраняется, чтобы список совпал с десктопом,
     * который тоже остаётся в выбранном контейнере.
     */
    private void refresh() {
        List<Integer> ids = new ArrayList<>();
        for (BoxNode node : path) {
            ids.add(node.id);
        }
        loadTree(ids);
    }

    /** Полная перезагрузка с корня (старт и смена адреса сервера). */
    private void loadTree() {
        loadTree(null);
    }

    private void loadTree(List<Integer> keepIds) {
        setLoading(true);

        ApiClient.api().getBoxTree().enqueue(new Callback<List<BoxNode>>() {
            @Override
            public void onResponse(Call<List<BoxNode>> call, Response<List<BoxNode>> response) {
                setLoading(false);
                binding.swipeRefresh.setRefreshing(false);

                if (response.isSuccessful() && response.body() != null) {
                    treeRoots = response.body();
                    path.clear();
                    if (keepIds != null) {
                        for (int id : keepIds) {
                            BoxNode node = findNode(treeRoots, id);
                            if (node == null) {
                                break;
                            }
                            path.addLast(node);
                        }
                    }
                    renderLevel();
                } else {
                    toast(getString(R.string.error_load_tree, response.code()));
                }
            }

            @Override
            public void onFailure(Call<List<BoxNode>> call, Throwable t) {
                setLoading(false);
                binding.swipeRefresh.setRefreshing(false);
                toast(getString(R.string.error_network, t.getMessage()));
            }
        });
    }

    private void openBox(BoxNode box) {
        path.addLast(box);
        loadContents(box);
    }

    /** Открывает экран редактирования позиции товара. */
    private void openItemEditor(int itemId) {
        BoxNode current = path.peekLast();
        openItemEditor(itemId, current != null ? current.id : 0);
    }

    private void openItemEditor(int itemId, int boxId) {
        Intent intent = new Intent(this, ItemManageActivity.class);
        intent.putExtra(ItemManageActivity.EXTRA_ITEM_ID, itemId);
        intent.putExtra(ItemManageActivity.EXTRA_BOX_ID, boxId);
        itemManageLauncher.launch(intent);
    }

    /**
     * Быстрое удаление позиции из списка (долгое нажатие) с подтверждением.
     * Сервер отвечает 204/200 — в любом случае перечитываем контейнер.
     */
    private void confirmDeleteFromList(BoxContents.ItemRow item) {
        new AlertDialog.Builder(this)
                .setTitle(R.string.delete_item_title)
                .setMessage(getString(R.string.delete_item_message,
                        item.item_type_name, item.quantity, item.item_id))
                .setPositiveButton(R.string.action_delete, (dialog, which) ->
                        ApiClient.api().deleteItem(item.item_id).enqueue(new Callback<Void>() {
                            @Override
                            public void onResponse(Call<Void> call, Response<Void> response) {
                                if (response.isSuccessful()) {
                                    toast(getString(R.string.toast_item_deleted));
                                    refreshCurrentLevel();
                                } else {
                                    toast(getString(R.string.error_delete, response.code()));
                                }
                            }

                            @Override
                            public void onFailure(Call<Void> call, Throwable t) {
                                toast(getString(R.string.error_network, t.getMessage()));
                            }
                        }))
                .setNegativeButton(R.string.action_cancel, null)
                .show();
    }

    /** Перечитывает текущий уровень: содержимое контейнера или дерево (для корня). */
    private void refreshCurrentLevel() {
        BoxNode current = path.peekLast();
        if (current != null) {
            loadContents(current);
        } else {
            loadTree();
        }
    }

    /**
     * Реакция на результат QR-сканирования.
     *
     * Товар открывается в редакторе. Контейнер — переход в него.
     * Тип товара остаётся в диалоге сканера.
     */
    private void onScanned(int itemId, int boxId) {
        if (itemId > 0) {
            openItemEditor(itemId, boxId);
            return;
        }
        if (boxId > 0) {
            BoxNode target = findNode(treeRoots, boxId);
            if (target != null) {
                path.clear();
                collectPath(treeRoots, boxId, path);
                loadContents(target);
                return;
            }
            toast(getString(R.string.error_box_not_in_tree));
            return;
        }
        toast(getString(R.string.toast_scanned_type));
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

    private void goUp() {
        if (!path.isEmpty()) {
            path.removeLast();
            renderLevel();
        }
    }

    /**
     * Корень склада: контейнеры верхнего уровня и позиции без контейнера.
     * Вторые есть на сервере и в десктопе, в дереве коробок их нет.
     */
    private void showRoots() {
        List<WarehouseAdapter.Row> rows = new ArrayList<>();
        if (treeRoots != null) {
            for (BoxNode node : treeRoots) {
                rows.add(WarehouseAdapter.Row.ofBox(node));
            }
        }
        adapter.setRows(rows);

        final int generation = ++unboxedGeneration;
        ApiClient.api().getUnboxedItems(true).enqueue(new Callback<List<ItemSummary>>() {
            @Override
            public void onResponse(Call<List<ItemSummary>> call,
                                   Response<List<ItemSummary>> response) {
                if (generation != unboxedGeneration || !path.isEmpty()) {
                    return;
                }
                if (!response.isSuccessful() || response.body() == null) {
                    toast(getString(R.string.error_unboxed, response.code()));
                    return;
                }
                List<WarehouseAdapter.Row> combined = new ArrayList<>();
                if (treeRoots != null) {
                    for (BoxNode node : treeRoots) {
                        combined.add(WarehouseAdapter.Row.ofBox(node));
                    }
                }
                for (ItemSummary summary : response.body()) {
                    combined.add(WarehouseAdapter.Row.ofItem(toUnboxedRow(summary)));
                }
                adapter.setRows(combined);
            }

            @Override
            public void onFailure(Call<List<ItemSummary>> call, Throwable t) {
                if (generation != unboxedGeneration || !path.isEmpty()) {
                    return;
                }
                toast(getString(R.string.error_network, t.getMessage()));
            }
        });
    }

    private BoxContents.ItemRow toUnboxedRow(ItemSummary summary) {
        BoxContents.ItemRow row = new BoxContents.ItemRow();
        row.item_id = summary.id;
        row.item_type_id = summary.item_type_id;
        row.item_type_name = summary.item_type_name;
        row.weight_g = summary.weight_g;
        row.quantity = summary.quantity;
        row.total_weight_g = summary.total_weight_g;
        row.box_name = getString(R.string.no_location);
        return row;
    }

    /**
     * Верхний уровень: показываем корневые ячейки.
     */
    private void renderLevel() {
        updatePathLabel();

        if (path.isEmpty()) {
            showRoots();
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
                            toast(getString(R.string.error_load_contents, response.code()));
                        }
                    }

                    @Override
                    public void onFailure(Call<BoxContents> call, Throwable t) {
                        setLoading(false);
                        binding.swipeRefresh.setRefreshing(false);
                        toast(getString(R.string.error_network, t.getMessage()));
                    }
                });
    }

    /**
     * Имя и тип берутся из свежего {@code /contents}. Из кэша дерева — только
     * вложенные узлы, чтобы счётчик «вложенных» не обнулялся.
     */
    private BoxNode toNode(BoxContents.ChildBox child) {
        BoxNode node = new BoxNode();
        node.id = child.id;
        node.name = child.name;
        node.box_type_id = child.box_type_id;
        node.box_type_name = child.box_type_name;
        BoxNode known = findNode(treeRoots, child.id);
        if (known != null && known.children != null) {
            node.children = known.children;
        }
        return node;
    }

    private void updatePathLabel() {
        binding.btnUp.setEnabled(!path.isEmpty());

        StringBuilder sb = new StringBuilder(getString(R.string.warehouse_root));
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

    /** Диалог настройки адреса сервера. */
    private void showServerDialog() {
        View view = getLayoutInflater().inflate(R.layout.dialog_server_config, null);
        TextInputEditText input = view.findViewById(R.id.etBaseUrl);
        String current = ServerConfig.getBaseUrl(this);
        input.setText(current);
        if (input.getText() != null) {
            input.setSelection(input.getText().length());
        }

        new AlertDialog.Builder(this)
                .setTitle(R.string.action_server)
                .setView(view)
                .setPositiveButton(R.string.action_save, (DialogInterface dialog, int which) -> {
                    CharSequence typed = input.getText();
                    String url = ServerConfig.normalize(typed != null ? typed.toString() : "");
                    if (url.isEmpty()) {
                        toast(getString(R.string.server_address_empty));
                        return;
                    }
                    ServerConfig.setBaseUrl(this, url);
                    toast(getString(R.string.server_set, url));
                    loadTree();
                })
                .setNeutralButton(R.string.action_reset, (DialogInterface dialog, int which) -> {
                    ServerConfig.clearBaseUrl(this);
                    toast(getString(R.string.server_reset, BuildConfig.API_BASE_URL));
                    loadTree();
                })
                .setNegativeButton(R.string.action_cancel, null)
                .show();
    }

    /** Тема применяется сразу, язык переключает весь интерфейс. */
    private void showSettingsDialog() {
        View view = getLayoutInflater().inflate(R.layout.dialog_settings, null);
        MaterialSwitch themeSwitch = view.findViewById(R.id.switchTheme);
        MaterialButtonToggleGroup language = view.findViewById(R.id.toggleLanguage);

        themeSwitch.setChecked(AppSettings.isNightNow(this));
        themeSwitch.setOnCheckedChangeListener((button, checked) -> {
            if (checked == AppSettings.isNightNow(this)) {
                AppSettings.setDarkTheme(this, checked);
                return;
            }
            keepSettingsOpen();
            AppSettings.setDarkTheme(this, checked);
        });

        language.check(AppSettings.LANG_EN.equals(AppSettings.getLanguage(this))
                ? R.id.btnLangEn
                : R.id.btnLangRu);
        language.addOnButtonCheckedListener((group, checkedId, isChecked) -> {
            if (!isChecked) {
                return;
            }
            String lang = checkedId == R.id.btnLangEn
                    ? AppSettings.LANG_EN
                    : AppSettings.LANG_RU;
            if (lang.equals(AppSettings.getLanguage(this))) {
                return;
            }
            keepSettingsOpen();
            AppSettings.setLanguage(this, lang);
        });

        new AlertDialog.Builder(this)
                .setTitle(R.string.settings_title)
                .setView(view)
                .setNegativeButton(R.string.action_close, null)
                .show();
    }

    private void keepSettingsOpen() {
        getIntent().putExtra(EXTRA_OPEN_SETTINGS, true);
    }
}
