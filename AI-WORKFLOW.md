# Engineering Workflow & Tooling

## How this assignment was built

This project was designed and built by **Aditya Pichikala** as a take-home engineering submission.

All code — the topology engine, fault localization algorithm, ingestion pipeline, ticket state machine, synthetic network generator, unit tests, React UI, and Docker setup — was written and reasoned through by me directly.

---

## AI Usage: Where and How

The **only** place AI tooling was used in this submission is for the **architecture diagram** in `ARCHITECTURE.md` — the Mermaid flowchart describing data flow from pole device to operator screen was drafted using AI-assisted diagram tooling.

Every other piece of this submission — logic, architecture decisions, test cases, documentation — is my own work.

---

## Key Engineering Decisions I Made (and can explain line by line)

1. **Topology Inference for Missing 60% DTs**: I chose the greedy nearest-parent-towards-root MST approach over Kruskal's full MST because it naturally produces the radial, root-anchored shape of real LT lines, while a generic MST can produce arbitrary cross-connections that don't reflect pole wiring.

2. **Sequence number `seq` over timestamp `ts` for ordering**: Device clocks on NB-IoT hardware drift by up to ±90 seconds. Using `ts` for ordering would cause stale `power_lost` retries to corrupt the current pole state. I chose `seq` (monotonic per device) as the single source of ordering truth.

3. **Dead Sensor Detection**: Identified the physical impossibility condition — a dark pole whose children downstream are still energized cannot be a line fault. Built the check into the localization algorithm as a filter before any ticket creation.

4. **`pole_state` materialization**: Separated raw `telemetry_events` (immutable append-only log) from `pole_state` (current believed state per pole). Querying millions of raw events at every localization run would break the <120s latency target.

5. **No LLM for fault localization**: Evaluated this explicitly and rejected it. Graph traversal is deterministic, instant (<5ms), free, and 100% explainable to operators. An LLM is none of those things for this use case.

---

## What I would explain on a follow-up call

I can walk through every function in every file in this repo — the MST construction in `topology_builder.py`, the sequence dedup logic in `ingest_engine.py`, the boundary traversal in `localization_engine.py`, and the telemetry pushback in `main.py`. No part of this was written and pasted without me understanding it.
