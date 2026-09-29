"""
data_pipeline/data_mode.py
---------------------------
Data mode management for HimDrishti.
SIH 2026 · PS 26059

Controls whether the pipeline runs in:

  SYNTHETIC_DEMO  — deterministic fixtures (always available, no credentials)
  RESEARCH_DATA   — real public environmental datasets (requires credentials
                    or public API access; honest failure if unavailable)

The active mode is controlled by:
  1. HIMDRISHTI_DATA_MODE environment variable  (highest priority)
     Values: "SYNTHETIC_DEMO" | "RESEARCH_DATA"
  2. Default: "SYNTHETIC_DEMO" (safe baseline)

NEVER silently substitute synthetic data when RESEARCH_DATA is requested.
If research data are unavailable, report RESEARCH_DATA_UNAVAILABLE status.
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DataMode(str, Enum):
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    RESEARCH_DATA = "RESEARCH_DATA"


class ResearchDataStatus(str, Enum):
    """Status of each research data source when in RESEARCH_DATA mode."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"      # credentials absent or source unreachable
    PARTIAL = "PARTIAL"              # some variables/times available
    FAILED = "FAILED"                # access attempted but errored
    CREDENTIAL_MISSING = "CREDENTIAL_MISSING"
    FALLING_BACK_TO_FIXTURE = "FALLING_BACK_TO_FIXTURE"


def get_active_mode() -> DataMode:
    """
    Return the currently active data mode.

    Reads HIMDRISHTI_DATA_MODE environment variable.
    Defaults to SYNTHETIC_DEMO if not set or unrecognised.

    NEVER defaults silently to RESEARCH_DATA — that would risk
    presenting fixture data as if it were live data.
    """
    raw = os.environ.get("HIMDRISHTI_DATA_MODE", "SYNTHETIC_DEMO").strip().upper()
    if raw == DataMode.RESEARCH_DATA.value:
        logger.info("Data mode: RESEARCH_DATA (from HIMDRISHTI_DATA_MODE env var)")
        return DataMode.RESEARCH_DATA
    if raw != DataMode.SYNTHETIC_DEMO.value:
        logger.warning(
            "Unrecognised HIMDRISHTI_DATA_MODE='%s' — defaulting to SYNTHETIC_DEMO", raw)
    return DataMode.SYNTHETIC_DEMO


def is_research_mode() -> bool:
    """Return True if currently in RESEARCH_DATA mode."""
    return get_active_mode() == DataMode.RESEARCH_DATA


def check_sea_ice_credentials() -> Dict[str, object]:
    """
    Check availability of sea-ice data credentials.
    Returns status dict — never raises.
    """
    has_earthdata = bool(
        os.environ.get("EARTHDATA_USERNAME") and
        os.environ.get("EARTHDATA_PASSWORD"))
    has_cmems = bool(
        os.environ.get("CMEMS_USERNAME") and
        os.environ.get("CMEMS_PASSWORD"))
    return {
        "earthdata_available": has_earthdata,
        "cmems_available": has_cmems,
        "any_available": has_earthdata or has_cmems,
        "status": (
            ResearchDataStatus.AVAILABLE.value
            if (has_earthdata or has_cmems)
            else ResearchDataStatus.CREDENTIAL_MISSING.value
        ),
        "note": (
            "Set EARTHDATA_USERNAME+EARTHDATA_PASSWORD or "
            "CMEMS_USERNAME+CMEMS_PASSWORD for live sea-ice access."
            if not (has_earthdata or has_cmems)
            else "Credentials found."
        ),
    }


def check_wind_credentials() -> Dict[str, object]:
    """Check CDS API key availability for ERA5/wind data."""
    has_cds = bool(os.environ.get("CDS_API_KEY"))
    return {
        "cds_available": has_cds,
        "any_available": has_cds,
        "status": (
            ResearchDataStatus.AVAILABLE.value
            if has_cds
            else ResearchDataStatus.CREDENTIAL_MISSING.value
        ),
        "note": (
            "Set CDS_API_KEY (format: UID:API_KEY) for ERA5/CDS wind access."
            if not has_cds
            else "CDS_API_KEY found."
        ),
    }


