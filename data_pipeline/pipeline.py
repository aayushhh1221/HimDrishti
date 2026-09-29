"""
data_pipeline/pipeline.py
---------------------------
Pipeline orchestrator for HimDrishti scientific core.
SIH 2026 · PS 26059

Architecture:
    fetch adapters → normalize → validate → assemble PipelineInput
        → iceberg drift (ai/iceberg_drift.py)
        → hazard field construction
        → POLARIS risk (ai/polaris_risk.py)
        → route search (ai/route_search.py)
        → PipelineResult

This orchestrator contains NO scientific formulas.
It calls the scientific modules (iceberg_drift, polaris_risk, route_search)
as separate, independently testable units.

The orchestrator is responsible for:
  - Logging every stage
  - Failing safely with structured errors (no silent fallback)
  - Translating normalized pipeline data into science-core interfaces
  - Collecting provenance for the Data Provenance UI

It is NOT responsible for:
  - Physics (iceberg_drift.py handles that)
  - Risk index computation (polaris_risk.py handles that)
  - Route optimization (route_search.py handles that)
"""

from __future__ import annotations

import logging
import sys
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Science core — located in ai/
_AI_DIR = Path(__file__).resolve().parent.parent / "ai"
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from iceberg_drift import Iceberg, ensemble_drift
from polaris_risk import compute_rio, concentration_to_regime, rio_to_cost
from route_search import RouteWeights, RouteResult, find_route

