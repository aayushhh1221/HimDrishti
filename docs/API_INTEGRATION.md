# HimDrishti API Integration Guide
> SIH 2026 · PS 26059 · Phase 7  
> **PROTOTYPE / DEMONSTRATION SYSTEM — Not an operational navigation authority.**

---

## Overview

Phase 7 connects the React frontend to the FastAPI backend and the Phase 6 data pipeline.

```
React Frontend (Vite, port 5173)
      │
      │  HTTP (fetch API, CORS-enabled)
      ▼
FastAPI Backend (uvicorn, port 8000)
      │
      │  Python imports
      ▼
HimDrishtiPipeline (data_pipeline/pipeline.py)
      │
      ├── Adapters (sea ice / wind / ocean current / icebergs)
      │     └── Fixture fallback (SYNTHETIC_DEMO mode by default)
      ▼
Scientific Core (ai/)
  ├── iceberg_drift.py   — ensemble drift, uncertainty cones
  ├── polaris_risk.py    — POLARIS RIO (illustrative RIV table)
  └── route_search.py    — deterministic multi-objective Dijkstra / UCS
      │
      ▼
PipelineResult → API response → React UI
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness check |
| `POST` | `/api/v1/routes/generate` | Run pipeline, return 3 candidate routes |
| `GET`  | `/api/v1/risk/{route_id}` | Risk profile for a route |
| `GET`  | `/api/v1/forecast` | Forecast metadata and data quality |
| `GET`  | `/api/v1/provenance` | Data lineage records |
| `GET`  | `/api/v1/alerts` | Operational alerts from pipeline |
| `GET`  | `/docs` | OpenAPI / Swagger UI |
| `GET`  | `/redoc` | ReDoc documentation |

---

## Request Schemas

### `POST /api/v1/routes/generate`

```json
{
  "origin": {
    "name": "Cape Town, South Africa",
    "lat": -33.93,
    "lon": 18.42
  },
  "destination": {
    "name": "Bharati Station, Larsemann Hills",
    "lat": -69.41,
    "lon": 76.19
  },
  "departure_time": "2026-05-21T12:00:00Z",
  "vessel": {
    "name": "NCPOR Charter Vessel (Ice Class 1B)",
    "ice_class": "PC3_PC5",
    "draft_m": 7.2,
    "speed_knots": 12.0
  },
  "forecast_horizon_hours": 120,
  "route_preferences": {
    "risk_weight": 4.0,
    "time_weight": 1.0,
    "fuel_weight": 0.4
  }
}
```

> **Note:** `departure_time` must be timezone-aware ISO 8601 (e.g. `Z` suffix). Naive timestamps are rejected (HTTP 422).

---

## Response Schemas

### Route object (within `GenerateRoutesResponse`)

```json
{
  "route_id": "recommended",
  "name": "Recommended Route",
  "risk_level": "LOW",
  "risk_category": "normal_operation",
  "polaris_rio": 18.0,
  "cost_breakdown": {
    "time_hours": 134.0,
    "fuel_tonnes": 142.6,
    "risk_cost": 1.5,
    "weighted_cost": 228.2
  },
  "risk_factors": {
    "environmental": 12,
    "navigation": 22,
    "ice_condition": 18,
    "iceberg_collision": 17
  },
  "points": [
    { "lon": 18.42, "lat": -33.93 },
    "..."
  ],
  "color": "#00c896",
  "data_mode": "SYNTHETIC_DEMO",
  "prototype_notice": "SIH 2026 Prototype ..."
}
```

### Error response

```json
{
  "error": "Pipeline execution failed",
  "detail": "An internal error occurred during route generation.",
  "status": "SERVER_ERROR",
  "prototype_notice": "SIH 2026 Prototype..."
}
```

---

## Data Mode

Every API response includes `data_mode`:

| Value | Meaning |
|-------|---------|
| `SYNTHETIC_DEMO` | Deterministic fixture data — not live data |
| `FIXTURE` | Cached fixture with known provenance |
| `LIVE` | Live public dataset (requires credentials) |

> **Rule:** The frontend must never display fixture data as if it were live satellite or operational data.

---

## Demo / API Mode

The frontend operates in two modes:

| Mode | Trigger | Behaviour |
|------|---------|-----------|
| **Demo** | Backend unreachable or routes not yet generated | Shows static `DEMO_ROUTES`, `DEMO_RISK`, `DEMO_ALERTS`, `DEMO_PROVENANCE` from `frontend/src/data/` |
| **API** | User clicks "Generate Routes" and backend responds | Shows API-backed routes; Alerts and Provenance panels show API data on mount |

The demo fallback is **explicit** — the UI shows "Backend unavailable — showing demo data" banners when appropriate.

---

## Loading and Error States

| State | Description | Component behaviour |
|-------|-------------|---------------------|
| `idle` | No request made | Shows demo data |
| `loading` | Request in flight | Button shows spinner, panels show last data |
| `success` | API responded OK | Shows API data |
| `error` | API returned non-2xx | Shows inline error message |
| `unavailable` | Network error (backend unreachable) | Shows yellow "Backend unavailable" banner, uses demo fallback |

---

## Frontend Service Architecture

```
frontend/src/
  services/api/
    config.ts      ← VITE_API_BASE_URL
    types.ts       ← TypeScript types matching backend schemas
    client.ts      ← Centralized fetch functions (all API calls here)
    index.ts       ← Barrel re-export
  hooks/
    useApi.ts      ← React hooks: useRoutes, useAlerts, useProvenance, useForecast
  contexts/
    RoutePlannerContext.tsx  ← Shared state: routeState, selectedRouteId, activeRoute
