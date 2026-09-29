# HimDrishti

**AI-Enabled Antarctic Sea-Ice, Iceberg Trajectory & Navigation Decision Support System**

---

> **⚠ Prototype Notice**
>
> This is an **SIH 2026 prototype / demonstration system** and is **not an operational navigation authority**.
> It is not certified, not affiliated with any official government authority, and must not be used for real-world navigation decisions.

---

## Project Identity

| Field | Value |
|---|---|
| **Project name** | HimDrishti |
| **Competition** | Smart India Hackathon 2026 (SIH 2026) |
| **Problem Statement** | PS 26059 |
| **Domain** | Antarctic sea-ice monitoring, iceberg trajectory forecasting, ship navigation decision support |
| **Status** | Prototype / Demonstration |
| **Prototype label** | "SIH 2026 Prototype · PS 26059" |

---

## Purpose

HimDrishti provides an AI-assisted decision-support console for Antarctic maritime navigation:

- **Sea-ice hazard assessment** — satellite-derived ice concentration and edge mapping
- **Iceberg trajectory forecasting** — physics-based drift + ML correction with uncertainty cones
- **POLARIS risk scoring** — Polar Operational Limit Assessment Risk Indexing System (RIO) per route segment
- **Multi-objective route optimisation** — time / fuel / risk trade-offs
- **Captain decision interface** — system recommends, human decides

The system is designed for academic demonstration purposes under SIH 2026.

---

## Design Source of Truth

| File | Role |
|---|---|
| [`design.md`](design.md) | Complete visual, UX, and component specification — **must be read before any frontend work** |
| [`reference-ui.png`](reference-ui.png) | High-resolution annotated target UI screenshot — **final visual reference** |

All frontend decisions must be consistent with `design.md`.
When `design.md` and `reference-ui.png` conflict, `reference-ui.png` is the visual authority.

---

## Repository Structure

```
HimDrishti/
│
├── design.md                   ← Frontend design source of truth
├── reference-ui.png            ← Visual UI reference
├── README.md                   ← This file
├── .gitignore
│
├── frontend/                   ← React + TypeScript + Vite
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── components/         ← Reusable UI components
│       ├── pages/              ← Route Planner, Forecast Explorer, etc.
│       ├── design-system/      ← Tokens, typography, accessibility
│       ├── hooks/              ← Custom React hooks
│       ├── services/           ← API client layer
│       ├── types/              ← Shared TypeScript types
│       ├── utils/              ← Pure utility functions
│       └── assets/             ← Static assets
│
├── backend/                    ← Python + FastAPI
│   ├── main.py                 ← FastAPI entry point
│   ├── requirements.txt
│   ├── api/                    ← Route handlers
│   ├── models/                 ← Database models
│   ├── schemas/                ← Pydantic schemas
│   └── services/               ← Business logic
│
├── ai/                         ← Scientific AI modules
│   ├── iceberg_drift.py        ← Physics + ML iceberg drift
│   ├── polaris_risk.py         ← POLARIS RIO calculation
│   └── route_search.py         ← Multi-objective route optimisation
│
├── forecasting/                ← Forecast pipeline modules
├── risk_routing/               ← Risk and routing engine
├── data_pipeline/              ← Ingestion + preprocessing
├── digital_twin/               ← Digital twin layer
│
├── data/
│   ├── raw/                    ← Unprocessed satellite/model data
│   ├── processed/              ← Cleaned, gridded data
│   ├── historical_replay/      ← Historical voyage replay data
│   └── synthetic/              ← Synthetic demo data fixtures
│
├── database/                   ← DB migrations and schema
├── evaluation/                 ← Model evaluation scripts
├── tests/                      ← Top-level integration tests
├── docs/                       ← Technical documentation
│   ├── PROJECT_AUDIT.md        ← Phase 1 repository audit
│   └── PHASE_2_FOUNDATION.md   ← Phase 2 foundation log
└── deployment/                 ← Docker, CI/CD, deployment configs
```

