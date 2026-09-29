"""
backend/api/routes/replay.py
------------------------------
Historical replay API endpoint.
SIH 2026 · PS 26059

Phase 9.

POST /api/v1/replay/run
  → ReplayRunResponse

Runs a historical replay using the dataset_contract registry.
Reuses existing Phase-6 adapter + pipeline architecture.
Returns provenance, forecast verification, computation trace, and route metrics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from backend.schemas.requests import ReplayRunRequest
from backend.schemas.responses import (
    DatasetContractResponse,
    ForecastVerificationResponse,
    HorizonVerificationResult,
    ReplayRunResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/replay", tags=["replay"])


@router.post(
    "/run",
    response_model=ReplayRunResponse,
    summary="Run a historical replay",
    description=(
        "Runs a reproducible historical pipeline replay using the specified dataset contract. "
        "Same dataset_id + same seed → same output. "
        "SYNTHETIC_REPLAY mode used by default (offline-first). "
        "Forecast verification results are NOT_EVALUABLE for SYNTHETIC_REPLAY data."
    ),
)
def run_replay_endpoint(request: ReplayRunRequest) -> ReplayRunResponse:
    from data_pipeline.replay.runner import ReplayRunRequest as RunnerRequest, run_replay
    from data_pipeline.replay.verification import (
        verify_iceberg_trajectory,
        ForecastPositionPoint,
    )

    logger.info(
        "Replay run: dataset=%s start=%s seed=%d",
        request.dataset_id, request.start_time.isoformat(), request.seed,
    )

    try:
        runner_req = RunnerRequest(
            dataset_id=request.dataset_id,
            start_time=request.start_time,
            end_time=request.end_time,
            seed=request.seed,
            config=request.config or {"vessel_class": "PC3_PC5"},
            forecast_horizon_hours=request.forecast_horizon_hours,
        )
        result = run_replay(runner_req)
    except Exception as exc:
        logger.error("Replay run failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Replay execution failed",
                "detail": str(exc),
                "status": "SERVER_ERROR",
                "prototype_notice": "SIH 2026 Prototype — not an operational navigation authority.",
            },
        )

    # ── Forecast verification ─────────────────────────────────────────
    # No ground-truth observations in SYNTHETIC_REPLAY mode.
    verification_report = verify_iceberg_trajectory(
        run_id=result.run_id,
        dataset_id=result.dataset_id,
        data_mode=result.data_mode,
        forecast_positions=[],     # no forecast positions from pipeline yet
        actual_observations=[],    # no independent ground truth
    )

    # ── Extract route metrics from pipeline result ─────────────────────
    route_risk = None
    route_fuel = None
    route_eta  = None
    if result.pipeline_result and result.pipeline_result.route_fast:
        rf = result.pipeline_result.route_fast
        route_risk = round(rf.total_risk_cost / 10.0, 4) if rf.total_risk_cost else None
        route_fuel = round(rf.total_fuel_tonnes, 2)      if rf.total_fuel_tonnes else None
        route_eta  = round(rf.total_time_hours, 2)       if rf.total_time_hours else None

    # ── Build response ─────────────────────────────────────────────────
    contract = result.dataset_contract
    contract_resp = DatasetContractResponse(
        dataset_id       = contract.dataset_id,
        source           = contract.source,
        product          = contract.product,
        start_time       = contract.start_time,
        end_time         = contract.end_time,
        spatial_coverage = contract.spatial_coverage,
        retrieved_at     = contract.retrieved_at,
        data_mode        = contract.data_mode,
        quality_status   = contract.quality_status,
        access_note      = contract.access_note,
        prototype_notice = contract.prototype_notice,
    )

    verification_resp = ForecastVerificationResponse(
        run_id           = verification_report.run_id,
        dataset_id       = verification_report.dataset_id,
        data_mode        = verification_report.data_mode,
        per_horizon      = [
            HorizonVerificationResult(
                horizon_h               = h.horizon_h,
                sample_count            = h.sample_count,
                mean_distance_error_km  = h.mean_distance_error_km,
                max_distance_error_km   = h.max_distance_error_km,
                mean_lat_error_deg      = h.mean_lat_error_deg,
                mean_lon_error_deg      = h.mean_lon_error_deg,
                evaluation_status       = h.evaluation_status,
                notes                   = h.notes,
            )
            for h in verification_report.per_horizon
        ],
        evaluation_status              = verification_report.evaluation_status,
        confidence_calibration_status  = verification_report.confidence_calibration_status,
    )

    return ReplayRunResponse(
        run_id               = result.run_id,
        dataset_id           = result.dataset_id,
        data_mode            = result.data_mode,
        elapsed_seconds      = round(result.elapsed_seconds, 2),
        evaluation_status    = result.evaluation_status,
        evaluation_note      = result.evaluation_note,
        dataset_contract     = contract_resp,
        computation_trace    = result.computation_trace,
        forecast_verification= verification_resp,
        route_risk           = route_risk,
        route_fuel_tonnes    = route_fuel,
        route_eta_hours      = route_eta,
        provenance           = result.provenance,
        error                = result.error,
    )