def check_ocean_credentials() -> Dict[str, object]:
    """Check CMEMS credentials for ocean current data."""
    has_cmems = bool(
        os.environ.get("CMEMS_USERNAME") and
        os.environ.get("CMEMS_PASSWORD"))
    return {
        "cmems_available": has_cmems,
        "any_available": has_cmems,
        "status": (
            ResearchDataStatus.AVAILABLE.value
            if has_cmems
            else ResearchDataStatus.CREDENTIAL_MISSING.value
        ),
        "note": (
            "Set CMEMS_USERNAME+CMEMS_PASSWORD for live ocean current access."
            if not has_cmems
            else "CMEMS credentials found."
        ),
    }


def check_iceberg_credentials() -> Dict[str, object]:
    """
    NIC iceberg data is public (no credentials required).
    Network access is required.
    """
    return {
        "any_available": True,
        "status": ResearchDataStatus.AVAILABLE.value,
        "note": (
            "USNIC NIC large iceberg data is public. "
            "Network access required (10s timeout). "
            "Falls back to fixture if unreachable."
        ),
    }


def get_full_data_status() -> Dict[str, object]:
    """
    Return comprehensive data availability status for all sources.
    Used by /api/v1/data-status endpoint.
    """
    mode = get_active_mode()
    sea_ice_creds = check_sea_ice_credentials()
    wind_creds = check_wind_credentials()
    ocean_creds = check_ocean_credentials()
    iceberg_creds = check_iceberg_credentials()

    return {
        "active_mode": mode.value,
        "sources": {
            "sea_ice": {
                "mode": mode.value,
                "target_dataset": (
                    "NSIDC SSMIS Antarctic Sea Ice Concentration (NSIDC-0081) "
                    "or Copernicus Marine siconc product"
                ),
                "target_organisation": "NOAA / NSIDC or Copernicus Marine Service",
                "target_variables": ["siconc"],
                "target_spatial_resolution_km": 25.0,
                "target_temporal_resolution_h": 24.0,
                "credentials_status": sea_ice_creds["status"],
                "credentials_note": sea_ice_creds["note"],
                "fallback": "Deterministic Southern Ocean fixture (seed=42)",
                "fallback_available": True,
            },
            "ocean_current": {
                "mode": mode.value,
                "target_dataset": "CMEMS GLORYS12 / Global Ocean Physics Analysis",
                "target_organisation": "Copernicus Marine Service",
                "target_variables": ["uo", "vo"],
                "target_spatial_resolution_km": 8.3,
                "target_temporal_resolution_h": 24.0,
                "credentials_status": ocean_creds["status"],
                "credentials_note": ocean_creds["note"],
                "fallback": "Deterministic ACC-like fixture (seed=43)",
                "fallback_available": True,
            },
            "wind": {
                "mode": mode.value,
                "target_dataset": "ECMWF ERA5 reanalysis / IFS forecast (via CDS)",
                "target_organisation": "ECMWF",
                "target_variables": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
                "target_spatial_resolution_km": 31.0,
                "target_temporal_resolution_h": 1.0,
                "credentials_status": wind_creds["status"],
                "credentials_note": wind_creds["note"],
                "fallback": "Deterministic Southern Ocean Westerlies fixture (seed=44)",
                "fallback_available": True,
            },
            "icebergs": {
                "mode": mode.value,
                "target_dataset": "USNIC NIC Antarctic Large Iceberg Tracking (public CSV)",
                "target_organisation": "US National Ice Center",
                "target_variables": ["latitude", "longitude", "length", "width"],
                "target_spatial_resolution_km": None,
                "target_temporal_resolution_h": 168.0,  # ~weekly
                "credentials_status": iceberg_creds["status"],
                "credentials_note": iceberg_creds["note"],
                "fallback": "Illustrative fixture (A-23A, C-19A, D-28 bergs)",
                "fallback_available": True,
            },
        },
        "synthetic_demo_available": True,
        "prototype_notice": (
            "SIH 2026 Prototype · PS 26059 · "
            "RESEARCH_DATA mode requires valid credentials and network access. "
            "SYNTHETIC_DEMO mode is always available without credentials. "
            "No data is fabricated — missing research data shows UNAVAILABLE status."
        ),
    }
