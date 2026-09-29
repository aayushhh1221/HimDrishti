"""
backend/schemas/responses.py
------------------------------
Pydantic response models for HimDrishti API v1.
SIH 2026 · PS 26059

Phase 8 additions:
  - RouteMetrics: whole-voyage metrics per route
  - RiskBudgetStatus: WITHIN_BUDGET | EXCEEDS_BUDGET | NO_ROUTE_WITHIN_RISK_BUDGET
  - CounterfactualDelta: per-route delta vs baseline (from actual outputs, not invented)
  - CounterfactualComparison: baseline + comparisons list
  - ForecastConfidence: HIGH | MEDIUM | LOW | UNKNOWN + degradation flags
  - WholeVoyageRisk: max/integrated risk, highest-risk segment (where computable)
  - GenerateRoutesResponse extended with all above + operating_mode + run_log

All numpy arrays and dataclasses from the scientific core are converted
to JSON-safe Python types before reaching these models.

IMPORTANT LANGUAGE CONVENTION:
  - Never use "safe", "certified", "approved" for routes.
  - Always use "recommended", "lower modeled risk", "higher modeled risk".
  - Always expose data_mode: "SYNTHETIC_DEMO" | "FIXTURE" | "LIVE"
  - Never make fixture data appear as live satellite / operational data.
  - All risk values are "modeled" — not operational safety guarantees.
  - Captain/Master/Ice Pilot retains final navigation authority.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class DataModeEnum:
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    FIXTURE = "FIXTURE"
    LIVE = "LIVE"


# ---------------------------------------------------------------------------
# Route geometry point
# ---------------------------------------------------------------------------

class RoutePoint(BaseModel):
    """A single [lon, lat] coordinate pair on a route."""
    lon: float
    lat: float
    segment: str = Field(
        "pipeline",
        description=(
            "Segment type: 'approach' (origin → grid boundary, open ocean, not hazard-modeled), "
            "'pipeline' (within the Dijkstra / UCS hazard grid, scientifically computed), "
            "'arrival' (grid boundary → destination, not hazard-modeled). "
            "Frontend should style approach/arrival segments differently to indicate "
            "the pipeline did not model that portion of the route."
        ),
    )


# ---------------------------------------------------------------------------
# Cost breakdown
# ---------------------------------------------------------------------------

class RouteCostBreakdown(BaseModel):
    time_hours: float = Field(..., description="Estimated transit time in hours")
    fuel_tonnes: float = Field(..., description="Estimated fuel consumption in metric tonnes")
    risk_cost: float = Field(..., description="Cumulative POLARIS-based risk cost (dimensionless, prototype)")
    weighted_cost: float = Field(..., description="Total weighted objective cost (internal optimiser units)")


# ---------------------------------------------------------------------------
# Risk factors
# ---------------------------------------------------------------------------

class RiskFactors(BaseModel):
    environmental: float = Field(..., ge=0, le=100, description="Environmental risk score 0-100 (prototype)")
    navigation: float = Field(..., ge=0, le=100, description="Navigation risk score 0-100 (prototype)")
    ice_condition: float = Field(..., ge=0, le=100, description="Ice condition risk 0-100 (prototype)")
    iceberg_collision: float = Field(..., ge=0, le=100, description="Iceberg collision risk 0-100 (prototype)")


# ---------------------------------------------------------------------------
# Phase 8: Per-route metrics (whole-voyage, not just start point)
# ---------------------------------------------------------------------------

class RouteMetrics(BaseModel):
    """
    Whole-voyage metrics for a single route candidate.
    All values are from actual route outputs or marked None.
    Never fabricated.
    """
    max_segment_risk: Optional[float] = Field(
        None,
        description=(
            "Maximum risk cost encountered on any single route segment. "
            "None if not computable from current pipeline output."
        ),
    )
    integrated_risk: Optional[float] = Field(
        None,
        description=(
            "Cumulative (sum) risk cost across the whole route. "
            "Equal to RouteResult.total_risk_cost from route_search.py."
        ),
    )
    highest_risk_segment_index: Optional[int] = Field(
        None,
        description="Index of the highest-risk segment in the path. None if path not available.",
    )
    uncertainty_contribution: Optional[float] = Field(
        None,
        description=(
            "Estimated contribution of forecast uncertainty to total risk cost. "
            "In current SYNTHETIC_DEMO mode: fraction of risk attributable to iceberg ensemble spread."
        ),
    )
    distance_km: Optional[float] = Field(
        None,
        description="Approximate great-circle route distance in kilometres. None if not computed.",
    )
    path_cell_count: Optional[int] = Field(
        None,
        description="Number of grid cells in the route path (from route_search.py).",
    )


# ---------------------------------------------------------------------------
# Phase 8: Risk budget status
# ---------------------------------------------------------------------------

class RiskBudgetStatus(BaseModel):
    """
    Outcome of risk-budget constraint evaluation for a single route.

    WITHIN_BUDGET:   route's normalized modeled risk <= max_acceptable_risk
    EXCEEDS_BUDGET:  route's normalized modeled risk > max_acceptable_risk
    NO_ROUTE_WITHIN_RISK_BUDGET: no route found satisfying the risk budget
                     (not fabricated — the pipeline returned no valid path)
    """
    status: str = Field(
        ...,
        description="WITHIN_BUDGET | EXCEEDS_BUDGET | NO_ROUTE_WITHIN_RISK_BUDGET",
    )
    budget_limit: float = Field(..., description="max_acceptable_risk from request")
    actual_risk: Optional[float] = Field(
        None,
        description="Normalized modeled risk of this route. None if no route found.",
    )
    prototype_notice: str = Field(
        "Risk budget evaluation uses SYNTHETIC_DEMO values — not operational risk assessment.",
    )


# ---------------------------------------------------------------------------
# Phase 8: Counterfactual comparison
# ---------------------------------------------------------------------------

class CounterfactualDelta(BaseModel):
    """
    Delta metrics for one route vs the baseline route.
    ALL values come from actual route outputs.
    Missing metric → None (never fabricated, never a guessed offset).
    """
    route_id: str = Field(..., description="Route being compared")
    route_name: str = Field(..., description="Human-readable route name")

    fuel_delta_pct: Optional[float] = Field(
        None,
        description="Fuel change vs baseline in percent. Positive = more fuel. None if unavailable.",
    )
    eta_delta_hours: Optional[float] = Field(
        None,
        description="ETA change vs baseline in hours. Positive = longer. None if unavailable.",
    )
    risk_delta_pct: Optional[float] = Field(
        None,
        description="Modeled risk change vs baseline in percent. Positive = higher risk. None if unavailable.",
    )
    uncertainty_delta_pct: Optional[float] = Field(
        None,
        description="Uncertainty contribution change vs baseline in percent. None if unavailable.",
    )
    distance_delta_km: Optional[float] = Field(
        None,
        description="Route distance change vs baseline in km. None if unavailable.",
    )
    risk_budget_status: Optional[str] = Field(
        None,
        description="WITHIN_BUDGET | EXCEEDS_BUDGET for this route",
    )


class CounterfactualComparison(BaseModel):
    """
    Deterministic counterfactual comparison: all alternatives vs the baseline route.
    Values are calculated from actual route outputs — not invented.
    """
    baseline_route_id: str
    baseline_route_name: str
    comparisons: List[CounterfactualDelta] = Field(
        default_factory=list,
        description="Deltas for each non-baseline route vs the baseline",
    )
    prototype_notice: str = Field(
        "Counterfactual values calculated from SYNTHETIC_DEMO pipeline outputs. Not operational.",
    )


# ---------------------------------------------------------------------------
# Phase 8: Forecast confidence
# ---------------------------------------------------------------------------

class ForecastConfidence(BaseModel):
    """
    Deterministic forecast confidence/degradation assessment.

    Level:
        HIGH    — data fresh, horizon short, all sources available
        MEDIUM  — SYNTHETIC_DEMO baseline or moderate horizon
        LOW     — stale/partial sources or extended horizon (>72h)
        UNKNOWN — invalid/unavailable source data

    Degradation flags explain WHY confidence is reduced.
    No historical accuracy is invented.
    """
    level: str = Field(
        ...,
        description="HIGH | MEDIUM | LOW | UNKNOWN",
    )
    score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description=(
            "Optional 0-1 confidence score. "
            "None if insufficient data to compute. "
            "Not invented — only set when derivable from data quality."
        ),
    )
    degradation_flags: List[str] = Field(
        default_factory=list,
        description=(
            "Conditions that reduced forecast confidence. "
            "Examples: SYNTHETIC_DEMO_DATA, STALE_DATA_SOURCE, "
            "EXTENDED_HORIZON_REDUCED_CONFIDENCE, PARTIAL_DATA, INSUFFICIENT_VALIDATION"
        ),
    )
    horizon_policy: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Confidence level per forecast horizon step. "
            "Keys: '0h', '24h', '48h', '72h', '96h', '120h'. "
            "Values: HIGH | MEDIUM | LOW | UNKNOWN | INSUFFICIENT_VALIDATION"
        ),
    )
    assessment_basis: str = Field(
        ...,
        description="Brief explanation of how the confidence was determined",
    )


# ---------------------------------------------------------------------------
# Phase 8: Whole-voyage risk
# ---------------------------------------------------------------------------

class WholeVoyageRisk(BaseModel):
    """
    Risk assessment across the whole planned route — not just the starting point.

    Values derived from route_search.py RouteResult where available.
    Missing values are None — never fabricated.
    """
    max_segment_risk: Optional[float] = Field(
        None,
        description="Maximum risk on any single segment across all routes",
    )
    integrated_risk_recommended: Optional[float] = Field(
        None,
        description="Whole-route cumulative risk for the recommended route",
    )
    risk_budget_status_recommended: Optional[str] = Field(
        None,
        description="WITHIN_BUDGET | EXCEEDS_BUDGET for the recommended route",
    )
    highest_risk_segment_index: Optional[int] = Field(
        None,
        description="Grid step index of highest-risk segment in recommended route",
    )
    prototype_notice: str = Field(
        "Whole-voyage risk values are from SYNTHETIC_DEMO pipeline outputs. Not operational.",
    )


# ---------------------------------------------------------------------------
# Single route response
# ---------------------------------------------------------------------------

class RouteResponse(BaseModel):
    """One candidate route returned by the pipeline."""
    route_id: str
    name: str = Field(..., description="Human-readable route name. Uses 'recommended'/'alternative'/'higher-risk' language.")
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH")
    risk_category: str = Field(..., description="normal_operation | elevated_risk | special_consideration")
    polaris_rio: float = Field(
        ...,
        description=(
            "POLARIS Risk Index Outcome (RIO). "
            "PROTOTYPE: current RIV table is illustrative, not from IMO MSC.1/Circ.1519. "
            "Do not use for operational navigation decisions."
        ),
    )
    cost_breakdown: RouteCostBreakdown
    risk_factors: RiskFactors
    points: List[RoutePoint] = Field(..., description="Route geometry as ordered [lon, lat] points")
    label_coord: Optional[RoutePoint] = Field(None, description="Map label anchor point")
    color: str = Field(..., description="Hex colour for map rendering")
    system_explanation: str = Field(..., description="Deterministic explanation of why this route was chosen/ordered")
    rationale: str = Field(..., description="Short operational rationale for Captain Decision panel")

    # Phase 8 additions
    metrics: Optional[RouteMetrics] = Field(None, description="Whole-voyage metrics for this route")
    risk_budget_status: Optional[RiskBudgetStatus] = Field(None, description="Risk budget evaluation result")

    # Phase 10 additions: path distinctness
    is_distinct: bool = Field(
        True,
        description=(
            "True if this route's pipeline path_cells differ from all other routes. "
            "False means the Dijkstra / UCS search produced the same grid path under these weights — "
            "the hazard field does not support a meaningfully different route at this grid resolution. "
            "When False, do NOT draw a duplicate line on the map."
        ),
    )
    convergence_note: Optional[str] = Field(
        None,
        description=(
            "Explanation of why this route converged with another route, when is_distinct=False. "
            "Only set when is_distinct=False. Never set to hide a genuine difference."
        ),
    )

    # Metadata
    data_mode: str = Field(
        DataModeEnum.SYNTHETIC_DEMO,
        description="SYNTHETIC_DEMO | FIXTURE | LIVE — never omit",
    )
    prototype_notice: str = Field(
        "SIH 2026 Prototype · PS 26059 · Demonstration system only. "
        "POLARIS RIV table is illustrative. Not an operational navigation authority.",
        description="Mandatory prototype disclaimer",
    )


# ---------------------------------------------------------------------------
# Route generation response
# ---------------------------------------------------------------------------

class GenerateRoutesResponse(BaseModel):
    """Response from POST /api/v1/routes/generate."""
    request_id: str
    generated_at: str = Field(..., description="UTC ISO 8601 timestamp of generation")
    routes: List[RouteResponse]
    recommended_route_id: Optional[str] = Field(
        None,
        description=(
            "ID of the recommended route. None when the pipeline produced no viable routes "
            "(see pipeline_warnings and run_log for diagnostic details)."
        ),
    )
    forecast_horizon_hours: int
    data_mode: str
    data_quality_summary: Dict[str, str]
    provenance_summary: List[Dict[str, Any]]
    pipeline_warnings: List[str] = Field(default_factory=list)

    # Phase 8 additions
    operating_mode: str = Field(
        "BALANCED",
        description="Operating mode used for this run: SAFETY_FIRST | BALANCED | FUEL_SAVER",
    )
    risk_budget_limit: float = Field(
        0.55,
        description="max_acceptable_risk value used for this run",
    )
    counterfactual: Optional[CounterfactualComparison] = Field(
        None,
        description="Deterministic counterfactual comparison vs recommended baseline route",
    )
    forecast_confidence: Optional[ForecastConfidence] = Field(
        None,
        description="Forecast confidence/degradation assessment",
    )
    whole_voyage_risk: Optional[WholeVoyageRisk] = Field(
        None,
        description="Whole-voyage risk summary across all routes",
    )
    run_log: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Observability: run_id, operating_mode, risk_budget, forecast_horizon, "
            "data_mode, selected_route, timestamp. No secrets logged."
        ),
    )

    prototype_notice: str = Field(
        "SIH 2026 Prototype · PS 26059 · Demonstration system only. "
        "Not an operational navigation authority.",
    )


# ---------------------------------------------------------------------------
# Risk response
# ---------------------------------------------------------------------------

class RiskResponse(BaseModel):
    """Response from GET /api/v1/risk/{route_id}."""
    route_id: str
    polaris_rio: float
    polaris_status: str = Field(
        ...,
        description=(
            "ILLUSTRATIVE — not official POLARIS compliance. "
            "Authoritative RIV values must come from IMO MSC.1/Circ.1519."
        ),
    )
    risk_level: str
    risk_category: str
    risk_factors: RiskFactors
    system_explanation: str
    data_mode: str
    prototype_notice: str


# ---------------------------------------------------------------------------
# Forecast response
# ---------------------------------------------------------------------------

class ForecastDataQuality(BaseModel):
    sea_ice: str
    wind: str
    ocean_current: str
    icebergs: str


class ForecastResponse(BaseModel):
    """Response from GET /api/v1/forecast."""
    reference_time: str
    available_horizon_hours: int
    requested_horizon_hours: int
    horizon_steps: List[int] = Field(..., description="Available horizon steps in hours e.g. [0,24,48,72,96,120]")
    data_quality: ForecastDataQuality
    provenance: List[Dict[str, Any]]
    data_mode: str
    prototype_notice: str


# ---------------------------------------------------------------------------
# Provenance response
# ---------------------------------------------------------------------------

class ProvenanceRecord(BaseModel):
    source: str
    dataset_name: str
    retrieved_at: str
    valid_time_start: str
    valid_time_end: str
    spatial_coverage: str
    units: str
    coordinate_system: str
    status: str
    notes: str


class ProvenanceResponse(BaseModel):
    """Response from GET /api/v1/provenance."""
    records: List[ProvenanceRecord]
    data_mode: str
    generated_at: str
    prototype_notice: str


# ---------------------------------------------------------------------------
# Alert response
# ---------------------------------------------------------------------------

class AlertDetail(BaseModel):
    label: str
    value: str


class AlertResponse(BaseModel):
    id: str
    severity: str = Field(..., description="info | warning | critical")
    title: str
    description: str
    details: List[AlertDetail]
    forecast_horizon: str
    data_mode: str


class AlertsListResponse(BaseModel):
    """Response from GET /api/v1/alerts."""
    alerts: List[AlertResponse]
    data_mode: str
    generated_at: str
    prototype_notice: str


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Structured error returned on API failures."""
    error: str
    detail: str
    status: str = Field(
        ...,
        description=(
            "INVALID_INPUT | SERVER_ERROR | INSUFFICIENT_DATA | UNAVAILABLE | "
            "NO_ROUTE_WITHIN_RISK_BUDGET | INSUFFICIENT_FORECAST | INVALID_DATA"
        ),
    )
    prototype_notice: str = "SIH 2026 Prototype — not an operational navigation authority."


