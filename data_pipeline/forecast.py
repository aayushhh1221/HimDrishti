"""
data_pipeline/forecast.py
---------------------------
Sea-ice forecast service for HimDrishti.
SIH 2026 · PS 26059

PURPOSE
-------
Implements a lightweight, reproducible sea-ice concentration forecast
that directly supports PS 26059:
  "AI-Enabled Antarctic Sea-Ice, Iceberg Trajectory, and
   Navigation Decision Support System"

ARCHITECTURE
------------
The forecast chain is:
  SeaIceField (observation / fixture)
    → Feature extraction (lagged conc, wind, ocean current)
    → Persistence baseline
    → ML model (HistGradientBoostingRegressor or RandomForest)
    → Evaluation (MAE, RMSE, time-ordered split)
    → SeaIceForecast output (structured, with provenance)

TWO MODES
---------
SYNTHETIC_DEMO:  uses existing fixture SeaIceField only
RESEARCH_DATA:   uses real ingested SeaIceField from adapters

IMPORTANT
---------
- Time-series cross-validation ONLY (never random shuffle of temporal rows).
- If ML ≤ persistence: retained, disclosed, persistence used in production.
- No fabricated accuracy numbers.
- All results carry source + dataset provenance.
- This module contains NO navigation logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .schemas import DataQuality, DataSource, SeaIceField
from .provenance import create_provenance, create_synthetic_provenance

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output contracts
# ---------------------------------------------------------------------------

@dataclass
class ForecastMetrics:
    """Evaluation metrics for sea-ice forecast."""
    persistence_mae: Optional[float] = None   # Mean Absolute Error
    persistence_rmse: Optional[float] = None  # Root Mean Square Error
    model_mae: Optional[float] = None
    model_rmse: Optional[float] = None
    n_samples_train: int = 0
    n_samples_val: int = 0
    model_better_than_persistence: Optional[bool] = None
    evaluation_status: str = "NOT_EVALUATED"  # EVALUATED | INSUFFICIENT_DATA | SYNTHETIC_ONLY
    notes: str = ""


@dataclass
class SeaIceForecastStep:
    """Sea-ice concentration forecast for a single horizon step."""
    horizon_hours: float
    valid_time: datetime
    concentration: np.ndarray          # (n_lat, n_lon), float32, [0,1]
    lats: np.ndarray
    lons: np.ndarray
    method: str                        # PERSISTENCE | ML | SYNTHETIC
    confidence: str = "MEDIUM"        # HIGH | MEDIUM | LOW | UNKNOWN
    notes: str = ""


@dataclass
class SeaIceForecast:
    """
    Complete sea-ice forecast output.

    Carries full provenance and evaluation so downstream consumers
    (route_service, API, reports) can truthfully report what they used.
    """
    reference_time: datetime
    valid_times: List[datetime]
    horizon_hours: List[float]
    steps: List[SeaIceForecastStep]
    method: str                       # PERSISTENCE | ML | HYBRID
    baseline_method: str = "PERSISTENCE"
    metrics: Optional[ForecastMetrics] = None
    data_mode: str = "SYNTHETIC_DEMO"  # SYNTHETIC_DEMO | RESEARCH_DATA
    source_dataset: str = ""
    source_organisation: str = ""
    spatial_resolution_km: Optional[float] = None
    temporal_resolution_h: Optional[float] = None
    spatial_coverage: str = ""
    retrieved_at: Optional[datetime] = None
    quality: DataQuality = DataQuality.AVAILABLE
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    prototype_notice: str = (
        "SIH 2026 Prototype · PS 26059 · Sea-ice forecast is ILLUSTRATIVE. "
        "Not an operational ice-service product. "
        "Do not use for navigation without authoritative ice-service advisory."
    )


# ---------------------------------------------------------------------------
# Persistence baseline
# ---------------------------------------------------------------------------

def persistence_forecast(
    obs: SeaIceField,
    horizon_hours: List[float],
) -> SeaIceForecast:
    """
    Persistence forecast: assume ice concentration at T+h equals
    the most recently observed concentration.

    This is the scientifically standard baseline for short-range
    sea-ice forecasting. It requires NO external model.

    Evaluation: uses time-ordered train/val split on the observed field.
    """
    logger.info(
        "Sea-ice persistence forecast: %d horizons, source=%s",
        len(horizon_hours), obs.provenance.source.value)

    ref_time = obs.times[-1]   # use last observation as reference
    valid_times = [ref_time + timedelta(hours=h) for h in horizon_hours]

    # Build forecast steps (all identical: persistence)
    steps: List[SeaIceForecastStep] = []
    # Use concentration at last observation time
    last_conc = obs.concentration[-1].copy()

    for h, vt in zip(horizon_hours, valid_times):
        # Add small temporal degradation for honest realism
        # At longer horizons persistence skill genuinely degrades
        # We do NOT artificially adjust values — the concentration stays
        # the same (pure persistence). Confidence decreases with horizon.
        confidence = _horizon_to_confidence(h, method="PERSISTENCE")
        steps.append(SeaIceForecastStep(
            horizon_hours=h,
            valid_time=vt,
            concentration=last_conc.astype(np.float32),
            lats=obs.lats.copy(),
            lons=obs.lons.copy(),
            method="PERSISTENCE",
            confidence=confidence,
            notes=f"Persistence: observed concentration at {ref_time.isoformat()} held constant.",
        ))

    # Evaluate on available multi-time observations
    metrics = _evaluate_persistence(obs)

    is_synthetic = obs.provenance.source.value in ("SYNTHETIC", "FIXTURE")
    data_mode = "SYNTHETIC_DEMO" if is_synthetic else "RESEARCH_DATA"

    return SeaIceForecast(
        reference_time=ref_time,
        valid_times=valid_times,
        horizon_hours=list(horizon_hours),
        steps=steps,
        method="PERSISTENCE",
        baseline_method="PERSISTENCE",
        metrics=metrics,
        data_mode=data_mode,
        source_dataset=obs.provenance.dataset_name,
        source_organisation=_source_to_organisation(obs.provenance.source),
        spatial_coverage=obs.provenance.spatial_coverage,
        retrieved_at=obs.provenance.retrieved_at,
        quality=obs.quality,
        provenance=[{
            "source": obs.provenance.source.value,
            "dataset_name": obs.provenance.dataset_name,
            "retrieved_at": obs.provenance.retrieved_at.isoformat(),
            "valid_time_start": obs.provenance.valid_time_start.isoformat(),
            "valid_time_end": obs.provenance.valid_time_end.isoformat(),
            "spatial_coverage": obs.provenance.spatial_coverage,
            "units": obs.provenance.units,
            "status": obs.provenance.status.value,
            "notes": obs.provenance.notes,
        }],
    )


def _evaluate_persistence(obs: SeaIceField) -> ForecastMetrics:
    """
    Evaluate persistence forecast using time-ordered split.

    Method:
      Train (first 60% of timesteps): not used for persistence evaluation.
      Validation (last 40%): for each validation step T_v, forecast = T_v - 1.
      MAE and RMSE computed on all valid (non-NaN) cells.

    This is honest evaluation on whatever temporal resolution exists.
    """
    n_times = obs.n_times
    if n_times < 3:
        return ForecastMetrics(
            evaluation_status="INSUFFICIENT_DATA",
            notes=f"Only {n_times} time steps available; need ≥3 for evaluation.",
        )

    n_val = max(1, n_times - int(n_times * 0.6))
    n_train = n_times - n_val
    val_start = n_train

    errors: List[float] = []
    for t_idx in range(val_start, n_times):
        observed = obs.concentration[t_idx]
        forecast = obs.concentration[t_idx - 1]   # persistence
        diff = observed.astype(np.float64) - forecast.astype(np.float64)
        valid = np.isfinite(diff)
        if valid.any():
            errors.extend(diff[valid].tolist())

    if not errors:
        return ForecastMetrics(
            evaluation_status="INSUFFICIENT_DATA",
            notes="No valid (non-NaN) cells for persistence evaluation.",
        )

    errors_arr = np.array(errors)
    mae = float(np.mean(np.abs(errors_arr)))
    rmse = float(np.sqrt(np.mean(errors_arr ** 2)))

    is_synthetic = obs.provenance.source.value in ("SYNTHETIC", "FIXTURE")

    return ForecastMetrics(
        persistence_mae=round(mae, 5),
        persistence_rmse=round(rmse, 5),
        model_mae=None,   # no ML yet
        model_rmse=None,
        n_samples_train=n_train,
        n_samples_val=n_val,
        model_better_than_persistence=None,
        evaluation_status="SYNTHETIC_ONLY" if is_synthetic else "EVALUATED",
        notes=(
            f"Persistence baseline evaluated on {n_val} validation step(s) "
            f"({len(errors)} spatial samples). Time-ordered split; no random shuffle."
        ),
    )


# ---------------------------------------------------------------------------
# ML forecast model
# ---------------------------------------------------------------------------

def ml_forecast(
    obs: SeaIceField,
    wind: Optional["WindField"],    # noqa: F821
    ocean: Optional["OceanCurrentField"],  # noqa: F821
    horizon_hours: List[float],
    dt_obs_hours: float = 24.0,
) -> SeaIceForecast:
    """
    ML sea-ice forecast using HistGradientBoostingRegressor.

    FEATURE SET (only from genuinely available data):
      - lag-1 sea-ice concentration (primary predictor)
      - lag-1 temporal trend (concentration change)
      - spatial mean concentration of neighbourhood
      - domain-mean wind speed (if wind available)
      - domain-mean current speed (if ocean available)
      - fractional time index (for seasonal trend)

    TARGET:
      - next-step sea-ice concentration (t+1)

    TEMPORAL SPLIT:
      - Train: first 60% of time steps (in order)
      - Validation: remaining 40% (in order)
      - NEVER random shuffle of temporal rows

    Fallback to persistence if:
      - sklearn not available
      - < 4 time steps available
      - training fails for any reason

    Results:
      Always report whether ML > persistence. Never hide a failure.
    """
    n_times = obs.n_times

    # Attempt ML
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
        sklearn_available = True
    except ImportError:
        sklearn_available = False
        logger.warning(
            "scikit-learn not available — falling back to persistence forecast.")

    if not sklearn_available or n_times < 4:
        logger.info(
            "ML forecast: insufficient data (%d steps) or sklearn unavailable. "
            "Falling back to persistence.", n_times)
        fc = persistence_forecast(obs, horizon_hours)
        if fc.metrics:
            fc.metrics.evaluation_status = (
                "ML_SKIPPED_SKLEARN_UNAVAILABLE"
                if not sklearn_available else
                "ML_SKIPPED_INSUFFICIENT_DATA"
            )
        return fc

    try:
        X, y, spatial_shape = _build_features(obs, wind, ocean)
    except Exception as exc:
        logger.error("Feature extraction failed: %s — using persistence.", exc)
        return persistence_forecast(obs, horizon_hours)

    if X.shape[0] < 4:
        logger.warning("Too few feature samples (%d) — using persistence.", X.shape[0])
        return persistence_forecast(obs, horizon_hours)

    # Time-ordered split
    n_total = X.shape[0]
    n_train = max(2, int(n_total * 0.6))
    n_val = n_total - n_train

    X_train, y_train = X[:n_train], y[:n_train]
    X_val, y_val = X[n_train:], y[n_train:]

    # Persistence baseline for comparison
    # (predict y_val using the lag-1 feature directly)
    pers_pred = X_val[:, 0]   # lag-1 concentration is first feature
    valid_pers = np.isfinite(y_val) & np.isfinite(pers_pred)
    pers_mae = float(np.mean(np.abs(y_val[valid_pers] - pers_pred[valid_pers])))
    pers_rmse = float(np.sqrt(np.mean((y_val[valid_pers] - pers_pred[valid_pers]) ** 2)))

    try:
        model = HistGradientBoostingRegressor(
            max_iter=100,
            max_depth=4,
            learning_rate=0.1,
            min_samples_leaf=5,
            random_state=42,
        )
        # Mask NaN in training (HistGBR handles NaN natively)
        model.fit(X_train, y_train)

        y_pred_val = model.predict(X_val)
        valid_ml = np.isfinite(y_val)
        ml_mae = float(np.mean(np.abs(y_val[valid_ml] - y_pred_val[valid_ml])))
        ml_rmse = float(np.sqrt(np.mean((y_val[valid_ml] - y_pred_val[valid_ml]) ** 2)))

        ml_better = ml_mae < pers_mae
        logger.info(
            "ML sea-ice forecast: persistence MAE=%.5f RMSE=%.5f | "
            "ML MAE=%.5f RMSE=%.5f | ML_better=%s",
            pers_mae, pers_rmse, ml_mae, ml_rmse, ml_better)

        if not ml_better:
            logger.info(
                "ML did not outperform persistence — using persistence for production "
                "steps. ML results retained for reporting transparency.")

    except Exception as exc:
        logger.error("ML model training/prediction failed: %s — using persistence.", exc)
        metrics = ForecastMetrics(
            persistence_mae=round(pers_mae, 5),
            persistence_rmse=round(pers_rmse, 5),
            n_samples_train=n_train,
            n_samples_val=n_val,
            evaluation_status="ML_TRAINING_FAILED",
            notes=f"ML training failed: {exc}. Persistence used.",
        )
        fc = persistence_forecast(obs, horizon_hours)
        fc.metrics = metrics
        fc.method = "PERSISTENCE"
        return fc

    # Build forecast steps — use ML where it genuinely helps, persistence otherwise
    ref_time = obs.times[-1]
    valid_times = [ref_time + timedelta(hours=h) for h in horizon_hours]
    steps: List[SeaIceForecastStep] = []
    last_conc = obs.concentration[-1].copy()

    for h, vt in zip(horizon_hours, valid_times):
        confidence = _horizon_to_confidence(h, method="ML" if ml_better else "PERSISTENCE")
        method_used = "ML" if ml_better else "PERSISTENCE"

        if ml_better and n_times >= 2:
            # Use ML prediction for the full spatial grid at last-observed state
            feat = _single_point_features_from_obs(obs, wind, ocean)
            if feat is not None:
                try:
                    pred_flat = model.predict(feat)
                    pred_conc = pred_flat.reshape(spatial_shape).astype(np.float32)
                    pred_conc = np.clip(pred_conc, 0.0, 1.0)
                    method_used = "ML"
                except Exception:
                    pred_conc = last_conc.astype(np.float32)
                    method_used = "PERSISTENCE"
            else:
                pred_conc = last_conc.astype(np.float32)
                method_used = "PERSISTENCE"
        else:
            pred_conc = last_conc.astype(np.float32)

        steps.append(SeaIceForecastStep(
            horizon_hours=h,
            valid_time=vt,
            concentration=pred_conc,
            lats=obs.lats.copy(),
            lons=obs.lons.copy(),
            method=method_used,
            confidence=confidence,
            notes=(
                f"Method: {method_used}. "
                f"ML MAE={ml_mae:.5f}, persistence MAE={pers_mae:.5f}. "
                f"ML better: {ml_better}."
            ),
        ))

    is_synthetic = obs.provenance.source.value in ("SYNTHETIC", "FIXTURE")
    data_mode = "SYNTHETIC_DEMO" if is_synthetic else "RESEARCH_DATA"
    production_method = "ML" if ml_better else "PERSISTENCE"

    metrics = ForecastMetrics(
        persistence_mae=round(pers_mae, 5),
        persistence_rmse=round(pers_rmse, 5),
        model_mae=round(ml_mae, 5),
        model_rmse=round(ml_rmse, 5),
        n_samples_train=n_train,
        n_samples_val=n_val,
        model_better_than_persistence=ml_better,
        evaluation_status="SYNTHETIC_ONLY" if is_synthetic else "EVALUATED",
        notes=(
            f"HistGradientBoostingRegressor vs persistence. "
            f"Time-ordered split ({n_train} train / {n_val} val). "
            f"No random shuffle of temporal rows. "
            f"{'ML used in production steps.' if ml_better else 'Persistence retained (ML did not outperform baseline).'}"
        ),
    )

    return SeaIceForecast(
        reference_time=ref_time,
        valid_times=valid_times,
        horizon_hours=list(horizon_hours),
        steps=steps,
        method=production_method,
        baseline_method="PERSISTENCE",
        metrics=metrics,
        data_mode=data_mode,
        source_dataset=obs.provenance.dataset_name,
        source_organisation=_source_to_organisation(obs.provenance.source),
        spatial_coverage=obs.provenance.spatial_coverage,
        retrieved_at=obs.provenance.retrieved_at,
        quality=obs.quality,
        provenance=[{
            "source": obs.provenance.source.value,
            "dataset_name": obs.provenance.dataset_name,
            "retrieved_at": obs.provenance.retrieved_at.isoformat(),
            "valid_time_start": obs.provenance.valid_time_start.isoformat(),
            "valid_time_end": obs.provenance.valid_time_end.isoformat(),
            "spatial_coverage": obs.provenance.spatial_coverage,
            "units": obs.provenance.units,
            "status": obs.provenance.status.value,
            "notes": obs.provenance.notes,
        }],
    )


# ---------------------------------------------------------------------------
# Feature extraction helpers
# ---------------------------------------------------------------------------

def _build_features(
    obs: SeaIceField,
    wind: Optional[Any],
    ocean: Optional[Any],
) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int]]:
    """
    Build feature matrix X and target vector y from available data.

    X shape: (n_samples, n_features)
    y shape: (n_samples,)

    Each sample corresponds to one (time, spatial_point) pair,
    where temporal ordering is strictly preserved.

    Features:
      [0] lag-1 concentration
      [1] lag-2 concentration (if available, else 0)
      [2] temporal trend: lag1 - lag2
      [3] spatial neighbourhood mean
      [4] domain-mean wind speed (if available, else 0)
      [5] domain-mean current speed (if available, else 0)
      [6] fractional time index (0→1)
    """
    n_t, n_lat, n_lon = obs.concentration.shape

    # We predict t+1 from t features → n_t-1 time pairs
    samples_X = []
    samples_y = []

    for t in range(n_t - 1):
        conc_t = obs.concentration[t].astype(np.float64)
        conc_t1 = obs.concentration[t + 1].astype(np.float64)
        conc_tm1 = obs.concentration[t - 1].astype(np.float64) if t > 0 else conc_t

        frac_t = t / max(n_t - 2, 1)

        # Scalars for this time step
        w_speed = 0.0
        if wind is not None:
            try:
                u = wind.u_wind[min(t, wind.u_wind.shape[0] - 1)]
                v = wind.v_wind[min(t, wind.v_wind.shape[0] - 1)]
                w_speed = float(np.nanmean(np.sqrt(u**2 + v**2)))
            except Exception:
                w_speed = 0.0

        c_speed = 0.0
        if ocean is not None:
            try:
                u = ocean.u_current[min(t, ocean.u_current.shape[0] - 1)]
                v = ocean.v_current[min(t, ocean.v_current.shape[0] - 1)]
                c_speed = float(np.nanmean(np.sqrt(u**2 + v**2)))
            except Exception:
                c_speed = 0.0

        # Vectorize over spatial points
        for iy in range(n_lat):
            for ix in range(n_lon):
                lag1 = conc_t[iy, ix]
                lag2 = conc_tm1[iy, ix]
                trend = lag1 - lag2
                # 3x3 neighbourhood mean (clamped)
                neigh = conc_t[
                    max(0, iy-1):min(n_lat, iy+2),
                    max(0, ix-1):min(n_lon, ix+2)
                ]
                neigh_mean = float(np.nanmean(neigh)) if np.any(np.isfinite(neigh)) else lag1

                x = [lag1, lag2, trend, neigh_mean, w_speed, c_speed, frac_t]
                y_val = conc_t1[iy, ix]
                samples_X.append(x)
                samples_y.append(y_val)

    X = np.array(samples_X, dtype=np.float64)
    y = np.array(samples_y, dtype=np.float64)
    spatial_shape = (n_lat, n_lon)
    return X, y, spatial_shape


def _single_point_features_from_obs(
    obs: SeaIceField,
    wind: Optional[Any],
    ocean: Optional[Any],
) -> Optional[np.ndarray]:
    """
    Build feature rows for EVERY spatial point at the last observed time step.
    Returns (n_lat * n_lon, n_features) or None on failure.
    """
    try:
        n_t, n_lat, n_lon = obs.concentration.shape
        t = n_t - 1
        conc_t = obs.concentration[t].astype(np.float64)
        conc_tm1 = obs.concentration[t - 1].astype(np.float64) if t > 0 else conc_t
        frac_t = 1.0

        w_speed = 0.0
        if wind is not None:
            try:
                u = wind.u_wind[min(t, wind.u_wind.shape[0] - 1)]
                v = wind.v_wind[min(t, wind.v_wind.shape[0] - 1)]
                w_speed = float(np.nanmean(np.sqrt(u**2 + v**2)))
            except Exception:
                w_speed = 0.0

        c_speed = 0.0
        if ocean is not None:
            try:
                u = ocean.u_current[min(t, ocean.u_current.shape[0] - 1)]
                v = ocean.v_current[min(t, ocean.v_current.shape[0] - 1)]
                c_speed = float(np.nanmean(np.sqrt(u**2 + v**2)))
            except Exception:
                c_speed = 0.0

        rows = []
        for iy in range(n_lat):
            for ix in range(n_lon):
                lag1 = conc_t[iy, ix]
                lag2 = conc_tm1[iy, ix]
                trend = lag1 - lag2
                neigh = conc_t[
                    max(0, iy-1):min(n_lat, iy+2),
                    max(0, ix-1):min(n_lon, ix+2)
                ]
                neigh_mean = float(np.nanmean(neigh)) if np.any(np.isfinite(neigh)) else lag1
                rows.append([lag1, lag2, trend, neigh_mean, w_speed, c_speed, frac_t])

        return np.array(rows, dtype=np.float64)
    except Exception as exc:
        logger.warning("Single-point feature extraction failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _horizon_to_confidence(horizon_h: float, method: str = "PERSISTENCE") -> str:
    """
    Return forecast confidence string based on horizon and method.
    Based on accepted sea-ice forecast skill norms — not invented.
    """
    if method == "PERSISTENCE":
        # Persistence skill degrades with horizon
        if horizon_h <= 24:
            return "HIGH"
        elif horizon_h <= 48:
            return "MEDIUM"
        else:
            return "LOW"
    elif method == "ML":
        if horizon_h <= 24:
            return "MEDIUM"
        elif horizon_h <= 72:
            return "LOW"
        else:
            return "UNKNOWN"
    return "UNKNOWN"


def _source_to_organisation(source: DataSource) -> str:
    """Map DataSource enum to human-readable organisation string."""
    mapping = {
        DataSource.NSIDC_SSMI:       "NOAA / NSIDC (National Snow and Ice Data Center)",
        DataSource.COPERNICUS_SEAICE: "Copernicus Marine Service / OSI-SAF",
        DataSource.CMEMS_PHY:        "Copernicus Marine Service (CMEMS)",
        DataSource.GLORYS:           "Copernicus Marine Service — GLORYS12",
        DataSource.ECMWF_IFS:        "ECMWF (European Centre for Medium-Range Weather Forecasts)",
        DataSource.ERA5:             "ECMWF ERA5 reanalysis",
        DataSource.NCEP_GFS:         "NOAA / NCEP (National Centers for Environmental Prediction)",
        DataSource.USNIC_NIC:        "US National Ice Center (NIC)",
        DataSource.BYU_ICEBERG:      "BYU / NSIDC Iceberg Tracking Database",
        DataSource.ALTIBERG:         "CNES / Ifremer Altiberg",
        DataSource.SYNTHETIC:        "HimDrishti Synthetic Demo Fixture",
        DataSource.FIXTURE:          "HimDrishti Recorded Replay Fixture",
        DataSource.UNKNOWN:          "Unknown source",
    }
    return mapping.get(source, str(source.value))


def forecast_to_dict(forecast: SeaIceForecast) -> Dict[str, Any]:
    """
    Serialize a SeaIceForecast to a JSON-compatible dict.
    Used by the API response layer.
    """
    def _metrics_to_dict(m: Optional[ForecastMetrics]) -> Optional[Dict[str, Any]]:
        if m is None:
            return None
        return {
            "persistence_mae": m.persistence_mae,
            "persistence_rmse": m.persistence_rmse,
            "model_mae": m.model_mae,
            "model_rmse": m.model_rmse,
            "n_samples_train": m.n_samples_train,
            "n_samples_val": m.n_samples_val,
            "model_better_than_persistence": m.model_better_than_persistence,
            "evaluation_status": m.evaluation_status,
            "notes": m.notes,
        }

    def _step_to_dict(s: SeaIceForecastStep) -> Dict[str, Any]:
        return {
            "horizon_hours": s.horizon_hours,
            "valid_time": s.valid_time.isoformat(),
            "method": s.method,
            "confidence": s.confidence,
            "mean_concentration": round(float(np.nanmean(s.concentration)), 4),
            "max_concentration": round(float(np.nanmax(s.concentration)), 4),
            "min_concentration": round(float(np.nanmin(s.concentration)), 4),
            "shape": list(s.concentration.shape),
            "notes": s.notes,
        }

    return {
        "reference_time": forecast.reference_time.isoformat(),
        "valid_times": [t.isoformat() for t in forecast.valid_times],
        "horizon_hours": forecast.horizon_hours,
        "method": forecast.method,
        "baseline_method": forecast.baseline_method,
        "data_mode": forecast.data_mode,
        "source_dataset": forecast.source_dataset,
        "source_organisation": forecast.source_organisation,
        "spatial_resolution_km": forecast.spatial_resolution_km,
        "temporal_resolution_h": forecast.temporal_resolution_h,
        "spatial_coverage": forecast.spatial_coverage,
        "retrieved_at": forecast.retrieved_at.isoformat() if forecast.retrieved_at else None,
        "quality": forecast.quality.value,
        "steps": [_step_to_dict(s) for s in forecast.steps],
        "metrics": _metrics_to_dict(forecast.metrics),
        "provenance": forecast.provenance,
        "prototype_notice": forecast.prototype_notice,
    }
