# ── Stage 1: build the React UI ─────────────────────────────
FROM node:20-alpine AS ui-build
WORKDIR /ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY ui/ ./
RUN npm run build

# ── Stage 2: the API + scheduler ─────────────────────────────
FROM python:3.12-slim

WORKDIR /srv/pinnacle-sentinel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY --from=ui-build /ui/dist ui/dist

EXPOSE 8010

# Single worker ON PURPOSE: APScheduler runs inside the app process
# (app/services/scheduler_service.py), and multiple workers would mean
# duplicate EDGAR ingestion / flag-detection jobs firing concurrently --
# the exact race condition found and fixed by hand on 2026-07-27
# (concurrent going_concern_detector runs producing duplicate
# flag_events rows before the uq_filing_flag_type constraint existed).
# Matches Pinnacle Quant's identical --workers 1 reasoning.
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1"]
