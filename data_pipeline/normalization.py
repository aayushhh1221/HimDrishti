"""
data_pipeline/normalization.py
--------------------------------
Normalization utilities — converts incoming raw data to the
pipeline's internal common format.
SIH 2026 · PS 26059

Internal conventions (all adapters must produce these):
  Concentration : float32, [0.0, 1.0], NaN for missing
  Velocities    : float32, m/s, finite or NaN for missing
  Coordinates   : float64, latitude [-90,90], longitude [-180,+180]
  Timestamps    : datetime, UTC-aware (timezone.utc)

This module does NOT silently repair scientifically suspicious values.
It only:
  1. Converts units to the internal standard
  2. Converts coordinate conventions (0-360 lon → -180/+180)
  3. Converts fill values to NaN (explicitly documented)
  4. Ensures float32 arrays for memory efficiency

Any value that is logically invalid (e.g. concentration = -0.5) is
set to NaN and flagged in the log — NOT silently clipped to 0.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Timestamp normalization
# ---------------------------------------------------------------------------

def normalize_timestamp(dt: datetime) -> datetime:
    """
    Ensure a datetime is UTC-aware. If naive, assume UTC and warn.
    Never silently assume a non-UTC timezone.
    """
    if dt.tzinfo is None:
        logger.warning(
            "Naive datetime %s encountered — assuming UTC. "
            "Source adapter should provide timezone-aware datetimes.", dt)
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_timestamps(times: List[datetime]) -> List[datetime]:
    return [normalize_timestamp(t) for t in times]


# ---------------------------------------------------------------------------
# Coordinate normalization
# ---------------------------------------------------------------------------

def normalize_longitude(lon_arr: np.ndarray) -> np.ndarray:
    """
    Convert 0-360 longitude convention to -180/+180.
    Values already in -180..+180 are returned unchanged.
    """
    lon = lon_arr.copy().astype(np.float64)
    mask = lon > 180.0
    if np.any(mask):
        n_converted = int(np.sum(mask))
        logger.debug("Longitude: converting %d values from 0-360 to -180/+180", n_converted)
        lon[mask] -= 360.0
    return lon


def normalize_lat_order(
    lats: np.ndarray,
    data: np.ndarray,
    lat_axis: int = -2,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Ensure latitudes are in ascending order (south to north).
    Flips the data array along lat_axis if needed.
    """
    if lats[0] > lats[-1]:
        logger.debug("Flipping latitude axis from descending to ascending order")
        lats = lats[::-1].copy()
        data = np.flip(data, axis=lat_axis).copy()
    return lats, data


# ---------------------------------------------------------------------------
# Fill-value handling
# ---------------------------------------------------------------------------

def replace_fill_value(
    arr: np.ndarray,
    fill_value,
    reason: str = "source fill value",
) -> np.ndarray:
    """
    Replace a known fill value with NaN.
    The reason string is logged so the substitution is documented.
    """
    arr = arr.astype(np.float32)
    if fill_value is not None:
        mask = arr == fill_value
        n = int(np.sum(mask))
        if n > 0:
            logger.debug("Replacing %d fill_value=%s with NaN (%s)", n, fill_value, reason)
            arr[mask] = np.nan
    return arr


def mask_invalid_concentration(arr: np.ndarray) -> np.ndarray:
    """
    Set scientifically invalid concentration values to NaN.
    Logs how many values were affected — does NOT silently clip.
    Values < 0 or > 1 are INVALID (not just out-of-range noise)
    because normalized concentration must be in [0, 1] by definition.
    """
    arr = arr.astype(np.float32)
    below = arr < 0.0
    above = arr > 1.0
    n_below = int(np.sum(below))
    n_above = int(np.sum(above))
    if n_below:
        logger.warning(
            "%d concentration values < 0.0 (min=%.4f) — set to NaN, not 0",
            n_below, float(arr[below].min()))
        arr[below] = np.nan
    if n_above:
        logger.warning(
            "%d concentration values > 1.0 (max=%.4f) — set to NaN, not 1",
            n_above, float(arr[above].max()))
        arr[above] = np.nan
    return arr


# ---------------------------------------------------------------------------
# Unit conversions
# ---------------------------------------------------------------------------

def knots_to_ms(arr: np.ndarray) -> np.ndarray:
    """Convert wind/current speed from knots to m/s."""
    return (arr * 0.514444).astype(np.float32)


def percent_to_fraction(arr: np.ndarray) -> np.ndarray:
    """Convert ice concentration from % (0-100) to fraction (0-1)."""
    result = (arr / 100.0).astype(np.float32)
    logger.debug("Converted ice concentration: % → fraction")
    return result


def tenths_to_fraction(arr: np.ndarray) -> np.ndarray:
    """Convert ice concentration from tenths (0-10) to fraction (0-1)."""
    result = (arr / 10.0).astype(np.float32)
    logger.debug("Converted ice concentration: tenths → fraction")
    return result


