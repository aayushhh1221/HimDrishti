# Phase 8 — Decision Intelligence

**HimDrishti · SIH 2026 · PS 26059**
*Risk-Budgeted Decision Intelligence*

---

## Overview

Phase 8 adds a deterministic risk-budgeting layer, counterfactual route comparison, forecast-confidence assessment, and whole-voyage risk reporting on top of the existing POLARIS-based routing core. No scientific algorithms were modified.

## Architecture

```
PHYSICS + DATA (Phase 6 adapters)
        ↓
PROBABILISTIC HAZARD (iceberg_drift.py)
        ↓
POLARIS RIO (polaris_risk.py)
        ↓
RISK-BUDGETED ROUTING
  └── apply_operating_mode() → RouteWeights
  └── find_route() (route_search.py — unchanged)
  └── evaluate_risk_budget() → WITHIN_BUDGET | EXCEEDS_BUDGET
        ↓
COUNTERFACTUAL COMPARISON
  └── compute_counterfactuals() → Δ fuel / Δ ETA / Δ risk (actual values)
        ↓
FORECAST CONFIDENCE
  └── assess_forecast_confidence() → HIGH | MEDIUM | LOW | UNKNOWN
        ↓
DECISION SUPPORT (Captain Decision Panel)
```

## New Files

| File | Purpose |
|------|---------|
| `backend/services/risk_budget.py` | Operating mode → RouteWeights mapping, risk normalization, budget evaluation |
| `backend/services/counterfactual.py` | Δ metrics from actual route outputs (null when unavailable) |
| `backend/services/forecast_confidence.py` | Deterministic confidence assessment from data quality |
| `tests/test_phase8.py` | 66 new tests across 16 test classes |

## Modified Files

| File | Changes |
|------|---------|
| `backend/schemas/requests.py` | Added `OperatingMode`, `RiskBudget`, `extreme_risk_acknowledged` |
| `backend/schemas/responses.py` | Added `RouteMetrics`, `RiskBudgetStatus`, `CounterfactualComparison`, `ForecastConfidence`, `WholeVoyageRisk` |
| `backend/services/route_service.py` | Wired all Phase 8 services; updated safety-critical wording |
| `frontend/src/services/api/types.ts` | Extended with all Phase 8 TypeScript types |
| `frontend/src/services/api/client.ts` | Extended `GenerateRoutesPayload` with Phase 8 fields |
| `frontend/src/components/route-planner/VoyageScenarioPanel.tsx` | Operating Mode, Risk Budget slider, Extreme-risk gate |
| `frontend/src/components/route-planner/RouteComparisonPanel.tsx` | Counterfactual delta rows embedded in route cards |
| `frontend/src/components/decision/RiskCompliancePanel.tsx` | Forecast Confidence badge, Growler limitation notice |
| `frontend/src/components/decision/CaptainDecisionPanel.tsx` | Safety-critical wording audit |
| `tests/test_api.py` | Updated `_VALID_ROUTE_REQUEST` with Phase 8 fields |

---

## Operating Modes

| Mode | Risk Weight | Fuel Weight | Default Max Risk |
|------|-------------|-------------|-----------------|
| `SAFETY_FIRST` | 8.0 | 0.3 | 0.35 |
| `BALANCED` (default) | 4.0 | 0.4 | 0.55 |
| `FUEL_SAVER` | 2.0 | 1.5 | 0.55 |

These weights drive `route_search.py`'s Dijkstra / UCS optimizer — the scientific core is unchanged.

---

## Risk Budget Constraint

The optimizer minimizes fuel/time **subject to**:
```
normalized_risk = route.total_risk_cost / 10.0
status = WITHIN_BUDGET if normalized_risk <= max_acceptable_risk else EXCEEDS_BUDGET
```

If no route is found: `NO_ROUTE_WITHIN_RISK_BUDGET` — never fabricated.

### Extreme-Risk Gate

If `max_acceptable_risk > 0.70`, the request is rejected (HTTP 422) unless `extreme_risk_acknowledged = True`.

---

## Counterfactual Comparison

All delta values are calculated from **actual route outputs**:

| Metric | Calculation | Missing |
|--------|-------------|---------|
| Δ Fuel % | `(alt - baseline) / baseline × 100` | `null` |
| Δ ETA h | `alt - baseline` | `null` |
| Δ Risk % | `(alt - baseline) / baseline × 100` | `null` |
| Δ Uncertainty % | `(alt - baseline) / baseline × 100` | `null` |
| Δ Distance km | `alt - baseline` | `null` |

No invented values, no guessed offsets.

---

## Forecast Confidence

| Level | Conditions |
|-------|-----------|
| `HIGH` | Live data, short horizon (≤48h), all sources available |
| `MEDIUM` | SYNTHETIC_DEMO baseline, moderate horizon |
| `LOW` | Stale/partial data, or extended horizon (>72h) |
| `UNKNOWN` | Invalid or unavailable source data |

Degradation flags: `SYNTHETIC_DEMO_DATA`, `STALE_DATA_*`, `PARTIAL_DATA`, `EXTENDED_HORIZON_REDUCED_CONFIDENCE`

Scores (0.85 / 0.60 / 0.35 / null) are ordinal descriptors mapped to [0,1] for display — **not calibrated probabilities**.

---

## Growler / Bergy-Bit Limitation

Displayed in `RiskCompliancePanel`:
> "Satellite detection may miss small growlers/bergy bits. Radar watch and visual lookout remain necessary."

This notice is always visible when API data is loaded.

---

## Safety-Critical Language Policy

| FORBIDDEN | REQUIRED |
|-----------|---------|
| "AI selected the safest route" | "Recommended under current forecast" |
| "safe route" | "lower modeled risk route" |
| "approved / certified" | "recommended" |
| Fabricated risk scores | Actual pipeline values or `null` |

---

## Deferred to Phase 9

**Departure-window sandbox** — planning with alternative departure times requires a genuine pipeline rerun per candidate departure time. This is **not implemented in Phase 8** because:
- A full pipeline rerun takes ~30s
- Deterministic offsets would be fabricated (prohibited)
- Phase 9 will implement genuine multi-departure comparison

---

## API Changes

### POST `/api/v1/routes/generate`

**New request fields:**
```json
{
  "operating_mode": "BALANCED",
  "risk_budget": {
    "max_acceptable_risk": 0.55,
    "uncertainty_weight": 0.5
  },
  "extreme_risk_acknowledged": false
}
```

**New response fields:**
```json
{
  "operating_mode": "BALANCED",
  "risk_budget_limit": 0.55,
  "counterfactual": { "baseline_route_id": "...", "comparisons": [...] },
  "forecast_confidence": { "level": "MEDIUM", "score": 0.60, ... },
  "whole_voyage_risk": { "integrated_risk_recommended": 0.15, ... },
  "run_log": { "run_id": "...", "timestamp_utc": "..." }
}
```

**Per-route new fields:**
```json
{
  "metrics": { "integrated_risk": 0.15, "uncertainty_contribution": 0.53, ... },
  "risk_budget_status": { "status": "WITHIN_BUDGET", "actual_risk": 0.15, ... }
}
```
