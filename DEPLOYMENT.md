# Deployment & Setup Guide

Written for someone who has cloned the repo and has nothing else installed.

---

## Prerequisites

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Docker | 20.10+ | https://docs.docker.com/get-docker/ |
| Docker Compose | 2.0+ (bundled with Docker Desktop) | Included with Docker Desktop |

No Python, Node.js, or database installation required on the host machine.

---

## Quick Start (Single Command)

```bash
git clone <your-repo-url>
cd prophel
docker compose up --build
```

The build takes approximately 2–3 minutes on first run (downloading base images and installing dependencies). Subsequent starts with `docker compose up` (no `--build`) take about 10 seconds.

---

## How to Verify It Worked

After `docker compose up` completes, you should see in terminal:

```
backend  | [OK] Seeding Complete: 412 DTs, 3708 Poles, 412 Trees loaded.
backend  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

Then open these URLs:

| URL | What you should see |
|-----|---------------------|
| http://localhost:3000 | Operator Console — dark UI with "Active Incidents (0)" and the fault simulator tab |
| http://localhost:8000/docs | FastAPI Swagger UI listing all API endpoints |
| http://localhost:8000/api/v1/health | JSON: `{"status": "ok", "system": "KSPDB Fault Localization System"}` |

**To confirm the system works end-to-end in 60 seconds:**
1. Open http://localhost:3000
2. Click **Fault Simulator** tab
3. Click **"Inject DT Transformer Blackout"**
4. Switch to **Operator Console** tab
5. You should see an incident `INC-DT-D-0003` appear within 1–2 seconds

---

## Environment Variables

All variables have safe defaults and the system will run without a `.env` file. Copy `.env.example` to `.env` to customise.

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `PORT` | Port the FastAPI backend listens on | No | `8000` |
| `DATABASE_URL` | PostgreSQL connection string. Not used in the in-memory demo mode — present for production extension. | No | `postgresql://kspdb_user:kspdb_pass@db:5432/kspdb` |
| `REDIS_URL` | Redis connection for telemetry rate-limiting and WebSocket pub/sub. The demo uses in-memory fallback if Redis is unreachable. | No | `redis://redis:6379/0` |

```bash
cp .env.example .env
# Edit .env if needed, then:
docker compose up --build
```

---

## Troubleshooting

These are failure modes encountered during development and deployment. For each: the symptom, and the fix.

---

### 1. Port 8000 or 3000 already in use

**Symptom:** Docker errors with `bind: address already in use` or the frontend shows a blank page.

**Fix:** Either stop the process using the port:
```bash
# Find and kill what's using port 8000
netstat -ano | findstr :8000   # Windows
lsof -i :8000                  # Mac/Linux
```
Or change the host port in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"   # Use 8001 instead
```

---

### 2. `UnicodeEncodeError` on Windows terminal (startup crash)

**Symptom:** Backend crashes immediately with `UnicodeEncodeError: 'charmap' codec can't encode character '\u2705'`.

**Fix:** Already patched in `main.py` — the `✅` emoji has been replaced with `[OK]`. If you see this, pull latest.

---

### 3. WebSocket connection fails / real-time updates not working

**Symptom:** Console shows "WebSocket connection failed" in browser devtools. Incidents only update on manual refresh.

**Fix — local:** The WS endpoint is `ws://localhost:8000/ws`. The app falls back to 3-second HTTP polling automatically, so functionality is preserved even if WS fails.

**Fix — behind a proxy (Nginx, Cloudflare, Railway):** Ensure the proxy passes the `Upgrade` header:
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

---

### 4. Frontend shows "Failed to fetch" / CORS error

**Symptom:** Browser console shows `Access-Control-Allow-Origin` error. Incidents don't load.

**Fix:** The backend has `allow_origins=["*"]` for the demo. This error usually means the backend isn't running or is on a different port than `8000`. Check that `docker compose up` started both services.

If deploying to a public URL, update `API_BASE` in `frontend/src/App.tsx`:
```typescript
const API_BASE = 'https://your-backend-url.com/api/v1';
```

---

### 5. `docker compose up` fails with "no space left on device"

**Symptom:** Docker build fails mid-way, usually on `pip install` or `npm install`.

**Fix:** Prune unused Docker images and volumes:
```bash
docker system prune -af
docker compose up --build
```

---

### 6. ARM vs x86 image mismatch (Apple Silicon / M1/M2 Mac)

**Symptom:** Container exits immediately with `exec format error`.

**Fix:** Force platform in `docker-compose.yml`:
```yaml
services:
  backend:
    platform: linux/amd64
    ...
```
Or build with:
```bash
docker compose build --platform linux/amd64
```

---

### 7. Backend starts but returns empty incidents list

**Symptom:** `GET /api/v1/incidents` returns `[]` even after injecting a fault.

**Cause:** The simulator endpoint requires `fault_type` and `target_id` as query parameters, not body JSON.

**Fix:** Use the UI simulator buttons, or call:
```bash
curl -X POST "http://localhost:8000/api/v1/simulator/inject-fault?fault_type=DT_FAULT&target_id=D-0003"
```

---

### 8. Redis unavailable warning in logs

**Symptom:** Logs show `redis.exceptions.ConnectionError` but the app still works.

**Cause:** The demo uses in-memory state stores, not Redis. Redis is included in `docker-compose.yml` for production readiness but is not required for the demo to function.

**Fix:** No action needed. This warning can be ignored in local demo mode.

---

## How to Reset to a Clean State

The system stores all state in memory — there is no persistent database in the demo mode. A full reset requires only restarting the backend:

```bash
# Full clean restart (re-seeds network from scratch):
docker compose down
docker compose up --build

# Quick restart without rebuilding images:
docker compose restart backend
```

After restart, all injected faults, incidents, and acknowledged tickets are wiped. The synthetic network is re-seeded automatically with the same 412 DTs and ~4,000 poles (deterministic random seed 42).

---

## Running Tests

```bash
# Run the full backend test suite (no Docker required):
python -m pytest backend/ -v
```

Expected output: **12 passed** across ingest, topology, localization, and lifecycle tests.
