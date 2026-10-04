package com.example.warehouse.data.model;

/**
 * Разбор содержимого QR-кода, сгенерированного десктопным приложением.
 *
 * Формат совпадает с {@code shared/protocol.py} на стороне сервера:
 * <pre>
 *   qwentory:item:42   — позиция товара
 *   qwentory:type:7    — тип товара (справочник)
 *   qwentory:box:3     — контейнер
 * </pre>
 *
 * Зеркалит серверный протокол, чтобы отсеивать чужие QR-коды до похода в сеть.
 */
public final class QrCode {

    public static final String SCHEME = "qwentory";

    public final String kind;
    public final int id;

    private QrCode(String kind, int id) {
        this.kind = kind;
        this.id = id;
    }

    /**
     * @return разобранный код либо {@code null}, если это не наш формат
     */
    public static QrCode parse(String raw) {
        if (raw == null) {
            return null;
        }
        String text = raw.trim();
        // Сканеры часто добавляют к результату перевод строки.
        while (text.endsWith("\n") || text.endsWith("\r")) {
            text = text.substring(0, text.length() - 1).trim();
        }
        if (text.isEmpty()) {
            return null;
        }

        String[] parts = text.split(":");
        if (parts.length != 3 || !SCHEME.equals(parts[0])) {
            return null;
        }

        String kind = parts[1];
        if (!"item".equals(kind) && !"type".equals(kind) && !"box".equals(kind)) {
            return null;
        }

        int id;
        try {
            id = Integer.parseInt(parts[2].trim());
        } catch (NumberFormatException e) {
            return null;
        }
        if (id <= 0) {
            return null;
        }

        return new QrCode(kind, id);
    }

    /** Значение для запроса {@code GET /lookup?code=...}. */
    public String payload() {
        return SCHEME + ":" + kind + ":" + id;
    }

    @Override
    public String toString() {
        return payload();
    }
}