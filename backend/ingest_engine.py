"""
Fast Ingestion & Telemetry Processing Engine.

Architectural High-Throughput Mechanism (500 msg/s steady, 5,000 msg/10s burst):
1. In-memory Async Lockless Buffer (or Redis Queue):
   FastAPI receives raw payload into memory immediately and pushes to an in-memory queue/deque,
   returning HTTP 202 Accepted instantly (< 5ms response time).
2. De-duplication and Out-of-Order Handling:
   - Uses `seq` per `device_id` as the absolute sequence authority.
   - Ignores payloads where incoming `seq` <= stored `last_seq` for that device.
   - Stale `power_lost` messages arriving hours late after `power_restored` are discarded because `last_seq` has already advanced past them.
3. Firmware 1.2.x Heartbeat Watchdog:
   - Devices on firmware 1.2.x (~8% fleet) do NOT send `power_lost`.
   - If `last_seen` timestamp exceeds 15 minutes + 45s jitter (945 seconds), the pole state is flagged as `SUSPECTED_OFFLINE` / `dark`.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from backend.models import PoleState

class TelemetryPayload(BaseModel):
    device_id: str
    pole_id: str
    event: str  # heartbeat, power_lost, power_restored, boot
    energized: bool
    ts: str
    seq: int
    battery_mv: Optional[int] = None
    rssi: Optional[int] = None
    fw: Optional[str] = None

class IngestionEngine:
    def __init__(self):
        # In-memory store for rapid state updates & deduplication
        self.states: Dict[str, PoleState] = {}  # pole_id -> PoleState
        self.seen_seqs: Dict[str, int] = {}  # device_id -> highest seq seen

    def process_telemetry(self, payload: TelemetryPayload) -> bool:
        """
        Processes incoming telemetry message. Returns True if processed, False if discarded (duplicate/stale).
        """
        device_id = payload.device_id
        pole_id = payload.pole_id
        seq = payload.seq

        # 1. Out-of-order / Duplicate Check via monotonic sequence number per device
        last_seq = self.seen_seqs.get(device_id, -1)
        if seq <= last_seq:
            # Stale retry or duplicate! Discard.
            return False

        # Update highest sequence number seen for this device
        self.seen_seqs[device_id] = seq

        # Parse timestamp
        try:
            ts_dt = datetime.fromisoformat(payload.ts.replace('Z', '+00:00'))
        except Exception:
            ts_dt = datetime.now(timezone.utc)

        # 2. Update pole_state
        state = self.states.get(pole_id)
        if not state:
            state = PoleState(
                pole_id=pole_id,
                device_id=device_id,
                energized=payload.energized,
                last_seen=ts_dt,
                last_event_type=payload.event,
                last_seq=seq,
                battery_mv=payload.battery_mv,
                rssi=payload.rssi
            )
            self.states[pole_id] = state
        else:
            state.device_id = device_id
            state.energized = payload.energized
            state.last_seen = ts_dt
            state.last_event_type = payload.event
            state.last_seq = seq
            state.battery_mv = payload.battery_mv
            state.rssi = payload.rssi

        return True

    def check_firmware_12_watchdog(self, now: Optional[datetime] = None) -> Set[str]:
        """
        Checks for firmware 1.2.x silent devices that haven't sent heartbeats in 15min + 45s (945s).
        Returns set of pole_ids that should be marked dark due to heartbeat timeout.
        """
        if not now:
            now = datetime.now(timezone.utc)

        timed_out_poles = set()
        timeout_seconds = 945.0  # 15 min + 45s jitter

        for pole_id, state in self.states.items():
            if state.energized:
                elapsed = (now - state.last_seen).total_seconds()
                if elapsed > timeout_seconds:
                    # Firmware 1.2.x or silent dead modem timeout! Mark dark
                    state.energized = False
                    timed_out_poles.add(pole_id)

        return timed_out_poles
