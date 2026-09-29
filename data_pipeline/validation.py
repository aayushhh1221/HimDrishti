"""
data_pipeline/validation.py
-----------------------------
Pre-pipeline validation for all incoming datasets.
SIH 2026 · PS 26059

Rules:
  - Concentration must be in [0, 1] (NaN allowed = missing, NOT substituted).
  - Wind/current must be finite, in plausible m/s range.
  - Coordinates must be valid lat/lon.
  - Timestamps must be UTC-aware, monotonically increasing.
  - Forecast horizons must be non-negative and consistent.

Validation failures raise structured ValidationError exceptions.
The pipeline MUST NOT silently substitute values for invalid data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timezone
from typing import List, Optional

import numpy as np

from .schemas import (
    DataQuality, IcebergObservation, OceanCurrentField,
    SeaIceField, WindField, ForecastWindow,
)

logger = logging.getLogger(__name__)

# Physical plausibility limits (conservative — flag but do not auto-correct)
MAX_WIND_MS = 100.0        # strongest recorded surface wind ~96 m/s (Typhoon Tip)
MAX_CURRENT_MS = 5.0       # very strong oceanic current ~3 m/s; 5 m/s is outer bound
MAX_LAT = 90.0
MAX_LON = 180.0
MAX_ICEBERG_DIM_M = 300_000.0  # 300 km — largest recorded tabular berg ~295 km


@dataclass
class ValidationError(Exception):
    field: str
    message: str
    severity: str = "error"   # "error" | "warning"

    def __str__(self):
        return f"[{self.severity.upper()}] {self.field}: {self.message}"


@dataclass
class ValidationResult:
    valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    quality: DataQuality

    @property
    def summary(self) -> str:
        parts = [f"valid={self.valid}", f"quality={self.quality.value}"]
        if self.errors:
            parts.append(f"errors={len(self.errors)}")
        if self.warnings:
            parts.append(f"warnings={len(self.warnings)}")
        return " | ".join(parts)


def _check_utc(dt, field_name: str) -> Optional[ValidationError]:
    """Confirm datetime is timezone-aware and UTC."""
    if dt is None:
        return ValidationError(field_name, "timestamp is None", severity="error")
    if dt.tzinfo is None:
        return ValidationError(field_name, "timestamp is not timezone-aware (must be UTC)", severity="error")
    return None


def validate_sea_ice(field: SeaIceField) -> ValidationResult:
    """
    Validate a SeaIceField before it enters the science pipeline.

    Rules:
      1. concentration values in [0.0, 1.0] (NaN = missing, accepted)
      2. No negative concentrations
      3. Lats in [-90, 90], lons in [-180, 180]
      4. Timestamps UTC-aware and monotonically increasing
      5. Shape consistency
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []

    # Shape
    if field.concentration.ndim != 3:
        errors.append(ValidationError(
            "concentration", f"expected 3-D array (n_t, n_lat, n_lon), got {field.concentration.ndim}-D"))

    # Coordinate ranges
    if np.any(field.lats < -90) or np.any(field.lats > 90):
        errors.append(ValidationError("lats", "latitude values outside [-90, 90]"))
    if np.any(field.lons < -180) or np.any(field.lons > 180):
        errors.append(ValidationError("lons", "longitude values outside [-180, 180]"))

    # Concentration range
    finite = field.concentration[np.isfinite(field.concentration)]
    if len(finite) == 0:
        errors.append(ValidationError("concentration", "all values are NaN/Inf — no usable data"))
    else:
        if np.any(finite < 0.0):
            errors.append(ValidationError(
                "concentration", f"negative values found (min={finite.min():.4f})"))
        if np.any(finite > 1.0):
            errors.append(ValidationError(
                "concentration", f"values > 1.0 found (max={finite.max():.4f}) — not normalized"))
        nan_frac = np.isnan(field.concentration).mean()
        if nan_frac > 0.5:
            warnings.append(ValidationError(
                "concentration", f"{nan_frac*100:.1f}% missing (NaN) — partial coverage",
                severity="warning"))

    # Timestamps
    for i, t in enumerate(field.times):
        err = _check_utc(t, f"times[{i}]")
        if err:
            errors.append(err)
    if len(field.times) > 1:
        diffs = [(field.times[i+1] - field.times[i]).total_seconds()
                 for i in range(len(field.times) - 1)]
        if any(d <= 0 for d in diffs):
            errors.append(ValidationError("times", "timestamps are not strictly monotonically increasing"))

    valid = len(errors) == 0
    if not valid:
        quality = DataQuality.INVALID
    elif warnings:
        quality = DataQuality.PARTIAL
    else:
        quality = DataQuality.AVAILABLE

    result = ValidationResult(valid=valid, errors=errors, warnings=warnings, quality=quality)
    logger.info("SeaIceField validation: %s", result.summary)
    for e in errors:
        logger.error("  %s", e)
    for w in warnings:
        logger.warning("  %s", w)
    return result


