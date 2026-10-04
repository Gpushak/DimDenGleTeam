package com.example.warehouse.ui;

import android.Manifest;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.Image;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.widget.EditText;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageAnalysis;
import androidx.camera.core.ImageProxy;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.core.content.ContextCompat;

import com.example.warehouse.data.api.ApiClient;
import com.example.warehouse.data.model.BoxContents;
import com.example.warehouse.data.model.BoxSummary;
import com.example.warehouse.data.model.ItemSummary;
import com.example.warehouse.data.model.ItemTypeSummary;
import com.example.warehouse.data.model.LookupResult;
import com.example.warehouse.data.model.QrCode;
import com.example.warehouse.databinding.ActivityScanBinding;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.mlkit.vision.barcode.BarcodeScanner;
import com.google.mlkit.vision.barcode.BarcodeScannerOptions;
import com.google.mlkit.vision.barcode.BarcodeScanning;
import com.google.mlkit.vision.barcode.common.Barcode;
import com.google.mlkit.vision.common.InputImage;

import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * Сканирование QR-кодов, сгенерированных десктопным приложением, и получение
 * сведений о товаре / типе товара / контейнере с сервера.
 *
 * Формат кодов — {@code qwentory:<kind>:<id>}. Распознанный код отправляется
 * в {@code GET /lookup?code=...}, результат показывается диалогом.
 *
 * Активность возвращает результат вызывающей стороне через
 * {@link #setResult}: {@link #RESULT_ITEM_ID} и {@link #RESULT_BOX_ID}
 * (0, если не применимо), чтобы {@link MainActivity} мог перейти в контейнер,
 * где находится найденный товар.
 */
public class ScanActivity extends AppCompatActivity {

    /** Идентификатор отсканированного товара (0 — если отсканировано не товар). */
    public static final String RESULT_ITEM_ID = "item_id";
    /** Идентификатор контейнера, где лежит товар (0 — неизвестно). */
    public static final String RESULT_BOX_ID = "box_id";

    private static final long RESCAN_COOLDOWN_MS = 1200L;

    private ActivityScanBinding binding;
    private ExecutorService analysisExecutor;
    private BarcodeScanner scanner;

    /** Пока идёт распознавание кадра — чтобы не нагружать ML Kit. */
    private final AtomicBoolean analyzing = new AtomicBoolean(false);
    /** Недавно обработанный код: защита от повторного запроса на каждый кадр. */
    private volatile String lastPayload;
    private volatile long lastScanAt;
    /** Запрос к серверу уже в работе — не отправляем новый до ответа. */
    private volatile boolean requestInFlight;

    private final ActivityResultLauncher<String> permissionLauncher =
            registerForActivityResult(new ActivityResultContracts.RequestPermission(),
                    granted -> {
                        if (Boolean.TRUE.equals(granted)) {
                            startCamera();
                        } else {
                            onCameraUnavailable("Нет доступа к камере. Разрешите его в настройках или введите код вручную.");
                        }
                    });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityScanBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        ApiClient.init(this);

        analysisExecutor = Executors.newSingleThreadExecutor();
        // Сканируем только QR-коды: остальные форматы не нужны и замедляют
        // распознавание (обход форматов идёт по очереди).
        BarcodeScannerOptions scannerOptions = new BarcodeScannerOptions.Builder()
                .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                .build();
        scanner = BarcodeScanning.getClient(scannerOptions);

        binding.btnManual.setOnClickListener(v -> promptManualEntry());

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED) {
            startCamera();
        } else {
            permissionLauncher.launch(Manifest.permission.CAMERA);
        }
    }

    // ───────────────────────────────────────────────────────────── камера

    private void startCamera() {
        // getInstance() возвращает ListenableFuture: провайдер создаётся
        // асинхронно, готовый объект получаем уже в addListener.
        ListenableFuture<ProcessCameraProvider> future =
                ProcessCameraProvider.getInstance(this);

        future.addListener(() -> {
            try {
                ProcessCameraProvider provider = future.get();

                Preview preview = new Preview.Builder().build();
                preview.setSurfaceProvider(binding.preview.getSurfaceProvider());

                // KEEP_ONLY_LATEST: обрабатываем только последний кадр,
                // иначе очередь кадров будет расти без пользы.
                ImageAnalysis analysis = new ImageAnalysis.Builder()
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .build();
                analysis.setAnalyzer(analysisExecutor, this::analyzeFrame);

                provider.unbindAll();
                provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA,
                        preview, analysis);

            } catch (Exception e) {
                onCameraUnavailable("Не удалось запустить камеру: " + e.getMessage());
            }
        }, ContextCompat.getMainExecutor(this));
    }

    /** Распознавание одного кадра. Вызывается из фонового потока. */
    private void analyzeFrame(@NonNull ImageProxy imageProxy) {
        Image mediaImage = imageProxy.getImage();
        if (mediaImage == null || !analyzing.compareAndSet(false, true)) {
            imageProxy.close();
            return;
        }

        InputImage image = InputImage.fromMediaImage(
                mediaImage, imageProxy.getImageInfo().getRotationDegrees());

        scanner.process(image)
                .addOnSuccessListener(this::onBarcodes)
                .addOnCompleteListener(task -> {
                    analyzing.set(false);
                    imageProxy.close();
                });
    }

    private void onBarcodes(List<Barcode> barcodes) {
        if (barcodes.isEmpty()) {
            return;
        }

        String raw = barcodes.get(0).getRawValue();
        QrCode code = QrCode.parse(raw);
        if (code == null) {
            // Чужой QR-код: сообщаем один раз, чтобы не спамить на каждом кадре.
            if (!String.valueOf(raw).equals(lastPayload)) {
                lastPayload = String.valueOf(raw);
                runOnUiThread(() -> setStatus("Это не складской QR-код. Ожидается " + QrCode.SCHEME + ":item|type|box:<id>"));
            }
            return;
        }

        long now = System.currentTimeMillis();
        if (requestInFlight) {
            return;
        }
        if (code.payload().equals(lastPayload) && now - lastScanAt < RESCAN_COOLDOWN_MS) {
            return;
        }

        lastPayload = code.payload();
        lastScanAt = now;
        runOnUiThread(() -> lookup(code));
    }

    private void onCameraUnavailable(String reason) {
        binding.progress.setVisibility(View.GONE);
        setStatus(reason);
        binding.btnManual.setVisibility(View.VISIBLE);
    }

    // ────────────────────────────────────────────────────── запрос к серверу

    private void lookup(QrCode code) {
        requestInFlight = true;
        binding.progress.setVisibility(View.VISIBLE);
        setStatus("Запрос " + code.payload() + " …");

        ApiClient.api().lookup(code.payload()).enqueue(new Callback<LookupResult>() {
            @Override
            public void onResponse(Call<LookupResult> call, Response<LookupResult> response) {
                requestInFlight = false;
                binding.progress.setVisibility(View.GONE);

                LookupResult body = response.body();
                if (response.isSuccessful() && body != null) {
                    showResult(code, body);
                } else {
                    setStatus("Сервер не нашёл объект по коду " + code.payload()
                            + " (HTTP " + response.code() + ")");
                    // body здесь может быть null — результат не сбрасываем,
                    // чтобы MainActivity не пытался перейти по несуществующему id.
                    setResult(RESULT_CANCELED);
                    resetScanGuard();
                }
            }

            @Override
            public void onFailure(Call<LookupResult> call, Throwable t) {
                requestInFlight = false;
                binding.progress.setVisibility(View.GONE);
                setStatus("Сеть недоступна: " + t.getMessage());
            }
        });
    }

    private void showResult(QrCode code, LookupResult result) {
        setStatus("Найдено: " + describe(result));

        releaseResult(result);

        new AlertDialog.Builder(this)
                .setTitle(titleFor(result))
                .setMessage(messageFor(result))
                .setPositiveButton("Закрыть", (dialog, which) -> dialog.dismiss())
                .setOnDismissListener(dialog -> resetScanGuard())
                .show();
    }

    /**
     * Прокидывает результат вызывающей Activity, чтобы MainActivity мог
     * перейти в найденный контейнер.
     */
    private void releaseResult(LookupResult result) {
        int itemId = 0;
        int boxId = 0;

        if ("item".equals(result.kind) && result.item != null) {
            itemId = result.item.id;
            boxId = result.item.box_id != null ? result.item.box_id : 0;
        } else if ("box".equals(result.kind) && result.box != null) {
            boxId = result.box.id;
        }

        setResult(RESULT_OK, new Intent()
                .putExtra(RESULT_ITEM_ID, itemId)
                .putExtra(RESULT_BOX_ID, boxId));

        // Снимаем «кулдаун»: после закрытия диалога можно сканировать тот же код заново.
        lastScanAt = 0;
    }

    /**
     * Сбрасывает защиту от повторного срабатывания, когда диалог закрыт:
     * тот же код можно отсканировать снова намеренно.
     */
    private void resetScanGuard() {
        lastPayload = null;
        lastScanAt = 0;
    }

    // ─────────────────────────────────────────────────────── форматирование

    private String titleFor(LookupResult result) {
        if ("item".equals(result.kind) && result.item != null) {
            return safe(result.item.item_type_name);
        }
        if ("type".equals(result.kind) && result.item_type != null) {
            return safe(result.item_type.name);
        }
        if ("box".equals(result.kind) && result.box != null) {
            return safe(result.box.name);
        }
        return "Результат";
    }

    private String describe(LookupResult result) {
        if ("item".equals(result.kind)) {
            return "товар";
        }
        if ("type".equals(result.kind)) {
            return "тип товара";
        }
        if ("box".equals(result.kind)) {
            return "контейнер";
        }
        return "объект";
    }

    private String messageFor(LookupResult result) {
        StringBuilder sb = new StringBuilder();

        if ("item".equals(result.kind) && result.item != null) {
            ItemSummary it = result.item;
            sb.append("Тип товара: ").append(safe(it.item_type_name)).append('\n');
            sb.append("Количество: ").append(it.quantity).append('\n');
            sb.append("Вес единицы: ").append(formatWeight(it.weight_g)).append('\n');
            sb.append("Общий вес: ").append(formatWeight(it.total_weight_g)).append('\n');
            sb.append("Расположение: ")
                    .append(it.box_name != null && !it.box_name.isEmpty() ? it.box_name : "без расположения")
                    .append('\n');
            sb.append("\nID позиции: ").append(it.id);

        } else if ("type".equals(result.kind) && result.item_type != null) {
            ItemTypeSummary t = result.item_type;
            sb.append("Справочная запись типа товара\n\n");
            sb.append("Название: ").append(safe(t.name)).append('\n');
            sb.append("Вес единицы: ").append(formatWeight(t.weight_g)).append('\n');
            sb.append("\nID типа: ").append(t.id);

        } else if ("box".equals(result.kind) && result.box != null) {
            BoxSummary b = result.box;
            sb.append("Тип контейнера: ").append(safe(b.box_type_name)).append('\n');
            sb.append("ID контейнера: ").append(b.id).append("\n\n");

            if (result.contents != null) {
                if (result.contents.items.isEmpty()) {
                    sb.append("Товаров нет\n");
                } else {
                    sb.append("Товаров: ").append(result.contents.items.size()).append("\n\n");
                    for (BoxContents.ItemRow item : result.contents.items) {
                        sb.append("• ").append(safe(item.item_type_name))
                                .append(" × ").append(item.quantity)
                                .append(" (").append(formatWeight(item.total_weight_g)).append(")\n");
                    }
                }

                if (!result.contents.child_boxes.isEmpty()) {
                    sb.append("\nВложенных контейнеров: ")
                            .append(result.contents.child_boxes.size()).append("\n");
                    for (BoxContents.ChildBox child : result.contents.child_boxes) {
                        sb.append("• ").append(safe(child.name))
                                .append(" (").append(safe(child.box_type_name)).append(")\n");
                    }
                }
            }
        } else {
            sb.append("Сервер вернул неожиданный ответ.");
        }

        return sb.toString().trim();
    }

    private static String safe(String value) {
        return (value == null || value.isEmpty()) ? "—" : value;
    }

    private static String formatWeight(Integer grams) {
        if (grams == null) {
            return "—";
        }
        if (grams >= 1000) {
            return String.format(Locale.getDefault(), "%.3f кг", grams / 1000.0);
        }
        return grams + " г";
    }

    // ───────────────────────────────────────────────────────── ручной ввод

    private void promptManualEntry() {
        EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_TEXT);
        input.setHint("qwentory:item:1");

        new AlertDialog.Builder(this)
                .setTitle("Ввести код вручную")
                .setMessage("Введите QR-код вручную, если камера недоступна.")
                .setView(input)
                .setPositiveButton("Найти", (DialogInterface dialog, int which) -> {
                    QrCode code = QrCode.parse(input.getText().toString());
                    if (code == null) {
                        setStatus("Неверный формат. Ожидается " + QrCode.SCHEME + ":item|type|box:<id>");
                        toast("Неверный формат кода");
                    } else {
                        lookup(code);
                    }
                })
                .setNegativeButton("Отмена", null)
                .show();
    }

    // ──────────────────────────────────────────────────────────────── прочее

    private void setStatus(String text) {
        runOnUiThread(() -> binding.tvStatus.setText(text));
    }

    private void toast(String text) {
        Toast.makeText(this, text, Toast.LENGTH_SHORT).show();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (analysisExecutor != null) {
            analysisExecutor.shutdown();
        }
        if (scanner != null) {
            scanner.close();
        }
    }
}