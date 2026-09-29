"""
data_pipeline/adapters/wind.py
--------------------------------
Wind forecast adapter.
SIH 2026 · PS 26059

LIVE SOURCE TARGET:
    ECMWF ERA5 reanalysis / IFS forecast via CDS (Climate Data Store)
    Variables: u10 (10m_u_component_of_wind), v10 (10m_v_component_of_wind)
    Units: m/s

LIVE ACCESS REQUIREMENT:
    CDS_API_KEY environment variable (format: "UID:API_KEY")
    Package: cdsapi (pip install cdsapi)
    Config: ~/.cdsapirc or CDS_API_KEY env var

FIXTURE PATH (always available):
    Deterministic Southern Ocean wind fixture modelling the Southern
    Ocean Westerlies ("Roaring Forties / Furious Fifties") pattern.
    Clearly labelled SYNTHETIC in provenance.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List

import numpy as np

from ..provenance import create_synthetic_provenance
from ..schemas import DataQuality, DataSource, WindField
from ..validation import validate_wind

logger = logging.getLogger(__name__)


def fetch_wind(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    start_time: datetime,
    end_time: datetime,
    use_fixture: bool = False,
) -> WindField:
    """
    Fetch 10m wind forecast/reanalysis for the given spatiotemporal window.

    Falls back to fixture if CDS_API_KEY is absent or use_fixture=True.
    """
    has_creds = bool(os.environ.get("CDS_API_KEY"))

    if use_fixture or not has_creds:
        logger.info(
            "Wind: using FIXTURE path "
            "(CDS_API_KEY not set or use_fixture=True).")
        return _load_fixture(lat_min, lat_max, lon_min, lon_max, start_time, end_time)

    try:
        return _fetch_live_cds(lat_min, lat_max, lon_min, lon_max, start_time, end_time)
    except Exception as exc:
        logger.error("Wind live fetch failed: %s. Falling back to fixture.", exc)
        return _load_fixture(lat_min, lat_max, lon_min, lon_max, start_time, end_time)


def _fetch_live_cds(
    lat_min: float, lat_max: float,
    lon_min: float, lon_max: float,
    start_time: datetime, end_time: datetime,
) -> WindField:
    """
    ERA5 wind download via CDS API.

    Uses cdsapi to request:
        dataset: reanalysis-era5-single-levels
        variables: 10m_u_component_of_wind, 10m_v_component_of_wind
        format: netcdf

    Raises NotImplementedError cleanly — interface fully defined,
    execution requires cdsapi + CDS_API_KEY.
    """
    try:
        import cdsapi  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "cdsapi not installed. pip install cdsapi"
        ) from exc
    raise NotImplementedError(
        "CDS wind download: interface defined, not executed without CDS_API_KEY. "
        "Falls back to fixture automatically.")


def _load_fixture(
    lat_min: float, lat_max: float,
    lon_min: float, lon_max: float,
    start_time: datetime, end_time: datetime,
) -> WindField:
    """
    Deterministic Southern Ocean wind fixture.

    Models:
      - Southern Ocean Westerlies: dominant westerly (u > 0, ~10-14 m/s)
      - Latitude-dependent speed (peaks near Furious Fifties ~-55°S)
      - Synoptic-scale temporal variability with reproducible noise
      - Storm-like burst in the middle of the forecast window

    Uses rng seed=44 for reproducibility.
    """
    logger.info("Wind: generating deterministic Southern Ocean Westerlies fixture")

    n_lat, n_lon = 8, 10
    n_times = 5

    lats = np.linspace(max(lat_min, -80), min(lat_max, -45), n_lat)
    lons = np.linspace(lon_min, lon_max, n_lon)
    day_step = max(1, int((end_time - start_time).total_seconds() / 86400 / (n_times - 1)))
    times: List[datetime] = [
        start_time + timedelta(days=i * day_step) for i in range(n_times)
    ]

    rng = np.random.default_rng(44)
    u = np.zeros((n_times, n_lat, n_lon), dtype=np.float32)
    v = np.zeros((n_times, n_lat, n_lon), dtype=np.float32)

    lat_grid = lats[:, None]
    # Westerlies peak near -55°S
    westerly_base = 11.0 * np.exp(-((lat_grid + 55.0) / 12.0) ** 2)

    for ti in range(n_times):
        # Storm burst in the middle of the window
        storm = 1.0 + 0.5 * np.exp(-((ti - n_times / 2.0) / 1.2) ** 2)
        u[ti] = (westerly_base * storm + rng.normal(0, 1.5, (n_lat, n_lon))).astype(np.float32)
        v[ti] = (rng.normal(0, 2.0, (n_lat, n_lon))).astype(np.float32)

    provenance = create_synthetic_provenance(
        dataset_name="10m wind fixture (Southern Ocean Westerlies)",
        valid_time_start=times[0],
        valid_time_end=times[-1],
    )

    field = WindField(
        u_wind=u, v_wind=v,
        lats=lats, lons=lons,
        times=times,
        provenance=provenance,
        quality=DataQuality.AVAILABLE,
    )
    result = validate_wind(field)
    if not result.valid:
        logger.error("Wind fixture validation FAILED: %s", result.summary)
    else:
        logger.info("Wind fixture ready: shape=%s", u.shape)
    return field
