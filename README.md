# Karnataka State Power Distribution Board (KSPDB)
## Automated Outage Detection & Fault Localization System

A high-performance, fault-tolerant telemetry ingestion, graph fault localization, and incident management system built for low-tension electricity distribution networks in Karnataka.

> **Compresses the 2-hour manual fault identification process down to under 2 minutes.**

---

## 🔗 Quick Links

| Resource | Link |
|----------|------|
| **Live Public URL** | `[ADD AFTER DEPLOYMENT]` — Opens in browser, no login required |
| **Demo Video** | `[ADD LOOM/YOUTUBE LINK]` — 5-minute walkthrough: fault injected → detected → localized → ticketed → repaired → auto-verified |
| **API Docs (local)** | http://localhost:8000/docs |

> ⚠️ If the live URL is slow to respond on first load, the free-tier backend may be cold-starting. Wait 15–20 seconds and refresh.

---

## 🚀 One-Command Start

```bash
git clone <repo-url>
cd prophel
docker compose up --build
```

The stack starts seeded with 412 Distribution Transformers and ~4,000 poles. No manual migration, no config changes, no empty screen.

| URL | What you see |
|-----|-------------|
| http://localhost:3000 | Operator Console — 2 a.m. fault management UI |
| http://localhost:8000/docs | Swagger API documentation |
| http://localhost:8000/api/v1/health | Health check JSON |

---

## 📌 Problem Statement

When a low-tension domestic supply line develops a fault — a snapped wire, a blown fuse, a cut jumper — electricity goes out for a cluster of houses. The control room currently finds out only when customers call the complaint hotline.

**The 2-hour window:** From the first call, identifying the specific span of wire that failed requires a lineman to drive to the area and walk the line pole-by-pole from the dark houses back to the live transformer. Only then can the correct crew, vehicle, and materials be dispatched.

**This system:** Compresses fault identification to under 2 minutes using 1-bit pole telemetry (`energized: true/false`), outputting exact span coordinates, PIN codes, affected household counts, and plain-English confidence explanations — automatically, the moment telemetry arrives.

---

## 🔍 Key Design Decisions

**Nodes vs. Edges:** Telemetry devices report on poles (nodes). Faults occur on wire spans (edges). The system infers edge state from node state by finding the live/dark boundary in the radial tree.

**Single Incident Aggregation:** 50 dark poles downstream of one snapped wire produce one ticket, not 50 alerts. A system that fires an alert per dark pole makes the control room's night worse than no system.

**60% Missing Topology:** 40% of DTs have digitized wiring records. 60% have only GPS coordinates. The system infers a topology tree using a greedy nearest-parent-towards-root algorithm and reports 0.65 confidence (vs. 0.95 for digitized) surfaced clearly to operators.

**Dead Sensor Detection:** A dark pole whose downstream children are still live is physically impossible as a line fault. The system detects this as a dead IoT sensor and does not open a power outage ticket.

**Telemetry-Verified Closure:** An operator cannot mark a ticket resolved if downstream poles are still reporting dark. The system pushes back with a specific error message.

---

## 🏗️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 / FastAPI (async REST + WebSockets) |
| State (demo) | In-memory Python dicts — zero DB dependency for demo |
| State (production) | PostgreSQL 16 (SQLAlchemy schema in `models.py`) |
| Cache / PubSub | Redis 7 (rate limiting + WS fanout) |
| Frontend | React 19 / Vite / TypeScript |
| Containerization | Docker + Docker Compose |

---

## 🧪 Testing

```bash
python -m pytest backend/ -v
```

**12 tests, all passing.** Covers:
- Telemetry deduplication and out-of-order handling
- Firmware 1.2.x heartbeat watchdog timeout
- Known topology span fault → correct span ID and confidence
- Dead sensor → no ticket created
- Three simultaneous independent faults → exactly 3 tickets
- Scheduled outage suppression
- Ticket resolution pushback when poles still dark
- Ticket auto-verification on power restoration

---

## 📑 Documentation Index

| Document | Contents |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Data flow diagram, ingestion design, topology representation, full localization algorithm, API surface, UI reasoning, AI feature decision, performance targets |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Prerequisites, exact commands, all environment variables, verification steps, 8 troubleshooting scenarios, clean-state reset |
| [DECISIONS.md](DECISIONS.md) | Decision log (5 decisions), rejected alternatives, assumptions, known fragile points, what 2 more weeks would add |
| [AI-WORKFLOW.md](AI-WORKFLOW.md) | AI tools used, what was delegated vs. written personally, % AI-generated code, 3 cases where AI was wrong, best prompts |
