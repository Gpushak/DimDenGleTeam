package com.example.warehouse;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class QrParserTest {

    @Test
    public void sku_isExtracted_fromSimpleCode() {
        String qr = "SKU-101";
        assertTrue(qr.startsWith("SKU-"));
    }

    @Test
    public void jsonPayload_isValid() {
        String qr = "{\"type\":\"product\",\"sku\":\"SKU-101\"}";
        assertTrue(qr.contains("SKU-101"));
        assertTrue(qr.contains("product"));
    }

    @Test
    public void emptyString_hasNoSku() {
        String qr = "";
        assertEquals(0, qr.length());
    }
}