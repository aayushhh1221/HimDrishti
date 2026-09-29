# HimDrishti — Data Pipeline Architecture
**SIH 2026 · PS 26059**

> **PROTOTYPE NOTICE**: This document describes a hackathon-grade pipeline
> foundation. Scientific models, data sources, and regulatory constants are
> illustrative. No operational decisions should be made from this prototype.

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Adapters](#adapters)
4. [Data Schemas](#data-schemas)
5. [Validation Layer](#validation-layer)
6. [Normalization Layer](#normalization-layer)
7. [Provenance](#provenance)
8. [Cache](#cache)
9. [Replay](#replay)
10. [Pipeline Orchestrator](#pipeline-orchestrator)
11. [Synthetic vs Real Data](#synthetic-vs-real-data)
12. [Real Data Access Status](#real-data-access-status)
13. [Known Limitations](#known-limitations)
14. [How to Run the Pipeline](#how-to-run-the-pipeline)

---

## Overview

The data pipeline transforms raw public environmental data into normalized,
validated scientific inputs for the HimDrishti route-planning engine:

```
Public Data Sources                 Science Core
─────────────────────               ─────────────────────
NSIDC / Copernicus Marine           iceberg_drift.py
   (Sea Ice Concentration)               ↓
CMEMS GLORYS / PHYS Analysis   →    polaris_risk.py
   (Ocean Currents)                      ↓
ECMWF ERA5 / IFS               →    route_search.py
   (Wind Forecast)                       ↓
USNIC NIC / BYU / Altiberg     →    PipelineResult
   (Iceberg Observations)
```

---

## Architecture

```
data_pipeline/
├── __init__.py          Package entry point
├── schemas.py           Typed data contracts (dataclasses)
├── validation.py        Pre-processing validation rules
├── normalization.py     Unit/coordinate/NaN normalization
├── provenance.py        Lineage record creation + serialization
├── pipeline.py          Orchestrator (calls ai/*.py modules)
│
├── adapters/
│   ├── sea_ice.py       Sea-ice concentration adapter
│   ├── ocean_current.py Ocean surface current adapter
│   ├── wind.py          Wind forecast adapter
│   └── iceberg.py       Iceberg observation adapter
│
├── cache/
│   └── __init__.py      Local SHA-256 verified file cache
│
└── replay/
    └── __init__.py      Deterministic historical replay system
```

---

## Adapters

### Sea Ice — `adapters/sea_ice.py`
| Property | Value |
|----------|-------|
| Live target | Copernicus Marine `cmems_mod_glo_phy_anfc_0.083deg_P1D-m` |
| Variable | `siconc` (sea-ice area fraction) |
| Units | fraction 0.0–1.0 |
| Credentials | `CMEMS_USERNAME`, `CMEMS_PASSWORD` env vars |
| Package | `copernicusmarine` |
| Fallback | Deterministic synthetic fixture (seed=42) |

### Ocean Current — `adapters/ocean_current.py`
| Property | Value |
|----------|-------|
| Live target | CMEMS GLORYS12 / PHYS Analysis `uo`, `vo` at surface |
| Units | m/s |
| Credentials | `CMEMS_USERNAME`, `CMEMS_PASSWORD` env vars |
| Fallback | ACC-like fixture (seed=43) |

### Wind — `adapters/wind.py`
| Property | Value |
|----------|-------|
| Live target | ERA5 `reanalysis-era5-single-levels` `u10`, `v10` |
| Units | m/s at 10m |
| Credentials | `CDS_API_KEY` env var |
| Package | `cdsapi` |
| Fallback | Southern Westerlies fixture (seed=44) |

### Iceberg — `adapters/iceberg.py`
| Property | Value |
|----------|-------|
| Live target | USNIC Antarctic Iceberg CSV (no auth required) |
| URL | `https://usicecenter.gov/File/DownloadProduct?...` |
| Fallback | Illustrated NIC historical berg IDs (A-23A, C-19A, D-28) |
| Missing fields | Left as `None` — never fabricated |

---

## Data Schemas

All datasets are typed dataclasses in `schemas.py`:

| Schema | Description |
|--------|-------------|
| `SeaIceField` | concentration array + lats + lons + times + provenance |
| `OceanCurrentField` | u_current, v_current + spatial/temporal coords |
| `WindField` | u_wind, v_wind + spatial/temporal coords |
| `IcebergObservation` | single berg: position + optional dimensions |
| `ForecastWindow` | reference time + valid times + horizon hours |
| `DataProvenance` | full lineage: source, dataset, times, coverage, units, status |
| `PipelineInput` | assembled, validated input ready for science core |

`DataQuality` enum states: `AVAILABLE | STALE | PARTIAL | INVALID | UNAVAILABLE`

---

## Validation Layer

`validation.py` — checked before any scientific processing:

| Check | Rule |
|-------|------|
| Concentration | 0.0 ≤ value ≤ 1.0 (NaN = missing, accepted) |
| Wind/current | finite, |value| ≤ 100 m/s (wind) / 5 m/s (current) |
| Coordinates | lat ∈ [-90, 90], lon ∈ [-180, 180] |
| Iceberg dimensions | positive if present; `None` if unknown |
| Timestamps | UTC-aware, monotonically increasing |
| Forecast | non-negative horizons, strictly increasing |

> **Rule**: Validation **never** silently repairs invalid data.
> Invalid concentration becomes `NaN`, not `0`.

---

## Normalization Layer

`normalization.py`:

| Function | Purpose |
|----------|---------|
| `normalize_longitude()` | 0-360 → -180/+180 |
| `normalize_lat_order()` | ensure ascending south→north |
| `replace_fill_value()` | known fill value → NaN (logged) |
| `mask_invalid_concentration()` | out-of-range → NaN (logged, NOT 0) |
| `percent_to_fraction()` | 0-100% → 0.0-1.0 |
| `tenths_to_fraction()` | 0-10 tenths → 0.0-1.0 |
| `extract_wind_series_at_point()` | nearest-neighbour time series for iceberg forcing |
| `sea_ice_to_model_grid()` | regrid SeaIceField to route-search model grid |

The **only** NaN→0 substitution: `sea_ice_to_model_grid()` after regridding,
explicitly documented as "open water assumption" and logged with source name.

---

## Provenance

`provenance.py` — every dataset carries a `DataProvenance` record:

```python
DataProvenance(
    source=DataSource.NSIDC_SSMI,
    dataset_name="NSIDC SSMI Sea Ice Concentration",
    retrieved_at=datetime(2026, 5, 21, 0, 0, tzinfo=utc),
    valid_time_start=...,
    valid_time_end=...,
    spatial_coverage="Southern Ocean 60°S–90°S",
    units="fraction 0.0–1.0",
    coordinate_system="WGS84",
    status=DataQuality.AVAILABLE,
)
```

`provenance_to_dict()` serializes to a JSON-compatible dict — the backend
contract for the Phase 5 Data Provenance UI panel. Connected in Phase 7.

---

## Cache

`cache/__init__.py` — local deterministic filesystem cache:

```
data/cache/
    sea_ice/<16-char-hex-key>.npy
    sea_ice/<16-char-hex-key>.meta.json
    wind/...
    ocean_current/...
```

Features:
- Deterministic keys from (source, lat/lon bounds, time window)
- SHA-256 checksum verification on read
- Metadata sidecar with provenance + retrieval time
- No accidental overwrite (`force=True` required)
- No credentials stored in cache
- Override cache root: `HIMDRISHTI_CACHE_DIR` env var

---

## Replay

`replay/__init__.py` — reproducible historical runs:

```
data/historical_replay/<run_id>/
    manifest.json      — provenance + config + seed + software version
    sea_ice.npy        — normalized array
    wind.npy           — [u, v] stack
    current.npy        — [u, v] stack
    icebergs.json      — serialized IcebergObservation list
    output_digest.json — science output hashes for change detection
```

Guarantee: same `manifest.json` + same code + same seed → same route output.

---

## Pipeline Orchestrator

`pipeline.py` — `HimDrishtiPipeline.run(PipelineInput) → PipelineResult`

Stages:
1. Completeness check (fails safely if mandatory input missing)
2. Provenance collection
3. Sea ice → model grid (`sea_ice_to_model_grid`)
4. Wind/current extraction at iceberg position
5. Iceberg drift ensemble (`ensemble_drift`)
6. Probabilistic hazard field construction
7. Route search × 2 operating points (`find_route`)

The orchestrator contains **no scientific formulas** — it calls `ai/*.py` modules.

---

## Synthetic vs Real Data

| | Synthetic demo | Fixture (replay) | Live real data |
|-|---------------|-----------------|----------------|
| Source | Deterministic RNG | Recorded real data | Public APIs |
| Provenance label | `[SYNTHETIC DEMO]` | `[FIXTURE]` | Source name |
| Credentials needed | No | No | Yes |
| Reproducible | Yes (seed=42–44) | Yes (checksummed) | No |
| Used for | Tests / demo | Integration tests | Production |

**NEVER** mix synthetic and real data silently. The provenance record always
identifies the data origin.

---

## Real Data Access Status

| Source | Access in this environment | Reason |
|--------|---------------------------|--------|
| Copernicus Marine (CMEMS) | ❌ Unavailable | `CMEMS_USERNAME`/`CMEMS_PASSWORD` not set |
| NSIDC SSMI | ❌ Unavailable | `EARTHDATA_USERNAME`/`EARTHDATA_PASSWORD` not set |
| ERA5 via CDS | ❌ Unavailable | `CDS_API_KEY` not set |
| USNIC NIC CSV | ✅ Attempted | Public endpoint, no auth — network dependent |

All adapters implement the interface fully. Live access is deferred to when
credentials are set. Fixture data is always available as a fallback.

---

## Known Limitations

1. **Coordinate system**: Pipeline uses WGS-84 lat/lon throughout. The science
   core uses local planar metres. The `sea_ice_to_model_grid` bridge is a
   nearest-neighbour approximation, not a proper polar-stereographic projection.

2. **Spatial resolution**: Fixtures use 8–10 × 10–12 cell grids. Real SSMI
   data is 25 km resolution (~432×360 cells for full Antarctic domain).

3. **Ice-type classification**: `concentration_to_regime()` collapses a single
   concentration value into one of three ice types. Real POLARIS requires
   full WMO ice-type composition from an ice chart or SAR classification.

4. **No temporal interpolation**: Forcing time series are tiled if too short.
   Production should interpolate properly between forecast time steps.

5. **NIC iceberg fixture**: Positions are illustrative (based on historical
   NIC records), not current real-time positions. A production system should
   poll the live NIC CSV or Altiberg API every 6–12 hours.

6. **POLARIS RIV table**: `RISK_INDEX_VALUES` in `polaris_risk.py` is an
   illustrative placeholder. Authoritative values must come from IMO
   MSC.1/Circ.1519, not from this codebase.

---

## How to Run the Pipeline

### Demo (always works, no credentials)
```bash
python demo/demo_run.py
# Output: demo/toy_scenario_output.png + printed route costs
```

### Tests
```bash
pytest tests/test_data_pipeline.py -v
```

### Pipeline with fixture data
```python
from datetime import datetime, timezone
from data_pipeline.adapters.sea_ice import fetch_sea_ice
from data_pipeline.adapters.wind import fetch_wind
from data_pipeline.adapters.ocean_current import fetch_ocean_current
from data_pipeline.adapters.iceberg import fetch_icebergs
from data_pipeline.schemas import ForecastWindow, PipelineInput
from data_pipeline.pipeline import HimDrishtiPipeline, PipelineConfig

T0 = datetime(2026, 5, 21, tzinfo=timezone.utc)
T1 = datetime(2026, 5, 26, tzinfo=timezone.utc)

si = fetch_sea_ice(-80, -60, -60, -20, T0, T1, use_fixture=True)
wf = fetch_wind(-80, -60, -60, -20, T0, T1, use_fixture=True)
oc = fetch_ocean_current(-80, -60, -60, -20, T0, T1, use_fixture=True)
bergs = fetch_icebergs(-80, -60, -60, -20, use_fixture=True)

fw = ForecastWindow(T0, [T0], [0.0])
pi = PipelineInput(fw, si, wf, oc, bergs)
result = HimDrishtiPipeline().run(pi)
print(result.route_fast)
```

### With real credentials (when available)
```bash
export CMEMS_USERNAME=your_username
export CMEMS_PASSWORD=your_password
export CDS_API_KEY=your_uid:your_key
# Then run pipeline without use_fixture=True
```

> ⚠️ **Never commit credentials.** Use environment variables only.
