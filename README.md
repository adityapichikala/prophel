# Karnataka State Power Distribution Board (KSPDB)
## Automated Outage Detection & Fault Localization System

A high-performance, fault-tolerant telemetry ingestion, graph fault localization, and incident management system built for low-tension electricity distribution networks in Karnataka.

---

## 📌 1. Problem Statement

When a low-tension domestic supply line develops a fault—a snapped wire, a blown fuse at a distribution transformer, or a cut jumper—electricity goes out for a cluster of houses. Historically, the control room only finds out when customers call the complaint hotline.

### The 2-Hour Window Problem
From the first call, it currently takes at least **two hours** to identify which specific span of wire failed:
1. Operators manually plot complaint calls on ward spreadsheets to guess the transformer.
2. A lineman drives to the area on a two-wheeler and walks/rides the line pole-by-pole starting from the dark houses back to the live transformer.
3. Only after locating the physical break can the control room dispatch the correct crew, ladder, materials, and repair vehicle.

**Objective**: Compress this 2-hour manual identification process down to **under 2 minutes** using 1-bit pole telemetry, automatically outputting exact span coordinates, PIN codes, affected household counts, and human-readable confidence explanations.

---

## 🔍 2. Key Observations & Physical Constraints

1. **Radial Tree Network (No Loops)**:
   - Low-tension distribution is strictly a forest of trees: `Substation -> Feeder -> Distribution Transformer (DT) -> LT Line Poles -> Service Drops`.
   - Every pole has exactly one path back to its transformer.

2. **Nodes vs. Edges**:
   - Telemetry devices report on **NODES** (poles report 1 bit: `energized` True/False).
   - Faults occur on **EDGES** (wire spans between poles, or equipment at DTs/feeders).
   - The observable signature of a line fault is a **LIVE/DARK BOUNDARY**: the last live pole and the first dark pole beyond it. The fault is on the span between them.

3. **Single Incident Aggregation (Anti-Cry-Wolf)**:
   - A single snapped span causes dozens of downstream poles to go dark.
   - All dark poles downstream of the same boundary represent **ONE incident**, not dozens of individual alerts.

4. **Dead Sensor Detection**:
   - A single isolated dark pole whose downstream children are still live is **PHYSICALLY IMPOSSIBLE** as a line fault.
   - The system recognizes this as a dead sensor (hardware failure) and refuses to open a power outage ticket.

5. **The Central Hard Problem (60% Missing Topology)**:
   - **40% of DTs** have a digitized wiring tree (`parent_pole_id` and `seq_on_line` present).
   - **60% of DTs** have NO recorded pole ordering—only surveyed GPS coordinates (`lat`, `lon`).
   - The system infers a tree using a Minimum Spanning Tree (MST) based on GPS coordinates rooted at the transformer location, tagging inferred edges with explicit lower confidence (`0.65`) and surfacing this to operators.

---

## 🏗️ 3. Architecture & Technology Stack

- **Backend Framework**: Python 3.12 / FastAPI (Async REST APIs + WebSockets)
- **Database**: PostgreSQL 16 (Relational schemas & incident state machine)
- **In-Memory Store / Cache**: Redis 7 (Telemetry rate limiting, state caching & real-time message fanout)
- **Frontend**: React 18 (Vite, TypeScript, TailwindCSS, Lucide Icons, Leaflet / OpenStreetMap)
- **Containerization**: Docker & Docker Compose (`docker-compose.yml`)

---

## 🚀 4. Quick Start (Single Command Startup)

Bring up the entire stack seeded with synthetic network data:

```bash
docker compose up --build
```

Access local endpoints:
- **2 a.m. Operator Control Console**: [http://localhost:3000](http://localhost:3000)
- **Backend Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Integrated Fault Simulator**: Available directly inside the Operator Console UI.

---

## 🧪 5. Testing & Verification

Run the complete backend test suite covering graph topology inference, burst deduplication, dead sensor filtering, simultaneous faults, and ticket lifecycle pushback:

```bash
python -m pytest backend/
```

---

## 📑 6. Project Documentation Index

- [ARCHITECTURE.md](file:///c:/Users/adity/OneDrive/Desktop/Github/prophel/ARCHITECTURE.md) - Graph algorithms, 60% missing topology strategy, burst handling & UI design rationale.
- [DEPLOYMENT.md](file:///c:/Users/adity/OneDrive/Desktop/Github/prophel/DEPLOYMENT.md) - Environment setup, configuration, and step-by-step troubleshooting guide.
- [DECISIONS.md](file:///c:/Users/adity/OneDrive/Desktop/Github/prophel/DECISIONS.md) - Architectural decision log, trade-offs, and assumptions.
- [AI-WORKFLOW.md](file:///c:/Users/adity/OneDrive/Desktop/Github/prophel/AI-WORKFLOW.md) - Detailed breakdown of AI leverage, prompt engineering, and discarded code analysis.
