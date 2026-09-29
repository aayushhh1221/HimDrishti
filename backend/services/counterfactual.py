"""
backend/services/counterfactual.py
-------------------------------------
Deterministic counterfactual route comparison.
SIH 2026 · PS 26059

Phase 8.

Calculates Δ fuel, Δ ETA, Δ risk, Δ uncertainty, Δ distance for each
non-baseline route vs the baseline (recommended) route.

DESIGN RULES:
  - ALL delta values are calculated from actual RouteResponse outputs
  - Missing metric → None (never a fabricated number or guessed offset)
  - No arbitrary offsets, no invented percentages
  - If baseline metric is 0 or unavailable → delta = None (avoid div-by-zero)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _pct_delta(baseline: Optional[float], other: Optional[float]) -> Optional[float]:
    """
    Compute percentage delta: (other - baseline) / baseline * 100.
    Returns None if either value is missing or baseline is zero.
    """
    if baseline is None or other is None:
        return None
    if baseline == 0.0:
        return None
    return round((other - baseline) / abs(baseline) * 100.0, 2)


def _abs_delta(baseline: Optional[float], other: Optional[float]) -> Optional[float]:
    """
    Compute absolute delta: other - baseline.
    Returns None if either value is missing.
    """
    if baseline is None or other is None:
        return None
    return round(other - baseline, 3)


def compute_counterfactuals(
    routes: List[Dict[str, Any]],
    baseline_route_id: str,
) -> Dict[str, Any]:
    """
    Compute counterfactual deltas for all non-baseline routes vs baseline.

    Args:
        routes: list of dicts with route data (from _build_route_responses output).
                Expected keys per route: route_id, name, cost_breakdown
                (time_hours, fuel_tonnes, risk_cost), metrics (optional)
        baseline_route_id: route_id of the reference route (usually 'recommended')

    Returns:
        dict matching CounterfactualComparison schema fields.

    All delta calculations use actual values from route outputs.
    Missing data → None. No fabrication.
    """
    baseline = next(
        (r for r in routes if r["route_id"] == baseline_route_id), None
    )
    if baseline is None:
        logger.warning(
            "Counterfactual baseline route_id '%s' not found in routes. Returning empty.",
            baseline_route_id,
        )
        return {
            "baseline_route_id": baseline_route_id,
            "baseline_route_name": "Unknown",
            "comparisons": [],
            "prototype_notice": (
                "Counterfactual: baseline route not found — no deltas computed."
            ),
        }

    baseline_cb = baseline.get("cost_breakdown", {})
    baseline_fuel = baseline_cb.get("fuel_tonnes")
    baseline_time = baseline_cb.get("time_hours")
    baseline_risk = baseline_cb.get("risk_cost")
    baseline_distance = (baseline.get("metrics") or {}).get("distance_km")
    baseline_uncertainty = (baseline.get("metrics") or {}).get("uncertainty_contribution")

    comparisons = []
    for route in routes:
        if route["route_id"] == baseline_route_id:
            continue

        cb = route.get("cost_breakdown", {})
        metrics = route.get("metrics") or {}
        budget_status = (route.get("risk_budget_status") or {}).get("status")

        fuel_delta = _pct_delta(baseline_fuel, cb.get("fuel_tonnes"))
        eta_delta = _abs_delta(baseline_time, cb.get("time_hours"))
        risk_delta = _pct_delta(baseline_risk, cb.get("risk_cost"))
        distance_delta = _abs_delta(baseline_distance, metrics.get("distance_km"))
        uncertainty_delta = _pct_delta(
            baseline_uncertainty, metrics.get("uncertainty_contribution")
        )

        comparison = {
            "route_id": route["route_id"],
            "route_name": route.get("name", route["route_id"]),
            "fuel_delta_pct": fuel_delta,
            "eta_delta_hours": eta_delta,
            "risk_delta_pct": risk_delta,
            "uncertainty_delta_pct": uncertainty_delta,
            "distance_delta_km": distance_delta,
            "risk_budget_status": budget_status,
        }
        comparisons.append(comparison)

        logger.debug(
            "Counterfactual %s vs %s: fuel=%s%% eta=%sh risk=%s%%",
            route["route_id"], baseline_route_id,
            fuel_delta, eta_delta, risk_delta,
        )

    return {
        "baseline_route_id": baseline_route_id,
        "baseline_route_name": baseline.get("name", baseline_route_id),
        "comparisons": comparisons,
        "prototype_notice": (
            "Counterfactual values calculated from SYNTHETIC_DEMO pipeline outputs. "
            "Not operational. Missing metrics shown as null."
        ),
    }
