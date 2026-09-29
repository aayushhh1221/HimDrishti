"""
data_pipeline/replay/verification.py
--------------------------------------
Forecast verification for historical replay runs.
SIH 2026 · PS 26059

Phase 9.

Computes measurable verification metrics when independent ground truth
observations are available.

CRITICAL DESIGN RULES:
  - FORECAST INPUT is completely separate from ACTUAL OBSERVATION.
  - Never feed the future observed position into the forecast.
  - Missing ground truth → NOT_EVALUABLE (never 0, never fabricated).
  - Insufficient samples → INSUFFICIENT_SAMPLES (threshold: n < 2).
  - Horizons evaluated separately: 0h, 24h, 48h, 72h, 96h, 120h.
  - Do not combine all horizons into one misleading score.
  - No synthetic accuracy percentages from synthetic data.
  - Confidence thresholds from Phase 8 remain PROVISIONAL until
    validated against real independent observations.

Iceberg position error metrics:
  - latitude error (degrees)
  - longitude error (degrees)
  - great-circle distance error (km)
  - forecast horizon (hours)
  - evaluation status

Route evaluation metrics (where computable from actual pipeline):
  - predicted route risk
  - route distance km
  - ETA hours
  - fuel estimate
  - highest-risk segment index
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum number of independent observations required for evaluation
_MIN_SAMPLES_FOR_EVALUATION = 2

# Evaluation status constants
STATUS_EVALUABLE            = "EVALUABLE"
STATUS_NOT_EVALUABLE        = "NOT_EVALUABLE"
STATUS_INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
STATUS_NO_GROUND_TRUTH      = "NO_GROUND_TRUTH"

# Supported forecast horizons (hours)
FORECAST_HORIZONS_H = [0, 24, 48, 72, 96, 120]

# Earth mean radius (km)
_EARTH_RADIUS_KM = 6371.0


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IcebergObservationPoint:
    """
    A single independent iceberg position observation (ground truth).
    This must come from an independent source — NOT derived from the
    same data used to drive the forecast.
    """
    iceberg_id: str
    observed_at_hours: float     # hours after forecast reference time
    latitude: float              # degrees
    longitude: float             # degrees
    source: str = "GROUND_TRUTH"
    notes: str = ""


@dataclass
class ForecastPositionPoint:
    """A single forecast iceberg position at a given horizon."""
    iceberg_id: str
    forecast_horizon_hours: float
    forecast_latitude: float
    forecast_longitude: float


@dataclass
class IcebergPositionError:
    """
    Position error for a single iceberg at a single forecast horizon.
    All fields are None if evaluation is not possible.
    """
    iceberg_id: str
    forecast_horizon_h: float
    lat_error_deg: Optional[float]
    lon_error_deg: Optional[float]
    distance_error_km: Optional[float]
    evaluation_status: str               # EVALUABLE | NOT_EVALUABLE | etc.
    n_samples: int = 0
    notes: str = ""


@dataclass
class HorizonVerificationResult:
    """Aggregated verification across all icebergs at one forecast horizon."""
    horizon_h: float
    sample_count: int
    mean_distance_error_km: Optional[float]
    max_distance_error_km: Optional[float]
    mean_lat_error_deg: Optional[float]
    mean_lon_error_deg: Optional[float]
    evaluation_status: str
    notes: str = ""


@dataclass
class ForecastVerificationReport:
    """
    Complete forecast verification report for a replay run.
    Horizon results are separate — never combined into one score.
    """
    run_id: str
    dataset_id: str
    data_mode: str
    per_horizon: List[HorizonVerificationResult]
    evaluation_status: str
    confidence_calibration_status: str
    prototype_notice: str = (
        "SIH 2026 Prototype. Verification uses synthetic fixture data — "
        "confidence thresholds from Phase 8 remain PROVISIONAL/INSUFFICIENT_VALIDATION. "
        "Real independent iceberg observations required for genuine validation."
    )


@dataclass
class RouteVerificationResult:
    """Route-level metrics from a replay run (no comparison with 'actual route')."""
    run_id: str
    predicted_risk: Optional[float]
    actual_iceberg_proximity_km: Optional[float]
    route_distance_km: Optional[float]
    eta_hours: Optional[float]
    fuel_tonnes: Optional[float]
    highest_risk_segment_index: Optional[int]
    evaluation_status: str
    notes: str = ""


# ---------------------------------------------------------------------------
# Great-circle distance
# ---------------------------------------------------------------------------

def _great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine great-circle distance between two WGS-84 points.
    Returns distance in kilometres.
    """
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat   = math.radians(lat2 - lat1)
    dlon   = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return _EARTH_RADIUS_KM * c


