"""
backend/services/departure_window.py
--------------------------------------
Departure-window comparison service.
SIH 2026 · PS 26059

Phase 9.

Runs GENUINE sequential pipeline executions for each candidate departure
time (Current, +6h, +12h, +24h).

DESIGN RULES:
  - Each candidate departure time triggers a real pipeline rerun.
  - NO deterministic offsets. NO fabricated risk/ETA/fuel/confidence.
  - All deltas are calculated from actual pipeline outputs.
  - Missing metric → None (never fabricated).
  - Performance: ~60s per run × 4 runs ≈ 4 minutes total.
    Sequential execution — no Redis/Celery/Kafka.
    Caller should display appropriate loading state.
  - Language: "Recommended under current forecast" / "Lower modeled risk"
    Never "safest departure" or "guaranteed" or "AI selected".
  - Final navigation authority rests with the Captain/Master/Ice Pilot.

DEFERRED from Phase 8:
  This is the feature deferred because Phase 8 prohibited deterministic offsets.
  Phase 9 now implements it correctly with genuine pipeline reruns.
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Supported departure offsets (hours from base departure time)
SUPPORTED_OFFSETS_H = [0, 6, 12, 24]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DepartureWindowResult:
    """
    Result for a single departure time candidate.
    All metrics come from actual pipeline execution — never fabricated.
    """
    offset_hours: int                    # 0, 6, 12, or 24
    departure_time: str                  # ISO 8601 UTC
    route_id: Optional[str] = None
    route_name: Optional[str] = None
    risk: Optional[float] = None                # normalized risk [0-1]
    fuel_tonnes: Optional[float] = None
    eta_hours: Optional[float] = None
    distance_km: Optional[float] = None
    risk_budget_status: Optional[str] = None    # WITHIN_BUDGET | EXCEEDS_BUDGET | NO_ROUTE_WITHIN_RISK_BUDGET
    forecast_confidence_level: Optional[str] = None  # HIGH | MEDIUM | LOW | UNKNOWN
    forecast_confidence_score: Optional[float] = None
    data_quality: Dict[str, str] = field(default_factory=dict)
    provenance_summary: List[Dict[str, Any]] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    error: Optional[str] = None         # set if pipeline failed for this candidate


@dataclass
class DepartureWindowDelta:
    """Delta between a candidate departure and the baseline (offset=0)."""
    offset_hours: int
    risk_delta_pct: Optional[float]
    fuel_delta_pct: Optional[float]
    eta_delta_hours: Optional[float]
    distance_delta_km: Optional[float]


@dataclass
class DepartureWindowComparison:
    """
    Full departure-window comparison: 4 genuine pipeline runs + deltas.
    """
    base_departure_time: str
    operating_mode: str
    risk_budget_limit: float
    results: List[DepartureWindowResult]
    deltas: List[DepartureWindowDelta]   # vs baseline (offset=0)
    recommended_offset_hours: Optional[int]
    recommendation_basis: str
    total_elapsed_seconds: float
    prototype_notice: str = (
        "SIH 2026 Prototype. Departure-window results from SYNTHETIC_DEMO pipeline. "
        "Each candidate ran a genuine pipeline execution (no fabricated offsets). "
        "Not an operational navigation authority. "
        "Final decision rests with the Captain/Master/Ice Pilot."
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pct_delta(base: Optional[float], other: Optional[float]) -> Optional[float]:
    if base is None or other is None or base == 0.0:
        return None
    return round((other - base) / abs(base) * 100.0, 2)


def _abs_delta(base: Optional[float], other: Optional[float]) -> Optional[float]:
    if base is None or other is None:
        return None
    return round(other - base, 3)


def _extract_best_route_metrics(response_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key metrics from a GenerateRoutesResponse dict.
    Returns metrics for the recommended route.
    """
    recommended_id = response_dict.get("recommended_route_id", "recommended")
    routes = response_dict.get("routes", [])
    rec_route = next((r for r in routes if r.get("route_id") == recommended_id), None)
    if rec_route is None and routes:
        rec_route = routes[0]

    cb    = (rec_route or {}).get("cost_breakdown") or {}
    mets  = (rec_route or {}).get("metrics") or {}
    rbs   = (rec_route or {}).get("risk_budget_status") or {}
    conf  = response_dict.get("forecast_confidence") or {}

    return {
        "route_id":          (rec_route or {}).get("route_id"),
        "route_name":        (rec_route or {}).get("name"),
        "risk":              (mets.get("integrated_risk")
                              if mets.get("integrated_risk") is not None
                              else _normalize_risk_cost(cb.get("risk_cost"))),
        "fuel_tonnes":       cb.get("fuel_tonnes"),
        "eta_hours":         cb.get("time_hours"),
        "distance_km":       mets.get("distance_km"),
        "risk_budget_status": rbs.get("status"),
        "confidence_level":  conf.get("level"),
        "confidence_score":  conf.get("score"),
        "data_quality":      response_dict.get("data_quality_summary", {}),
        "provenance":        response_dict.get("provenance_summary", [])[:3],
    }


