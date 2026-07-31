# Karnataka State Power Distribution Board (KSPDB)
## Automated Outage Detection & Fault Localization System

A real-time telemetry processing, fault localization, and incident management system built for low-tension electricity distribution networks in Karnataka.

---

## 🏗️ Architecture & Technology Stack

- **Backend Framework**: Python 3.12 / FastAPI (async REST APIs + WebSockets)
- **Database**: PostgreSQL 16 (Relational state & ticket management)
- **In-Memory Store / PubSub**: Redis 7 (Telemetry rate limiting, state caching & real-time message fanout)
- **Frontend**: React 18 (Vite, TypeScript, TailwindCSS, Lucide Icons, Leaflet / OpenStreetMap)
- **Containerization**: Docker & Docker Compose (`docker-compose.yml`)

---

## 🚀 Quick Start (Local Docker Setup)

Bring up the entire stack with seeded data in a single command:

```bash
docker compose up --build
```

Access the services:
- **Operator Console**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Simulator Interface**: Integrated into the Operator Console UI.

---

## 📑 System Documentation

- [ARCHITECTURE.md](file:///c:/Users/adity/OneDrive/Desktop/Github/prophel/ARCHITECTURE.md) - Deep dive into algorithm, topology handling (100% known vs 60% missing), graph model, burst performance & AI integration.
- [DEPLOYMENT.md](file:///c:/Users/adity/OneDrive/Desktop/Github/prophel/DEPLOYMENT.md) - Comprehensive setup guide, environment variables & detailed troubleshooting.
- [DECISIONS.md](file:///c:/Users/adity/OneDrive/Desktop/Github/prophel/DECISIONS.md) - Architecture decision log, trade-offs, scope choices & future roadmap.
- [AI-WORKFLOW.md](file:///c:/Users/adity/OneDrive/Desktop/Github/prophel/AI-WORKFLOW.md) - Honest account of AI usage, prompts, discarded code & leverage analysis.
