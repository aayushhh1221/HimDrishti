"""
backend/api/routes/forecast.py
--------------------------------
GET /api/v1/forecast
SIH 2026 · PS 26059
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from ...schemas.responses import ErrorResponse, ForecastResponse
from ...services import route_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/forecast", tags=["forecast"])

_VALID_HORIZONS = {0, 24, 48, 72, 96, 120}


@router.get(
    "",
    response_model=ForecastResponse,
    summary="Get forecast metadata and data quality",
    description=(
        "Returns forecast horizon availability and data quality for the current pipeline run. "
        "Supports horizon_hours: 0, 24, 48, 72, 96, 120. "
        "PROTOTYPE: all data is SYNTHETIC_DEMO fixture. "
        "Not live satellite or NWP forecast data."
    ),
    responses={
        200: {"description": "Forecast metadata returned"},
        422: {"description": "Invalid horizon value"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def get_forecast(
    horizon_hours: int = Query(
        48,
        description="Requested forecast horizon in hours. Supported: 0, 24, 48, 72, 96, 120.",
        ge=0,
        le=120,
    ),
) -> ForecastResponse:
    if horizon_hours not in _VALID_HORIZONS:
        raise HTTPException(
            status_code=422,
            detail={
                "error": f"Invalid horizon_hours={horizon_hours}",
                "detail": f"Must be one of {sorted(_VALID_HORIZONS)}",
                "status": "INVALID_INPUT",
            },
        )
    try:
        return route_service.get_forecast(horizon_hours)
    except Exception as exc:
        logger.exception("Forecast service failed: %s", exc)
        raise HTTPException(status_code=500, detail={"status": "SERVER_ERROR"}) from exc
