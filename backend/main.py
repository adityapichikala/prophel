"""
FastAPI Main Application for KSPDB Fault Localization System.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.ingest_engine import IngestionEngine, TelemetryPayload
from backend.localization_engine import LocalizationEngine, IncidentOutput, ScheduledOutageRule
from backend.seed_generator import generate_synthetic_network
from backend.topology_builder import Tree

# Global In-Memory Stores for Fast Prototyping and Demo Execution
ingest_engine = IngestionEngine()
localization_engine = LocalizationEngine()

network_dts = []
network_poles = []
network_trees: Dict[str, Tree] = {}
pole_metadata = {}
incidents_db: Dict[str, IncidentOutput] = {}
scheduled_outages_db: List[ScheduledOutageRule] = []

connected_websockets: List[WebSocket] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed Synthetic Network
    global network_dts, network_poles, network_trees, pole_metadata
    dts, poles, states, trees = generate_synthetic_network()
    network_dts = dts
    network_poles = poles
    network_trees = trees

    for p in poles:
        pole_metadata[p.pole_id] = {
            "dt_id": p.dt_id,
            "feeder_id": p.feeder_id,
            "pincode": p.pincode or "560078",
            "lat": p.lat,
            "lon": p.lon,
            "device_id": p.device_id
        }

    for s in states:
        ingest_engine.states[s.pole_id] = s

    print(f"[OK] Seeding Complete: {len(dts)} DTs, {len(poles)} Poles, {len(trees)} Trees loaded.")
    yield

app = FastAPI(
    title="Karnataka SPDB Outage & Fault Localization API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def notify_websockets(event_type: str, data: dict):
    payload = json.dumps({"event": event_type, "data": data})
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)

def run_localization_eval():
    pole_states = {pid: s.energized for pid, s in ingest_engine.states.items()}
    results = localization_engine.localize(
        trees=network_trees,
        pole_states=pole_states,
        pole_metadata=pole_metadata,
        scheduled_outages=scheduled_outages_db
    )
    for inc in results:
        if inc.incident_id in incidents_db:
            # Preserve lifecycle status — don't overwrite ACKNOWLEDGED / RESOLVED / VERIFIED
            inc.status = incidents_db[inc.incident_id].status
        incidents_db[inc.incident_id] = inc
    return results

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "system": "KSPDB Fault Localization System", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/v1/telemetry")
async def receive_telemetry(payload: TelemetryPayload):
    processed = ingest_engine.process_telemetry(payload)
    if processed:
        run_localization_eval()
        await notify_websockets("TELEMETRY_UPDATE", {"pole_id": payload.pole_id, "energized": payload.energized})
    return {"status": "accepted", "processed": processed}

@app.get("/api/v1/incidents")
def list_incidents():
    run_localization_eval()
    return [inc.__dict__ for inc in incidents_db.values()]

@app.post("/api/v1/incidents/{incident_id}/acknowledge")
async def acknowledge_incident(incident_id: str):
    if incident_id not in incidents_db:
        raise HTTPException(status_code=404, detail="Incident not found")
    incidents_db[incident_id].status = "ACKNOWLEDGED"
    await notify_websockets("INCIDENT_UPDATED", incidents_db[incident_id].__dict__)
    return incidents_db[incident_id].__dict__

@app.post("/api/v1/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str):
    """
    Lineman marks ticket resolved. System pushes back if telemetry confirms poles are STILL DARK!
    """
    if incident_id not in incidents_db:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc = incidents_db[incident_id]

    # Verify Telemetry!
    still_dark = [pid for pid in inc.affected_pole_ids if not ingest_engine.states.get(pid, type('obj', (object,), {'energized': True})).energized]

    if still_dark:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resolve ticket! Telemetry shows {len(still_dark)} affected poles are STILL DARK. Verification failed."
        )

    inc.status = "VERIFIED"
    await notify_websockets("INCIDENT_UPDATED", inc.__dict__)
    return inc.__dict__

@app.post("/api/v1/simulator/inject-fault")
async def inject_fault(fault_type: str, target_id: str):
    """
    Simulator endpoint to inject span, DT, or feeder faults.
    """
    affected_poles = []
    if fault_type == "SPAN_FAULT":
        # Turn target pole and children dark
        target_tree = None
        for tree in network_trees.values():
            if target_id in tree.parent_map:
                target_tree = tree
                break
        if target_tree:
            affected_poles = list(target_tree.children_map.get(target_id, [])) + [target_id]
    elif fault_type == "DT_FAULT":
        tree = network_trees.get(target_id)
        if tree:
            affected_poles = list(tree.parent_map.keys())

    for pid in affected_poles:
        if pid in ingest_engine.states:
            ingest_engine.states[pid].energized = False

    new_incidents = run_localization_eval()
    await notify_websockets("FAULT_INJECTED", {"fault_type": fault_type, "target_id": target_id})
    return {"status": "injected", "affected_poles_count": len(affected_poles), "active_incidents": [i.__dict__ for i in new_incidents]}

@app.post("/api/v1/simulator/repair-fault")
async def repair_fault(incident_id: str):
    """
    Simulator endpoint to restore power and trigger telemetry auto-verification.
    """
    if incident_id not in incidents_db:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc = incidents_db[incident_id]

    for pid in inc.affected_pole_ids:
        if pid in ingest_engine.states:
            ingest_engine.states[pid].energized = True

    inc.status = "CLOSED"
    await notify_websockets("FAULT_REPAIRED", {"incident_id": incident_id})
    return {"status": "repaired_and_verified", "incident": inc.__dict__}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