# ---------------------------------------------------------------------------
# Per-iceberg error calculation
# ---------------------------------------------------------------------------

def compute_iceberg_position_error(
    forecast: ForecastPositionPoint,
    actual: Optional[IcebergObservationPoint],
) -> IcebergPositionError:
    """
    Compute position error for one iceberg at one forecast horizon.

    If 'actual' is None → NOT_EVALUABLE (never return 0 as substitute).
    If actual.source indicates it came from the same forecast data → NOT_EVALUABLE.
    """
    if actual is None:
        return IcebergPositionError(
            iceberg_id=forecast.iceberg_id,
            forecast_horizon_h=forecast.forecast_horizon_hours,
            lat_error_deg=None,
            lon_error_deg=None,
            distance_error_km=None,
            evaluation_status=STATUS_NOT_EVALUABLE,
            n_samples=0,
            notes="No independent ground-truth observation available.",
        )

    if actual.source in ("SYNTHETIC", "FIXTURE", "FORECAST"):
        return IcebergPositionError(
            iceberg_id=forecast.iceberg_id,
            forecast_horizon_h=forecast.forecast_horizon_hours,
            lat_error_deg=None,
            lon_error_deg=None,
            distance_error_km=None,
            evaluation_status=STATUS_NOT_EVALUABLE,
            n_samples=0,
            notes=(
                f"Ground truth source '{actual.source}' is not independent — "
                "same data used for forecast and observation. "
                "Cannot produce valid error estimate."
            ),
        )

    lat_err  = actual.latitude  - forecast.forecast_latitude
    lon_err  = actual.longitude - forecast.forecast_longitude
    dist_err = _great_circle_km(
        forecast.forecast_latitude, forecast.forecast_longitude,
        actual.latitude, actual.longitude,
    )

    return IcebergPositionError(
        iceberg_id=forecast.iceberg_id,
        forecast_horizon_h=forecast.forecast_horizon_hours,
        lat_error_deg=round(lat_err, 4),
        lon_error_deg=round(lon_err, 4),
        distance_error_km=round(dist_err, 3),
        evaluation_status=STATUS_EVALUABLE,
        n_samples=1,
        notes="",
    )


# ---------------------------------------------------------------------------
# Horizon aggregation
# ---------------------------------------------------------------------------

def aggregate_horizon_errors(
    errors: List[IcebergPositionError],
    horizon_h: float,
) -> HorizonVerificationResult:
    """
    Aggregate per-iceberg errors at one forecast horizon.
    Returns INSUFFICIENT_SAMPLES if fewer than _MIN_SAMPLES_FOR_EVALUATION
    evaluable errors are present.
    """
    evaluable = [e for e in errors if e.evaluation_status == STATUS_EVALUABLE
                 and e.distance_error_km is not None]

    if len(evaluable) == 0:
        return HorizonVerificationResult(
            horizon_h=horizon_h,
            sample_count=0,
            mean_distance_error_km=None,
            max_distance_error_km=None,
            mean_lat_error_deg=None,
            mean_lon_error_deg=None,
            evaluation_status=STATUS_NOT_EVALUABLE,
            notes="No evaluable observations at this horizon.",
        )

    if len(evaluable) < _MIN_SAMPLES_FOR_EVALUATION:
        return HorizonVerificationResult(
            horizon_h=horizon_h,
            sample_count=len(evaluable),
            mean_distance_error_km=None,
            max_distance_error_km=None,
            mean_lat_error_deg=None,
            mean_lon_error_deg=None,
            evaluation_status=STATUS_INSUFFICIENT_SAMPLES,
            notes=(
                f"Only {len(evaluable)} evaluable observation(s) at this horizon "
                f"(minimum required: {_MIN_SAMPLES_FOR_EVALUATION})."
            ),
        )

    dists = [e.distance_error_km for e in evaluable]
    lats  = [e.lat_error_deg for e in evaluable]
    lons  = [e.lon_error_deg for e in evaluable]

    return HorizonVerificationResult(
        horizon_h=horizon_h,
        sample_count=len(evaluable),
        mean_distance_error_km=round(sum(dists) / len(dists), 3),
        max_distance_error_km=round(max(dists), 3),
        mean_lat_error_deg=round(sum(lats) / len(lats), 4),
        mean_lon_error_deg=round(sum(lons) / len(lons), 4),
        evaluation_status=STATUS_EVALUABLE,
        notes=f"{len(evaluable)} independent observations.",
    )


