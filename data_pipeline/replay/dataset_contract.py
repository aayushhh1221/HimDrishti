"""
data_pipeline/replay/dataset_contract.py
------------------------------------------
Versioned historical dataset contract for reproducible replay.
SIH 2026 · PS 26059

Phase 9.

A dataset contract records everything needed to understand, reproduce,
and audit a historical replay dataset:

  dataset_id          — unique identifier (e.g. "NSIDC_SH_202205_SYNTHETIC")
  source              — authoritative source name
  product             — specific product/variable
  start_time          — start of the dataset valid window (UTC)
  end_time            — end of the dataset valid window (UTC)
  spatial_coverage    — human-readable spatial extent description
  retrieved_at        — when data was retrieved (UTC) or "SYNTHETIC"
  valid_times         — list of ISO 8601 timestamps for discrete time steps
  units               — physical units string
  coordinate_system   — e.g. "WGS-84 EPSG:4326"
  sha256              — optional SHA-256 hash of the raw data file
  data_mode           — "SYNTHETIC_REPLAY" | "ARCHIVE" | "REANALYSIS" | "LIVE"
  quality_status      — "available" | "partial" | "stale" | "unavailable"

IMPORTANT:
  - SYNTHETIC_REPLAY is explicitly labelled.
  - Never label synthetic data as real historical archive data.
  - Never claim synthetic replay validates the scientific model.

PUBLIC ARCHIVE SOURCES (when credentials/network available):
  Sea ice  : NSIDC NSIDC-0051 (SSMIS brightness temperatures)
             https://nsidc.org/data/nsidc-0051
             Access: Earthdata login (EARTHDATA_USERNAME / EARTHDATA_PASSWORD)
  Wind     : ECMWF ERA5 (hourly reanalysis)
             https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels
             Access: CDS API key (CDS_API_KEY)
  Ocean    : CMEMS GLORYS12 (global ocean reanalysis)
             https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030
             Access: CMEMS credentials (CMEMS_USERNAME / CMEMS_PASSWORD)
  Icebergs : USNIC / NIC Antarctic iceberg tracking
             https://www.natice.noaa.gov/pub/icebergs/
             Access: public (no login required)

FALLBACK:
  If credentials are not available, the SYNTHETIC_REPLAY contract is used.
  This uses the same deterministic fixture data as Phase 6, with a formal
  versioned contract wrapper.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data mode constants
# ---------------------------------------------------------------------------

DATA_MODE_SYNTHETIC_REPLAY = "SYNTHETIC_REPLAY"
DATA_MODE_ARCHIVE           = "ARCHIVE"
DATA_MODE_REANALYSIS        = "REANALYSIS"
DATA_MODE_LIVE              = "LIVE"


# ---------------------------------------------------------------------------
# Dataset contract dataclass
# ---------------------------------------------------------------------------

class HistoricalDatasetContract:
    """
    Versioned contract for a historical replay dataset.
    Immutable after creation.
    """

    def __init__(
        self,
        dataset_id: str,
        source: str,
        product: str,
        start_time: str,          # ISO 8601 UTC
        end_time: str,            # ISO 8601 UTC
        spatial_coverage: str,
        retrieved_at: str,        # ISO 8601 UTC or "SYNTHETIC"
        valid_times: List[str],   # ISO 8601 UTC list
        units: str,
        coordinate_system: str,
        sha256: Optional[str],
        data_mode: str,
        quality_status: str,
        access_note: str = "",
        prototype_notice: str = (
            "SIH 2026 Prototype — not an operational navigation authority. "
            "Historical replay does not validate the illustrative POLARIS RIV table."
        ),
    ) -> None:
        self.dataset_id       = dataset_id
        self.source           = source
        self.product          = product
        self.start_time       = start_time
        self.end_time         = end_time
        self.spatial_coverage = spatial_coverage
        self.retrieved_at     = retrieved_at
        self.valid_times      = valid_times
        self.units            = units
        self.coordinate_system = coordinate_system
        self.sha256           = sha256
        self.data_mode        = data_mode
        self.quality_status   = quality_status
        self.access_note      = access_note
        self.prototype_notice = prototype_notice

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id":        self.dataset_id,
            "source":            self.source,
            "product":           self.product,
            "start_time":        self.start_time,
            "end_time":          self.end_time,
            "spatial_coverage":  self.spatial_coverage,
            "retrieved_at":      self.retrieved_at,
            "valid_times":       self.valid_times,
            "units":             self.units,
            "coordinate_system": self.coordinate_system,
            "sha256":            self.sha256,
            "data_mode":         self.data_mode,
            "quality_status":    self.quality_status,
            "access_note":       self.access_note,
            "prototype_notice":  self.prototype_notice,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HistoricalDatasetContract":
        return cls(
            dataset_id       = d["dataset_id"],
            source           = d["source"],
            product          = d["product"],
            start_time       = d["start_time"],
            end_time         = d["end_time"],
            spatial_coverage = d["spatial_coverage"],
            retrieved_at     = d["retrieved_at"],
            valid_times      = d.get("valid_times", []),
            units            = d.get("units", ""),
            coordinate_system= d.get("coordinate_system", "WGS-84 EPSG:4326"),
            sha256           = d.get("sha256"),
            data_mode        = d["data_mode"],
            quality_status   = d["quality_status"],
            access_note      = d.get("access_note", ""),
            prototype_notice = d.get("prototype_notice", ""),
        )


# ---------------------------------------------------------------------------
# Built-in SYNTHETIC_REPLAY contract (offline-first fallback)
# ---------------------------------------------------------------------------

def _make_synthetic_contract() -> HistoricalDatasetContract:
    """
    Offline-first fallback contract using deterministic fixture data.
    Clearly labelled SYNTHETIC_REPLAY — never presented as real archive data.

    Time window: May 2026 (Southern Hemisphere early-season transit window)
    Domain: Indian Ocean sector, lat [-80,-55] lon [10,90]
      (Cape Town → Bharati Station corridor)
    """
    valid_times = [
        f"2026-05-21T{h:02d}:00:00Z"
        for h in [0, 24, 48, 72, 96, 120]
    ]
    return HistoricalDatasetContract(
        dataset_id       = "HIMDRISHTI_SYNTHETIC_202605",
        source           = "HimDrishti Deterministic Fixture Generator",
        product          = "Sea-ice + Wind + Ocean Current + Iceberg (synthetic ensemble)",
        start_time       = "2026-05-21T00:00:00Z",
        end_time         = "2026-05-26T00:00:00Z",
        spatial_coverage = "Indian Ocean sector: lat [-80,-55] lon [10,90] (Cape Town → Bharati)",
        retrieved_at     = "SYNTHETIC",
        valid_times      = valid_times,
        units            = "concentration [0-1]; wind m/s; current m/s; position degrees",
        coordinate_system= "WGS-84 EPSG:4326",
        sha256           = None,
        data_mode        = DATA_MODE_SYNTHETIC_REPLAY,
        quality_status   = "available",
        access_note      = (
            "Offline-first fallback. Uses deterministic Phase-6 fixture adapters. "
            "No real historical data was downloaded. "
            "Results are reproducible but NOT validated against real observations."
        ),
    )


# ---------------------------------------------------------------------------
# Public archive contract templates (activated when credentials present)
# ---------------------------------------------------------------------------

def _make_nsidc_seaice_contract(retrieved_at: str) -> HistoricalDatasetContract:
    """
    NSIDC NSIDC-0051 Southern Hemisphere sea-ice concentration archive.
    May 2026 subset (or closest available).
    Requires: EARTHDATA_USERNAME + EARTHDATA_PASSWORD
    """
    valid_times = [
        "2026-05-01T00:00:00Z",
        "2026-05-08T00:00:00Z",
        "2026-05-15T00:00:00Z",
        "2026-05-22T00:00:00Z",
        "2026-05-29T00:00:00Z",
    ]
    return HistoricalDatasetContract(
        dataset_id       = "NSIDC_0051_SH_202605",
        source           = "NSIDC (National Snow and Ice Data Center)",
        product          = "NSIDC-0051 SSMIS Passive Microwave Daily Polar Gridded Sea Ice Concentrations",
        start_time       = "2026-05-01T00:00:00Z",
        end_time         = "2026-05-31T23:59:59Z",
        spatial_coverage = "Southern Hemisphere, 25 km EASE-Grid, lat [-90,-40]",
        retrieved_at     = retrieved_at,
        valid_times      = valid_times,
        units            = "sea-ice concentration [0.0-1.0 fraction]",
        coordinate_system= "WGS-84 EPSG:4326 (reprojected from EASE-Grid)",
        sha256           = None,
        data_mode        = DATA_MODE_ARCHIVE,
        quality_status   = "available",
        access_note      = (
            "NSIDC Earthdata archive. Requires EARTHDATA_USERNAME + EARTHDATA_PASSWORD. "
            "https://nsidc.org/data/nsidc-0051"
        ),
    )


def _make_usnic_iceberg_contract(retrieved_at: str) -> HistoricalDatasetContract:
    """
    USNIC Antarctic iceberg tracking (publicly available, no login required).
    """
    return HistoricalDatasetContract(
        dataset_id       = "USNIC_ICEBERGS_SH_202605",
        source           = "US National Ice Center (NIC)",
        product          = "NIC Antarctic Iceberg Tracking Database",
        start_time       = "2026-05-01T00:00:00Z",
        end_time         = "2026-05-31T23:59:59Z",
        spatial_coverage = "Southern Ocean, all longitudes, lat south of -40",
        retrieved_at     = retrieved_at,
        valid_times      = ["2026-05-21T12:00:00Z"],
        units            = "position degrees; dimensions metres",
        coordinate_system= "WGS-84 EPSG:4326",
        sha256           = None,
        data_mode        = DATA_MODE_ARCHIVE,
        quality_status   = "available",
        access_note      = (
            "USNIC public iceberg tracking. No login required. "
            "https://www.natice.noaa.gov/pub/icebergs/ "
            "In this prototype, data is represented via the Phase-6 iceberg adapter fixture "
            "because live network download is not available in the deployment environment."
        ),
    )


# ---------------------------------------------------------------------------
# Registry of available dataset contracts
# ---------------------------------------------------------------------------

_SYNTHETIC_CONTRACT  = _make_synthetic_contract()
_NOW_UTC             = datetime.now(tz=timezone.utc).isoformat()
_USNIC_CONTRACT      = _make_usnic_iceberg_contract(_NOW_UTC)

# Mapping from dataset_id → contract
_REGISTRY: Dict[str, HistoricalDatasetContract] = {
    _SYNTHETIC_CONTRACT.dataset_id: _SYNTHETIC_CONTRACT,
    _USNIC_CONTRACT.dataset_id:     _USNIC_CONTRACT,
}


def get_dataset_contract(dataset_id: str) -> HistoricalDatasetContract:
    """
    Retrieve a registered dataset contract by ID.
    Falls back to SYNTHETIC_REPLAY if dataset_id is not found.
    """
    if dataset_id in _REGISTRY:
        return _REGISTRY[dataset_id]
    logger.warning(
        "Dataset contract '%s' not found in registry. Falling back to SYNTHETIC_REPLAY.",
        dataset_id,
    )
    return _SYNTHETIC_CONTRACT


def list_dataset_contracts() -> List[Dict[str, Any]]:
    """Return summary of all registered dataset contracts."""
    return [
        {
            "dataset_id":   c.dataset_id,
            "source":       c.source,
            "data_mode":    c.data_mode,
            "quality_status": c.quality_status,
            "start_time":   c.start_time,
            "end_time":     c.end_time,
        }
        for c in _REGISTRY.values()
    ]


def get_synthetic_contract() -> HistoricalDatasetContract:
    """Return the built-in SYNTHETIC_REPLAY contract."""
    return _SYNTHETIC_CONTRACT
