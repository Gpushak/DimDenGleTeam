package com.example.warehouse.ui;

/**
 * Решает, нужно ли снова запрашивать сервер по коду, который камера
 * видит на каждом кадре.
 *
 * Пока открыт диалог с результатом, новые запросы не уходят. После закрытия
 * тот же код игнорируется, пока не пропадёт из кадра: иначе удержание
 * телефона над этикеткой открывает диалог снова и снова.
 */
public final class ScanGate {

    private String heldPayload;
    private boolean dialogOpen;
    private boolean waitUntilLeaves;
    private String lastForeign;

    /** true — по этому коду пора сделать один запрос и показать один диалог. */
    public synchronized boolean shouldLookup(String payload) {
        if (payload == null || dialogOpen) {
            return false;
        }
        if (waitUntilLeaves) {
            if (payload.equals(heldPayload)) {
                return false;
            }
            waitUntilLeaves = false;
        }
        dialogOpen = true;
        heldPayload = payload;
        return true;
    }

    /** Ручной ввод: камера не должна параллельно открыть второй диалог. */
    public synchronized void hold(String payload) {
        dialogOpen = true;
        heldPayload = payload;
        waitUntilLeaves = false;
    }

    /** Кадр без распознанного кода. Снимает ожидание, что этикетку уберут. */
    public synchronized void onFrameWithoutCode() {
        if (!dialogOpen && waitUntilLeaves) {
            waitUntilLeaves = false;
            heldPayload = null;
        }
        lastForeign = null;
    }

    public synchronized void onDialogDismissed() {
        dialogOpen = false;
        waitUntilLeaves = heldPayload != null;
    }

    /** Сеть или сервер отказали: не держать диалог, но и не долбить тот же кадр. */
    public synchronized void onLookupFailed() {
        dialogOpen = false;
        waitUntilLeaves = heldPayload != null;
    }

    /** Чужой QR сообщаем один раз, пока он остаётся в кадре. */
    public synchronized boolean shouldReportForeign(String raw) {
        if (dialogOpen) {
            return false;
        }
        String value = raw == null ? "" : raw;
        if (value.equals(lastForeign)) {
            return false;
        }
        lastForeign = value;
        return true;
    }
}
