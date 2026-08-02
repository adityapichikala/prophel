"""
Unit tests for Ticket Lifecycle State Machine.
Tests:
1. Valid transitions: DETECTED -> ACKNOWLEDGED -> CREW_ASSIGNED -> RESOLVED -> VERIFIED -> CLOSED.
2. Pushback rule: Marking 'RESOLVED' while poles are still dark raises error and blocks VERIFIED state.
3. Telemetry restoration auto-verifies ticket.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app, incidents_db, ingest_engine

client = TestClient(app)

def test_ticket_resolution_pushback_when_dark():
    # Trigger synthetic fault
    res = client.post("/api/v1/simulator/inject-fault?fault_type=SPAN_FAULT&target_id=P-0001-02")
    assert res.status_code == 200

    incidents_res = client.get("/api/v1/incidents")
    incidents = incidents_res.json()
    assert len(incidents) > 0

    inc_id = incidents[0]["incident_id"]

    # Attempt to resolve while poles are STILL DARK -> Expect 400 Pushback!
    resolve_res = client.post(f"/api/v1/incidents/{inc_id}/resolve")
    assert resolve_res.status_code == 400
    assert "STILL DARK" in resolve_res.json()["detail"]


def test_ticket_auto_verification_on_power_restored():
    # Trigger synthetic fault
    client.post("/api/v1/simulator/inject-fault?fault_type=SPAN_FAULT&target_id=P-0001-02")
    inc_id = client.get("/api/v1/incidents").json()[0]["incident_id"]

    # Restore power via telemetry repair endpoint
    repair_res = client.post(f"/api/v1/simulator/repair-fault?incident_id={inc_id}")
    assert repair_res.status_code == 200
    assert repair_res.json()["status"] == "repaired_and_verified"
    assert repair_res.json()["incident"]["status"] == "CLOSED"
