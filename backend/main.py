"""
HimDrishti — FastAPI Backend
SIH 2026 · PS 26059

Phase 7: Full API integration.
  GET  /health
  POST /api/v1/routes/generate
  GET  /api/v1/risk/{route_id}
  GET  /api/v1/forecast
  GET  /api/v1/provenance
  GET  /api/v1/alerts
  GET  /docs   (OpenAPI / Swagger UI)
  GET  /redoc

Phase 9 additions:
  POST /api/v1/replay/run
  POST /api/v1/planning/departure-windows

Deployment (Phase — Deployment):
  ALLOWED_ORIGINS env var: comma-separated list of allowed CORS origins.
  PORT env var: Render injects the port to bind — handled by render start command.

IMPORTANT: This is a prototype / demonstration system.
Not an operational navigation authority.
The POLARIS RIV table is illustrative — not from IMO MSC.1/Circ.1519.
"""

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Ensure project root is importable (for data_pipeline / ai modules) ────────
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("himdrishti.api")

# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="HimDrishti API",
    description=(
        "AI-Enabled Antarctic Sea-Ice, Iceberg Trajectory & "
        "Navigation Decision Support System. "
        "SIH 2026 · PS 26059 · Prototype / Demonstration System. "
        "Not an operational navigation authority. "
        "POLARIS RIV table is illustrative."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "system",   "description": "Health and liveness checks"},
        {"name": "routes",   "description": "Route generation (deterministic pipeline)"},
        {"name": "risk",     "description": "POLARIS-based risk profiles (illustrative)"},
        {"name": "forecast", "description": "Forecast metadata and data quality"},
        {"name": "sea-ice-forecast", "description": "Sea-ice concentration forecast (persistence + ML)"},
        {"name": "data-status", "description": "Active data mode and source availability"},
        {"name": "provenance","description": "Data lineage records"},
        {"name": "alerts",   "description": "Operational alerts derived from pipeline"},
        {"name": "replay",   "description": "Historical replay + forecast verification (Phase 9)"},
        {"name": "planning", "description": "Departure-window planning via genuine reruns (Phase 9)"},
    ],
)

# ── CORS — reads ALLOWED_ORIGINS env var for production ───────────────────────
# Always include local development origins.
# Production: set ALLOWED_ORIGINS=https://himdrishti.onrender.com (or your domain)
# in the Render environment variables panel — do NOT commit production URLs.
_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
]
_env_origins = os.environ.get("ALLOWED_ORIGINS", "")
_extra_origins = [o.strip() for o in _env_origins.split(",") if o.strip()]
_allowed_origins = list(dict.fromkeys(_DEFAULT_ORIGINS + _extra_origins))  # deduplicated

logger.info("CORS allowed origins: %s", _allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

# ── Register routers ──────────────────────────────────────────────────────────
from backend.api.routes.health import router as health_router                        # noqa: E402
from backend.api.routes.route_planner import router as routes_router                 # noqa: E402
from backend.api.routes.risk import router as risk_router                            # noqa: E402
from backend.api.routes.forecast import router as forecast_router                    # noqa: E402
from backend.api.routes.provenance import router as provenance_router                # noqa: E402
from backend.api.routes.alerts import router as alerts_router                        # noqa: E402
from backend.api.routes.replay import router as replay_router                        # noqa: E402
from backend.api.routes.planning import router as planning_router                    # noqa: E402
from backend.api.routes.reports import router as reports_router                      # noqa: E402
from backend.api.routes.data_status import router as data_status_router              # noqa: E402
from backend.api.routes.sea_ice_forecast import router as sea_ice_forecast_router    # noqa: E402

app.include_router(health_router)
app.include_router(routes_router)
app.include_router(risk_router)
app.include_router(forecast_router)
app.include_router(provenance_router)
app.include_router(alerts_router)
app.include_router(replay_router)
app.include_router(planning_router)
app.include_router(reports_router)
app.include_router(data_status_router)
app.include_router(sea_ice_forecast_router)

logger.info("HimDrishti API v0.4.0 — routers registered (PS26059 real-data upgrade)")
