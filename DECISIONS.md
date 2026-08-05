# Key Architectural Decisions Log

Newest decisions first. Each entry covers: what was chosen, what was rejected, why.

---

## 5. In-Memory State Instead of PostgreSQL (Demo Mode)

**Chosen:** All network state, telemetry, and incident data is stored in Python dicts in memory. No database connection required to run the demo.

**Rejected:** Using SQLAlchemy + PostgreSQL (the schema is modelled in `models.py`) for the demo runtime.

**Why:** The assignment asks for a system that comes up with `docker compose up` and works immediately for a reviewer. A PostgreSQL-backed system requires migration scripts, connection pooling, and startup ordering — all of which are classic demo failure modes. The in-memory design eliminates all of that while the `models.py` schema demonstrates the production data model. The SQLAlchemy ORM models are committed and ready; switching to a real database is a config change, not a redesign.

**Assumption:** The reviewers understand this is a demo, not a production deployment. The schema in `models.py` is the production answer; the in-memory store is the demo answer.

---

## 4. No LLM for Fault Localization

**Chosen:** Deterministic graph traversal (O(V+E) per DT tree) for all fault detection and localization.

**Rejected:** Using an LLM to interpret pole state patterns and produce fault descriptions.

**Why:** Graph traversal is deterministic (same input → same output, every time), instant (<5ms per DT), free (no API cost), and 100% explainable to operators. An LLM is none of those things. The assignment explicitly warns this route will be "interrogated hard." The one place where an LLM would genuinely help is generating richer natural-language reasoning for ambiguous inferred-topology faults — I chose to hand-write those strings instead, and they are honest about what they know and don't know.

---

## 3. Incident Ticket Auto-Closure

**Chosen:** Block manual resolution if downstream telemetry shows dark poles.

**Rejected:** Trust lineman's word that the fault is fixed.

**Why:** Linemen mark tickets closed prematurely. The system requires positive `energized=True` signals from every pole in `affected_pole_ids` before allowing VERIFIED status. If any pole is still dark, the API returns HTTP 400 with a specific error message. This is the physical verification the assignment requires.

---

## 2. Sequence Number `seq` Over Timestamp `ts` for Ordering

**Chosen:** `seq` per `device_id` as the sole authority for message ordering and deduplication.

**Rejected:** Using `ts` (device clock) for ordering.

**Why:** Device clocks on NB-IoT hardware drift by up to ±90 seconds and are unsynchronized across poles. Two poles that lose power simultaneously may report timestamps a minute apart, and the downstream one may arrive first. `seq` is monotonically increasing per device and resets only on `boot`. Any message with `seq` ≤ the last seen `seq` for that device is a duplicate or stale retry and is discarded without touching pole state.

**Known limitation:** `seq` resets to 0 on device reboot (`boot` event). A retransmitted stale `power_lost` from after a reboot could theoretically pass the dedup check. Mitigated by checking for `boot` events and resetting the `last_seq` baseline.

---

## 1. Greedy Nearest-Parent-Towards-Root MST for Missing 60% Topology

**Chosen:** For DTs with no recorded `parent_pole_id` or `seq_on_line`, construct a tree by sorting poles by distance-to-DT and greedily connecting each pole to the nearest already-connected pole that is strictly closer to the DT.

**Rejected options considered:**
- **Kruskal's full MST:** Produces globally minimum spanning tree but doesn't enforce radial shape — can produce arbitrary cross-connections that don't reflect LT wiring.
- **DT-level coarse localization:** Fall back to "fault somewhere in DT-0112" with no span. Rejected because it gives the operator no actionable GPS coordinates.
- **Survey request:** Specifying the pole-ordering survey is useful context but not a system answer. The brief explicitly says "also ship something that works today."
- **Learn from history:** Using observed co-dark patterns to infer adjacency over time. Valid but requires weeks of data to be useful; not available at system launch.

**Why greedy nearest-parent:** It naturally produces the radial, root-anchored shape of real LT lines because it only attaches a pole to a parent that is already closer to the DT — enforcing the directional flow of the physical network. Confidence is reported as 0.65 (vs 0.95 for digitized topology) and this is surfaced to the operator in the UI.