def celsius_to_kelvin(arr: np.ndarray) -> np.ndarray:
    """Convert temperature from Celsius to Kelvin."""
    return (arr + 273.15).astype(np.float32)


# ---------------------------------------------------------------------------
# Spatial interpolation placeholder
# ---------------------------------------------------------------------------

def regrid_concentration_to_model_grid(
    conc: np.ndarray,
    src_lats: np.ndarray,
    src_lons: np.ndarray,
    dst_lats: np.ndarray,
    dst_lons: np.ndarray,
) -> np.ndarray:
    """
    Bilinear regrid of concentration field from source to destination grid.

    PROTOTYPE NOTE: This is a nearest-neighbour fallback for now.
    A production implementation should use scipy.interpolate.RegularGridInterpolator
    or xesmf for conservative regridding (which preserves area-weighted
    concentration — important for sea-ice work).

    conc shape: (n_lat_src, n_lon_src) for a single time step.
    Returns shape: (n_lat_dst, n_lon_dst)
    """
    try:
        from scipy.interpolate import RegularGridInterpolator
        interp = RegularGridInterpolator(
            (src_lats, src_lons), conc, method="nearest",
            bounds_error=False, fill_value=np.nan)
        dst_ll = np.meshgrid(dst_lats, dst_lons, indexing="ij")
        pts = np.stack([dst_ll[0].ravel(), dst_ll[1].ravel()], axis=-1)
        return interp(pts).reshape(len(dst_lats), len(dst_lons)).astype(np.float32)
    except ImportError:
        logger.warning(
            "scipy not available — returning concentration on original grid "
            "(no regridding applied). Install scipy for proper spatial interpolation.")
        return conc.astype(np.float32)


# ---------------------------------------------------------------------------
# Science-core interface helpers
# ---------------------------------------------------------------------------

def extract_wind_series_at_point(
    wind: "WindField",
    lat: float,
    lon: float,
) -> np.ndarray:
    """
    Extract a (n_steps, 2) [u, v] wind time series at the nearest grid point
    to (lat, lon). This is what iceberg_drift.simulate_drift expects.

    For a production system, bilinear spatial interpolation should replace
    the nearest-neighbour lookup here.
    """
    lat_idx = int(np.argmin(np.abs(wind.lats - lat)))
    lon_idx = int(np.argmin(np.abs(wind.lons - lon)))
    u = wind.u_wind[:, lat_idx, lon_idx]
    v = wind.v_wind[:, lat_idx, lon_idx]
    return np.column_stack([u, v]).astype(np.float64)


def extract_current_series_at_point(
    current: "OceanCurrentField",
    lat: float,
    lon: float,
) -> np.ndarray:
    """
    Extract a (n_steps, 2) [u, v] current time series at the nearest grid point.
    """
    lat_idx = int(np.argmin(np.abs(current.lats - lat)))
    lon_idx = int(np.argmin(np.abs(current.lons - lon)))
    u = current.u_current[:, lat_idx, lon_idx]
    v = current.v_current[:, lat_idx, lon_idx]
    return np.column_stack([u, v]).astype(np.float64)


def sea_ice_to_model_grid(
    sea_ice: "SeaIceField",
    nx: int,
    ny: int,
) -> np.ndarray:
    """
    Map a SeaIceField onto the route-search model grid.
    Returns shape (n_times, ny, nx) with values in [0, 1].

    PROTOTYPE: bilinear interpolation to the model grid.
    Missing values (NaN) are set to 0.0 (open water assumption)
    with a logged warning — this is the one place where NaN→0
    is permitted, and it is explicitly documented.
    """
    n_t = sea_ice.n_times
    result = np.zeros((n_t, ny, nx), dtype=np.float32)

    # Build simple equally-spaced model grid lats/lons from the data extent
    model_lats = np.linspace(sea_ice.lats.min(), sea_ice.lats.max(), ny)
    model_lons = np.linspace(sea_ice.lons.min(), sea_ice.lons.max(), nx)

    for t in range(n_t):
        raw = sea_ice.concentration[t]  # (n_lat, n_lon)
        regridded = regrid_concentration_to_model_grid(
            raw, sea_ice.lats, sea_ice.lons, model_lats, model_lons)
        # Only here: NaN → 0.0 (open water) because the science core
        # cannot receive NaN concentration. Logged explicitly.
        n_nan = int(np.isnan(regridded).sum())
        if n_nan:
            logger.warning(
                "t=%d: %d NaN concentration values after regrid → set to 0.0 "
                "(open-water assumption, not physical fill). "
                "Source: %s", t, n_nan, sea_ice.provenance.source.value)
        regridded = np.where(np.isnan(regridded), 0.0, regridded)
        result[t] = np.clip(regridded, 0.0, 1.0)

    return result
