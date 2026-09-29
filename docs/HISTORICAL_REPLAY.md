# Historical Replay — Architecture & Reference
## SIH 2026 · PS 26059 · Phase 9

---

## Overview

The HimDrishti historical replay system enables reproducible pipeline executions
using versioned dataset contracts. Given the same dataset_id, configuration, and
random seed, the pipeline produces the same result every time.

**Primary use:** Prototype demonstration and reproducibility testing.

---

## Dataset Contract

Every replay dataset is described by a `HistoricalDatasetContract`:

| Field | Type | Description |
|-------|------|-------------|
| `dataset_id` | str | Unique identifier (e.g. `HIMDRISHTI_SYNTHETIC_202605`) |
| `source` | str | Authoritative source name |
| `product` | str | Specific product/variable |
| `start_time` | str ISO 8601 UTC | Start of valid window |
| `end_time` | str ISO 8601 UTC | End of valid window |
| `spatial_coverage` | str | Human-readable coverage |
| `retrieved_at` | str | Retrieval time or `"SYNTHETIC"` |
| `valid_times` | list[str] | Discrete time steps |
| `units` | str | Physical units |
| `coordinate_system` | str | WGS-84 EPSG:4326 |
| `sha256` | str | Optional checksum |
| `data_mode` | str | `SYNTHETIC_REPLAY` \| `ARCHIVE` \| `REANALYSIS` |
| `quality_status` | str | `available` \| `partial` \| `stale` \| `unavailable` |

---

## Registered Datasets

| dataset_id | Mode | Source |
|-----------|------|--------|
| `HIMDRISHTI_SYNTHETIC_202605` | `SYNTHETIC_REPLAY` | Phase-6 fixture generator |
| `USNIC_ICEBERGS_SH_202605` | `ARCHIVE` | US National Ice Center |

### Public Archive Access (when credentials available)

| Dataset | Product | Access |
|---------|---------|--------|
| NSIDC-0051 | SSMIS Southern Hemisphere sea-ice concentration | EARTHDATA_USERNAME + EARTHDATA_PASSWORD |
| CMEMS GLORYS12 | Global ocean reanalysis | CMEMS_USERNAME + CMEMS_PASSWORD |
| ECMWF ERA5 | Hourly wind reanalysis | CDS_API_KEY |
| USNIC NIC | Antarctic iceberg tracking | Public (no login) |

> In this prototype deployment: no external credentials are configured.
> All replay runs use `SYNTHETIC_REPLAY` mode (Phase-6 fixture adapters).

---

## Replay Architecture

```
POST /api/v1/replay/run
        ↓
ReplayRunRequest (dataset_id, start_time, end_time, seed, config)
        ↓
dataset_contract.get_dataset_contract(dataset_id)
        ↓
runner.run_replay():
    1. Fetch data (fixture adapters in SYNTHETIC mode)
    2. Build PipelineInput (FORECAST data only)
    3. Run HimDrishtiPipeline (same scientific core)
    4. Persist replay record (create_replay)
    5. Return ReplayRunResult with computation trace
        ↓
verification.verify_iceberg_trajectory()
    ← actual_observations (separate from forecast inputs)
        ↓
ReplayRunResponse (JSON)
```

---

## Forecast / Actual Separation

> **CRITICAL:** Forecast input is completely separate from actual observations.

- The pipeline receives only **FORECAST inputs** (sea ice, wind, current, initial iceberg positions).
- **Actual observations** (ground truth iceberg positions at future times) are managed separately.
- They are NEVER fed into the pipeline as forecast inputs.
- Violation of this principle would make verification meaningless.

---

## Verification Metrics

For each forecast horizon (0h, 24h, 48h, 72h, 96h, 120h) **separately**:

| Metric | Unit | Notes |
|--------|------|-------|
| `mean_distance_error_km` | km | Great-circle distance, Haversine formula |
| `max_distance_error_km` | km | Worst case at this horizon |
| `mean_lat_error_deg` | degrees | Signed (positive = northward bias) |
| `mean_lon_error_deg` | degrees | Signed (positive = eastward bias) |
| `sample_count` | count | Independent observations at this horizon |
| `evaluation_status` | enum | See below |

### Evaluation Status Values

| Status | Meaning |
|--------|---------|
| `EVALUABLE` | Sufficient independent observations present |
| `NOT_EVALUABLE` | Synthetic data or source not independent |
| `INSUFFICIENT_SAMPLES` | Fewer than 2 independent observations |
| `NO_GROUND_TRUTH` | No actual observations provided |

> **PROVISIONAL:** All confidence thresholds from Phase 8 (0h→HIGH, 48h→MEDIUM, 96h→LOW)
> remain `PROVISIONAL/INSUFFICIENT_VALIDATION` because no real independent iceberg
> observations have been used to calibrate them. The Phase-8 thresholds are conservative
> prototype policies, not statistically validated thresholds.

---

## Offline-First Behaviour

Once the `HIMDRISHTI_SYNTHETIC_202605` dataset is registered, the core demo works
without external network access:

- Dataset contract available in registry (no download required)
- Replay runner uses deterministic fixture adapters (Phase-6 pipeline)
- Data age/source visible in `retrieved_at: "SYNTHETIC"`
- Never labelled as LIVE or real historical data

---

## Provenance

Every replay result exposes:
- `dataset_contract.source` — authoritative source name
- `dataset_contract.retrieved_at` — retrieval time or "SYNTHETIC"
- `dataset_contract.data_mode` — explicit mode
- `computation_trace` — deterministic step-by-step trace (no LLM)
- `provenance` — per-adapter provenance records

---

## Known Limitations

1. **No real historical data in this deployment** — credentials unavailable.
   All results use `SYNTHETIC_REPLAY` mode.
2. **Verification is NOT_EVALUABLE** — no independent iceberg observations provided.
3. **POLARIS RIV table is illustrative** — not from IMO MSC.1/Circ.1519.
   Historical replay does not validate the POLARIS table.
4. **Iceberg ensemble (48 members)** makes each replay run ~60s.
5. **Growler/bergy-bit detection gap** — satellite cannot detect small features.
   Replay results do not capture this limitation.

---

## POLARIS Warning

> The current POLARIS RIV table used in this prototype is **illustrative**.
> It was not derived from authoritative validated constants.
> Historical replay results must NOT be used as evidence that the POLARIS table
> produces correct operational risk scores.

---

*SIH 2026 · PS 26059 · Prototype / Demonstration System.*
*Not an operational navigation authority.*
*Final navigation authority rests with the Captain/Master/Ice Pilot.*
