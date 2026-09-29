"""
backend/services/risk_budget.py
---------------------------------
Risk-budget constraint evaluation and operating-mode weight mapping.
SIH 2026 · PS 26059

Phase 8.

Architecture:
  OperatingModeWeights  — maps SAFETY_FIRST/BALANCED/FUEL_SAVER to RouteWeights
  RiskNormalizer        — derives a 0-1 normalized risk from RouteResult.total_risk_cost
  RiskBudgetEvaluator   — evaluates WITHIN_BUDGET | EXCEEDS_BUDGET | NO_ROUTE
  apply_operating_mode  — merges mode defaults with user overrides

DESIGN RULES:
  - Does NOT modify any scientific formula in ai/
  - Does NOT replace route_search.py
  - Does NOT fabricate a route if budget is not satisfiable
  - Uses RouteResult.total_risk_cost directly from the pipeline
  - "Risk" here means MODELED risk — never an operational safety claim
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Ensure ai/ is importable
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "ai"))

from route_search import RouteWeights  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentinel — no route satisfies budget
# ---------------------------------------------------------------------------

NO_ROUTE_WITHIN_RISK_BUDGET = "NO_ROUTE_WITHIN_RISK_BUDGET"

# ---------------------------------------------------------------------------
# Operating mode → default RouteWeights
# ---------------------------------------------------------------------------

# Risk-cost normalizer: values observed in SYNTHETIC_DEMO pipeline runs.
# The route_search risk_cost accumulates per-cell hazard costs (0–scale).
# We normalize against a representative maximum so budget thresholds (0–1)
# are intuitive for the user.
#
# This constant is empirically derived from SYNTHETIC_DEMO fixture runs:
#   - fast route:  ~1.5  risk_cost
#   - safe route:  ~0.5  risk_cost
#   - higher risk: ~6.0  risk_cost (4× multiplier applied in service layer)
#
# Using 10.0 as the normalization ceiling gives headroom without compressing
# the lower end. Not an absolute physical quantity — SYNTHETIC_DEMO only.
_RISK_NORMALIZER = 10.0


@dataclass
class ModeWeights:
    """Route weights for one operating mode."""
    mode_name: str
    risk_weight: float
    fuel_weight: float
    time_weight: float
    default_max_risk: float   # default budget.max_acceptable_risk for this mode


# Operating mode weight table
_MODE_WEIGHTS = {
    "SAFETY_FIRST": ModeWeights(
        mode_name="SAFETY_FIRST",
        risk_weight=8.0,
        fuel_weight=0.3,
        time_weight=1.0,
        default_max_risk=0.35,
    ),
    "BALANCED": ModeWeights(
        mode_name="BALANCED",
        risk_weight=4.0,
        fuel_weight=0.4,
        time_weight=1.0,
        default_max_risk=0.55,
    ),
    "FUEL_SAVER": ModeWeights(
        mode_name="FUEL_SAVER",
        risk_weight=2.0,
        fuel_weight=1.5,
        time_weight=1.0,
        default_max_risk=0.55,
    ),
}


def apply_operating_mode(
    mode: str,
    risk_weight_override: Optional[float] = None,
    fuel_weight_override: Optional[float] = None,
    time_weight_override: Optional[float] = None,
) -> RouteWeights:
    """
    Build RouteWeights from the operating mode, optionally overriding
    individual weights from the user's RiskBudget overrides.

    Does NOT modify any scientific formula — only produces the RouteWeights
    input for route_search.py's find_route().
    """
    mw = _MODE_WEIGHTS.get(mode, _MODE_WEIGHTS["BALANCED"])

    weights = RouteWeights(
        risk_weight=risk_weight_override if risk_weight_override is not None else mw.risk_weight,
        fuel_weight=fuel_weight_override if fuel_weight_override is not None else mw.fuel_weight,
        time_weight=time_weight_override if time_weight_override is not None else mw.time_weight,
    )
    logger.debug(
        "Operating mode %s → RouteWeights(risk=%.2f fuel=%.2f time=%.2f)",
        mode, weights.risk_weight, weights.fuel_weight, weights.time_weight,
    )
    return weights


def get_mode_default_max_risk(mode: str) -> float:
    """Return the default max_acceptable_risk for an operating mode."""
    return _MODE_WEIGHTS.get(mode, _MODE_WEIGHTS["BALANCED"]).default_max_risk


# ---------------------------------------------------------------------------
# Risk normalization
# ---------------------------------------------------------------------------

def normalize_risk(raw_risk_cost: float) -> float:
    """
    Normalize RouteResult.total_risk_cost to [0, 1] for budget comparison.

    Uses _RISK_NORMALIZER as ceiling. Clamps to [0, 1].
    SYNTHETIC_DEMO only — not an operational risk measure.
    """
    if _RISK_NORMALIZER <= 0:
        return 0.0
    return max(0.0, min(1.0, raw_risk_cost / _RISK_NORMALIZER))


# ---------------------------------------------------------------------------
# Risk budget evaluator
# ---------------------------------------------------------------------------

def evaluate_risk_budget(
    route_id: str,
    raw_risk_cost: Optional[float],
    max_acceptable_risk: float,
) -> dict:
    """
    Evaluate whether a route satisfies the risk budget constraint.

    Returns a dict matching RiskBudgetStatus fields.

    WITHIN_BUDGET:              normalized risk <= max_acceptable_risk
    EXCEEDS_BUDGET:             normalized risk > max_acceptable_risk
    NO_ROUTE_WITHIN_RISK_BUDGET: raw_risk_cost is None (no route found)
    """
    notice = (
        "Risk budget evaluation uses SYNTHETIC_DEMO values — not operational risk assessment."
    )

    if raw_risk_cost is None:
        return {
            "status": NO_ROUTE_WITHIN_RISK_BUDGET,
            "budget_limit": max_acceptable_risk,
            "actual_risk": None,
            "prototype_notice": notice,
        }

    normalized = normalize_risk(raw_risk_cost)
    status = "WITHIN_BUDGET" if normalized <= max_acceptable_risk else "EXCEEDS_BUDGET"

    logger.debug(
        "Route %s: raw_risk=%.3f normalized=%.3f budget=%.3f → %s",
        route_id, raw_risk_cost, normalized, max_acceptable_risk, status,
    )

    return {
        "status": status,
        "budget_limit": max_acceptable_risk,
        "actual_risk": round(normalized, 4),
        "prototype_notice": notice,
    }


# ---------------------------------------------------------------------------
# Whole-voyage risk computation
# ---------------------------------------------------------------------------

def compute_whole_voyage_risk(
    route_id: str,
    raw_risk_cost: Optional[float],
    max_acceptable_risk: float,
    path_cell_count: Optional[int] = None,
) -> dict:
    """
    Compute whole-voyage risk summary from actual route outputs.

    Fields set to None where not computable from current pipeline.
    Never fabricated.

    Returns dict matching WholeVoyageRisk fields.
    """
    if raw_risk_cost is None:
        return {
            "max_segment_risk": None,
            "integrated_risk_recommended": None,
            "risk_budget_status_recommended": NO_ROUTE_WITHIN_RISK_BUDGET,
            "highest_risk_segment_index": None,
            "prototype_notice": (
                "Whole-voyage risk: no route found — cannot compute metrics."
            ),
        }

    normalized = normalize_risk(raw_risk_cost)
    budget_status = "WITHIN_BUDGET" if normalized <= max_acceptable_risk else "EXCEEDS_BUDGET"

    # max_segment_risk: route_search accumulates total risk but doesn't expose
    # per-segment breakdowns. Use total/cell_count as average if available,
    # otherwise use total_risk_cost (conservative upper bound per segment is
    # not derivable without path-level data — return None).
    max_segment_risk: Optional[float] = None
    highest_risk_idx: Optional[int] = None
    # Note: route_search.py RouteResult does not expose per-segment risk.
    # Per-segment breakdown would require storing breakdown dict per state.
    # This is a Phase 9 extension — for now, we report what is available.

    return {
        "max_segment_risk": max_segment_risk,
        "integrated_risk_recommended": round(normalized, 4),
        "risk_budget_status_recommended": budget_status,
        "highest_risk_segment_index": highest_risk_idx,
        "prototype_notice": (
            "Whole-voyage risk from SYNTHETIC_DEMO pipeline outputs. "
            "Per-segment breakdown requires Phase 9 route_search extension."
        ),
    }
