package com.example.warehouse;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import com.example.warehouse.data.model.QrCode;

import org.junit.Test;

/**
 * Тесты разбора QR-кодов, которые генерирует десктопное приложение
 * (формат задан в shared/protocol.py).
 */
public class QrCodeTest {

    @Test
    public void parsesItemPayload() {
        QrCode code = QrCode.parse("qwentory:item:42");
        assertEquals("item", code.kind);
        assertEquals(42, code.id);
        assertEquals("qwentory:item:42", code.payload());
    }

    @Test
    public void parsesTypePayload() {
        QrCode code = QrCode.parse("qwentory:type:7");
        assertEquals("type", code.kind);
        assertEquals(7, code.id);
    }

    @Test
    public void parsesBoxPayload() {
        QrCode code = QrCode.parse("qwentory:box:3");
        assertEquals("box", code.kind);
        assertEquals(3, code.id);
    }

    @Test
    public void toleratesSurroundingWhitespace() {
        assertEquals(5, QrCode.parse("  qwentory:item:5  ").id);
    }

    /** Сканеры часто прикладывают перевод строки к значению кода. */
    @Test
    public void toleratesTrailingNewline() {
        assertEquals(9, QrCode.parse("qwentory:box:9\n").id);
        assertEquals(9, QrCode.parse("qwentory:box:9\r\n").id);
    }

    @Test
    public void rejectsForeignScheme() {
        assertNull(QrCode.parse("https://example.com"));
        assertNull(QrCode.parse("other:item:1"));
    }

    @Test
    public void rejectsUnknownKind() {
        assertNull(QrCode.parse("qwentory:user:1"));
    }

    @Test
    public void rejectsWrongPartCount() {
        assertNull(QrCode.parse("qwentory:item"));
        assertNull(QrCode.parse("qwentory:item:1:2"));
    }

    @Test
    public void rejectsNonNumericId() {
        assertNull(QrCode.parse("qwentory:item:abc"));
    }

    @Test
    public void rejectsNonPositiveId() {
        assertNull(QrCode.parse("qwentory:item:0"));
        assertNull(QrCode.parse("qwentory:item:-3"));
    }

    @Test
    public void rejectsEmptyAndNull() {
        assertNull(QrCode.parse(null));
        assertNull(QrCode.parse(""));
        assertNull(QrCode.parse("   "));
    }

    /** Обычный товарный штрихкод не должен уходить на сервер. */
    @Test
    public void rejectsPlainBarcode() {
        assertNull(QrCode.parse("4601234567890"));
    }
}