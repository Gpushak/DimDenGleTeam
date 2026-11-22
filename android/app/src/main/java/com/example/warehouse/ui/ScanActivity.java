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

import com.example.warehouse.R;
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
 * в {@code GET /lookup?code=...}. Товар сразу возвращается в
 * {@link MainActivity} для открытия экрана редактирования; тип и контейнер
 * показываются диалогом.
 *
 * Активность возвращает результат через {@link #setResult}:
 * {@link #RESULT_ITEM_ID} и {@link #RESULT_BOX_ID} (0, если не применимо).
 */
public class ScanActivity extends AppCompatActivity {

    /** Идентификатор отсканированного товара (0 — если отсканировано не товар). */
    public static final String RESULT_ITEM_ID = "item_id";
    /** Идентификатор контейнера, где лежит товар (0 — неизвестно). */
    public static final String RESULT_BOX_ID = "box_id";

    private ActivityScanBinding binding;
    private ExecutorService analysisExecutor;
    private BarcodeScanner scanner;
    private AlertDialog resultDialog;

    /** Пока идёт распознавание кадра — чтобы не нагружать ML Kit. */
    private final AtomicBoolean analyzing = new AtomicBoolean(false);
    /** Один диалог на код, пока этикетка остаётся в кадре. */
    private final ScanGate gate = new ScanGate();

    private final ActivityResultLauncher<String> permissionLauncher =
            registerForActivityResult(new ActivityResultContracts.RequestPermission(),
                    granted -> {
                        if (Boolean.TRUE.equals(granted)) {
                            startCamera();
                        } else {
                            onCameraUnavailable(getString(R.string.camera_denied));
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
                onCameraUnavailable(getString(R.string.camera_failed, e.getMessage()));
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
            gate.onFrameWithoutCode();
            return;
        }

        String raw = barcodes.get(0).getRawValue();
        QrCode code = QrCode.parse(raw);
        if (code == null) {
            if (gate.shouldReportForeign(raw)) {
                runOnUiThread(() -> setStatus(getString(R.string.scan_foreign, QrCode.SCHEME)));
            }
            return;
        }

        if (!gate.shouldLookup(code.payload())) {
            return;
        }
        runOnUiThread(() -> lookup(code));
    }

    private void onCameraUnavailable(String reason) {
        binding.progress.setVisibility(View.GONE);
        setStatus(reason);
        binding.btnManual.setVisibility(View.VISIBLE);
    }

    // ────────────────────────────────────────────────────── запрос к серверу

    private void lookup(QrCode code) {
        binding.progress.setVisibility(View.VISIBLE);
        setStatus(getString(R.string.scan_request, code.payload()));

        ApiClient.api().lookup(code.payload()).enqueue(new Callback<LookupResult>() {
            @Override
            public void onResponse(Call<LookupResult> call, Response<LookupResult> response) {
                binding.progress.setVisibility(View.GONE);

                LookupResult body = response.body();
                if (response.isSuccessful() && body != null) {
                    showResult(body);
                } else {
                    setStatus(getString(R.string.scan_not_found, code.payload(), response.code()));
                    setResult(RESULT_CANCELED);
                    gate.onLookupFailed();
                }
            }

            @Override
            public void onFailure(Call<LookupResult> call, Throwable t) {
                binding.progress.setVisibility(View.GONE);
                setStatus(getString(R.string.error_network, t.getMessage()));
                gate.onLookupFailed();
            }
        });
    }

    private void showResult(LookupResult result) {
        if (isFinishing()) {
            gate.onDialogDismissed();
            return;
        }
        if (resultDialog != null && resultDialog.isShowing()) {
            return;
        }

        setStatus(getString(R.string.scan_found, describe(result)));
        releaseResult(result);

        if ("item".equals(result.kind) && result.item != null) {
            finish();
            return;
        }

        resultDialog = new AlertDialog.Builder(this)
                .setTitle(titleFor(result))
                .setMessage(messageFor(result))
                .setPositiveButton(R.string.action_close, (dialog, which) -> dialog.dismiss())
                .setOnDismissListener(dialog -> gate.onDialogDismissed())
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
        return getString(R.string.result_fallback);
    }

    private String describe(LookupResult result) {
        if ("item".equals(result.kind)) {
            return getString(R.string.kind_item);
        }
        if ("type".equals(result.kind)) {
            return getString(R.string.kind_type);
        }
        if ("box".equals(result.kind)) {
            return getString(R.string.kind_box);
        }
        return getString(R.string.kind_object);
    }

    private String messageFor(LookupResult result) {
        StringBuilder sb = new StringBuilder();

        if ("item".equals(result.kind) && result.item != null) {
            ItemSummary it = result.item;
            String place = it.box_name != null && !it.box_name.isEmpty()
                    ? it.box_name
                    : getString(R.string.scan_no_location);
            sb.append(getString(R.string.scan_item_type, safe(it.item_type_name))).append('\n');
            sb.append(getString(R.string.scan_quantity, it.quantity)).append('\n');
            sb.append(getString(R.string.scan_unit_weight, Weights.format(this, it.weight_g))).append('\n');
            sb.append(getString(R.string.scan_total_weight, Weights.format(this, it.total_weight_g))).append('\n');
            sb.append(getString(R.string.scan_location, place)).append('\n');
            sb.append('\n').append(getString(R.string.scan_position_id, it.id));

        } else if ("type".equals(result.kind) && result.item_type != null) {
            ItemTypeSummary t = result.item_type;
            sb.append(getString(R.string.scan_type_intro)).append("\n\n");
            sb.append(getString(R.string.scan_name, safe(t.name))).append('\n');
            sb.append(getString(R.string.scan_unit_weight, Weights.format(this, t.weight_g))).append('\n');
            sb.append('\n').append(getString(R.string.scan_type_id, t.id));

        } else if ("box".equals(result.kind) && result.box != null) {
            BoxSummary b = result.box;
            sb.append(getString(R.string.scan_box_type, safe(b.box_type_name))).append('\n');
            sb.append(getString(R.string.scan_box_id, b.id)).append("\n\n");

            if (result.contents != null) {
                if (result.contents.items.isEmpty()) {
                    sb.append(getString(R.string.scan_no_items)).append('\n');
                } else {
                    sb.append(getString(R.string.scan_item_count, result.contents.items.size()))
                            .append("\n\n");
                    for (BoxContents.ItemRow item : result.contents.items) {
                        sb.append(getString(R.string.scan_item_line,
                                safe(item.item_type_name),
                                item.quantity,
                                Weights.format(this, item.total_weight_g))).append('\n');
                    }
                }

                if (!result.contents.child_boxes.isEmpty()) {
                    sb.append('\n').append(getString(
                            R.string.scan_child_count, result.contents.child_boxes.size())).append('\n');
                    for (BoxContents.ChildBox child : result.contents.child_boxes) {
                        sb.append(getString(R.string.scan_child_line,
                                safe(child.name), safe(child.box_type_name))).append('\n');
                    }
                }
            }
        } else {
            sb.append(getString(R.string.scan_unexpected));
        }

        return sb.toString().trim();
    }

    private static String safe(String value) {
        return (value == null || value.isEmpty()) ? "—" : value;
    }

    // ───────────────────────────────────────────────────────── ручной ввод

    private void promptManualEntry() {
        EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_TEXT);
        input.setHint("qwentory:item:1");

        new AlertDialog.Builder(this)
                .setTitle(R.string.action_manual)
                .setMessage(R.string.manual_message)
                .setView(input)
                .setPositiveButton(R.string.action_find, (DialogInterface dialog, int which) -> {
                    QrCode code = QrCode.parse(input.getText().toString());
                    if (code == null) {
                        setStatus(getString(R.string.scan_bad_format, QrCode.SCHEME));
                        toast(getString(R.string.toast_bad_format));
                    } else {
                        gate.hold(code.payload());
                        lookup(code);
                    }
                })
                .setNegativeButton(R.string.action_cancel, null)
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
        if (resultDialog != null && resultDialog.isShowing()) {
            resultDialog.dismiss();
        }
        super.onDestroy();
        if (analysisExecutor != null) {
            analysisExecutor.shutdown();
        }
        if (scanner != null) {
            scanner.close();
        }
    }
}