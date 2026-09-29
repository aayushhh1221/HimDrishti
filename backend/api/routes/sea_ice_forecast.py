"""
backend/api/routes/sea_ice_forecast.py
----------------------------------------
GET /api/v1/sea-ice-forecast
SIH 2026 · PS 26059

Returns a structured sea-ice forecast (persistence + ML) derived from the
current data pipeline's sea-ice field.

This endpoint implements the core PS 26059 requirement:
  "Sea-Ice Forecasting"

Two modes:
  SYNTHETIC_DEMO  — uses fixture sea-ice field (always available)
  RESEARCH_DATA   — uses real ingested field (requires credentials)

The forecast chain:
  SeaIceField (obs/fixture)
    → persistence baseline (always)
    → ML model (if data + sklearn available)
    → evaluation (MAE, RMSE, time-ordered)
    → structured response
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/sea-ice-forecast", tags=["sea-ice-forecast"])
logger = logging.getLogger(__name__)

# Ensure project root importable
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_ROOT))

_VALID_METHODS = {"persistence", "ml", "auto"}
_PROTOTYPE_NOTICE = (
    "SIH 2026 Prototype · PS 26059 · Sea-ice forecast is ILLUSTRATIVE. "
    "Persistence and ML model trained on available data only. "
    "Not an operational ice-service product."
)


@router.get(
    "",
    summary="Sea-ice concentration forecast",
    description=(
        "Returns a sea-ice concentration forecast for the Southern Ocean / "
        "Indian Ocean sector (Cape Town → Bharati corridor). "
        "Implements persistence baseline and HistGradientBoostingRegressor ML model. "
        "Always reports honest MAE/RMSE comparison — no fabricated accuracy. "
        "SIH 2026 · PS 26059."
    ),
)
async def get_sea_ice_forecast(
    horizon_hours: int = Query(
        120,
        description="Max forecast horizon hours. Steps: 24, 48, 72, 96, 120.",
        ge=24,
        le=120,
    ),
    method: str = Query(
        "auto",
        description=(
            "'persistence' — persistence baseline only. "
            "'ml' — attempt ML (falls back to persistence if insufficient data). "
            "'auto' — ML if data supports it, else persistence."
        ),
    ),
) -> Dict[str, Any]:

    if method not in _VALID_METHODS:
        raise HTTPException(
            status_code=422,
            detail={
                "error": f"Invalid method='{method}'",
                "detail": f"Must be one of: {sorted(_VALID_METHODS)}",
                "status": "INVALID_INPUT",
            },
        )

    try:
        return await _run_forecast(horizon_hours, method)
    except Exception as exc:
        logger.exception("Sea-ice forecast failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"error": str(exc), "status": "SERVER_ERROR"},
        ) from exc


async def _run_forecast(horizon_hours: int, method: str) -> Dict[str, Any]:
    """Orchestrate the forecast run."""
    from data_pipeline.adapters.sea_ice import fetch_sea_ice
    from data_pipeline.adapters.wind import fetch_wind
    from data_pipeline.adapters.ocean_current import fetch_ocean_current
    from data_pipeline.data_mode import get_active_mode, DataMode
    from data_pipeline.forecast import (
        persistence_forecast, ml_forecast, forecast_to_dict,
    )

    mode = get_active_mode()
    use_fixture = (mode == DataMode.SYNTHETIC_DEMO)

    # ── Fetch environmental data ─────────────────────────────────────────
    now_utc = datetime.now(tz=timezone.utc)
    start_time = now_utc - timedelta(days=5)   # 5 days of obs history
    end_time = now_utc

    lat_min, lat_max = -80.0, -55.0
    lon_min, lon_max = 10.0, 90.0   # Indian Ocean sector

    logger.info(
        "Sea-ice forecast: mode=%s method=%s horizon=%dh",
        mode.value, method, horizon_hours)

    sea_ice = fetch_sea_ice(
        lat_min, lat_max, lon_min, lon_max,
        start_time, end_time,
        use_fixture=use_fixture,
    )

    # Fetch wind + ocean for ML features (graceful on failure)
    wind = None
    ocean = None
    if method in ("ml", "auto"):
        try:
            wind = fetch_wind(
                lat_min, lat_max, lon_min, lon_max,
                start_time, end_time,
                use_fixture=use_fixture,
            )
        except Exception as exc:
            logger.warning("Wind fetch for ML features failed: %s", exc)
        try:
            ocean = fetch_ocean_current(
                lat_min, lat_max, lon_min, lon_max,
                start_time, end_time,
                use_fixture=use_fixture,
            )
        except Exception as exc:
            logger.warning("Ocean fetch for ML features failed: %s", exc)

    # ── Build horizon steps ──────────────────────────────────────────────
    all_steps = [24, 48, 72, 96, 120]
    h_steps = [h for h in all_steps if h <= horizon_hours]
    if not h_steps:
        h_steps = [24]

    # ── Run forecast ─────────────────────────────────────────────────────
    if method == "persistence":
        forecast = persistence_forecast(sea_ice, h_steps)
    else:
        # ml or auto — ml_forecast falls back to persistence gracefully
        forecast = ml_forecast(sea_ice, wind, ocean, h_steps)

    result = forecast_to_dict(forecast)

    # Add mode label
    result["active_mode"] = mode.value
    result["prototype_notice"] = _PROTOTYPE_NOTICE

    return result