# ---------------------------------------------------------------------------
# Phase 9: Historical Replay response schemas
# ---------------------------------------------------------------------------

class HorizonVerificationResult(BaseModel):
    """Verification result at a single forecast horizon."""
    horizon_h: float
    sample_count: int
    mean_distance_error_km: Optional[float] = None
    max_distance_error_km: Optional[float] = None
    mean_lat_error_deg: Optional[float] = None
    mean_lon_error_deg: Optional[float] = None
    evaluation_status: str     # EVALUABLE | NOT_EVALUABLE | INSUFFICIENT_SAMPLES | NO_GROUND_TRUTH
    notes: str = ""


class ForecastVerificationResponse(BaseModel):
    """Forecast verification report for a replay run."""
    run_id: str
    dataset_id: str
    data_mode: str
    per_horizon: List[HorizonVerificationResult]
    evaluation_status: str
    confidence_calibration_status: str
    prototype_notice: str = (
        "SIH 2026 Prototype. Verification uses SYNTHETIC_REPLAY data. "
        "Confidence thresholds are PROVISIONAL/INSUFFICIENT_VALIDATION. "
        "Real independent observations required for genuine validation."
    )


class DatasetContractResponse(BaseModel):
    """Summary of a historical dataset contract."""
    dataset_id: str
    source: str
    product: str
    start_time: str
    end_time: str
    spatial_coverage: str
    retrieved_at: str
    data_mode: str
    quality_status: str
    access_note: str = ""
    prototype_notice: str = ""