```

---

## CORS Configuration

FastAPI allows only:
- `http://localhost:5173`
- `http://127.0.0.1:5173`

Never use `allow_origins=["*"]` in production.

---

## Environment Configuration

**Backend:**  Set env vars in shell or `.env` (never commit):
```
HIMDRISHTI_FORCE_FIXTURE=1      # 1 = always use fixture adapters (default)
CMEMS_USERNAME=...              # For live CMEMS sea-ice / ocean current
CMEMS_PASSWORD=...
CDS_API_KEY=...                 # For live ECMWF IFS wind
EARTHDATA_USERNAME=...          # For NASA EarthData (NSIDC icebergs)
```

**Frontend:**  Copy `frontend/.env.example` → `frontend/.env.local`:
```
VITE_API_BASE_URL=http://localhost:8000
```

> **NEVER** put backend credentials in `VITE_*` variables — they are visible in the browser.

---

## Local Development Commands

```bash
# 1. Start the backend
cd D:\HimDrishti
uvicorn backend.main:app --reload --port 8000

# 2. Start the frontend (separate terminal)
cd D:\HimDrishti\frontend
npm run dev

# 3. Open in browser
http://localhost:5173/route-planner

# 4. OpenAPI docs
http://localhost:8000/docs

# 5. Run all tests
cd D:\HimDrishti
python -m pytest tests/ -v

# 6. Run demo pipeline
python demo/demo_run.py
```

---

## Known Limitations

1. **SYNTHETIC_DEMO data only** — The scientific pipeline currently operates on deterministic fixture data seeded with `numpy.random.seed(42/43/44)`. It does NOT connect to live satellite data unless `CMEMS_USERNAME`, `CDS_API_KEY`, and `EARTHDATA_USERNAME` env vars are set.

2. **Illustrative POLARIS RIV table** — `ai/polaris_risk.py` uses a placeholder RIV lookup table. It is NOT the authoritative table from IMO MSC.1/Circ.1519. Do not use for operational navigation decisions.

3. **Demo geometry** — Route coordinates are preserved from Phase 4 (Cape Town → Bharati Station, Indian Ocean sector proxy). The pipeline operates in a synthetic local grid — coordinate-to-grid mapping requires a polar-stereographic projection not yet implemented.

4. **No authentication** — Phase 7 does not implement authentication. Do not expose the backend to the public internet in this state.

5. **Captain Decision is local only** — Accept/Reject/Modify decisions are UI-only state. No decision is persisted or sent to external systems.

6. **No real-time updates** — The frontend does not poll for live data. Each "Generate Routes" click makes a single synchronous request.

---

## Scientific Core

The following files are the scientific backbone and have not been modified:

| File | Purpose |
|------|---------|
| `ai/iceberg_drift.py` | Ensemble iceberg drift with uncertainty cones |
| `ai/polaris_risk.py` | POLARIS RIO calculation (illustrative RIV) |
| `ai/route_search.py` | Deterministic multi-objective Dijkstra / UCS route search |

These are treated as read-only logic engines by the pipeline and API layer.

---

## Git History

| Commit | Description |
|--------|-------------|
| `320aec8` | feat: establish real data pipeline foundation (Phase 6) |
| *(Phase 7)* | feat: integrate frontend with backend APIs |