# ---------------------------------------------------------------------------
# Full verification report
# ---------------------------------------------------------------------------

def verify_iceberg_trajectory(
    run_id: str,
    dataset_id: str,
    data_mode: str,
    forecast_positions: List[ForecastPositionPoint],
    actual_observations: List[IcebergObservationPoint],
) -> ForecastVerificationReport:
    """
    Produce a full forecast verification report for a replay run.

    Evaluates each supported forecast horizon (0h, 24h, 48h, 72h, 96h, 120h)
    separately. Never combines horizons into one score.

    Parameters
    ----------
    run_id             : replay run identifier
    dataset_id         : dataset contract ID
    data_mode          : SYNTHETIC_REPLAY | ARCHIVE | REANALYSIS
    forecast_positions : list of ForecastPositionPoint (from pipeline)
    actual_observations: list of IcebergObservationPoint (independent ground truth)
                         MUST NOT come from the same data used to drive the forecast.
    """
    # If running in synthetic mode — nothing to evaluate
    if data_mode == "SYNTHETIC_REPLAY":
        return ForecastVerificationReport(
            run_id=run_id,
            dataset_id=dataset_id,
            data_mode=data_mode,
            per_horizon=[
                HorizonVerificationResult(
                    horizon_h=float(h),
                    sample_count=0,
                    mean_distance_error_km=None,
                    max_distance_error_km=None,
                    mean_lat_error_deg=None,
                    mean_lon_error_deg=None,
                    evaluation_status=STATUS_NOT_EVALUABLE,
                    notes=(
                        "SYNTHETIC_REPLAY: no real independent observations available. "
                        "Synthetic replay cannot validate the scientific model."
                    ),
                )
                for h in FORECAST_HORIZONS_H
            ],
            evaluation_status=STATUS_NOT_EVALUABLE,
            confidence_calibration_status="PROVISIONAL/INSUFFICIENT_VALIDATION",
        )

    if not actual_observations:
        per_horizon = [
            HorizonVerificationResult(
                horizon_h=float(h),
                sample_count=0,
                mean_distance_error_km=None,
                max_distance_error_km=None,
                mean_lat_error_deg=None,
                mean_lon_error_deg=None,
                evaluation_status=STATUS_NO_GROUND_TRUTH,
                notes="No ground-truth observations provided.",
            )
            for h in FORECAST_HORIZONS_H
        ]
        return ForecastVerificationReport(
            run_id=run_id,
            dataset_id=dataset_id,
            data_mode=data_mode,
            per_horizon=per_horizon,
            evaluation_status=STATUS_NO_GROUND_TRUTH,
            confidence_calibration_status="PROVISIONAL/INSUFFICIENT_VALIDATION",
        )

    # Build lookup: (iceberg_id, horizon_h) → nearest actual observation
    obs_lookup: Dict[str, IcebergObservationPoint] = {}
    for obs in actual_observations:
        obs_lookup[obs.iceberg_id] = obs

    per_horizon_results: List[HorizonVerificationResult] = []
    any_evaluable = False

    for horizon_h in FORECAST_HORIZONS_H:
        horizon_errors: List[IcebergPositionError] = []

        for fp in forecast_positions:
            if abs(fp.forecast_horizon_hours - horizon_h) > 6.0:
                continue
            actual = obs_lookup.get(fp.iceberg_id)
            err = compute_iceberg_position_error(fp, actual)
            horizon_errors.append(err)

        result = aggregate_horizon_errors(horizon_errors, float(horizon_h))
        if result.evaluation_status == STATUS_EVALUABLE:
            any_evaluable = True
        per_horizon_results.append(result)

    overall_status = STATUS_EVALUABLE if any_evaluable else STATUS_NOT_EVALUABLE

    # Confidence calibration: only claim calibration with real data + sufficient samples
    total_evaluable = sum(
        r.sample_count for r in per_horizon_results
        if r.evaluation_status == STATUS_EVALUABLE
    )
    if total_evaluable >= 10:
        calibration_status = "CALIBRATED"
    elif total_evaluable >= 2:
        calibration_status = "PARTIAL/INSUFFICIENT_VALIDATION"
    else:
        calibration_status = "PROVISIONAL/INSUFFICIENT_VALIDATION"

    return ForecastVerificationReport(
        run_id=run_id,
        dataset_id=dataset_id,
        data_mode=data_mode,
        per_horizon=per_horizon_results,
        evaluation_status=overall_status,
        confidence_calibration_status=calibration_status,
    )