**Known failure modes (documented, not hidden):**
- **Parallel spurs:** Two LT lines running along opposite sides of a narrow alleyway (≈15m apart) may be misconnected across the street rather than along their true physical run. Tested in `test_topology.py::test_case_b_known_failure_mode_parallel_spurs`.
- **Dense urban clusters:** Multi-directional branching in dense blocks can mistake a secondary branch root for a main feeder continuation.

---

## Assumptions Where the Brief Was Ambiguous

1. **"Feeder fault" in the simulator** — The brief asks for span, DT, and feeder fault injection. The implemented simulator handles span and DT faults. Feeder faults are architecturally handled (the localization engine detects whole-feeder blackouts) but not exposed in the simulator UI. Assumption: DT fault injection sufficiently demonstrates the detection logic for evaluators.

2. **Scheduled outage "one in ten cancelled without feed update"** — The system applies a 40-minute overrun buffer (standard for maintenance delays) and still creates an incident tagged with the scheduled outage — it does not silently suppress. Assumption: creating a suppressed/tagged ticket is better than missing a real fault that overlaps a stale scheduled outage entry.

3. **"Pincode missing for ~3% of poles"** — All synthetic poles in the seed generator are assigned pincode `560078`. The fallback for missing pincodes uses the DT's associated pincode. No external geocoding API is used. Assumption: this is acceptable for a demo with synthetic data; production would use a local reverse-geocoding dataset.

4. **"One fault vs two" when two spans fail 10 minutes apart** — Each live/dark boundary is treated as an independent incident with a unique `incident_id`. They are not merged. Assumption: two separate repair crews dispatched to two separate locations is the correct operational response.

5. **Authentication** — No auth implemented. The FAQ explicitly says "a hardcoded operator identity is fine" and "do not spend hours on auth."

---

## What I Would Do With Two More Weeks

1. **Wire up PostgreSQL for persistence** — Incidents survive a backend restart. The `models.py` schema is ready; it's a config + migration step.
2. **Add a map view** — Leaflet/OpenStreetMap showing pole locations, the live/dark boundary, and the fault span highlighted. The coordinates are all present; the missing piece is a map component.
3. **Feeder-level fault injection in simulator** — Turn all poles on a given feeder dark simultaneously and verify the feeder-level detection path.
4. **WebSocket-first updates** — Currently the UI polls every 3 seconds. WebSocket push (`/ws`) is implemented on the backend; the frontend should switch to WS-first with HTTP polling as fallback.
5. **Load test the ingest endpoint** — Measure actual throughput under 500 msg/s sustained and 5,000 msg/10s burst with `locust` or `k6`. State the real numbers.
6. **Better handling of poles with no device** — If the fault boundary crosses a pole with no IoT device fitted (~9% of poles), the system currently cannot locate it precisely. A UI note ("fault may be between P-X and P-Y, one pole has no sensor") would be more honest than returning the nearest instrumented boundary.

---

## What Is Currently Wrong or Fragile

1. **State is lost on restart** — All incidents, acknowledged tickets, and injected faults disappear when the backend restarts. Acceptable for a demo; fatal for production.
2. **Ingest throughput is untested under load** — The in-memory design should handle 500 msg/s easily (no I/O, pure Python dict writes), but this is a claim, not a measurement.
3. **The 40-minute scheduled outage overrun buffer is arbitrary** — It is documented; it could be tunable. If a maintenance window overruns by 90 minutes, a real fault during that window would be suppressed.
4. **`GET /api/v1/incidents` calls `run_localization_eval()` on every poll** — This was originally a bug (it overwrote acknowledged status on every refresh). Fixed with a status-preservation guard, but re-running the full localization on every GET is unnecessary. Should be event-driven (triggered on telemetry arrival) not poll-triggered.
5. **No rate limiting on the ingest endpoint** — A misbehaving device could flood the endpoint. Redis rate limiting is in the architecture but not wired up in the demo.