---

## Technology Stack

### Frontend

| Item | Choice |
|---|---|
| Framework | React 18 |
| Language | TypeScript 5 |
| Build tool | Vite 5 |
| Styling | Vanilla CSS + design tokens |
| Font | Noto Sans (SIH 2026 Phase 3+) |
| Icons | Lucide (SIH 2026 Phase 3+) |
| Map | MapLibre GL JS (SIH 2026 Phase 3+) |

### Backend

| Item | Choice |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Server | Uvicorn |
| Validation | Pydantic v2 |

---

## Local Setup

### Prerequisites

- Node.js 20+ and npm 10+
- Python 3.11+

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok"}
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | System health check and prototype disclosure |
| `POST` | `/api/v1/routes/generate` | Deterministic Dijkstra / UCS multi-objective route generation |
| `GET` | `/api/v1/risk/{route_id}` | POLARIS RIO risk assessment (illustrative RIV table) |
| `GET` | `/api/v1/forecast` | Environmental forecast parameters and step metadata |
| `GET` | `/api/v1/sea-ice-forecast` | Sea-ice concentration forecast (persistence baseline & ML evaluation) |
| `GET` | `/api/v1/data-status` | Active data mode (`SYNTHETIC_DEMO` vs `RESEARCH_DATA`) & adapter status |
| `GET` | `/api/v1/provenance` | Data provenance records and sensor citations |
| `GET` | `/api/v1/alerts` | Active operational notices and ice warnings |
| `POST` | `/api/v1/replay/run` | Mission replay execution over historical/fixture data |
| `POST` | `/api/v1/planning/departure-windows` | Multi-candidate departure window analysis |
| `POST` | `/api/v1/reports/export` | Voyage Plan & POLARIS Dossier PDF export |
| `POST` | `/api/v1/reports/export/environmental` | Environmental Exposure Summary PDF export |

---

## Operating Modes

- **`SYNTHETIC_DEMO` (Default)**: Uses verified, deterministic Southern Ocean and Larsemann Hills fixtures for reproducible offline demonstrations. No external network or credentials required.
- **`RESEARCH_DATA`**: Designed to ingest research environmental data (CMEMS OSI-SAF sea-ice, Copernicus marine currents, ERA5 wind, Altiberg iceberg tracks). Requires valid data provider credentials configured in environment variables (`CMEMS_USERNAME`, `CMEMS_PASSWORD`, `CDS_API_KEY`). Real-world operational validation is not claimed.

---

## Development Rules

1. **`design.md` is the frontend design source of truth.** Read it completely before touching any frontend file.
2. **`reference-ui.png` is the visual target.** The final UI must reproduce it as closely as technically possible.
3. **Do not redesign the visual direction.** The target is a government-grade scientific navigation console.
4. **Every frontend component must align with the design system tokens** defined in `design.md` §33.
5. **Numbers must always have units** — `18.6 t`, `82 km`, `8h 42m`, `POLARIS RIO: 3.2`.
6. **Do not fake scientific accuracy.** Label all demo data clearly.
7. **WCAG 2.1 AA** accessibility is required throughout.
8. **Scientific modules** (`ai/`) use deterministic Dijkstra / Uniform-Cost Search (UCS) over 3D time-expanded grids, physics force-balance iceberg drift, and IMO MSC.1/Circ.1519-structured POLARIS RIO.
9. **Final navigation authority** rests solely with the Captain / Master / Ice Pilot.

---

## Disclaimer

```
HimDrishti is an academic prototype developed for SIH 2026 (PS 26059).

It is a demonstration system only.

It is not an operational navigation authority.
It is not certified for real Antarctic navigation.
It is not affiliated with or endorsed by any government ministry,
maritime authority, or scientific institution.

Data sources referenced are for demonstration purposes only.
Final navigation authority rests solely with the vessel Captain / Master.
```

---

*Last updated: 2026-09-29 | SIH 2026 Final Release (PS 26059)*
