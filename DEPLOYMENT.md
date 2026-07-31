# Deployment & Setup Guide

## Prerequisites
- Docker (v20.10+)
- Docker Compose (v2.0+)

## Quick Start (Single Command)

```bash
docker compose up --build
```

Access services:
- **Operator Console UI**: http://localhost:3000
- **FastAPI Swagger Docs**: http://localhost:8000/docs

## Environment Variables (.env.example)

| Variable | Description | Default |
|---|---|---|
| `PORT` | API Server Port | 8000 |
| `REDIS_URL` | Redis Cache Connection | redis://redis:6379/0 |

## Troubleshooting Guide

1. **Port 8000 or 3000 in use**:
   Change ports in `docker-compose.yml` to free host ports (e.g., `8001:8000`).
2. **WebSocket connection failed**:
   Ensure proxy allows WebSocket upgrades (`ws://localhost:8000/ws`).
