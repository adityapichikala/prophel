"""
Comprehensive Unit Tests for Fault Localization Algorithm.
Verifies:
1. Known topology + injected fault -> expected span output with correct confidence.
2. Isolated dark pole with live children -> dead sensor (NO ticket created).
3. Simultaneous independent faults -> exact count of separate tickets.
4. Scheduled outage window -> incident correctly tagged/suppressed.
"""

from datetime import datetime, timezone
import pytest
from backend.topology_builder import build_topology, PoleData
from backend.localization_engine import LocalizationEngine, ScheduledOutageRule

def test_localization_known_topology_span_fault():
    dt_id = "D-1000"
    dt_lat, dt_lon = 12.9678, 77.5951
    poles = [
        PoleData("P-1", 12.9680, 77.5951, seq_on_line=1, parent_pole_id=None, dt_id=dt_id),
        PoleData("P-2", 12.9682, 77.5951, seq_on_line=2, parent_pole_id="P-1", dt_id=dt_id),
        PoleData("P-3", 12.9684, 77.5951, seq_on_line=3, parent_pole_id="P-2", dt_id=dt_id),
        PoleData("P-4", 12.9686, 77.5951, seq_on_line=4, parent_pole_id="P-3", dt_id=dt_id),
    ]
    tree = build_topology(dt_id, dt_lat, dt_lon, poles)

    # Ingest Fault: Span between P-2 and P-3 breaks (P-3 and P-4 dark; P-1 and P-2 live)
    pole_states = {
        "P-1": True,
        "P-2": True,
        "P-3": False,
        "P-4": False,
    }
    pole_meta = {
        p.pole_id: {"dt_id": dt_id, "feeder_id": "F-01", "pincode": "560078", "lat": p.lat, "lon": p.lon}
        for p in poles
    }

    engine = LocalizationEngine()
    incidents = engine.localize({"D-1000": tree}, pole_states, pole_meta)

    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.fault_type == "SPAN_FAULT"
    assert inc.target_id == "P-2 -> P-3"
    assert inc.affected_pole_count == 2
    assert inc.confidence == 0.92
    assert inc.topology_known is True
    assert "verified digitized tree topology" in inc.confidence_reasoning


def test_localization_isolated_dead_sensor_no_ticket():
    dt_id = "D-2000"
    dt_lat, dt_lon = 12.9678, 77.5951
    poles = [
        PoleData("P-10", 12.9680, 77.5951, seq_on_line=1, parent_pole_id=None, dt_id=dt_id),
        PoleData("P-11", 12.9682, 77.5951, seq_on_line=2, parent_pole_id="P-10", dt_id=dt_id),
        PoleData("P-12", 12.9684, 77.5951, seq_on_line=3, parent_pole_id="P-11", dt_id=dt_id),
    ]
    tree = build_topology(dt_id, dt_lat, dt_lon, poles)

    # Sensor failure at P-11 (dark), but child P-12 is LIVE!
    pole_states = {
        "P-10": True,
        "P-11": False,  # Isolated dark!
        "P-12": True,   # Live child!
    }
    pole_meta = {
        p.pole_id: {"dt_id": dt_id, "feeder_id": "F-01", "pincode": "560078", "lat": p.lat, "lon": p.lon}
        for p in poles
    }

    engine = LocalizationEngine()
    incidents = engine.localize({"D-2000": tree}, pole_states, pole_meta)

    # Should NOT generate any power outage ticket!
    assert len(incidents) == 0


def test_localization_simultaneous_independent_faults():
    dt1_id, dt2_id = "D-3001", "D-3002"
    poles1 = [
        PoleData("P-31", 12.9680, 77.5951, seq_on_line=1, parent_pole_id=None, dt_id=dt1_id),
        PoleData("P-32", 12.9682, 77.5951, seq_on_line=2, parent_pole_id="P-31", dt_id=dt1_id),
    ]
    poles2 = [
        PoleData("P-41", 12.9710, 77.5980, seq_on_line=1, parent_pole_id=None, dt_id=dt2_id),
        PoleData("P-42", 12.9712, 77.5980, seq_on_line=2, parent_pole_id="P-41", dt_id=dt2_id),
    ]
    tree1 = build_topology(dt1_id, 12.9678, 77.5951, poles1)
    tree2 = build_topology(dt2_id, 12.9708, 77.5980, poles2)

    # Both P-32 and P-42 go dark independently in separate DTs
    pole_states = {"P-31": True, "P-32": False, "P-41": True, "P-42": False}
    pole_meta = {
        "P-31": {"dt_id": dt1_id, "feeder_id": "F-01", "pincode": "560078", "lat": 12.9680, "lon": 77.5951},
        "P-32": {"dt_id": dt1_id, "feeder_id": "F-01", "pincode": "560078", "lat": 12.9682, "lon": 77.5951},
        "P-41": {"dt_id": dt2_id, "feeder_id": "F-02", "pincode": "560079", "lat": 12.9710, "lon": 77.5980},
        "P-42": {"dt_id": dt2_id, "feeder_id": "F-02", "pincode": "560079", "lat": 12.9712, "lon": 77.5980},
    }

    engine = LocalizationEngine()
    incidents = engine.localize({dt1_id: tree1, dt2_id: tree2}, pole_states, pole_meta)

    # Must generate exactly 2 distinct tickets!
    assert len(incidents) == 2
    target_ids = {inc.target_id for inc in incidents}
    assert "P-31 -> P-32" in target_ids
    assert "P-41 -> P-42" in target_ids


def test_localization_scheduled_outage_suppression():
    dt_id = "D-4000"
    poles = [
        PoleData("P-51", 12.9680, 77.5951, seq_on_line=1, parent_pole_id=None, dt_id=dt_id),
        PoleData("P-52", 12.9682, 77.5951, seq_on_line=2, parent_pole_id="P-51", dt_id=dt_id),
    ]
    tree = build_topology(dt_id, 12.9678, 77.5951, poles)

    pole_states = {"P-51": True, "P-52": False}
    pole_meta = {
        "P-51": {"dt_id": dt_id, "feeder_id": "F-07-03", "pincode": "560078", "lat": 12.9680, "lon": 77.5951},
        "P-52": {"dt_id": dt_id, "feeder_id": "F-07-03", "pincode": "560078", "lat": 12.9682, "lon": 77.5951},
    }

    now = datetime.fromisoformat("2026-07-29T10:15:00+00:00")
    so = ScheduledOutageRule(
        id="SO-2026-07-29-014",
        scope="feeder",
        target_id="F-07-03",
        start_time=datetime.fromisoformat("2026-07-29T10:00:00+00:00"),
        end_time=datetime.fromisoformat("2026-07-29T12:30:00+00:00"),
        reason="Planned maintenance"
    )

    engine = LocalizationEngine()
    incidents = engine.localize({"D-4000": tree}, pole_states, pole_meta, scheduled_outages=[so], now=now)

    assert len(incidents) == 1
    assert incidents[0].suppressed_by_scheduled_outage is not None
    assert "SO-2026-07-29-014" in incidents[0].suppressed_by_scheduled_outage