class ReplayRunResponse(BaseModel):
    """Response for POST /api/v1/replay/run."""
    run_id: str
    dataset_id: str
    data_mode: str
    elapsed_seconds: float
    evaluation_status: str
    evaluation_note: str
    dataset_contract: DatasetContractResponse
    computation_trace: List[str]
    forecast_verification: ForecastVerificationResponse
    # Route result summary (from recommended route)
    route_risk: Optional[float] = None
    route_fuel_tonnes: Optional[float] = None
    route_eta_hours: Optional[float] = None
    provenance: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    prototype_notice: str = (
        "SIH 2026 Prototype — historical replay results from SYNTHETIC_DEMO pipeline. "
        "POLARIS RIV table is illustrative. Not an operational navigation authority."
    )


# ---------------------------------------------------------------------------
# Phase 9: Departure Window response schemas
# ---------------------------------------------------------------------------

class DepartureWindowResultResponse(BaseModel):
    """Result for a single departure window candidate."""
    offset_hours: int
    departure_time: str
    route_id: Optional[str] = None
    route_name: Optional[str] = None
    risk: Optional[float] = None
    fuel_tonnes: Optional[float] = None
    eta_hours: Optional[float] = None
    distance_km: Optional[float] = None
    risk_budget_status: Optional[str] = None
    forecast_confidence_level: Optional[str] = None
    forecast_confidence_score: Optional[float] = None
    data_quality: Dict[str, str] = Field(default_factory=dict)
    elapsed_seconds: float = 0.0
    error: Optional[str] = None


class DepartureWindowDeltaResponse(BaseModel):
    """Delta between a candidate departure and the baseline (offset=0)."""
    offset_hours: int
    risk_delta_pct: Optional[float] = None
    fuel_delta_pct: Optional[float] = None
    eta_delta_hours: Optional[float] = None
    distance_delta_km: Optional[float] = None


class DepartureWindowsResponse(BaseModel):
    """Response for POST /api/v1/planning/departure-windows."""
    base_departure_time: str
    operating_mode: str
    risk_budget_limit: float
    results: List[DepartureWindowResultResponse]
    deltas: List[DepartureWindowDeltaResponse]
    recommended_offset_hours: Optional[int] = None
    recommendation_basis: str = ""
    total_elapsed_seconds: float
    prototype_notice: str = (
        "SIH 2026 Prototype. Each departure-window candidate ran a genuine pipeline "
        "execution (no fabricated offsets). SYNTHETIC_DEMO data mode. "
        "Not an operational navigation authority. "
        "Final decision rests with the Captain/Master/Ice Pilot."
    )

