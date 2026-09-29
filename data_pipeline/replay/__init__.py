"""
data_pipeline/replay/__init__.py
----------------------------------
Historical replay system for reproducible pipeline runs.
SIH 2026 · PS 26059

Purpose:
    Given a source dataset + time window + configuration + random seed,
    produce the SAME normalized scientific input and therefore the SAME
    scientific output on every run.

    A replay record stores everything needed to reproduce a run:
      - dataset provenance (source, time window, retrieval time)
      - configuration (vessel class, domain size, etc.)
      - random seed
      - software version identifier
      - output digest (for change detection)

Replay records are stored in:
    data/historical_replay/<run_id>/
        manifest.json       ← full metadata
        sea_ice.npy         ← normalized concentration array
        wind.npy            ← normalized wind [u,v] array
        current.npy         ← normalized current [u,v] array
        icebergs.json       ← serialized IcebergObservation list
        output_digest.json  ← hash of science outputs

Usage:
    from data_pipeline.replay import create_replay, load_replay, run_replay
    run_id = create_replay(pipeline_input, config, seed=42)
    loaded = load_replay(run_id)
    # Re-run produces identical results if seed and data match.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from ..schemas import (
    DataQuality, DataSource, IcebergObservation,
    OceanCurrentField, PipelineInput, SeaIceField, WindField,
)

logger = logging.getLogger(__name__)

_REPLAY_VERSION = "himdrishti-pipeline-0.1.0"


# ---------------------------------------------------------------------------
# Replay root
# ---------------------------------------------------------------------------

def _replay_root() -> Path:
    override = os.environ.get("HIMDRISHTI_REPLAY_DIR")
    if override:
        return Path(override)
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "data" / "historical_replay"


# ---------------------------------------------------------------------------
# Create a replay record
# ---------------------------------------------------------------------------

def create_replay(
    pipeline_input: PipelineInput,
    config: Dict[str, Any],
    seed: int,
    run_id: Optional[str] = None,
) -> str:
    """
    Persist a pipeline input + configuration as a replay record.

    Parameters
    ----------
    pipeline_input : PipelineInput  (assembled, validated inputs)
    config         : dict  (vessel_class, grid params, weights, etc.)
    seed           : int   (random seed used in ensemble_drift)
    run_id         : str   (optional override; auto-generated if None)

    Returns
    -------
    run_id : str  (directory name under data/historical_replay/)
    """
    if run_id is None:
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"replay_{ts}_seed{seed}"

    run_dir = _replay_root() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Creating replay record: %s", run_id)

    manifest: Dict[str, Any] = {
        "run_id": run_id,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "software_version": _REPLAY_VERSION,
        "seed": seed,
        "config": config,
        "completeness": pipeline_input.completeness_report,
        "forecast_window": {
            "reference_time": pipeline_input.forecast_window.reference_time.isoformat(),
            "horizon_hours": pipeline_input.forecast_window.horizon_hours,
            "n_steps": pipeline_input.forecast_window.n_steps,
        },
    }

    # Persist sea ice
    if pipeline_input.sea_ice is not None:
        si = pipeline_input.sea_ice
        np.save(str(run_dir / "sea_ice.npy"), si.concentration)
        manifest["sea_ice"] = {
            "source": si.provenance.source.value,
            "dataset": si.provenance.dataset_name,
            "valid_start": si.provenance.valid_time_start.isoformat(),
            "valid_end": si.provenance.valid_time_end.isoformat(),
            "shape": list(si.concentration.shape),
            "sha256": _sha256_arr(si.concentration),
        }

    # Persist wind
    if pipeline_input.wind is not None:
        wf = pipeline_input.wind
        wind_arr = np.stack([wf.u_wind, wf.v_wind], axis=0)  # (2, T, lat, lon)
        np.save(str(run_dir / "wind.npy"), wind_arr)
        manifest["wind"] = {
            "source": wf.provenance.source.value,
            "dataset": wf.provenance.dataset_name,
            "shape": list(wind_arr.shape),
            "sha256": _sha256_arr(wind_arr),
        }

    # Persist ocean current
    if pipeline_input.ocean_current is not None:
        oc = pipeline_input.ocean_current
        cur_arr = np.stack([oc.u_current, oc.v_current], axis=0)
        np.save(str(run_dir / "current.npy"), cur_arr)
        manifest["ocean_current"] = {
            "source": oc.provenance.source.value,
            "dataset": oc.provenance.dataset_name,
            "shape": list(cur_arr.shape),
            "sha256": _sha256_arr(cur_arr),
        }

    # Persist icebergs
    berg_records = [_iceberg_to_dict(b) for b in pipeline_input.icebergs]
    (run_dir / "icebergs.json").write_text(
        json.dumps(berg_records, indent=2), encoding="utf-8")
    manifest["n_icebergs"] = len(berg_records)

    # Write manifest
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    logger.info("Replay record saved: %s (%d icebergs)", run_id, len(berg_records))
    return run_id


# ---------------------------------------------------------------------------
# Load a replay record
# ---------------------------------------------------------------------------

def load_replay(run_id: str) -> Dict[str, Any]:
    """
    Load a replay record by run_id.
    Returns the manifest dict plus numpy arrays.

    Does NOT run the science pipeline — call run_replay() for that.
    """
    run_dir = _replay_root() / run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"Replay record not found: {run_id}")

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    result = {"manifest": manifest}

    sea_ice_path = run_dir / "sea_ice.npy"
    if sea_ice_path.exists():
        arr = np.load(str(sea_ice_path), allow_pickle=False)
        stored_hash = manifest.get("sea_ice", {}).get("sha256", "")
        actual_hash = _sha256_arr(arr)
        if stored_hash and actual_hash != stored_hash:
            raise ValueError(f"Sea ice array checksum mismatch in replay {run_id}")
        result["sea_ice"] = arr

    wind_path = run_dir / "wind.npy"
    if wind_path.exists():
        result["wind"] = np.load(str(wind_path), allow_pickle=False)

    current_path = run_dir / "current.npy"
    if current_path.exists():
        result["current"] = np.load(str(current_path), allow_pickle=False)

    berg_path = run_dir / "icebergs.json"
    if berg_path.exists():
        result["icebergs"] = json.loads(berg_path.read_text(encoding="utf-8"))

    logger.info("Replay loaded: %s (seed=%s)", run_id, manifest.get("seed"))
    return result


# ---------------------------------------------------------------------------
# List replay records
# ---------------------------------------------------------------------------

def list_replays() -> List[str]:
    """Return sorted list of all replay run_ids."""
    root = _replay_root()
    if not root.exists():
        return []
    return sorted(
        d.name for d in root.iterdir()
        if d.is_dir() and (d / "manifest.json").exists())


# ---------------------------------------------------------------------------
# Save output digest (for change detection)
# ---------------------------------------------------------------------------

def save_output_digest(run_id: str, outputs: Dict[str, Any]) -> None:
    """
    Save a digest of science outputs for this replay.
    Enables detecting if a code change altered the results.
    """
    run_dir = _replay_root() / run_id
    digest = {
        "saved_at": datetime.now(tz=timezone.utc).isoformat(),
        "outputs": {k: str(v) for k, v in outputs.items()},
    }
    (run_dir / "output_digest.json").write_text(
        json.dumps(digest, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_arr(arr: np.ndarray) -> str:
    return hashlib.sha256(arr.tobytes()).hexdigest()


def _iceberg_to_dict(obs: IcebergObservation) -> Dict[str, Any]:
    return {
        "iceberg_id": obs.iceberg_id,
        "latitude": obs.latitude,
        "longitude": obs.longitude,
        "observed_at": obs.observed_at.isoformat(),
        "length_m": obs.length_m,
        "width_m": obs.width_m,
        "height_above_water_m": obs.height_above_water_m,
        "draft_m": obs.draft_m,
        "area_km2": obs.area_km2,
        "position_uncertainty_km": obs.position_uncertainty_km,
        "source": obs.source.value,
        "quality": obs.quality.value,
        "notes": obs.notes,
    }
