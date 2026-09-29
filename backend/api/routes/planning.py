"""
backend/api/routes/planning.py
--------------------------------
Departure-window planning API endpoint.
SIH 2026 · PS 26059

Phase 9.

POST /api/v1/planning/departure-windows
  → DepartureWindowsResponse

Runs GENUINE sequential pipeline executions for each candidate departure time.
No fabricated offsets. No invented metrics.

Performance note:
  Each candidate runs the full pipeline (~60s including iceberg ensemble).
  Default 4 candidates → ~4 minutes total.
  Client should display an appropriate loading state.

Language convention:
  "Recommended under current forecast" / "Lower modeled risk"
  Never "safest departure" or "guaranteed" or "AI selected".
  Final decision rests with the Captain/Master/Ice Pilot.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.schemas.requests import DepartureWindowsRequest
from backend.schemas.responses import (
    DepartureWindowDeltaResponse,
    DepartureWindowResultResponse,
    DepartureWindowsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/planning", tags=["planning"])


@router.post(
    "/departure-windows",
    response_model=DepartureWindowsResponse,
    summary="Departure-window comparison (genuine pipeline reruns)",
    description=(
        "Evaluates candidate departure times (Current, +6h, +12h, +24h) by running "
        "a genuine pipeline execution for each. No deterministic offsets. "
        "All metrics come from real pipeline output. "
        "Runtime: ~60s per candidate. Default 4 candidates ≈ 4 minutes. "
        "Language: 'Recommended under current forecast' / 'Lower modeled risk'. "
        "Final navigation authority rests with Captain/Master/Ice Pilot."
    ),
)
def departure_windows_endpoint(request: DepartureWindowsRequest) -> DepartureWindowsResponse:
    from backend.services.departure_window import run_departure_windows

    logger.info(
        "Departure-window request: base=%s offsets=%s mode=%s budget=%.2f",
        request.base_departure_time.isoformat(),
        request.candidate_offsets_hours,
        request.operating_mode.value,
        request.risk_budget.max_acceptable_risk,
    )

    # Build the base_request_dict that matches GenerateRoutesRequest fields
    base_dict = {
        "origin": request.origin.model_dump(),
        "destination": request.destination.model_dump(),
        "departure_time": request.base_departure_time.isoformat(),
        "vessel": request.vessel.model_dump(),
        "forecast_horizon_hours": request.forecast_horizon_hours,
        "operating_mode": request.operating_mode.value,
        "risk_budget": request.risk_budget.model_dump(),
        "extreme_risk_acknowledged": request.extreme_risk_acknowledged,
    }

    try:
        comparison = run_departure_windows(
            base_request_dict=base_dict,
            offsets_hours=request.candidate_offsets_hours,
        )
    except Exception as exc:
        logger.error("Departure-window comparison failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Departure-window comparison failed",
                "detail": str(exc),
                "status": "SERVER_ERROR",
                "prototype_notice": "SIH 2026 Prototype — not an operational navigation authority.",
            },
        )

    # Convert service results → response schema
    results_resp = [
        DepartureWindowResultResponse(
            offset_hours             = r.offset_hours,
            departure_time           = r.departure_time,
            route_id                 = r.route_id,
            route_name               = r.route_name,
            risk                     = r.risk,
            fuel_tonnes              = r.fuel_tonnes,
            eta_hours                = r.eta_hours,
            distance_km              = r.distance_km,
            risk_budget_status       = r.risk_budget_status,
            forecast_confidence_level= r.forecast_confidence_level,
            forecast_confidence_score= r.forecast_confidence_score,
            data_quality             = r.data_quality,
            elapsed_seconds          = round(r.elapsed_seconds, 2),
            error                    = r.error,
        )
        for r in comparison.results
    ]

    deltas_resp = [
        DepartureWindowDeltaResponse(
            offset_hours     = d.offset_hours,
            risk_delta_pct   = d.risk_delta_pct,
            fuel_delta_pct   = d.fuel_delta_pct,
            eta_delta_hours  = d.eta_delta_hours,
            distance_delta_km= d.distance_delta_km,
        )
        for d in comparison.deltas
    ]

    return DepartureWindowsResponse(
        base_departure_time     = comparison.base_departure_time,
        operating_mode          = comparison.operating_mode,
        risk_budget_limit       = comparison.risk_budget_limit,
        results                 = results_resp,
        deltas                  = deltas_resp,
        recommended_offset_hours= comparison.recommended_offset_hours,
        recommendation_basis    = comparison.recommendation_basis,
        total_elapsed_seconds   = comparison.total_elapsed_seconds,
    )
