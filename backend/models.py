"""
Database Schema Design Rationale (Karnataka SPDB Outage & Localization System)

1. Separation of telemetry_events vs. pole_state:
   - `telemetry_events` is an immutable append-only event log. It receives high volume (39 msgs/sec steady, up to 5,000 msgs/burst), with potential duplicates, out-of-order timestamps, and retransmitted packets.
   - `pole_state` is a materialized point-in-time view of the current believed state of each pole (energized, last_seen, last_event_type, sequence_number). 
   - WHY SEPARATE? Querying millions of raw telemetry rows to calculate current pole state dynamically for 38,400 poles every time the fault localization algorithm runs would crush DB performance and violate the <120s P95 latency budget. `pole_state` allows O(1) indexed state lookups for graph algorithm traversal.

2. Incident / Ticket Lifecycle:
   - States: DETECTED -> ACKNOWLEDGED -> CREW_ASSIGNED -> RESOLVED -> VERIFIED -> CLOSED.
   - Auto-verification requires checking telemetry over time against `affected_pole_ids` before reaching VERIFIED state.
"""

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class DtRegistry(Base):
    __tablename__ = "dt_registry"

    dt_id = Column(String(64), primary_key=True, index=True)
    feeder_id = Column(String(64), nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    capacity_kva = Column(Integer, nullable=False, default=250)
    households_served = Column(Integer, nullable=False, default=100)
    topology_known = Column(Boolean, nullable=False, default=True)

class PoleRegistry(Base):
    __tablename__ = "pole_registry"

    pole_id = Column(String(64), primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    feeder_id = Column(String(64), nullable=False, index=True)
    dt_id = Column(String(64), ForeignKey("dt_registry.dt_id"), nullable=False, index=True)
    seq_on_line = Column(Integer, nullable=True)
    parent_pole_id = Column(String(64), nullable=True)
    pole_type = Column(String(64), nullable=False, default="LT-9m-PCC")
    ward = Column(String(64), nullable=False, default="W-084")
    pincode = Column(String(16), nullable=True)
    device_id = Column(String(64), nullable=True, index=True)

class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, index=True)
    pole_id = Column(String(64), nullable=False, index=True)
    event = Column(String(32), nullable=False)  # heartbeat, power_lost, power_restored, boot
    energized = Column(Boolean, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    battery_mv = Column(Integer, nullable=True)
    rssi = Column(Integer, nullable=True)
    fw = Column(String(32), nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class PoleState(Base):
    __tablename__ = "pole_state"

    pole_id = Column(String(64), primary_key=True, index=True)
    device_id = Column(String(64), nullable=True)
    energized = Column(Boolean, nullable=False, default=True, index=True)
    last_seen = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_event_type = Column(String(32), nullable=False, default="heartbeat")
    last_seq = Column(Integer, nullable=False, default=0)
    battery_mv = Column(Integer, nullable=True)
    rssi = Column(Integer, nullable=True)

class IncidentTicket(Base):
    __tablename__ = "incidents"

    id = Column(String(64), primary_key=True, index=True)
    status = Column(String(32), nullable=False, default="DETECTED", index=True)  # DETECTED, ACKNOWLEDGED, CREW_ASSIGNED, RESOLVED, VERIFIED, CLOSED
    fault_type = Column(String(32), nullable=False)  # SPAN_FAULT, DT_FAULT, FEEDER_FAULT, DEAD_SENSOR
    target_id = Column(String(128), nullable=False)  # e.g., P-101->P-102 or D-0112 or F-07-03
    substation_id = Column(String(64), nullable=False, default="SUB-01")
    feeder_id = Column(String(64), nullable=False)
    dt_id = Column(String(64), nullable=False)
    pincode = Column(String(16), nullable=False, default="560078")
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    affected_pole_count = Column(Integer, nullable=False, default=1)
    confidence = Column(Float, nullable=False, default=0.90)
    confidence_reasoning = Column(Text, nullable=False)
    topology_known = Column(Boolean, nullable=False, default=True)
    affected_pole_ids = Column(Text, nullable=False)  # JSON array string of pole IDs
    root_dark_pole_id = Column(String(64), nullable=True)
    upstream_live_pole_id = Column(String(64), nullable=True)

    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    crew_assigned_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

class ScheduledOutage(Base):
    __tablename__ = "scheduled_outages"

    id = Column(String(64), primary_key=True, index=True)
    scope = Column(String(32), nullable=False)  # feeder, dt
    target_id = Column(String(64), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
