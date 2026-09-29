# Departure Window Planning — Reference
## SIH 2026 · PS 26059 · Phase 9

---

## Overview

The departure-window feature compares candidate departure times
(Current, +6h, +12h, +24h) by running **genuine pipeline executions**
for each candidate.

> **DEFERRED from Phase 8:** This feature was explicitly deferred in Phase 8
> because deterministic mathematical offsets would have fabricated risk/ETA/fuel.
> Phase 9 implements it correctly: every candidate runs the full pipeline.

---

## Design Principles

1. **No fabricated offsets.** Every metric comes from an actual pipeline execution.
2. **Missing metric → `null`** — never invented.
3. **Language:** "Recommended under current forecast" / "Lower modeled risk"  
   Never "safest departure" or "guaranteed" or "AI selected".
4. **Final authority** rests with the Captain/Master/Ice Pilot.
5. **Sequential execution** — no Redis/Celery/Kafka. Correct first, optimized later.

---

## API

### `POST /api/v1/planning/departure-windows`

#### Request

```json
{
  "origin": { "name": "Cape Town, South Africa", "lat": -33.93, "lon": 18.42 },
  "destination": { "name": "Bharati Station, Larsemann Hills", "lat": -69.41, "lon": 76.19 },
  "base_departure_time": "2026-05-21T12:00:00Z",
  "vessel": {
    "name": "RSV Nuyina (Ice Class PC3)",
    "ice_class": "PC3",
    "draft_m": 9.2,
    "speed_knots": 12.0
  },
  "forecast_horizon_hours": 120,
  "operating_mode": "BALANCED",
  "risk_budget": { "max_acceptable_risk": 0.55 },
  "candidate_offsets_hours": [0, 6, 12, 24]
}
```

#### Response

```json
{
  "base_departure_time": "2026-05-21T12:00:00Z",
  "operating_mode": "BALANCED",
  "risk_budget_limit": 0.55,
  "results": [
    {
      "offset_hours": 0,
      "departure_time": "2026-05-21T12:00:00Z",
      "risk": 0.347,
      "fuel_tonnes": 52.4,
      "eta_hours": 182,
      "distance_km": 4520.0,
      "risk_budget_status": "WITHIN_BUDGET",
      "forecast_confidence_level": "MEDIUM",
      "elapsed_seconds": 61.2,
      "error": null
    },
    ...
  ],
  "deltas": [
    { "offset_hours": 0, "risk_delta_pct": 0.0, ... },
    { "offset_hours": 6, "risk_delta_pct": -2.3, ... },
    ...
  ],
  "recommended_offset_hours": 6,
  "recommendation_basis": "Departure with lower modeled risk selected. Not a safety guarantee. Final decision rests with the Captain/Master/Ice Pilot.",
  "total_elapsed_seconds": 243.7,
  "prototype_notice": "..."
}
```

---

## Candidate Windows

| Candidate | Meaning |
|-----------|---------|
| `offset_hours: 0` | Current departure (base departure time) |
| `offset_hours: 6` | +6h from base departure time |
| `offset_hours: 12` | +12h from base departure time |
| `offset_hours: 24` | +24h from base departure time |

---

## How Each Candidate is Evaluated

```
For each offset in [0, 6, 12, 24]:
    candidate_departure = base_departure_time + offset_hours
    pipeline_input = assemble_data(candidate_departure)   ← genuine fetch
    result = HimDrishtiPipeline.run(pipeline_input, seed)  ← genuine run
    risk_budget_status = evaluate_risk_budget(result)
    forecast_confidence = assess_forecast_confidence(result)
    record DepartureWindowResult (all from actual pipeline output)

deltas = {r.risk - baseline.risk for r in results}
recommend = argmin(r.risk for r in results if r.error is None)
```

> **Note:** In SYNTHETIC_DEMO mode, all candidates use the same fixture data
> (deterministic). Risk/ETA/fuel differences between candidates reflect the
> ensemble stochasticity from different departure seeds, not real-world
> forecast differences. In a production deployment with live data, each
> candidate would use the appropriate forecast initialized at that departure time.

---

## Comparison Metrics

| Metric | Unit | Source |
|--------|------|--------|
| `risk` | 0–1 (normalized) | Actual pipeline output |
| `fuel_tonnes` | metric tonnes | Actual pipeline output |
| `eta_hours` | hours | Actual pipeline output |
| `distance_km` | km | Actual pipeline output |
| `risk_budget_status` | enum | Risk budget evaluation |
| `forecast_confidence_level` | HIGH/MEDIUM/LOW/UNKNOWN | Confidence assessment |

### Delta Calculation

All deltas are vs. the baseline (`offset_hours: 0`):
- `risk_delta_pct` = `(candidate.risk - baseline.risk) / |baseline.risk| × 100`
- `fuel_delta_pct` = `(candidate.fuel - baseline.fuel) / |baseline.fuel| × 100`
- `eta_delta_hours` = `candidate.eta - baseline.eta` (absolute, hours)

If baseline is `null` (failed) → all deltas are `null`.

---

## Performance

| Scenario | Approximate Runtime |
|----------|---------------------|
| 1 candidate | ~60s (one iceberg ensemble) |
| 4 candidates (default) | ~4 minutes (sequential) |

The UI displays a loading state during execution. No fabricated progress percentages.

> **Future optimization (Phase 10+):** If performance is unacceptable in production,
> consider caching the pipeline input data across candidates (same data, different
> departure times), or parallelizing ensemble runs. This requires measurement first.

---

## Safety Language

All departure-window results use this language:

| Prohibited | Used Instead |
|-----------|-------------|
| "Safest departure" | "Recommended under current forecast" |
| "Guaranteed low risk" | "Lower modeled risk" |
| "AI selected" | "Departure with lower modeled risk selected" |
| "Certified / approved" | *(not used)* |

> "Final decision rests with the Captain/Master/Ice Pilot."

---

## Known Limitations

1. **SYNTHETIC_DEMO data** — forecast data is the same for all candidates.
   Risk differences between candidates in this mode reflect ensemble stochasticity only.
2. **Sequential execution** — 4 runs × ~60s each.
3. **No parallel forecast initialization** — in production, each departure time should
   use the appropriate forecast model initialized at that time.
4. **POLARIS RIV table is illustrative** — risk scores are prototype values only.
5. **Growler/bergy-bit gap** — small ice features not captured in modeled risk.

---

*SIH 2026 · PS 26059 · Prototype / Demonstration System.*
*Not an operational navigation authority.*
