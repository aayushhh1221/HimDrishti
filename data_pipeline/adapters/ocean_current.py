"""
data_pipeline/adapters/ocean_current.py
-----------------------------------------
Ocean surface current adapter.
SIH 2026 · PS 26059

LIVE SOURCE TARGET:
    Copernicus Marine Physics Analysis (CMEMS GLORYS12 / PHYS Analysis)
    Variables: uo (eastward_sea_water_velocity), vo (northward_sea_water_velocity)
    Units: m/s at surface (depth=0.49m nominal first level)

LIVE ACCESS REQUIREMENT:
    CMEMS_USERNAME, CMEMS_PASSWORD environment variables.
    Package: copernicusmarine (pip install copernicusmarine)

FIXTURE PATH (always available):
    Deterministic Southern Ocean surface current fixture —
    models the Antarctic Circumpolar Current (ACC) structure with
    an approximate eastward baseline and meridional variability.
    Clearly labelled SYNTHETIC in provenance.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List

import numpy as np

from ..provenance import create_synthetic_provenance
from ..schemas import DataQuality, DataSource, OceanCurrentField
from ..validation import validate_ocean_current

logger = logging.getLogger(__name__)


def fetch_ocean_current(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    start_time: datetime,
    end_time: datetime,
    use_fixture: bool = False,
) -> OceanCurrentField:
    """
    Fetch surface ocean currents for the given window.

    Falls back to fixture if credentials are absent or use_fixture=True.
    Never fabricates data silently.
    """
    has_creds = (
        os.environ.get("CMEMS_USERNAME") and
        os.environ.get("CMEMS_PASSWORD"))

    if use_fixture or not has_creds:
        logger.info(
            "Ocean current: using FIXTURE path "
            "(CMEMS_USERNAME/CMEMS_PASSWORD not set or use_fixture=True).")
        return _load_fixture(lat_min, lat_max, lon_min, lon_max, start_time, end_time)

    try:
        return _fetch_live_cmems(lat_min, lat_max, lon_min, lon_max, start_time, end_time)
    except Exception as exc:
        logger.error("Ocean current live fetch failed: %s. Falling back to fixture.", exc)
        return _load_fixture(lat_min, lat_max, lon_min, lon_max, start_time, end_time)


def _fetch_live_cmems(
    lat_min: float, lat_max: float,
    lon_min: float, lon_max: float,
    start_time: datetime, end_time: datetime,
) -> OceanCurrentField:
    """
    CMEMS live ocean current download.

    Target product: cmems_mod_glo_phy_anfc_0.083deg_P1D-m
    Variables: uo, vo at depth level 0 (surface ~0.49m)

    Raises NotImplementedError cleanly without fabricating data.
    The interface is fully defined and ready for integration when
    credentials and copernicusmarine package are available.
    """
    try:
        import copernicusmarine  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "copernicusmarine not installed. pip install copernicusmarine"
        ) from exc
    raise NotImplementedError(
        "CMEMS ocean current live download: interface defined, not executed "
        "without credentials. Falls back to fixture.")


def _load_fixture(
    lat_min: float, lat_max: float,
    lon_min: float, lon_max: float,
    start_time: datetime, end_time: datetime,
) -> OceanCurrentField:
    """
    Deterministic Southern Ocean current fixture.

    Models:
      - Antarctic Circumpolar Current (ACC): dominant eastward u ~0.30 m/s
      - Latitudinal shear: current speed peaks near -55°S
      - Weak northward v component with realistic noise
      - Slow temporal drift over the forecast window

    Uses rng seed=43 for reproducibility.
    """
    logger.info("Ocean current: generating deterministic synthetic fixture (ACC-like)")

    n_lat, n_lon = 8, 10
    n_times = 5

    lats = np.linspace(max(lat_min, -80), min(lat_max, -55), n_lat)
    lons = np.linspace(lon_min, lon_max, n_lon)
    day_step = max(1, int((end_time - start_time).total_seconds() / 86400 / (n_times - 1)))
    times: List[datetime] = [
        start_time + timedelta(days=i * day_step) for i in range(n_times)
    ]

    rng = np.random.default_rng(43)
    u = np.zeros((n_times, n_lat, n_lon), dtype=np.float32)
    v = np.zeros((n_times, n_lat, n_lon), dtype=np.float32)

    lat_grid = lats[:, None]  # broadcast over lon
    # ACC: stronger near -55°S, weaker poleward
    acc_base = 0.30 * np.exp(-((lat_grid + 60.0) / 8.0) ** 2)

    for ti in range(n_times):
        drift = 1.0 + 0.05 * ti / max(n_times - 1, 1)
        u[ti] = (acc_base * drift + rng.normal(0, 0.04, (n_lat, n_lon))).astype(np.float32)
        v[ti] = (rng.normal(0, 0.06, (n_lat, n_lon))).astype(np.float32)

    provenance = create_synthetic_provenance(
        dataset_name="Ocean surface current fixture (Southern Ocean / ACC-like)",
        valid_time_start=times[0],
        valid_time_end=times[-1],
    )

    field = OceanCurrentField(
        u_current=u, v_current=v,
        lats=lats, lons=lons,
        times=times, depth_m=0.49,
        provenance=provenance,
        quality=DataQuality.AVAILABLE,
    )
    result = validate_ocean_current(field)
    if not result.valid:
        logger.error("Ocean current fixture validation FAILED: %s", result.summary)
    else:
        logger.info("Ocean current fixture ready: shape=%s", u.shape)
    return field
