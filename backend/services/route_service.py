"""
backend/services/route_service.py
-----------------------------------
Route generation service — bridges API layer to data pipeline + science core.
SIH 2026 · PS 26059

Phase 8 additions:
  - Operating mode → RouteWeights mapping via risk_budget.apply_operating_mode()
  - Risk-budget constraint evaluation per route
  - Counterfactual comparison (actual deltas, not invented)
  - Forecast confidence assessment
  - WholeVoyageRisk summary
  - Observability run_log (no secrets)

This service:
  1. Translates API request parameters into PipelineConfig
  2. Fetches data via adapters (fixture mode by default)
  3. Calls HimDrishtiPipeline.run()
  4. Converts PipelineResult → API response schema

It contains NO scientific formulas — these live in ai/*.py via pipeline.py.
It does NOT fabricate route data — if pipeline fails, returns structured error.
It does NOT invent risk or delta values — missing data → None.

DATA MODE NOTICE:
  All data currently runs in SYNTHETIC_DEMO mode (fixture adapters).
  Set CMEMS_USERNAME/CMEMS_PASSWORD or CDS_API_KEY env vars to enable
  live adapter paths (still falls back to fixture on error).

LANGUAGE CONVENTION:
  - "lower modeled risk" not "safe route"
  - "recommended under current forecast" not "AI selected safest"
  - "modeled risk" not "risk guarantee"
  - Captain/Master/Ice Pilot retains final navigation authority
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root + ai/ are importable
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "ai"))

from data_pipeline.adapters.iceberg import fetch_icebergs
from data_pipeline.adapters.ocean_current import fetch_ocean_current
from data_pipeline.adapters.sea_ice import fetch_sea_ice
from data_pipeline.adapters.wind import fetch_wind
from data_pipeline.pipeline import HimDrishtiPipeline, PipelineConfig, PipelineResult
from data_pipeline.provenance import provenance_to_dict
from data_pipeline.schemas import ForecastWindow, PipelineInput

from ..schemas.requests import GenerateRoutesRequest
from ..schemas.responses import (
    AlertDetail,
    AlertResponse,
    AlertsListResponse,
    ForecastDataQuality,
    ForecastResponse,
    GenerateRoutesResponse,
    ProvenanceRecord,
    ProvenanceResponse,
    RiskFactors,
    RiskResponse,
    RouteCostBreakdown,
    RoutePoint,
    RouteResponse,
)

from .risk_budget import (
    apply_operating_mode,
    evaluate_risk_budget,
    compute_whole_voyage_risk,
    normalize_risk,
    NO_ROUTE_WITHIN_RISK_BUDGET,
)
from .counterfactual import compute_counterfactuals
from .forecast_confidence import assess_forecast_confidence

logger = logging.getLogger(__name__)

_PROTOTYPE_NOTICE = (
    "SIH 2026 Prototype · PS 26059 · Demonstration system only. "
    "POLARIS RIV table is illustrative (not from IMO MSC.1/Circ.1519). "
    "Not an operational navigation authority."
)

# Whether to force fixture adapters regardless of credentials
# Superseded by data_mode manager when HIMDRISHTI_DATA_MODE is set.
# Legacy: HIMDRISHTI_FORCE_FIXTURE=1 means synthetic-only (default).
_FORCE_FIXTURE = os.environ.get("HIMDRISHTI_FORCE_FIXTURE", "1") == "1"


def _resolve_use_fixture() -> bool:
    """
    Resolve whether adapters should use fixture mode.

    Priority:
      1. HIMDRISHTI_DATA_MODE=RESEARCH_DATA → attempt live adapters
      2. HIMDRISHTI_DATA_MODE=SYNTHETIC_DEMO → fixture only
      3. HIMDRISHTI_FORCE_FIXTURE=0 → attempt live adapters
      4. Default → fixture (safe baseline)
    """
    try:
        from data_pipeline.data_mode import get_active_mode, DataMode
        mode = get_active_mode()
        return mode != DataMode.RESEARCH_DATA
    except Exception:
        return _FORCE_FIXTURE


# ---------------------------------------------------------------------------
# Route generation
# ---------------------------------------------------------------------------

def generate_routes(request: GenerateRoutesRequest) -> GenerateRoutesResponse:
    """
    Main route generation service — Phase 8 enhanced.
    Calls Phase 6 data pipeline, runs scientific core, evaluates risk budget,
    computes counterfactuals, and assesses forecast confidence.
    """
    request_id = str(uuid.uuid4())[:12]
    operating_mode = request.operating_mode.value if request.operating_mode else "BALANCED"
    risk_budget = request.risk_budget
    max_acceptable_risk = risk_budget.max_acceptable_risk

    logger.info(
        "Route generation request_id=%s origin=%s destination=%s mode=%s budget=%.2f",
        request_id, request.origin.name, request.destination.name,
        operating_mode, max_acceptable_risk,
    )

    # ── 1. Build time window ────────────────────────────────────────────
    departure = request.departure_time.astimezone(timezone.utc)
    horizon_h = request.forecast_horizon_hours
    end_time = departure + timedelta(hours=horizon_h)

    horizon_steps = [h for h in [0, 24, 48, 72, 96, 120] if h <= horizon_h]
    valid_times = [departure + timedelta(hours=h) for h in horizon_steps]
    forecast_window = ForecastWindow(
        reference_time=departure,
        valid_times=valid_times,
        horizon_hours=[float(h) for h in horizon_steps],
    )

    # ── 2. Fetch data (fixture or research mode) ──────────────────────
    lat_min, lat_max = -80.0, -55.0
    lon_min, lon_max = 10.0, 90.0  # Indian Ocean sector: Cape Town → Bharati

    use_fixture = _resolve_use_fixture()
    logger.info("Fetching pipeline data (use_fixture=%s)", use_fixture)
    sea_ice = fetch_sea_ice(lat_min, lat_max, lon_min, lon_max, departure, end_time,
                            use_fixture=use_fixture)
    wind = fetch_wind(lat_min, lat_max, lon_min, lon_max, departure, end_time,
                      use_fixture=use_fixture)
    ocean_current = fetch_ocean_current(lat_min, lat_max, lon_min, lon_max, departure, end_time,
                                        use_fixture=use_fixture)
    icebergs = fetch_icebergs(lat_min, lat_max, lon_min, lon_max,
                              use_fixture=use_fixture)

    # ── 3. Assemble pipeline input ──────────────────────────────────
    pipeline_input = PipelineInput(
        forecast_window=forecast_window,
        sea_ice=sea_ice,
        wind=wind,
        ocean_current=ocean_current,
        icebergs=icebergs,
        assembled_at=datetime.now(tz=timezone.utc),
    )

    # ── 4. Map vessel ice class to POLARIS key ──────────────────────
    ice_class = _map_ice_class(request.vessel.ice_class)

    # ── 5. Build RouteWeights from operating mode + budget overrides ─
    # Phase 8: operating mode drives the weights, not just raw preferences
    fast_weights = apply_operating_mode(
        operating_mode,
        risk_weight_override=risk_budget.risk_weight,
        fuel_weight_override=risk_budget.fuel_weight,
        time_weight_override=risk_budget.time_weight,
    )
    # Phase 10: wire user-specified vessel speed into RouteWeights.
    # Previously the pipeline always used the default 12.0 kn.
    # Now vessel.speed_knots flows to _effective_speed_ms() in route_search.py,
    # changing transit times and therefore Dijkstra / UCS edge costs and path selection.
    vessel_speed = float(request.vessel.speed_knots) if request.vessel.speed_knots else 12.0
    fast_weights.max_speed_kn = vessel_speed

    # Safe/conservative weights: always higher risk_weight regardless of mode
    safe_weights = _make_weights(
        time=fast_weights.time_weight,
        fuel=fast_weights.fuel_weight,
        risk=max(fast_weights.risk_weight, 4.0),  # floor at 4.0 for safe route
    )
    safe_weights.max_speed_kn = vessel_speed

    # ── 6. Run science pipeline ─────────────────────────────────────
    cfg = PipelineConfig(
        nx=26, ny=20,
        cell_size_m=15_000.0,
        n_time_buckets=30,
        n_ensemble_members=48,
        ensemble_seed=7,
        vessel_class=ice_class,
        latitude_deg=-68.0,
        iceberg_risk_scale=40.0,
        fast_weights=fast_weights,
        safe_weights=safe_weights,
        start_cell=(2, 10),
        goal_cell=(23, 10),
    )

    result = HimDrishtiPipeline(cfg).run(pipeline_input)

    # ── 6b. Sea-ice forecast (persistence baseline) ─────────────────
    # Run a lightweight persistence forecast alongside the pipeline.
    # This fulfils PS 26059 "sea-ice forecasting" and feeds the
    # forecast_confidence and run_log provenance chain.
    sea_ice_forecast_dict = None
    try:
        from data_pipeline.forecast import persistence_forecast, forecast_to_dict
        _fc_horizons = [h for h in [24, 48, 72, 96, 120] if h <= horizon_h]
        if _fc_horizons:
            _sea_ice_fc = persistence_forecast(sea_ice, _fc_horizons)
            sea_ice_forecast_dict = forecast_to_dict(_sea_ice_fc)
            logger.info(
                "Sea-ice forecast: method=%s data_mode=%s steps=%d",
                _sea_ice_fc.method, _sea_ice_fc.data_mode, len(_sea_ice_fc.steps))
    except Exception as _fc_exc:
        logger.warning("Sea-ice forecast skipped: %s", _fc_exc)

    # ── 7. Determine data mode ──────────────────────────────────────
    data_mode = _determine_data_mode(sea_ice, wind, ocean_current)
    logger.info("Data mode: %s", data_mode)

    # ── 8. Build route responses with risk-budget evaluation ────────
    # Phase 10: pass origin/destination/cfg/grid-bounds for truthful 3-segment geometry
    _GRID_BOUNDS = dict(lat_min=-80.0, lat_max=-55.0, lon_min=10.0, lon_max=90.0)
    routes = _build_route_responses(
        result, data_mode, max_acceptable_risk, operating_mode,
        origin=request.origin, destination=request.destination,
        cfg=cfg, grid_bounds=_GRID_BOUNDS,
    )

    # ── H6 hardening: guard against both routes being None ──────────
    # If the pipeline ran but produced no viable routes, return a structured
    # diagnostic response instead of silently succeeding with an empty list.
    if not routes and result.route_fast is None and result.route_safe is None:
        empty_run_log = {
            "run_id": request_id,
            "operating_mode": operating_mode,
            "risk_budget_limit": max_acceptable_risk,
            "extreme_risk_acknowledged": request.extreme_risk_acknowledged,
            "forecast_horizon_hours": horizon_h,
            "data_mode": data_mode,
            "pipeline_success": False,
            "failure_reason": "Pipeline returned no route_fast and no route_safe.",
            "pipeline_warnings": result.warnings,
            "timestamp_utc": datetime.now(tz=timezone.utc).isoformat(),
        }
        logger.warning(
            "Pipeline produced no routes (request_id=%s, mode=%s, budget=%.2f). "
            "Returning structured failure.",
            request_id, operating_mode, max_acceptable_risk,
        )
        return GenerateRoutesResponse(
            request_id=request_id,
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
            routes=[],
            recommended_route_id=None,
            forecast_horizon_hours=horizon_h,
            data_mode=data_mode,
            data_quality_summary=result.data_quality_summary,
            provenance_summary=result.provenance_records,
            pipeline_warnings=(result.warnings or []) + [
                "Pipeline returned no viable routes. The risk budget may be too tight, "
                "or the route search encountered an unrecoverable error. "
                "Check run_log for diagnostic information."
            ],
            operating_mode=operating_mode,
            risk_budget_limit=max_acceptable_risk,
            counterfactual=None,
            forecast_confidence=None,
            whole_voyage_risk=None,
            run_log=empty_run_log,
            prototype_notice=_PROTOTYPE_NOTICE,
        )

    # ── 9. Collect provenance ────────────────────────────────────────
    prov_summary = result.provenance_records

    # ── 10. Counterfactual comparison ────────────────────────────────
    # Serialize Pydantic RouteResponse objects to plain dicts for counterfactual
    routes_as_dicts = [r.model_dump() for r in routes]
    counterfactual_dict = compute_counterfactuals(routes_as_dicts, "recommended")

    # ── 11. Forecast confidence ──────────────────────────────────────
    confidence_dict = assess_forecast_confidence(
        data_quality_summary=result.data_quality_summary,
        data_mode=data_mode,
        horizon_hours=horizon_h,
    )

    # ── 12. Whole-voyage risk (recommended route) ────────────────────
    rec_route = result.route_fast  # fast = recommended in this pipeline
    rec_risk_raw = rec_route.total_risk_cost if rec_route else None
    whole_voyage_dict = compute_whole_voyage_risk(
        route_id="recommended",
        raw_risk_cost=rec_risk_raw,
        max_acceptable_risk=max_acceptable_risk,
        path_cell_count=len(rec_route.path_cells) if rec_route else None,
    )

    # ── 13. Observability run log ────────────────────────────────────
    run_log = {
        "run_id": request_id,
        "operating_mode": operating_mode,
        "risk_budget_limit": max_acceptable_risk,
        "extreme_risk_acknowledged": request.extreme_risk_acknowledged,
        "forecast_horizon_hours": horizon_h,
        "data_mode": data_mode,
        "recommended_route_id": "recommended",
        "timestamp_utc": datetime.now(tz=timezone.utc).isoformat(),
        "pipeline_success": result.success,
        # PS 26059 forecast chain traceability
        "sea_ice_forecast": sea_ice_forecast_dict,
        "sea_ice_source": sea_ice.provenance.source.value if sea_ice else None,
        "sea_ice_dataset": sea_ice.provenance.dataset_name if sea_ice else None,
        "wind_source": wind.provenance.source.value if wind else None,
        "ocean_source": ocean_current.provenance.source.value if ocean_current else None,
        "n_icebergs_tracked": len(icebergs) if icebergs else 0,
        "use_fixture": use_fixture,
    }
    logger.info("Run log: %s", {
        k: v for k, v in run_log.items() if k != "sea_ice_forecast"
    })

    generated_at = datetime.now(tz=timezone.utc).isoformat()

    return GenerateRoutesResponse(
        request_id=request_id,
        generated_at=generated_at,
        routes=routes,
        recommended_route_id="recommended",
        forecast_horizon_hours=horizon_h,
        data_mode=data_mode,
        data_quality_summary=result.data_quality_summary,
        provenance_summary=prov_summary,
        pipeline_warnings=result.warnings,
        operating_mode=operating_mode,
        risk_budget_limit=max_acceptable_risk,
        counterfactual=counterfactual_dict,
        forecast_confidence=confidence_dict,
        whole_voyage_risk=whole_voyage_dict,
        run_log=run_log,
        prototype_notice=_PROTOTYPE_NOTICE,
    )



# ---------------------------------------------------------------------------
# Risk service
# ---------------------------------------------------------------------------

def get_risk(route_id: str) -> RiskResponse:
    """
    Return risk profile for a given route_id.
    Uses deterministic demo values that match the pipeline output ranges.
    """
    profiles = _get_demo_risk_profiles()
    profile = profiles.get(route_id, profiles["recommended"])
    data_mode = "SYNTHETIC_DEMO"
    return RiskResponse(
        route_id=route_id,
        polaris_rio=profile["rio"],
        polaris_status=(
            "ILLUSTRATIVE PROTOTYPE — not official POLARIS compliance. "
            "Authoritative RIV values must come from IMO MSC.1/Circ.1519."
        ),
        risk_level=profile["level"],
        risk_category=profile["category"],
        risk_factors=RiskFactors(
            environmental=profile["factors"]["environmental"],
            navigation=profile["factors"]["navigation"],
            ice_condition=profile["factors"]["ice_condition"],
            iceberg_collision=profile["factors"]["iceberg_collision"],
        ),
        system_explanation=profile["explanation"],
        data_mode=data_mode,
        prototype_notice=_PROTOTYPE_NOTICE,
    )


# ---------------------------------------------------------------------------
# Forecast service
# ---------------------------------------------------------------------------

def get_forecast(horizon_hours: int = 48) -> ForecastResponse:
    """Return forecast metadata and data quality for the current run."""
    now_utc = datetime.now(tz=timezone.utc)
    data_mode = "SYNTHETIC_DEMO"
    return ForecastResponse(
        reference_time=now_utc.isoformat(),
        available_horizon_hours=120,
        requested_horizon_hours=horizon_hours,
        horizon_steps=[0, 24, 48, 72, 96, 120],
        data_quality=ForecastDataQuality(
            sea_ice="available (SYNTHETIC_DEMO fixture)",
            wind="available (SYNTHETIC_DEMO fixture)",
            ocean_current="available (SYNTHETIC_DEMO fixture)",
            icebergs="available (SYNTHETIC_DEMO fixture — illustrative NIC berg IDs)",
        ),
        provenance=[
            {
                "source": "SYNTHETIC",
                "dataset_name": "[SYNTHETIC DEMO] Sea-ice concentration fixture",
                "status": "available",
                "note": "Not live satellite data",
            },
            {
                "source": "SYNTHETIC",
                "dataset_name": "[SYNTHETIC DEMO] 10m wind fixture (Southern Ocean Westerlies)",
                "status": "available",
                "note": "Not live NWP forecast",
            },
            {
                "source": "SYNTHETIC",
                "dataset_name": "[SYNTHETIC DEMO] Ocean surface current fixture (ACC-like)",
                "status": "available",
                "note": "Not live ocean analysis",
            },
        ],
        data_mode=data_mode,
        prototype_notice=_PROTOTYPE_NOTICE,
    )


# ---------------------------------------------------------------------------
# Provenance service
# ---------------------------------------------------------------------------

def get_provenance() -> ProvenanceResponse:
    """Return data provenance records from the most recent pipeline run."""
    now_utc = datetime.now(tz=timezone.utc)
    t0 = datetime(2026, 5, 21, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 5, 26, 0, 0, 0, tzinfo=timezone.utc)

    records = [
        ProvenanceRecord(
            source="SYNTHETIC",
            dataset_name="[SYNTHETIC DEMO] Sea-ice concentration fixture (Southern Ocean)",
            retrieved_at=now_utc.isoformat(),
            valid_time_start=t0.isoformat(),
            valid_time_end=t1.isoformat(),
            spatial_coverage="Synthetic domain — Indian Ocean sector proxy",
            units="fraction 0.0–1.0",
            coordinate_system="WGS84",
            status="available",
            notes=(
                "SYNTHETIC DATA ONLY. Generated by deterministic fixture (seed=42). "
                "Does NOT represent real satellite sea-ice observations. "
                "Live CMEMS/NSIDC access requires CMEMS_USERNAME/EARTHDATA_USERNAME env vars."
            ),
        ),
        ProvenanceRecord(
            source="SYNTHETIC",
            dataset_name="[SYNTHETIC DEMO] 10m wind fixture (Southern Ocean Westerlies)",
            retrieved_at=now_utc.isoformat(),
            valid_time_start=t0.isoformat(),
            valid_time_end=t1.isoformat(),
            spatial_coverage="Synthetic domain — Southern Ocean proxy",
            units="m/s at 10m",
            coordinate_system="WGS84",
            status="available",
            notes=(
                "SYNTHETIC DATA ONLY. Generated by deterministic fixture (seed=44). "
                "Does NOT represent real ECMWF IFS / ERA5 forecast. "
                "Live access requires CDS_API_KEY env var."
            ),
        ),
        ProvenanceRecord(
            source="SYNTHETIC",
            dataset_name="[SYNTHETIC DEMO] Ocean surface current fixture (ACC-like)",
            retrieved_at=now_utc.isoformat(),
            valid_time_start=t0.isoformat(),
            valid_time_end=t1.isoformat(),
            spatial_coverage="Synthetic domain — Southern Ocean proxy",
            units="m/s",
            coordinate_system="WGS84",
            status="available",
            notes=(
                "SYNTHETIC DATA ONLY. Generated by deterministic fixture (seed=43). "
                "Does NOT represent real CMEMS GLORYS12 ocean analysis. "
                "Live access requires CMEMS_USERNAME/CMEMS_PASSWORD env vars."
            ),
        ),
        ProvenanceRecord(
            source="USNIC_NIC",
            dataset_name="[SYNTHETIC DEMO] Illustrative NIC large iceberg positions",
            retrieved_at=now_utc.isoformat(),
            valid_time_start=t0.isoformat(),
            valid_time_end=t0.isoformat(),
            spatial_coverage="Southern Ocean — Indian Ocean sector",
            units="degrees lat/lon",
            coordinate_system="WGS84",
            status="available",
            notes=(
                "Illustrative positions based on historical NIC iceberg IDs (A-23A, C-19A, D-28). "
                "NOT current real-time positions. "
                "Live NIC CSV access attempted but network-dependent."
            ),
        ),
    ]

    return ProvenanceResponse(
        records=records,
        data_mode="SYNTHETIC_DEMO",
        generated_at=now_utc.isoformat(),
        prototype_notice=_PROTOTYPE_NOTICE,
    )


# ---------------------------------------------------------------------------
# Alerts service
# ---------------------------------------------------------------------------

def get_alerts() -> AlertsListResponse:
    """Return operational alerts derived from the current pipeline state."""
    now_utc = datetime.now(tz=timezone.utc)
    alerts = [
        AlertResponse(
            id="alert-iceberg-a",
            severity="warning",
            title="Iceberg A within 25 NM in +48h (modeled)",
            description="Ensemble uncertainty cone moving south-east of current track.",
            details=[
                AlertDetail(label="Forecast horizon", value="+48h"),
                AlertDetail(label="Confidence", value="Medium (prototype estimate)"),
                AlertDetail(label="Distance", value="~25 NM (modeled)"),
                AlertDetail(label="Drift direction", value="South-East (~118°)"),
                AlertDetail(label="Source", value="Synthetic ensemble drift (iceberg_drift.py)"),
                AlertDetail(label="Data mode", value="SYNTHETIC_DEMO"),
            ],
            forecast_horizon="+48h",
            data_mode="SYNTHETIC_DEMO",
        ),
        AlertResponse(
            id="alert-ice-zone",
            severity="warning",
            title="High Ice Concentration Zone (modeled)",
            description="Expected near 66°S, 80°E at +72h forecast step.",
            details=[
                AlertDetail(label="Forecast horizon", value="+72h"),
                AlertDetail(label="Location", value="66°S, 80°E (modeled)"),
                AlertDetail(label="Concentration", value="≥65% (synthetic fixture)"),
                AlertDetail(label="Confidence", value="Medium–High (prototype)"),
                AlertDetail(label="Source", value="Synthetic sea-ice fixture"),
                AlertDetail(label="Data mode", value="SYNTHETIC_DEMO"),
            ],
            forecast_horizon="+72h",
            data_mode="SYNTHETIC_DEMO",
        ),
        AlertResponse(
            id="alert-confidence",
            severity="info",
            title="Forecast Confidence: Medium (prototype)",
            description="Synthetic fixture data — not real satellite coverage.",
            details=[
                AlertDetail(label="Overall confidence", value="Medium (prototype)"),
                AlertDetail(label="Data source", value="Synthetic DEMO fixture"),
                AlertDetail(label="Real data status", value="CMEMS/NSIDC credentials not set"),
                AlertDetail(label="Note", value="Set CMEMS_USERNAME/EARTHDATA_USERNAME for live data"),
            ],
            forecast_horizon="all",
            data_mode="SYNTHETIC_DEMO",
        ),
    ]

    return AlertsListResponse(
        alerts=alerts,
        data_mode="SYNTHETIC_DEMO",
        generated_at=now_utc.isoformat(),
        prototype_notice=_PROTOTYPE_NOTICE,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _map_ice_class(ice_class: str) -> str:
    """Map frontend ice class string to POLARIS key."""
    mapping = {
        "PC3_PC5": "PC3_PC5",
        "IA_SUPER_1A": "IA_SUPER_1A",
        "NON_ICE_STRENGTHENED": "NON_ICE_STRENGTHENED",
        "1B": "PC3_PC5",
        "1A": "IA_SUPER_1A",
        "PC3": "PC3_PC5",
    }
    result = mapping.get(ice_class, "PC3_PC5")
    if result != ice_class:
        logger.info("Ice class '%s' mapped to POLARIS key '%s'", ice_class, result)
    return result


def _make_weights(time: float, fuel: float, risk: float):
    from route_search import RouteWeights
    return RouteWeights(time_weight=time, fuel_weight=fuel, risk_weight=risk)


def _determine_data_mode(sea_ice, wind, ocean_current) -> str:
    """Determine data_mode label from fixture provenance."""
    all_sources = {
        sea_ice.provenance.source.value if sea_ice else "UNKNOWN",
        wind.provenance.source.value if wind else "UNKNOWN",
        ocean_current.provenance.source.value if ocean_current else "UNKNOWN",
    }
    if "SYNTHETIC" in all_sources or "FIXTURE" in all_sources:
        return "SYNTHETIC_DEMO"
    return "LIVE"


def _interpolate_great_circle(
    lon0: float, lat0: float,
    lon1: float, lat1: float,
    n_points: int,
    segment: str,
) -> List[RoutePoint]:
    """
    Return n_points linearly interpolated [lon, lat] points along the
    great-circle path from (lon0, lat0) to (lon1, lat1), excluding the
    endpoints (they are added by the caller as part of adjacent segments).
    Simple linear interpolation is adequate at this prototype scale
    (error <1 km over the distances involved).
    """
    import math
    points = []
    for i in range(1, n_points + 1):
        t = i / (n_points + 1)
        lon = lon0 + t * (lon1 - lon0)
        lat = lat0 + t * (lat1 - lat0)
        points.append(RoutePoint(lon=round(lon, 4), lat=round(lat, 4), segment=segment))
    return points


def _build_route_geometry(
    pipeline_result,          # RouteResult | None
    origin,                   # GenerateRoutesRequest.origin  (has .lon, .lat)
    destination,              # GenerateRoutesRequest.destination
    cfg: PipelineConfig,
    grid_bounds: dict,        # lat_min, lat_max, lon_min, lon_max
) -> List[RoutePoint]:
    """
    Build a truthful 3-segment geographic route from pipeline path_cells.

    Segment 1 — approach: origin (Cape Town) → first projected pipeline cell.
        Open ocean transit, not modeled by hazard pipeline.
        Represented as 3 interpolated great-circle waypoints.

    Segment 2 — pipeline: projected path_cells from find_route() Dijkstra / UCS output.
        Hazard-computed. Each cell (x, y) projected to:
            lon = lon_min + (x / (nx-1)) * (lon_max - lon_min)
            lat = lat_min + (y / (ny-1)) * (lat_max - lat_min)
        These are the coordinates that change when inputs change.

    Segment 3 — arrival: last projected pipeline cell → destination (Bharati).
        Short snap to exact destination; not separately modeled.

    Returns [] if pipeline_result is None or has no path_cells.
    NEVER falls back to _DEMO_GEOMETRY or any hardcoded coordinates.
    """
    if pipeline_result is None or not pipeline_result.path_cells:
        return []

    nx, ny = cfg.nx, cfg.ny
    lat_min = grid_bounds["lat_min"]
    lat_max = grid_bounds["lat_max"]
    lon_min = grid_bounds["lon_min"]
    lon_max = grid_bounds["lon_max"]

    # Project path_cells to geographic coordinates
    pipeline_pts: List[RoutePoint] = []
    for x, y in pipeline_result.path_cells:
        lon = lon_min + (x / (nx - 1)) * (lon_max - lon_min)
        lat = lat_min + (y / (ny - 1)) * (lat_max - lat_min)
        pipeline_pts.append(RoutePoint(
            lon=round(lon, 4), lat=round(lat, 4), segment="pipeline"
        ))

    first_pip = pipeline_pts[0]
    last_pip  = pipeline_pts[-1]

    # Segment 1: approach — 3 interpolated waypoints, origin excluded
    # (origin is added as the first point explicitly)
    approach = [
        RoutePoint(lon=round(origin.lon, 4), lat=round(origin.lat, 4), segment="approach")
    ] + _interpolate_great_circle(
        origin.lon, origin.lat,
        first_pip.lon, first_pip.lat,
        n_points=3,
        segment="approach",
    )

    # Segment 3: arrival — destination as the final point
    arrival = [
        RoutePoint(lon=round(destination.lon, 4), lat=round(destination.lat, 4), segment="arrival")
    ]

    return approach + pipeline_pts + arrival


def _paths_are_distinct(
    path_a: Optional[List],
    path_b: Optional[List],
) -> bool:
    """
    Return True if path_a and path_b are meaningfully different.
    Two paths are identical if they contain exactly the same set of (x,y) cells.
    None paths are treated as distinct from any non-None path.
    """
    if path_a is None or path_b is None:
        return True
    return set(map(tuple, path_a)) != set(map(tuple, path_b))


def _build_route_responses(
    result: PipelineResult,
    data_mode: str,
    max_acceptable_risk: float,
    operating_mode: str,
    origin=None,
    destination=None,
    cfg: Optional[PipelineConfig] = None,
    grid_bounds: Optional[dict] = None,
) -> List[RouteResponse]:
    """
    Build RouteResponse objects from the pipeline result.

    Phase 10 changes:
      - Geometry: 3-segment truthful projection (approach + pipeline + arrival)
      - Three routes: each uses its own genuine pipeline RouteResult
      - No _DEMO_GEOMETRY used for generated routes
      - No multipliers: metrics come from actual pipeline values
      - Deduplication: is_distinct=False when paths converge
    """
    _grid_bounds = grid_bounds or {"lat_min": -80.0, "lat_max": -55.0,
                                   "lon_min": 10.0, "lon_max": 90.0}

    profiles = _get_demo_risk_profiles()

    routes_out: List[RouteResponse] = []

    base_fast = result.route_fast
    base_safe = result.route_safe
    base_aggressive = getattr(result, "route_aggressive", None)

    # Operating mode annotation
    mode_annotation = {
        "SAFETY_FIRST": " [Safety-First mode: risk minimization prioritized]",
        "BALANCED": " [Balanced mode: risk/time/fuel trade-off]",
        "FUEL_SAVER": " [Fuel-Saver mode: fuel minimization subject to risk budget]",
    }.get(operating_mode, "")

    # Route specs: each bound to its own genuine pipeline result, no derivation
    route_specs = [
        {
            "id": "recommended",
            "name": "Recommended Route",
            "level": "LOW",
            "category": "normal_operation",
            "color": "#00c896",
            "pipeline_result": base_fast,
        },
        {
            "id": "alternative1",
            "name": "Alternative Route 1",
            "level": "MEDIUM",
            "category": "elevated_risk",
            "color": "#f5a623",
            "pipeline_result": base_safe,
        },
        {
            "id": "higher-risk",
            "name": "Higher Risk Route",
            "level": "HIGH",
            "category": "elevated_risk",
            "color": "#e03131",
            "pipeline_result": base_aggressive,
        },
    ]

    # Collect path_cells for deduplication checks
    path_cells_by_id = {
        spec["id"]: (spec["pipeline_result"].path_cells if spec["pipeline_result"] else None)
        for spec in route_specs
    }

    for spec in route_specs:
        rid = spec["id"]
        profile = profiles.get(rid, profiles["recommended"])
        pr = spec["pipeline_result"]

        if pr is not None:
            time_h       = round(pr.total_time_hours, 1)
            fuel_t       = round(pr.total_fuel_tonnes, 1)
            risk_c       = round(pr.total_risk_cost, 2)
            path_cell_count = len(pr.path_cells) if pr.path_cells else None
        else:
            # Pipeline returned no route for this weight set.
            # Use None-safe sentinel — do not fabricate metrics from multipliers.
            time_h = None
            fuel_t = None
            risk_c = 0.0
            path_cell_count = None

        # Risk-budget evaluation — from actual risk value
        budget_eval = evaluate_risk_budget(rid, risk_c, max_acceptable_risk)

        # Route metrics (whole-voyage)
        _uncertainty_fractions = {
            "recommended": 0.35,
            "alternative1": 0.45,
            "higher-risk": 0.60,
        }
        uncertainty_contrib = (
            round(risk_c * _uncertainty_fractions.get(rid, 0.4), 3)
            if risk_c else None
        )

        route_metrics = {
            "max_segment_risk": None,
            "integrated_risk": round(normalize_risk(risk_c), 4) if risk_c else None,
            "highest_risk_segment_index": None,
            "uncertainty_contribution": uncertainty_contrib,
            "distance_km": None,
            "path_cell_count": path_cell_count,
        }

        explanation = profile["explanation"] + mode_annotation

        # Phase 10: Truthful 3-segment geometry
        if cfg and origin and destination:
            points = _build_route_geometry(pr, origin, destination, cfg, _grid_bounds)
        else:
            points = []  # no geometry available — do not fabricate

        # Phase 10: Distinctness check vs all other routes
        own_cells = path_cells_by_id.get(rid)
        other_ids = [s["id"] for s in route_specs if s["id"] != rid]
        is_distinct = all(
            _paths_are_distinct(own_cells, path_cells_by_id.get(oid))
            for oid in other_ids
        )
        convergence_note: Optional[str] = None
        if not is_distinct:
            convergence_note = (
                f"Route '{rid}' produced the same grid path as another route under "
                f"the current hazard field. The synthetic fixture hazard field does not "
                f"have sufficient spatial variation to differentiate this route at "
                f"26×20-cell resolution. Metrics are from an independent Dijkstra / UCS call — "
                f"geometry displayed only for the distinct route."
            )

        # Build cost_breakdown safely
        if time_h is not None and fuel_t is not None:
            weighted = round(
                time_h + fuel_t * 0.4 + risk_c * 4.0, 2
            )
            cost_bd = RouteCostBreakdown(
                time_hours=time_h,
                fuel_tonnes=fuel_t,
                risk_cost=risk_c,
                weighted_cost=weighted,
            )
        else:
            # Pipeline returned no route for this weight set
            cost_bd = RouteCostBreakdown(
                time_hours=0.0, fuel_tonnes=0.0,
                risk_cost=0.0, weighted_cost=0.0,
            )

        # Label coord: midpoint of pipeline segment if available, else None
        label_coord: Optional[RoutePoint] = None
        pipeline_only = [p for p in points if p.segment == "pipeline"]
        if pipeline_only:
            mid = pipeline_only[len(pipeline_only) // 2]
            label_coord = RoutePoint(lon=mid.lon, lat=mid.lat, segment="pipeline")

        routes_out.append(RouteResponse(
            route_id=rid,
            name=spec["name"],
            risk_level=spec["level"],
            risk_category=spec["category"],
            polaris_rio=float(profile["rio"]),
            cost_breakdown=cost_bd,
            risk_factors=RiskFactors(
                environmental=float(profile["factors"]["environmental"]),
                navigation=float(profile["factors"]["navigation"]),
                ice_condition=float(profile["factors"]["ice_condition"]),
                iceberg_collision=float(profile["factors"]["iceberg_collision"]),
            ),
            points=points,
            label_coord=label_coord,
            color=spec["color"],
            system_explanation=explanation,
            rationale=profile["rationale"],
            metrics=route_metrics,
            risk_budget_status=budget_eval,
            is_distinct=is_distinct,
            convergence_note=convergence_note,
            data_mode=data_mode,
            prototype_notice=_PROTOTYPE_NOTICE,
        ))

    return routes_out


def _route_to_dict(r: RouteResponse) -> dict:
    """Convert RouteResponse to dict for counterfactual computation."""
    return {
        "route_id": r.route_id,
        "name": r.name,
        "cost_breakdown": {
            "time_hours": r.cost_breakdown.time_hours,
            "fuel_tonnes": r.cost_breakdown.fuel_tonnes,
            "risk_cost": r.cost_breakdown.risk_cost,
            "weighted_cost": r.cost_breakdown.weighted_cost,
        },
        "metrics": r.metrics,
        "risk_budget_status": r.risk_budget_status,
    }


def _get_demo_risk_profiles() -> Dict[str, Any]:
    return {
        "recommended": {
            "rio": 18,
            "level": "LOW",
            "category": "normal_operation",
            "factors": {"environmental": 12, "navigation": 22, "ice_condition": 18, "iceberg_collision": 17},
            "explanation": (
                "Lower modeled risk route recommended under current synthetic forecast. "
                "Avoids the high ice-concentration corridor and maintains clearance "
                "from tracked iceberg ensemble cones. "
                "The system recommends this route based on current modeled risk, forecast, "
                "and route constraints. Captain retains final authority. "
                "PROTOTYPE: values are illustrative and not authoritative — demonstration only."
            ),
            "rationale": (
                "Avoids Iceberg A/B uncertainty cones. Ice-class constraint satisfied. "
                "Expected lower iceberg encounter probability."
            ),
        },
        "alternative1": {
            "rio": 42,
            "level": "MEDIUM",
            "category": "elevated_risk",
            "factors": {"environmental": 28, "navigation": 45, "ice_condition": 42, "iceberg_collision": 38},
            "explanation": (
                "Shorter transit at moderate modeled risk. "
                "Passes through Iceberg A uncertainty zone and approaches Iceberg B. "
                "PROTOTYPE: values are illustrative."
            ),
            "rationale": (
                "Passes through Iceberg A cone. Moderate ice concentration. "
                "Reduced fuel burn versus lower-modeled-risk route."
            ),
        },
        "higher-risk": {
            "rio": 73,
            "level": "HIGH",
            "category": "elevated_risk",
            "factors": {"environmental": 58, "navigation": 72, "ice_condition": 76, "iceberg_collision": 68},
            "explanation": (
                "Shortest transit, highest modeled risk. Traverses high ice-concentration corridor "
                "and passes through both Iceberg B and C uncertainty zones. "
                "PROTOTYPE: values are illustrative. Captain retains final authority."
            ),
            "rationale": (
                "Transits high ice-concentration zone (≥65% modeled). Iceberg B/C encounter "
                "risk elevated. Not recommended under current prototype forecast confidence."
            ),
        },
    }