def _normalize_risk_cost(raw: Optional[float]) -> Optional[float]:
    """Normalize raw pipeline risk cost to [0-1] range (divide by 10)."""
    if raw is None:
        return None
    return round(min(raw / 10.0, 1.0), 4)


# ---------------------------------------------------------------------------
# Main departure-window runner
# ---------------------------------------------------------------------------

def run_departure_windows(
    base_request_dict: Dict[str, Any],
    offsets_hours: Optional[List[int]] = None,
) -> DepartureWindowComparison:
    """
    Run genuine pipeline executions for each departure window candidate.

    Each candidate shifts the base departure_time by offset_hours and
    runs the full pipeline independently. No offsets are applied to
    the outputs — all metrics come from real pipeline execution.

    Parameters
    ----------
    base_request_dict : dict matching GenerateRoutesRequest schema
    offsets_hours     : list of hour offsets (default: [0, 6, 12, 24])

    Returns
    -------
    DepartureWindowComparison with actual results for each candidate
    """
    # Import here to avoid circular dependency
    from backend.schemas.requests import GenerateRoutesRequest
    from backend.services import route_service

    if offsets_hours is None:
        offsets_hours = SUPPORTED_OFFSETS_H

    # Parse base departure time
    base_departure_str = base_request_dict.get("departure_time", "2026-05-21T12:00:00Z")
    if isinstance(base_departure_str, str):
        # Normalize to UTC
        if base_departure_str.endswith("Z"):
            base_departure_str = base_departure_str.replace("Z", "+00:00")
        base_dt = datetime.fromisoformat(base_departure_str).astimezone(timezone.utc)
    else:
        base_dt = base_departure_str.astimezone(timezone.utc)

    operating_mode = base_request_dict.get("operating_mode", "BALANCED")
    risk_budget_limit = (base_request_dict.get("risk_budget") or {}).get("max_acceptable_risk", 0.55)

    logger.info(
        "Departure-window comparison: base=%s offsets=%s mode=%s budget=%.2f",
        base_dt.isoformat(), offsets_hours, operating_mode, risk_budget_limit,
    )

    t_total_start = time.monotonic()
    results: List[DepartureWindowResult] = []

    for offset_h in offsets_hours:
        candidate_dt = base_dt + timedelta(hours=offset_h)
        candidate_departure = candidate_dt.isoformat().replace("+00:00", "Z")

        logger.info(
            "Departure window +%dh: departure=%s (genuine pipeline rerun)",
            offset_h, candidate_departure,
        )

        # Build modified request for this candidate
        candidate_request_dict = {
            **base_request_dict,
            "departure_time": candidate_dt.isoformat(),
        }

        t_run_start = time.monotonic()
        error_msg = None
        metrics: Dict[str, Any] = {}

        try:
            req = GenerateRoutesRequest(**candidate_request_dict)
            resp = route_service.generate_routes(req)
            resp_dict = resp.model_dump()
            metrics = _extract_best_route_metrics(resp_dict)
            logger.info(
                "+%dh run complete: risk=%.3f fuel=%.1f eta=%.1fh",
                offset_h,
                metrics.get("risk") or 0.0,
                metrics.get("fuel_tonnes") or 0.0,
                metrics.get("eta_hours") or 0.0,
            )
        except Exception as exc:
            error_msg = str(exc)
            logger.error("Departure window +%dh failed: %s", offset_h, exc)

        elapsed = time.monotonic() - t_run_start

        results.append(DepartureWindowResult(
            offset_hours=offset_h,
            departure_time=candidate_departure,
            route_id=metrics.get("route_id") if not error_msg else None,
            route_name=metrics.get("route_name") if not error_msg else None,
            risk=metrics.get("risk") if not error_msg else None,
            fuel_tonnes=metrics.get("fuel_tonnes") if not error_msg else None,
            eta_hours=metrics.get("eta_hours") if not error_msg else None,
            distance_km=metrics.get("distance_km") if not error_msg else None,
            risk_budget_status=metrics.get("risk_budget_status") if not error_msg else None,
            forecast_confidence_level=metrics.get("confidence_level") if not error_msg else None,
            forecast_confidence_score=metrics.get("confidence_score") if not error_msg else None,
            data_quality=metrics.get("data_quality", {}) if not error_msg else {},
            provenance_summary=metrics.get("provenance", []) if not error_msg else [],
            elapsed_seconds=elapsed,
            error=error_msg,
        ))

    total_elapsed = time.monotonic() - t_total_start

    # ── Compute deltas vs baseline (offset=0) ─────────────────────────
    baseline = next((r for r in results if r.offset_hours == 0), None)
    deltas: List[DepartureWindowDelta] = []
    for r in results:
        if r.offset_hours == 0:
            deltas.append(DepartureWindowDelta(
                offset_hours=0,
                risk_delta_pct=0.0,
                fuel_delta_pct=0.0,
                eta_delta_hours=0.0,
                distance_delta_km=0.0,
            ))
        else:
            deltas.append(DepartureWindowDelta(
                offset_hours=r.offset_hours,
                risk_delta_pct=_pct_delta(
                    getattr(baseline, "risk", None),
                    r.risk,
                ),
                fuel_delta_pct=_pct_delta(
                    getattr(baseline, "fuel_tonnes", None),
                    r.fuel_tonnes,
                ),
                eta_delta_hours=_abs_delta(
                    getattr(baseline, "eta_hours", None),
                    r.eta_hours,
                ),
                distance_delta_km=_abs_delta(
                    getattr(baseline, "distance_km", None),
                    r.distance_km,
                ),
            ))

    # ── Recommend the lower modeled risk option ─────────────────────────
    # Only among non-failed results with risk values.
    # Language: "lower modeled risk" — never "safest"
    evaluable = [r for r in results if r.risk is not None and r.error is None]
    recommended_offset = None
    if evaluable:
        best = min(evaluable, key=lambda r: r.risk)
        recommended_offset = best.offset_hours

    basis = (
        "Departure with lower modeled risk selected. "
        "Not a safety guarantee. Final decision rests with the Captain/Master/Ice Pilot."
        if recommended_offset is not None
        else "No recommendation — all candidates failed or produced null risk."
    )

    logger.info(
        "Departure-window comparison complete: %d candidates, total=%.1fs, recommended=+%sh",
        len(results), total_elapsed,
        recommended_offset if recommended_offset is not None else "?",
    )

    return DepartureWindowComparison(
        base_departure_time=base_dt.isoformat().replace("+00:00", "Z"),
        operating_mode=operating_mode,
        risk_budget_limit=risk_budget_limit,
        results=results,
        deltas=deltas,
        recommended_offset_hours=recommended_offset,
        recommendation_basis=basis,
        total_elapsed_seconds=round(total_elapsed, 2),
    )
