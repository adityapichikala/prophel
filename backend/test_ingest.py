"""
Unit tests for Ingest Engine & Deduplication Logic.
"""

from datetime import datetime, timezone
import pytest
from backend.ingest_engine import IngestionEngine, TelemetryPayload

def test_telemetry_deduplication_and_out_of_order():
    engine = IngestionEngine()

    p1 = TelemetryPayload(
        device_id="DEV-01",
        pole_id="P-100",
        event="heartbeat",
        energized=True,
        ts="2026-07-29T10:00:00Z",
        seq=100
    )
    assert engine.process_telemetry(p1) is True
    assert engine.states["P-100"].energized is True
    assert engine.states["P-100"].last_seq == 100

    # Duplicate message with same seq
    p1_dup = TelemetryPayload(
        device_id="DEV-01",
        pole_id="P-100",
        event="heartbeat",
        energized=True,
        ts="2026-07-29T10:00:05Z",
        seq=100
    )
    assert engine.process_telemetry(p1_dup) is False  # Discarded!

    # Out-of-order stale retry (seq 95 arrives after seq 100)
    p_stale = TelemetryPayload(
        device_id="DEV-01",
        pole_id="P-100",
        event="power_lost",
        energized=False,
        ts="2026-07-29T09:55:00Z",
        seq=95
    )
    assert engine.process_telemetry(p_stale) is False  # Discarded!
    assert engine.states["P-100"].energized is True  # State preserved live!

    # Valid newer event (seq 101)
    p_newer = TelemetryPayload(
        device_id="DEV-01",
        pole_id="P-100",
        event="power_lost",
        energized=False,
        ts="2026-07-29T10:01:00Z",
        seq=101
    )
    assert engine.process_telemetry(p_newer) is True
    assert engine.states["P-100"].energized is False


def test_firmware_12_heartbeat_watchdog_timeout():
    engine = IngestionEngine()
    engine.process_telemetry(TelemetryPayload(
        device_id="DEV-FW12",
        pole_id="P-200",
        event="heartbeat",
        energized=True,
        ts="2026-07-29T10:00:00Z",
        seq=1
    ))

    # Check timeout after 10 mins (600s) -> Should stay live
    now_10m = datetime.fromisoformat("2026-07-29T10:10:00+00:00")
    timed_out = engine.check_firmware_12_watchdog(now=now_10m)
    assert len(timed_out) == 0
    assert engine.states["P-200"].energized is True

    # Check timeout after 16 mins (960s > 945s limit) -> Should trigger dark!
    now_16m = datetime.fromisoformat("2026-07-29T10:16:00+00:00")
    timed_out = engine.check_firmware_12_watchdog(now=now_16m)
    assert "P-200" in timed_out
    assert engine.states["P-200"].energized is False