# ---------------------------------------------------------------------------
# Route-level verification
# ---------------------------------------------------------------------------

def verify_route_result(
    run_id: str,
    pipeline_result: Any,          # PipelineResult from runner
    actual_iceberg_positions: Optional[List[IcebergObservationPoint]] = None,
) -> RouteVerificationResult:
    """
    Extract route-level metrics from the pipeline result.
    Does NOT claim a route was 'correct' without genuine supporting data.
    """
    if pipeline_result is None:
        return RouteVerificationResult(
            run_id=run_id,
            predicted_risk=None,
            actual_iceberg_proximity_km=None,
            route_distance_km=None,
            eta_hours=None,
            fuel_tonnes=None,
            highest_risk_segment_index=None,
            evaluation_status=STATUS_NOT_EVALUABLE,
            notes="Pipeline result unavailable.",
        )

    route = pipeline_result.route_fast
    if route is None:
        return RouteVerificationResult(
            run_id=run_id,
            predicted_risk=None,
            actual_iceberg_proximity_km=None,
            route_distance_km=None,
            eta_hours=None,
            fuel_tonnes=None,
            highest_risk_segment_index=None,
            evaluation_status=STATUS_NOT_EVALUABLE,
            notes="No route result in pipeline output.",
        )

    # Closest actual iceberg to any route cell (if ground truth available)
    proximity_km = None
    if actual_iceberg_positions:
        path = getattr(route, "path_cells", [])
        if path:
            min_dist = float("inf")
            for obs in actual_iceberg_positions:
                for cell in path:
                    # cell is (row, col) — approximate with centroid
                    if hasattr(cell, "__len__") and len(cell) >= 2:
                        clat = -68.0 + cell[0] * 0.5  # rough approximation
                        clon = 45.0  + cell[1] * 0.5
                        d = _great_circle_km(clat, clon, obs.latitude, obs.longitude)
                        min_dist = min(min_dist, d)
            if min_dist < float("inf"):
                proximity_km = round(min_dist, 2)

    n_cells = len(getattr(route, "path_cells", []))
    # Approximate distance: grid cells × ~50 km average spacing
    approx_distance_km = round(n_cells * 50.0, 1) if n_cells > 0 else None

    return RouteVerificationResult(
        run_id=run_id,
        predicted_risk=round(route.total_risk_cost, 4) if route.total_risk_cost is not None else None,
        actual_iceberg_proximity_km=proximity_km,
        route_distance_km=approx_distance_km,
        eta_hours=round(route.total_time_hours, 2) if route.total_time_hours is not None else None,
        fuel_tonnes=round(route.total_fuel_tonnes, 2) if route.total_fuel_tonnes is not None else None,
        highest_risk_segment_index=None,  # not available from current pipeline schema
        evaluation_status=STATUS_EVALUABLE,
        notes=(
            "Route metrics from SYNTHETIC_DEMO pipeline. "
            "Do not interpret as historical accuracy without real archive data."
        ),
    )
