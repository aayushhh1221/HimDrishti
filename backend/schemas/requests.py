"""
backend/schemas/requests.py
-----------------------------
Pydantic request models for HimDrishti API v1.
SIH 2026 · PS 26059

Phase 8 additions:
  - OperatingMode: SAFETY_FIRST | BALANCED | FUEL_SAVER
  - RiskBudget: typed risk constraint (MINIMIZE fuel/time SUBJECT TO risk <= budget)
  - extreme_risk_acknowledged: required gate for unusually high risk tolerance
  - operating_mode + risk_budget fields in GenerateRoutesRequest

DEFERRED (Phase 9):
  - DepartureWindowOption: requires full pipeline rerun per candidate departure time.
    Not implemented in Phase 8. Do not add deterministic offsets as a substitute.

All inputs are validated by Pydantic before reaching any service or
scientific code. Invalid requests return HTTP 422 — never silently
corrected.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Coordinate point
# ---------------------------------------------------------------------------

class GeoPoint(BaseModel):
    """A named geographic point."""
    name: str = Field(..., description="Human-readable location name")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude, degrees north")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude, degrees east (-180…+180)")


# ---------------------------------------------------------------------------
# Vessel
# ---------------------------------------------------------------------------

class VesselSpec(BaseModel):
    """Vessel parameters for the voyage."""
    name: str = Field(..., description="Vessel name")
    ice_class: str = Field(
        "PC3_PC5",
        description=(
            "Polar/ice class identifier. Must match a key in polaris_risk.RISK_INDEX_VALUES. "
            "Options: PC3_PC5, IA_SUPER_1A, NON_ICE_STRENGTHENED"
        ),
    )
    draft_m: float = Field(..., gt=0.0, le=30.0, description="Vessel draft in metres")
    speed_knots: float = Field(..., gt=0.0, le=30.0, description="Planned transit speed in knots")


# ---------------------------------------------------------------------------
# Route preferences (kept for backward compatibility)
# ---------------------------------------------------------------------------

class RoutePreferences(BaseModel):
    """Multi-objective route weight sliders (legacy; superseded by OperatingMode + RiskBudget)."""
    risk_weight: float = Field(4.0, ge=0.0, le=20.0, description="Risk weighting (higher = prefer lower-modeled-risk routes)")
    time_weight: float = Field(1.0, ge=0.0, le=10.0, description="Time weighting")
    fuel_weight: float = Field(0.4, ge=0.0, le=10.0, description="Fuel weighting")


# ---------------------------------------------------------------------------
# Phase 8: Operating modes
# ---------------------------------------------------------------------------

class OperatingMode(str, Enum):
    """
    Operating modes for risk-budgeted route search.

    SAFETY_FIRST:
        Minimize modeled risk, with time and fuel as secondary objectives.
        High risk penalty. Low fuel priority.
        Default risk budget: max_acceptable_risk = 0.35

    BALANCED (default):
        Balanced trade-off between modeled risk, time, and fuel.
        Default risk budget: max_acceptable_risk = 0.55

    FUEL_SAVER:
        Minimize fuel consumption, subject to risk budget constraint.
        Lower risk penalty, higher fuel priority.
        The risk budget is STILL enforced — fuel saving never overrides
        the maximum acceptable modeled risk.
        Default risk budget: max_acceptable_risk = 0.55

    NOTE: These labels describe the optimizer objective, not a safety guarantee.
    The system never uses the word "safe" to describe a route.
    Final navigation authority rests with the Captain/Master/Ice Pilot.
    """
    SAFETY_FIRST = "SAFETY_FIRST"
    BALANCED = "BALANCED"
    FUEL_SAVER = "FUEL_SAVER"


# ---------------------------------------------------------------------------
# Phase 8: Risk budget
# ---------------------------------------------------------------------------

class RiskBudget(BaseModel):
    """
    Explicit risk constraint for route optimization.

    The optimizer minimizes fuel/time SUBJECT TO:
        modeled_risk_cost / normalizer <= max_acceptable_risk

    If no route satisfies this constraint, the response returns:
        risk_budget_status.status = "NO_ROUTE_WITHIN_RISK_BUDGET"

    DO NOT fabricate a route in this case.

    Threshold guidance (prototype, not operational):
        <= 0.35  — conservative (SAFETY_FIRST default)
        <= 0.55  — balanced (BALANCED / FUEL_SAVER default)
        > 0.70   — elevated tolerance (requires explicit acknowledgement)
    """
    max_acceptable_risk: float = Field(
        0.55,
        ge=0.0,
        le=1.0,
        description=(
            "Maximum acceptable normalized modeled risk (0.0–1.0). "
            "Routes exceeding this are flagged EXCEEDS_BUDGET. "
            "NOT an operational safety guarantee — prototype demonstration only."
        ),
    )
    risk_weight: Optional[float] = Field(
        None,
        ge=0.0,
        le=20.0,
        description="Override risk weight (defaults from OperatingMode if None)",
    )
    fuel_weight: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="Override fuel weight (defaults from OperatingMode if None)",
    )
    time_weight: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="Override time weight (defaults from OperatingMode if None)",
    )
    uncertainty_weight: float = Field(
        0.5,
        ge=0.0,
        le=5.0,
        description="Weighting for forecast uncertainty contribution to risk cost",
    )


# ---------------------------------------------------------------------------
# Route generation request
# ---------------------------------------------------------------------------

class GenerateRoutesRequest(BaseModel):
    """
    Request body for POST /api/v1/routes/generate.

    Phase 8 additions:
      - operating_mode: SAFETY_FIRST | BALANCED (default) | FUEL_SAVER
      - risk_budget: explicit risk constraint
      - extreme_risk_acknowledged: required acknowledgement if risk tolerance is unusually high

    Departure time must be timezone-aware ISO 8601 (UTC).
    If a naive timestamp is provided, it is rejected (HTTP 422).

    Note: The current prototype uses deterministic fixture data for the
    scientific pipeline regardless of the from/to coordinates provided.

    DEFERRED: Departure window (planning with different departure times)
    requires genuine pipeline reruns per candidate time. Deferred to Phase 9.
    """
    origin: GeoPoint = Field(
        ...,
        description="Departure location",
        examples=[{"name": "Cape Town, South Africa", "lat": -33.93, "lon": 18.42}],
    )
    destination: GeoPoint = Field(
        ...,
        description="Destination location",
        examples=[{"name": "Bharati Station, Larsemann Hills", "lat": -69.41, "lon": 76.19}],
    )
    departure_time: datetime = Field(
        ...,
        description="UTC departure time (ISO 8601 with timezone required)",
    )
    vessel: VesselSpec
    forecast_horizon_hours: int = Field(
        120,
        ge=24,
        le=240,
        description=(
            "Forecast horizon in hours. Must be a multiple of 24 and in the range [24, 240]. "
            "Valid values: 24, 48, 72, 96, 120, 144, 168, 192, 216, 240."
        ),
    )
    route_preferences: RoutePreferences = Field(default_factory=RoutePreferences)

    @field_validator("forecast_horizon_hours")
    @classmethod
    def must_be_multiple_of_24(cls, v: int) -> int:
        if v % 24 != 0:
            raise ValueError(
                f"forecast_horizon_hours must be a multiple of 24 (received {v}). "
                f"Valid values: 24, 48, 72, 96, 120, 144, 168, 192, 216, 240."
            )
        return v

    # ── Phase 8 ──────────────────────────────────────────────────────────────

    operating_mode: OperatingMode = Field(
        OperatingMode.BALANCED,
        description=(
            "Operating mode controls the optimizer objective. "
            "BALANCED is the default. SAFETY_FIRST maximizes risk avoidance. "
            "FUEL_SAVER prioritizes fuel, subject to risk budget."
        ),
    )
    risk_budget: RiskBudget = Field(
        default_factory=RiskBudget,
        description="Explicit risk constraint — the optimizer must satisfy this.",
    )
    extreme_risk_acknowledged: bool = Field(
        False,
        description=(
            "Must be True if risk_budget.max_acceptable_risk > 0.70. "
            "Acknowledgement text: 'I acknowledge that increasing the risk tolerance "
            "may expose the voyage to higher modeled hazard.' "
            "This acknowledgement is local UI state only — no data is sent externally."
        ),
    )

    @model_validator(mode="after")
    def validate_departure_timezone(self) -> "GenerateRoutesRequest":
        if self.departure_time.tzinfo is None:
            raise ValueError(
                "departure_time must be timezone-aware (e.g. '2026-05-21T12:00:00Z'). "
                "Naive timestamps are rejected — the scientific pipeline requires UTC."
            )
        return self

    @model_validator(mode="after")
    def validate_extreme_risk_acknowledgement(self) -> "GenerateRoutesRequest":
        """
        Gate: if max_acceptable_risk > 0.70, the user must explicitly acknowledge
        that they are accepting elevated modeled hazard exposure.
        This prevents silent bypass of the risk constraint.
        """
        if (
            self.risk_budget.max_acceptable_risk > 0.70
            and not self.extreme_risk_acknowledged
        ):
            raise ValueError(
                "risk_budget.max_acceptable_risk exceeds 0.70. "
                "You must set extreme_risk_acknowledged=True to proceed. "
                "Acknowledgement: 'I acknowledge that increasing the risk tolerance "
                "may expose the voyage to higher modeled hazard.' "
                "This gate exists to prevent silent bypass of the risk constraint."
            )
        return self


# ---------------------------------------------------------------------------
# Phase 9: Historical Replay request
# ---------------------------------------------------------------------------

class ReplayRunRequest(BaseModel):
    """
    Request body for POST /api/v1/replay/run.

    Runs a historical replay with the specified dataset and seed.
    Same dataset_id + same seed → identical reproducible output.

    dataset_id must match a registered contract in the dataset registry.
    If not found, falls back to SYNTHETIC_REPLAY with a warning.
    """
    dataset_id: str = Field(
        "HIMDRISHTI_SYNTHETIC_202605",
        description=(
            "Dataset contract ID. Use 'HIMDRISHTI_SYNTHETIC_202605' for offline-first "
            "SYNTHETIC_REPLAY mode. Use 'NSIDC_0051_SH_202605' or 'USNIC_ICEBERGS_SH_202605' "
            "for public archive contracts (credentials required in deployment)."
        ),
    )
    start_time: datetime = Field(
        ...,
        description="Start of replay window (UTC, timezone-aware ISO 8601 required).",
    )
    end_time: datetime = Field(
        ...,
        description="End of replay window (UTC, timezone-aware ISO 8601 required).",
    )
    seed: int = Field(
        42,
        ge=0,
        description="Random seed for the iceberg drift ensemble. Same seed → same output.",
    )
    config: dict = Field(
        default_factory=lambda: {"vessel_class": "PC3_PC5"},
        description="Pipeline configuration overrides. Key: vessel_class.",
    )
    forecast_horizon_hours: int = Field(
        120, ge=24, le=240,
        description="Forecast horizon for the replay run.",
    )

    @model_validator(mode="after")
    def validate_time_window(self) -> "ReplayRunRequest":
        if self.start_time.tzinfo is None:
            raise ValueError("start_time must be timezone-aware.")
        if self.end_time.tzinfo is None:
            raise ValueError("end_time must be timezone-aware.")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


# ---------------------------------------------------------------------------
# Phase 9: Departure Windows request
# ---------------------------------------------------------------------------

class DepartureWindowsRequest(BaseModel):
    """
    Request body for POST /api/v1/planning/departure-windows.

    Runs genuine pipeline executions for each candidate departure offset.
    Each candidate shifts the base departure_time and reruns the full pipeline.

    IMPORTANT:
      - No deterministic offsets. No fabricated outputs.
      - Each candidate is a genuine pipeline execution.
      - Total runtime: ~60s per candidate × n candidates.
      - Missing metric → null (never fabricated).
      - Language: "recommended under current forecast" / "lower modeled risk".
      - Final decision rests with the Captain/Master/Ice Pilot.

    DEFERRED: In Phase 8, departure-window was deferred because deterministic
    offsets would have been fabricated. Phase 9 implements it correctly.
    """
    # Base voyage scenario (same as GenerateRoutesRequest fields)
    origin: GeoPoint = Field(..., description="Departure location")
    destination: GeoPoint = Field(..., description="Destination location")
    base_departure_time: datetime = Field(
        ...,
        description="Base departure time (UTC, timezone-aware). Candidates are offset from this.",
    )
    vessel: VesselSpec
    forecast_horizon_hours: int = Field(
        120,
        ge=24,
        le=240,
        description=(
            "Forecast horizon in hours. Must be a multiple of 24 and in [24, 240]. "
            "Valid values: 24, 48, 72, 96, 120, 144, 168, 192, 216, 240."
        ),
    )
    operating_mode: OperatingMode = Field(OperatingMode.BALANCED)
    risk_budget: RiskBudget = Field(default_factory=RiskBudget)
    extreme_risk_acknowledged: bool = False

    # Departure window candidates
    candidate_offsets_hours: List[int] = Field(
        default=[0, 6, 12, 24],
        description=(
            "Hour offsets from base_departure_time to evaluate. "
            "Each offset triggers a genuine pipeline rerun. "
            "Supported: 0, 6, 12, 24."
        ),
    )

    @field_validator("forecast_horizon_hours")
    @classmethod
    def must_be_multiple_of_24(cls, v: int) -> int:
        if v % 24 != 0:
            raise ValueError(
                f"forecast_horizon_hours must be a multiple of 24 (received {v}). "
                f"Valid values: 24, 48, 72, 96, 120, 144, 168, 192, 216, 240."
            )
        return v

    @model_validator(mode="after")
    def validate_base_departure_timezone(self) -> "DepartureWindowsRequest":
        if self.base_departure_time.tzinfo is None:
            raise ValueError("base_departure_time must be timezone-aware UTC.")
        return self

    @model_validator(mode="after")
    def validate_offsets(self) -> "DepartureWindowsRequest":
        allowed = {0, 6, 12, 24}
        invalid = [o for o in self.candidate_offsets_hours if o not in allowed]
        if invalid:
            raise ValueError(
                f"Invalid departure offsets: {invalid}. "
                f"Supported: {sorted(allowed)}. "
                "Each offset requires a full pipeline rerun (~60s)."
            )
        return self

