# Key Architectural Decisions Log (Karnataka SPDB Fault Localization System)

---

## 1. Graph Data Model & 60% Missing Topology Strategy
- **Decision**: Represent distribution transformers as tree graphs.
- **Why**: Low-tension networks are physical trees (radial, no loops).
- **Handling Missing 60% Topology**: Constructed a **Minimum Spanning Tree (MST)** using surveyed GPS coordinates (`lat`, `lon`) rooted at the transformer location. 
- **Confidence Rating**:
  - `0.95`: Digitized tree with recorded parent poles.
  - `0.65`: Geometrically inferred MST tree.
- **Trade-off**: Parallel LT lines running in narrow streets can be misconnected across the street rather than along their true physical run. This is documented and surfaced clearly to the operator.

---

## 2. Ingestion Engine & Telemetry Ordering
- **Decision**: Use `seq` per `device_id` as sequence authority rather than timestamp `ts`.
- **Why**: Device clocks have up to ±90 seconds of skew and are un-synchronized across poles. `seq` is monotonically increasing per device.
- **Stale Retry Suppression**: Late-arriving `power_lost` messages with `seq` <= `last_seq` are discarded to prevent stale retries from opening invalid tickets on restored lines.

---

## 3. Incident Ticket Auto-Closure
- **Decision**: Block manual resolution if downstream telemetry shows dark poles.
- **Why**: Linemen may mark tickets closed prematurely. System requires positive `power_restored` / `energized=True` signals from downstream pole devices before auto-verifying resolution.
