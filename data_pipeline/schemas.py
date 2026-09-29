"""
data_pipeline/schemas.py
--------------------------
Typed data contracts for the HimDrishti scientific pipeline.
SIH 2026 · PS 26059

Every dataset entering the pipeline must carry one of these contracts.
No raw numpy arrays are passed between pipeline stages without provenance.

Units convention:
    Wind / current velocities : m/s
    Concentration             : 0.0 – 1.0  (fraction, not percent or tenths)
    Coordinates               : degrees latitude / longitude (WGS-84)
    Timestamps                : UTC (datetime with tzinfo=timezone.utc)
    Ice dimensions            : metres
    Pressure                  : hPa
    Temperature               : Kelvin

Coordinate convention:
    Latitude  : positive north, range [-90, 90]
    Longitude : -180 to +180  (NOT 0-360)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Quality / status enumerations
# ---------------------------------------------------------------------------

class DataQuality(Enum):
    """Operational status of a dataset entering the pipeline."""
    AVAILABLE   = "available"    # data present, validated, ready for use
    STALE       = "stale"        # data present but older than expected cadence
    PARTIAL     = "partial"      # data present but spatial/temporal coverage is incomplete
    INVALID     = "invalid"      # data present but failed validation checks
    UNAVAILABLE = "unavailable"  # source did not respond or returned no data


class DataSource(Enum):
    """Canonical data source identifiers."""
    # Sea ice
    NSIDC_SSMI       = "NSIDC_SSMI"        # NSIDC SSMIS passive microwave
    COPERNICUS_SEAICE = "COPERNICUS_SEAICE" # Copernicus Marine sea-ice product
    SYNTHETIC        = "SYNTHETIC"          # deterministic demo/test fixture
    FIXTURE          = "FIXTURE"            # recorded real-data replay
    UNKNOWN          = "UNKNOWN"

    # Ocean
    CMEMS_PHY        = "CMEMS_PHY"          # Copernicus Marine Physics Analysis
    GLORYS           = "GLORYS"             # CMEMS GLORYS12 reanalysis

    # Atmosphere
    ECMWF_IFS        = "ECMWF_IFS"         # ECMWF Integrated Forecasting System
    ERA5             = "ERA5"               # ECMWF ERA5 reanalysis
    NCEP_GFS         = "NCEP_GFS"          # NOAA GFS

    # Iceberg
    USNIC_NIC        = "USNIC_NIC"          # US National Ice Center
    BYU_ICEBERG      = "BYU_ICEBERG"       # BYU/NSIDC iceberg tracking
    ALTIBERG         = "ALTIBERG"           # CNES Altiberg altimetry


# ---------------------------------------------------------------------------
# Forecast window
# ---------------------------------------------------------------------------

@dataclass
class ForecastWindow:
    """
    Describes the time window of a forecast or reanalysis product.
    All times must be UTC-aware datetimes.
    """
    reference_time: datetime    # T+0 anchor (analysis time)
    valid_times: List[datetime] # list of forecast valid-time stamps
    horizon_hours: List[float]  # [0, 24, 48, 72, 96, 120] etc.

    def __post_init__(self):
        if len(self.valid_times) != len(self.horizon_hours):
            raise ValueError(
                f"valid_times ({len(self.valid_times)}) and "
                f"horizon_hours ({len(self.horizon_hours)}) must match."
            )

    @property
    def max_horizon_h(self) -> float:
        return max(self.horizon_hours) if self.horizon_hours else 0.0

    @property
    def n_steps(self) -> int:
        return len(self.horizon_hours)


# ---------------------------------------------------------------------------
# Spatial grid descriptor
# ---------------------------------------------------------------------------

@dataclass
class SpatialGrid:
    """
    Describes the spatial grid of a dataset.
    All coordinates in WGS-84 degrees.
    """
    lat_min: float
    lat_max: float
    lon_min: float  # -180 to +180 convention
    lon_max: float
    lat_resolution_deg: float
    lon_resolution_deg: float
    n_lat: int
    n_lon: int
    coordinate_system: str = "WGS84"

    @property
    def coverage_description(self) -> str:
        return (
            f"lat [{self.lat_min:.1f}°, {self.lat_max:.1f}°] "
            f"lon [{self.lon_min:.1f}°, {self.lon_max:.1f}°] "
            f"@ {self.lat_resolution_deg:.2f}°×{self.lon_resolution_deg:.2f}°"
        )


# ---------------------------------------------------------------------------
# Provenance record
# ---------------------------------------------------------------------------

@dataclass
class DataProvenance:
    """
    Complete lineage record for a dataset entering the pipeline.
    Every SeaIceField, OceanCurrentField, WindField, and IcebergObservation
    must carry one of these.
    """
    source: DataSource
    dataset_name: str           # e.g. "NSIDC SSMI Sea Ice Concentration (passive microwave)"
    retrieved_at: datetime      # when the data was fetched / created (UTC)
    valid_time_start: datetime  # earliest valid observation/forecast time (UTC)
    valid_time_end: datetime    # latest valid observation/forecast time (UTC)
    spatial_coverage: str       # human-readable, e.g. "Southern Ocean 30°S–90°S"
    units: str                  # units of the primary variable
    coordinate_system: str = "WGS84"
    status: DataQuality = DataQuality.AVAILABLE
    notes: str = ""             # any additional provenance annotations


# ---------------------------------------------------------------------------
# Sea-ice field
# ---------------------------------------------------------------------------

@dataclass
class SeaIceField:
    """
    Sea-ice concentration field on a regular lat/lon grid.

    concentration : np.ndarray of shape (n_times, n_lat, n_lon)
                    Values normalized to [0.0, 1.0].
                    0.0 = open water; 1.0 = complete ice cover.
                    np.nan = missing / land / fill-value (do NOT substitute 0).
    lats          : np.ndarray shape (n_lat,), degrees north
    lons          : np.ndarray shape (n_lon,), degrees east (-180..+180)
    times         : list of UTC datetimes, length n_times
    provenance    : data lineage record
    """
    concentration: np.ndarray          # (n_times, n_lat, n_lon), float32 preferred
    lats: np.ndarray                   # (n_lat,)
    lons: np.ndarray                   # (n_lon,)
    times: List[datetime]
    provenance: DataProvenance
    quality: DataQuality = DataQuality.AVAILABLE

    def __post_init__(self):
        n_t = len(self.times)
        n_lat = len(self.lats)
        n_lon = len(self.lons)
        expected = (n_t, n_lat, n_lon)
        if self.concentration.shape != expected:
            raise ValueError(
                f"concentration shape {self.concentration.shape} does not match "
                f"(n_times={n_t}, n_lat={n_lat}, n_lon={n_lon})."
            )

    @property
    def n_times(self) -> int:
        return len(self.times)


# ---------------------------------------------------------------------------
# Ocean current field
# ---------------------------------------------------------------------------

@dataclass
class OceanCurrentField:
    """
    Ocean surface current field.

    u_current, v_current : np.ndarray shape (n_times, n_lat, n_lon)
                           Eastward (u) and northward (v) components.
                           Units: m/s.
    depth_m              : reference depth (typically surface or ~0m)
    """
    u_current: np.ndarray    # (n_times, n_lat, n_lon), m/s
    v_current: np.ndarray    # (n_times, n_lat, n_lon), m/s
    lats: np.ndarray         # (n_lat,)
    lons: np.ndarray         # (n_lon,)
    times: List[datetime]
    depth_m: float
    provenance: DataProvenance
    quality: DataQuality = DataQuality.AVAILABLE


# ---------------------------------------------------------------------------
# Wind field
# ---------------------------------------------------------------------------

@dataclass
class WindField:
    """
    10-metre wind field.

    u_wind, v_wind : np.ndarray shape (n_times, n_lat, n_lon)
                     Eastward (u) and northward (v) components.
                     Units: m/s at 10 m above surface.
    """
    u_wind: np.ndarray       # (n_times, n_lat, n_lon), m/s
    v_wind: np.ndarray       # (n_times, n_lat, n_lon), m/s
    lats: np.ndarray         # (n_lat,)
    lons: np.ndarray         # (n_lon,)
    times: List[datetime]
    provenance: DataProvenance
    quality: DataQuality = DataQuality.AVAILABLE


# ---------------------------------------------------------------------------
# Iceberg observation
# ---------------------------------------------------------------------------

@dataclass
class IcebergObservation:
    """
    A single iceberg positional observation.

    Fields marked Optional[float] may be unavailable in the source;
    they MUST remain None rather than being filled with a synthetic value.
    """
    iceberg_id: str
    latitude: float                     # degrees north
    longitude: float                    # degrees east (-180..+180)
    observed_at: datetime               # UTC
    length_m: Optional[float] = None    # along major axis
    width_m: Optional[float] = None
    height_above_water_m: Optional[float] = None
    draft_m: Optional[float] = None
    area_km2: Optional[float] = None
    position_uncertainty_km: Optional[float] = None
    source: DataSource = DataSource.UNKNOWN
    quality: DataQuality = DataQuality.AVAILABLE
    notes: str = ""


# ---------------------------------------------------------------------------
# Assembled pipeline input
# ---------------------------------------------------------------------------

@dataclass
class PipelineInput:
    """
    Assembled, validated, normalized input for one science pipeline run.
    All fields that are None indicate the data could not be obtained;
    the orchestrator must check completeness before running the science core.
    """
    forecast_window: ForecastWindow
    sea_ice: Optional[SeaIceField] = None
    ocean_current: Optional[OceanCurrentField] = None
    wind: Optional[WindField] = None
    icebergs: List[IcebergObservation] = field(default_factory=list)
    assembled_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """True only if all mandatory fields are present and not UNAVAILABLE."""
        if self.sea_ice is None or self.sea_ice.quality == DataQuality.UNAVAILABLE:
            return False
        if self.wind is None or self.wind.quality == DataQuality.UNAVAILABLE:
            return False
        if self.ocean_current is None or self.ocean_current.quality == DataQuality.UNAVAILABLE:
            return False
        return True

    @property
    def completeness_report(self) -> dict:
        return {
            "sea_ice": self.sea_ice.quality.value if self.sea_ice else "missing",
            "wind": self.wind.quality.value if self.wind else "missing",
            "ocean_current": self.ocean_current.quality.value if self.ocean_current else "missing",
            "n_icebergs": len(self.icebergs),
            "complete": self.is_complete,
        }