def validate_wind(field: WindField) -> ValidationResult:
    """Validate a WindField."""
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []

    for name, arr in [("u_wind", field.u_wind), ("v_wind", field.v_wind)]:
        if not np.all(np.isfinite(arr)):
            n_bad = np.sum(~np.isfinite(arr))
            errors.append(ValidationError(name, f"{n_bad} non-finite values (NaN or Inf)"))
        magnitude = np.abs(arr)
        if np.any(magnitude > MAX_WIND_MS):
            errors.append(ValidationError(
                name, f"values exceed {MAX_WIND_MS} m/s (max={magnitude.max():.1f} m/s)"))

    if np.any(field.lats < -90) or np.any(field.lats > 90):
        errors.append(ValidationError("lats", "latitude out of range"))
    if np.any(field.lons < -180) or np.any(field.lons > 180):
        errors.append(ValidationError("lons", "longitude out of range"))

    for i, t in enumerate(field.times):
        err = _check_utc(t, f"times[{i}]")
        if err:
            errors.append(err)

    valid = len(errors) == 0
    quality = DataQuality.AVAILABLE if valid else DataQuality.INVALID
    result = ValidationResult(valid=valid, errors=errors, warnings=warnings, quality=quality)
    logger.info("WindField validation: %s", result.summary)
    return result


def validate_ocean_current(field: OceanCurrentField) -> ValidationResult:
    """Validate an OceanCurrentField."""
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []

    for name, arr in [("u_current", field.u_current), ("v_current", field.v_current)]:
        if not np.all(np.isfinite(arr)):
            n_bad = np.sum(~np.isfinite(arr))
            errors.append(ValidationError(name, f"{n_bad} non-finite values"))
        magnitude = np.abs(arr)
        if np.any(magnitude > MAX_CURRENT_MS):
            errors.append(ValidationError(
                name, f"values exceed {MAX_CURRENT_MS} m/s (max={magnitude.max():.2f} m/s)"))

    if np.any(field.lats < -90) or np.any(field.lats > 90):
        errors.append(ValidationError("lats", "latitude out of range"))

    for i, t in enumerate(field.times):
        err = _check_utc(t, f"times[{i}]")
        if err:
            errors.append(err)

    valid = len(errors) == 0
    quality = DataQuality.AVAILABLE if valid else DataQuality.INVALID
    result = ValidationResult(valid=valid, errors=errors, warnings=warnings, quality=quality)
    logger.info("OceanCurrentField validation: %s", result.summary)
    return result


def validate_iceberg_observation(obs: IcebergObservation) -> ValidationResult:
    """Validate a single IcebergObservation."""
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []

    if not (-90 <= obs.latitude <= 90):
        errors.append(ValidationError("latitude", f"value {obs.latitude} out of [-90, 90]"))
    if not (-180 <= obs.longitude <= 180):
        errors.append(ValidationError("longitude", f"value {obs.longitude} out of [-180, 180]"))

    err = _check_utc(obs.observed_at, "observed_at")
    if err:
        errors.append(err)

    for dim_name, dim_val in [
        ("length_m", obs.length_m),
        ("width_m", obs.width_m),
        ("height_above_water_m", obs.height_above_water_m),
        ("draft_m", obs.draft_m),
    ]:
        if dim_val is not None:
            if dim_val <= 0:
                errors.append(ValidationError(dim_name, f"must be positive, got {dim_val}"))
            elif dim_val > MAX_ICEBERG_DIM_M:
                warnings.append(ValidationError(
                    dim_name, f"unusually large: {dim_val} m (max recorded ~295 km)",
                    severity="warning"))

    valid = len(errors) == 0
    quality = DataQuality.AVAILABLE if valid else DataQuality.INVALID
    return ValidationResult(valid=valid, errors=errors, warnings=warnings, quality=quality)


def validate_forecast_window(window: ForecastWindow) -> ValidationResult:
    """Validate a ForecastWindow."""
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []

    err = _check_utc(window.reference_time, "reference_time")
    if err:
        errors.append(err)

    for i, (t, h) in enumerate(zip(window.valid_times, window.horizon_hours)):
        err = _check_utc(t, f"valid_times[{i}]")
        if err:
            errors.append(err)
        if h < 0:
            errors.append(ValidationError(f"horizon_hours[{i}]", f"negative horizon: {h}"))

    if len(window.horizon_hours) > 1:
        diffs = [window.horizon_hours[i+1] - window.horizon_hours[i]
                 for i in range(len(window.horizon_hours) - 1)]
        if any(d <= 0 for d in diffs):
            errors.append(ValidationError("horizon_hours", "not strictly increasing"))

    if window.max_horizon_h > 240:
        warnings.append(ValidationError(
            "horizon_hours", f"horizon {window.max_horizon_h}h exceeds typical 120h NWP ceiling",
            severity="warning"))

    valid = len(errors) == 0
    quality = DataQuality.AVAILABLE if valid else DataQuality.INVALID
    return ValidationResult(valid=valid, errors=errors, warnings=warnings, quality=quality)
