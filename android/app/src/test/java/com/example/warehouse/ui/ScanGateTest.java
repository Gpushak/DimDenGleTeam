package com.example.warehouse.ui;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class ScanGateTest {

    @Test
    public void sameCodeWhileDialogOpenIsIgnored() {
        ScanGate gate = new ScanGate();
        assertTrue(gate.shouldLookup("qwentory:item:9"));
        assertFalse(gate.shouldLookup("qwentory:item:9"));
        assertFalse(gate.shouldLookup("qwentory:item:10"));
    }

    @Test
    public void sameCodeStaysIgnoredAfterDismissUntilItLeavesTheFrame() {
        ScanGate gate = new ScanGate();
        assertTrue(gate.shouldLookup("qwentory:item:9"));
        gate.onDialogDismissed();

        assertFalse(gate.shouldLookup("qwentory:item:9"));
        assertFalse(gate.shouldLookup("qwentory:item:9"));

        gate.onFrameWithoutCode();
        assertTrue(gate.shouldLookup("qwentory:item:9"));
    }

    @Test
    public void differentCodeAfterDismissIsAccepted() {
        ScanGate gate = new ScanGate();
        assertTrue(gate.shouldLookup("qwentory:item:9"));
        gate.onDialogDismissed();
        assertTrue(gate.shouldLookup("qwentory:box:1"));
    }

    @Test
    public void failedLookupDoesNotRepeatUntilTheCodeLeaves() {
        ScanGate gate = new ScanGate();
        assertTrue(gate.shouldLookup("qwentory:item:9"));
        gate.onLookupFailed();
        assertFalse(gate.shouldLookup("qwentory:item:9"));
        gate.onFrameWithoutCode();
        assertTrue(gate.shouldLookup("qwentory:item:9"));
    }

    @Test
    public void manualHoldBlocksCamera() {
        ScanGate gate = new ScanGate();
        gate.hold("qwentory:item:3");
        assertFalse(gate.shouldLookup("qwentory:item:3"));
        assertFalse(gate.shouldLookup("qwentory:item:4"));
    }

    @Test
    public void foreignCodeIsReportedOnceUntilTheFrameIsEmpty() {
        ScanGate gate = new ScanGate();
        assertTrue(gate.shouldReportForeign("https://example.com"));
        assertFalse(gate.shouldReportForeign("https://example.com"));
        gate.onFrameWithoutCode();
        assertTrue(gate.shouldReportForeign("https://example.com"));
    }
}
