"""
data_pipeline/replay/runner.py
--------------------------------
Historical replay runner for reproducible pipeline executions.
SIH 2026 · PS 26059

Phase 9.

Given a dataset_id + time window + configuration + random seed,
produces a deterministic PipelineResult that can be compared with
historical observations.

DESIGN RULES:
  - Same seed + same data → same output, always.
  - FORECAST INPUT is kept separate from ACTUAL OBSERVATION.
  - Never feed the future observed position into the forecast.
  - SYNTHETIC_REPLAY is explicitly labelled. Not real historical data.
  - Results marked NOT_EVALUABLE when ground truth is unavailable.
  - Scientific core (ai/*.py) is NOT modified.

Usage:
    from data_pipeline.replay.runner import run_replay, ReplayRunRequest
    req = ReplayRunRequest(
        dataset_id="HIMDRISHTI_SYNTHETIC_202605",
        start_time=datetime(..., tzinfo=timezone.utc),
        end_time=datetime(..., tzinfo=timezone.utc),
        seed=42,
        config={"vessel_class": "PC3_PC5"},
    )
    result = run_replay(req)
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Ensure project root importable
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
from data_pipeline.replay import create_replay, save_output_digest
from data_pipeline.replay.dataset_contract import (
    HistoricalDatasetContract,
    get_dataset_contract,
    DATA_MODE_SYNTHETIC_REPLAY,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Result types
# ---------------------------------------------------------------------------

@dataclass
class ReplayRunRequest:
    """
    Input specification for a historical replay run.
    Same request + same seed → same output (reproducible).
    """
    dataset_id: str                     # from dataset_contract registry
    start_time: datetime                # UTC-aware
    end_time: datetime                  # UTC-aware
    seed: int = 42
    config: Dict[str, Any] = field(default_factory=dict)
    forecast_horizon_hours: int = 120
    # Domain — defaults to Cape Town → Bharati Station Indian Ocean corridor
    lat_min: float = -80.0
    lat_max: float = -55.0
    lon_min: float = 10.0
    lon_max: float = 90.0


@dataclass
class ReplayRunResult:
    """
    Output of a historical replay run.
    Includes the pipeline result, provenance, timing, and evaluation status.
    """
    run_id: str
    dataset_id: str
    data_mode: str
    pipeline_result: Optional[PipelineResult]
    provenance: List[Dict[str, Any]]
    elapsed_seconds: float
    evaluation_status: str               # "EVALUABLE" | "NOT_EVALUABLE" | "FAILED"
    evaluation_note: str
    dataset_contract: HistoricalDatasetContract
    # Explainability trace (deterministic, no LLM)
    computation_trace: List[str]
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Main replay runner
# ---------------------------------------------------------------------------

def run_replay(request: ReplayRunRequest) -> ReplayRunResult:
    """
    Execute a historical replay run.

    Steps:
      1. Load dataset contract
      2. Fetch data (fixture path — SYNTHETIC_REPLAY in offline environment)
      3. Assemble PipelineInput (FORECAST data only — no future observations)
      4. Run HimDrishtiPipeline with the specified seed
      5. Persist replay record via create_replay()
      6. Return structured result with provenance and explainability trace

    The 'actual observations' (ground truth) are managed separately by
    verification.py — they are NOT passed into the pipeline as forecast inputs.
    """
    t0 = time.monotonic()
    trace: List[str] = []

    contract = get_dataset_contract(request.dataset_id)
    data_mode = contract.data_mode
    trace.append(f"Dataset: {contract.dataset_id} ({data_mode})")
    trace.append(f"Source: {contract.source}")

    if data_mode == DATA_MODE_SYNTHETIC_REPLAY:
        logger.info(
            "Replay '%s': SYNTHETIC_REPLAY mode — deterministic fixture adapters",
            request.dataset_id,
        )
        trace.append("Adapters: SYNTHETIC fixture (no live network access)")
    else:
        logger.info(
            "Replay '%s': %s mode — attempting public archive adapters",
            request.dataset_id, data_mode,
        )
        trace.append(f"Adapters: {data_mode} (public archive)")

    # ── 1. Build forecast window ────────────────────────────────────────
    start = request.start_time.astimezone(timezone.utc)
    horizon_h = request.forecast_horizon_hours
    horizon_steps = [h for h in [0, 24, 48, 72, 96, 120] if h <= horizon_h]
    valid_times = [start + timedelta(hours=h) for h in horizon_steps]

    forecast_window = ForecastWindow(
        reference_time=start,
        valid_times=valid_times,
        horizon_hours=[float(h) for h in horizon_steps],
    )
    trace.append(
        f"Forecast window: {start.isoformat()} → +{horizon_h}h "
        f"({len(horizon_steps)} steps)"
    )

    # ── 2. Fetch data (FORECAST ONLY — actual observations kept separate) ─
    # In SYNTHETIC_REPLAY mode: deterministic Phase-6 fixture adapters.
    # In ARCHIVE/REANALYSIS mode: same adapters with use_fixture=False
    #   (will fall back to fixture if credentials absent).
    use_fixture = (data_mode == DATA_MODE_SYNTHETIC_REPLAY)

    try:
        sea_ice = fetch_sea_ice(
            request.lat_min, request.lat_max,
            request.lon_min, request.lon_max,
            start, request.end_time, use_fixture=use_fixture,
        )
        trace.append(f"Sea ice: {sea_ice.provenance.source.value} ({sea_ice.quality.value})")

        wind = fetch_wind(
            request.lat_min, request.lat_max,
            request.lon_min, request.lon_max,
            start, request.end_time, use_fixture=use_fixture,
        )
        trace.append(f"Wind: {wind.provenance.source.value} ({wind.quality.value})")

        ocean_current = fetch_ocean_current(
            request.lat_min, request.lat_max,
            request.lon_min, request.lon_max,
            start, request.end_time, use_fixture=use_fixture,
        )
        trace.append(f"Ocean current: {ocean_current.provenance.source.value} ({ocean_current.quality.value})")

        icebergs = fetch_icebergs(
            request.lat_min, request.lat_max,
            request.lon_min, request.lon_max,
            use_fixture=use_fixture,
        )
        trace.append(f"Icebergs: {len(icebergs)} observations (forecast input only)")

    except Exception as exc:
        logger.error("Replay data fetch failed: %s", exc)
        elapsed = time.monotonic() - t0
        return ReplayRunResult(
            run_id=f"replay_FAILED_{int(t0)}",
            dataset_id=request.dataset_id,
            data_mode=data_mode,
            pipeline_result=None,
            provenance=[],
            elapsed_seconds=elapsed,
            evaluation_status="FAILED",
            evaluation_note=f"Data fetch failed: {exc}",
            dataset_contract=contract,
            computation_trace=trace,
            error=str(exc),
        )

    # ── 3. Assemble PipelineInput ──────────────────────────────────────
    pipeline_input = PipelineInput(
        forecast_window=forecast_window,
        sea_ice=sea_ice,
        wind=wind,
        ocean_current=ocean_current,
        icebergs=icebergs,
        assembled_at=datetime.now(tz=timezone.utc),
    )

    # ── 4. Build PipelineConfig ────────────────────────────────────────
    vessel_class = request.config.get("vessel_class", "PC3_PC5")
    cfg = PipelineConfig(
        vessel_class=vessel_class,
        ensemble_seed=request.seed,
    )
    trace.append(f"Vessel class: {vessel_class}")
    trace.append(f"Domain: lat [{request.lat_min},{request.lat_max}] lon [{request.lon_min},{request.lon_max}]")

    # ── 5. Run scientific pipeline ─────────────────────────────────────
    logger.info("Running replay pipeline (seed=%d via ensemble_seed)...", request.seed)
    trace.append(f"Iceberg ensemble seed: {request.seed} (via PipelineConfig.ensemble_seed)")

    try:
        pipeline_result = HimDrishtiPipeline(cfg).run(pipeline_input)
    except Exception as exc:
        logger.error("Replay pipeline execution failed: %s", exc)
        elapsed = time.monotonic() - t0
        return ReplayRunResult(
            run_id=f"replay_FAILED_{int(t0)}",
            dataset_id=request.dataset_id,
            data_mode=data_mode,
            pipeline_result=None,
            provenance=[],
            elapsed_seconds=elapsed,
            evaluation_status="FAILED",
            evaluation_note=f"Pipeline execution failed: {exc}",
            dataset_contract=contract,
            computation_trace=trace,
            error=str(exc),
        )

    trace.append("Iceberg ensemble: complete")
    trace.append("Hazard field: built from ensemble + sea ice")
    trace.append("POLARIS RIO: computed per cell (illustrative values)")
    trace.append("Route search: Dijkstra / UCS optimizer")

    # ── 6. Collect provenance ──────────────────────────────────────────
    # pipeline_result.provenance_records may contain ProvenanceRecord objects
    # (Phase-6 pipeline) OR already-serialized dicts (Phase-7 response layer).
    # Handle both defensively.
    def _safe_prov_to_dict(p) -> dict:
        if isinstance(p, dict):
            return p
        try:
            return provenance_to_dict(p)
        except Exception as _e:
            logger.warning("Could not serialize provenance record (%s): %s", type(p).__name__, _e)
            return {"error": str(_e), "type": type(p).__name__}

    provenance = [_safe_prov_to_dict(p) for p in (pipeline_result.provenance_records or [])]

    # ── 7. Persist replay record ───────────────────────────────────────
    replay_config = {
        "dataset_id":    request.dataset_id,
        "vessel_class":  vessel_class,
        "seed":          request.seed,
        "horizon_hours": horizon_h,
        "data_mode":     data_mode,
    }
    run_id = create_replay(pipeline_input, replay_config, seed=request.seed)

    # Save output digest for change detection
    fast  = pipeline_result.route_fast
    safe  = pipeline_result.route_safe
    save_output_digest(run_id, {
        "fast_risk":  round(fast.total_risk_cost, 6) if fast else None,
        "safe_risk":  round(safe.total_risk_cost, 6) if safe else None,
        "fast_time":  round(fast.total_time_hours, 4) if fast else None,
    })

    # ── 8. Evaluation status ───────────────────────────────────────────
    if data_mode == DATA_MODE_SYNTHETIC_REPLAY:
        evaluation_status = "NOT_EVALUABLE"
        evaluation_note = (
            "SYNTHETIC_REPLAY data — no real historical observations available "
            "as independent ground truth. Results cannot be used to validate "
            "the scientific model. Use real archive data for evaluation."
        )
    else:
        evaluation_status = "EVALUABLE"
        evaluation_note = (
            f"Archive data ({data_mode}) used as forecast input. "
            "Independent ground truth (if available) can be compared via verification.py. "
            "Results are NOT independent — same dataset used for forecast and any collocated obs."
        )

    elapsed = time.monotonic() - t0
    logger.info(
        "Replay '%s' complete: run_id=%s elapsed=%.1fs status=%s",
        request.dataset_id, run_id, elapsed, evaluation_status,
    )
    trace.append(f"Run ID: {run_id}")
    trace.append(f"Elapsed: {elapsed:.1f}s")
    trace.append(f"Evaluation status: {evaluation_status}")

    return ReplayRunResult(
        run_id=run_id,
        dataset_id=request.dataset_id,
        data_mode=data_mode,
        pipeline_result=pipeline_result,
        provenance=provenance,
        elapsed_seconds=elapsed,
        evaluation_status=evaluation_status,
        evaluation_note=evaluation_note,
        dataset_contract=contract,
        computation_trace=trace,
    )