from .schemas import (
    DataQuality, IcebergObservation, PipelineInput,
)
from .normalization import (
    extract_current_series_at_point,
    extract_wind_series_at_point,
    sea_ice_to_model_grid,
)
from .provenance import provenance_to_dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class PipelineConfig:
    """
    Routing + science configuration for one pipeline run.
    All values are explicit — no hidden defaults.
    """
    # Model grid
    nx: int = 26                        # grid cells east-west
    ny: int = 20                        # grid cells north-south
    cell_size_m: float = 15_000.0       # 15 km cells

    # Forecast
    n_time_buckets: int = 30
    dt_hours: float = 3.0               # hazard-field cadence

    # Iceberg ensemble
    n_ensemble_members: int = 48
    ensemble_seed: int = 7

    # Vessel
    vessel_class: str = "PC3_PC5"       # must match RISK_INDEX_VALUES key
    latitude_deg: float = -68.0         # representative transit latitude

    # POLARIS
    iceberg_risk_scale: float = 40.0

    # Route weights (two operating points)
    fast_weights: RouteWeights = field(default_factory=lambda: RouteWeights(
        time_weight=1.0, fuel_weight=0.4, risk_weight=0.3))
    safe_weights: RouteWeights = field(default_factory=lambda: RouteWeights(
        time_weight=1.0, fuel_weight=0.4, risk_weight=4.0))

    # Route endpoints (grid cell indices)
    start_cell: tuple = (2, 10)
    goal_cell: tuple = (23, 10)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    """Complete result of one pipeline run."""
    run_at: datetime
    config: PipelineConfig
    route_fast: Optional[RouteResult]
    route_safe: Optional[RouteResult]
    route_aggressive: Optional[RouteResult]  # Third route: time-priority, low risk_weight
    n_iceberg_tracks: int
    provenance_records: List[Dict[str, Any]]
    data_quality_summary: Dict[str, str]
    warnings: List[str]
    success: bool
    failure_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class HimDrishtiPipeline:
    """
    Main pipeline orchestrator.

    Usage:
        pipeline = HimDrishtiPipeline(config)
        result = pipeline.run(pipeline_input)
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()

    def run(self, pipeline_input: PipelineInput) -> PipelineResult:
        """
        Execute the full pipeline for a given PipelineInput.

        Fails safely if mandatory inputs are missing — no silent substitution.
        """
        cfg = self.config
        run_at = datetime.now(tz=timezone.utc)
        warnings: List[str] = []
        provenance_records: List[Dict[str, Any]] = []

        logger.info("=" * 60)
        logger.info("HimDrishti pipeline START: %s", run_at.isoformat())
        logger.info("Config: vessel=%s lat=%.1f° nx=%d ny=%d",
                    cfg.vessel_class, cfg.latitude_deg, cfg.nx, cfg.ny)

        # ── Completeness check ──────────────────────────────────────────────
        report = pipeline_input.completeness_report
        logger.info("Input completeness: %s", report)
        for src, status in report.items():
            if status in ("missing", "unavailable", "invalid"):
                msg = f"Input {src} is {status}"
                warnings.append(msg)
                logger.warning(msg)

        if not pipeline_input.is_complete:
            reason = (
                "Pipeline cannot run: mandatory inputs missing or unavailable. "
                f"Completeness: {report}"
            )
            logger.error(reason)
            return PipelineResult(
                run_at=run_at,
                config=cfg,
                route_fast=None,
                route_safe=None,
                route_aggressive=None,
                n_iceberg_tracks=0,
                provenance_records=[],
                data_quality_summary={k: str(v) for k, v in report.items()},
                warnings=warnings,
                success=False,
                failure_reason=reason,
            )

        # ── Collect provenance ───────────────────────────────────────────────
        for ds, name in [
            (pipeline_input.sea_ice, "sea_ice"),
            (pipeline_input.wind, "wind"),
            (pipeline_input.ocean_current, "ocean_current"),
        ]:
            if ds is not None:
                provenance_records.append(
                    {"field": name, **provenance_to_dict(ds.provenance)})
        logger.info("Provenance: collected %d records", len(provenance_records))

        # ── Stage 1: Sea-ice → model grid ───────────────────────────────────
        logger.info("Stage 1: normalizing sea ice to model grid (%d×%d)", cfg.ny, cfg.nx)
        try:
            ice_concentration = sea_ice_to_model_grid(
                pipeline_input.sea_ice, cfg.nx, cfg.ny)
            # Trim or pad time axis to n_time_buckets
            ice_concentration = _match_time_axis(ice_concentration, cfg.n_time_buckets)
            logger.info("Sea-ice grid: shape=%s", ice_concentration.shape)
        except Exception as exc:
            return self._fail(run_at, cfg, warnings, provenance_records, report,
                              f"Sea-ice normalization failed: {exc}")

        # ── Stage 2: Extract forcing time-series at iceberg start position ──
        logger.info("Stage 2: extracting wind/current forcing series")
        try:
            # Use first iceberg position if available; else domain centre
            if pipeline_input.icebergs:
                berg_obs = pipeline_input.icebergs[0]
                forcing_lat = berg_obs.latitude
                forcing_lon = berg_obs.longitude
                logger.info("Using iceberg %s position (%.2f°, %.2f°) for forcing extraction",
                            berg_obs.iceberg_id, forcing_lat, forcing_lon)
            else:
                forcing_lat = cfg.latitude_deg
                forcing_lon = (pipeline_input.wind.lons.mean()
                               if pipeline_input.wind is not None else 0.0)
                warnings.append("No iceberg observations — using domain-centre forcing point")
                logger.warning("No iceberg observations: using domain centre for forcing")

            wind_series = extract_wind_series_at_point(
                pipeline_input.wind, forcing_lat, forcing_lon)
            current_series = extract_current_series_at_point(
                pipeline_input.ocean_current, forcing_lat, forcing_lon)

            # Ensure forcing has n_time_buckets−1 steps
            n_steps = cfg.n_time_buckets - 1
            wind_series = _trim_or_tile(wind_series, n_steps)
            current_series = _trim_or_tile(current_series, n_steps)
            logger.info("Forcing series: wind=%s current=%s",
                        wind_series.shape, current_series.shape)
        except Exception as exc:
            return self._fail(run_at, cfg, warnings, provenance_records, report,
                              f"Forcing extraction failed: {exc}")

        # ── Stage 3: Iceberg drift ensemble ─────────────────────────────────
        logger.info("Stage 3: iceberg drift ensemble (%d members)", cfg.n_ensemble_members)
        try:
            if pipeline_input.icebergs:
                b = pipeline_input.icebergs[0]
                berg = Iceberg(
                    length_m=b.length_m or 450.0,
                    width_m=b.width_m or 280.0,
                    height_above_water_m=b.height_above_water_m or 25.0,
                    draft_m=b.draft_m or 120.0,
                )
                # Convert geographic position to model-grid metres
                berg_start_xy = np.array([7.0 * cfg.cell_size_m, 7.0 * cfg.cell_size_m])
                if b.length_m is None:
                    warnings.append(f"Iceberg {b.iceberg_id}: dimensions unknown, using defaults")
            else:
                berg = Iceberg()
                berg_start_xy = np.array([7.0 * cfg.cell_size_m, 7.0 * cfg.cell_size_m])
                warnings.append("No iceberg observations — using default Iceberg dimensions")

            dt_s = cfg.dt_hours * 3600.0
            tracks_m = ensemble_drift(
                berg_start_xy, wind_series, current_series,
                cfg.latitude_deg, berg,
                n_members=cfg.n_ensemble_members,
                dt_s=dt_s,
                seed=cfg.ensemble_seed,
            )
            logger.info("Iceberg ensemble: shape=%s", tracks_m.shape)
        except Exception as exc:
            return self._fail(run_at, cfg, warnings, provenance_records, report,
                              f"Iceberg drift failed: {exc}")

        # ── Stage 4: Probabilistic hazard field ─────────────────────────────
        logger.info("Stage 4: building hazard field")
        try:
            tracks_cells = tracks_m / cfg.cell_size_m
            berg_density = _build_berg_density(
                tracks_cells, cfg.n_time_buckets, cfg.ny, cfg.nx)

            ice_rio_cost = _build_ice_rio_cost(
                ice_concentration, cfg.n_time_buckets, cfg.ny, cfg.nx,
                cfg.vessel_class)

            hazard_cost = ice_rio_cost + cfg.iceberg_risk_scale * berg_density
            logger.info("Hazard field: shape=%s, max=%.2f",
                        hazard_cost.shape, float(hazard_cost[np.isfinite(hazard_cost)].max()))
        except Exception as exc:
            return self._fail(run_at, cfg, warnings, provenance_records, report,
                              f"Hazard field construction failed: {exc}")

        # ── Stage 5: Route search ────────────────────────────────────────────
        logger.info("Stage 5: route search")
        try:
            route_fast = find_route(
                cfg.start_cell, cfg.goal_cell,
                ice_concentration, hazard_cost,
                cfg.cell_size_m, cfg.fast_weights)
            route_safe = find_route(
                cfg.start_cell, cfg.goal_cell,
                ice_concentration, hazard_cost,
                cfg.cell_size_m, cfg.safe_weights)

            # Third route: time-priority (low risk_weight → cuts through hazard for speed).
            # Genuinely independent Dijkstra / UCS call — no multipliers from fast/safe results.
            # risk_weight at 5% of fast_weights.risk_weight (or 0.05 floor).
            _aggressive_risk_w = max(cfg.fast_weights.risk_weight * 0.05, 0.05)
            aggressive_weights = RouteWeights(
                time_weight=cfg.fast_weights.time_weight * 2.0,
                fuel_weight=cfg.fast_weights.fuel_weight * 0.5,
                risk_weight=_aggressive_risk_w,
                max_speed_kn=cfg.fast_weights.max_speed_kn,
                min_speed_frac=cfg.fast_weights.min_speed_frac,
                ice_speed_penalty=cfg.fast_weights.ice_speed_penalty,
                base_fuel_tonnes_per_hour=cfg.fast_weights.base_fuel_tonnes_per_hour,
                ice_fuel_penalty=cfg.fast_weights.ice_fuel_penalty,
            )
            route_aggressive = find_route(
                cfg.start_cell, cfg.goal_cell,
                ice_concentration, hazard_cost,
                cfg.cell_size_m, aggressive_weights)

            for name, r in [("fast", route_fast), ("safe", route_safe), ("aggressive", route_aggressive)]:
                if r is None:
                    warnings.append(f"No {name} route found within time horizon")
                    logger.warning("No %s route found", name)
                else:
                    logger.info("%s route: %.1fh %.1ft risk=%.2f cells=%d",
                                name, r.total_time_hours,
                                r.total_fuel_tonnes, r.total_risk_cost,
                                len(r.path_cells))
        except Exception as exc:
            return self._fail(run_at, cfg, warnings, provenance_records, report,
                              f"Route search failed: {exc}")

        # ── Done ─────────────────────────────────────────────────────────────
        logger.info("Pipeline COMPLETE: fast=%s safe=%s aggressive=%s warnings=%d",
                    route_fast is not None, route_safe is not None,
                    route_aggressive is not None, len(warnings))

        return PipelineResult(
            run_at=run_at,
            config=cfg,
            route_fast=route_fast,
            route_safe=route_safe,
            route_aggressive=route_aggressive,
            n_iceberg_tracks=tracks_m.shape[0],
            provenance_records=provenance_records,
            data_quality_summary={k: str(v) for k, v in report.items()},
            warnings=warnings,
            success=True,
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _fail(self, run_at, cfg, warnings, prov, report, reason) -> PipelineResult:
        logger.error("Pipeline FAILED: %s", reason)
        return PipelineResult(
            run_at=run_at, config=cfg, route_fast=None, route_safe=None,
            route_aggressive=None, n_iceberg_tracks=0, provenance_records=prov,
            data_quality_summary={k: str(v) for k, v in report.items()},
            warnings=warnings, success=False, failure_reason=reason,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _match_time_axis(arr: np.ndarray, target_t: int) -> np.ndarray:
    """Trim or tile a (T, ...) array to exactly target_t time steps."""
    t = arr.shape[0]
    if t >= target_t:
        return arr[:target_t]
    # Tile: repeat last frame
    deficit = target_t - t
    tail = np.repeat(arr[[-1]], deficit, axis=0)
    return np.concatenate([arr, tail], axis=0)


def _trim_or_tile(series: np.ndarray, n_steps: int) -> np.ndarray:
    """Trim or tile a (T, 2) forcing series to exactly n_steps rows."""
    t = series.shape[0]
    if t >= n_steps:
        return series[:n_steps]
    deficit = n_steps - t
    tail = np.tile(series[[-1]], (deficit, 1))
    return np.concatenate([series, tail], axis=0)


def _build_berg_density(
    tracks_cells: np.ndarray,
    n_time_buckets: int,
    ny: int, nx: int,
    sigma_cells: float = 1.4,
) -> np.ndarray:
    """Build normalised iceberg probability density field. Shape: (T, ny, nx)."""
    yy, xx = np.mgrid[0:ny, 0:nx]
    density = np.zeros((n_time_buckets, ny, nx), dtype=np.float32)
    for t in range(n_time_buckets):
        for m in range(tracks_cells.shape[0]):
            cx, cy = tracks_cells[m, t]
            density[t] += np.exp(
                -((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma_cells ** 2))
    max_val = density.max()
    if max_val > 0:
        density /= max_val
    return density


def _build_ice_rio_cost(
    ice_concentration: np.ndarray,
    n_time_buckets: int,
    ny: int, nx: int,
    vessel_class: str,
) -> np.ndarray:
    """Compute POLARIS RIO cost grid. Shape: (T, ny, nx)."""
    cost = np.zeros((n_time_buckets, ny, nx), dtype=np.float32)
    for t in range(n_time_buckets):
        for iy in range(ny):
            for ix in range(nx):
                regime = concentration_to_regime(float(ice_concentration[t, iy, ix]))
                rio = compute_rio(regime, vessel_class).rio
                cost[t, iy, ix] = rio_to_cost(rio)
    return cost
