"""
backend/services/forecast_confidence.py
------------------------------------------
Deterministic forecast-confidence / degradation assessment.
SIH 2026 · PS 26059

Phase 8.

Confidence must respond to Phase 6/7 data-quality states:
  AVAILABLE   — normal
  STALE       → degrade confidence, add STALE_DATA_SOURCE flag
  PARTIAL     → PARTIAL_DATA flag, reduce confidence
  INVALID     → UNKNOWN (cannot produce a valid result)
  UNAVAILABLE → UNKNOWN

Horizon policy (SYNTHETIC_DEMO):
  0h  → HIGH
  24h → HIGH
  48h → MEDIUM
  72h → MEDIUM
  96h → LOW
  120h → LOW
  (No horizon is marked INSUFFICIENT_VALIDATION unless data is unavailable)

No historical forecast error is invented.
If historical accuracy is unavailable, that factor is not included.

DESIGN RULE:
  Never invent a confidence percentage.
  If the data does not support a score, score = None.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Horizon policy — SYNTHETIC_DEMO mode
# ---------------------------------------------------------------------------
# Confidence decreases with forecast horizon because NWP uncertainty grows.
# These levels reflect general best practice — not validated against historical
# forecast error for this specific domain (that data is not available).
# Marked INSUFFICIENT_VALIDATION only when data is unavailable.

_HORIZON_POLICY_SYNTHETIC = {
    "0h":   "HIGH",
    "24h":  "HIGH",
    "48h":  "MEDIUM",
    "72h":  "MEDIUM",
    "96h":  "LOW",
    "120h": "LOW",
}

_HORIZON_POLICY_UNKNOWN = {k: "UNKNOWN" for k in _HORIZON_POLICY_SYNTHETIC}

# ---------------------------------------------------------------------------
# Data quality string indicators
# ---------------------------------------------------------------------------

_STALE_INDICATORS = {"stale"}
_PARTIAL_INDICATORS = {"partial"}
_INVALID_INDICATORS = {"invalid", "unavailable", "missing"}


def _classify_quality_string(q: str) -> str:
    """
    Classify a data_quality_summary string into a status category.
    Returns: 'available' | 'stale' | 'partial' | 'invalid'
    """
    ql = q.lower()
    for ind in _INVALID_INDICATORS:
        if ind in ql:
            return "invalid"
    for ind in _STALE_INDICATORS:
        if ind in ql:
            return "stale"
    for ind in _PARTIAL_INDICATORS:
        if ind in ql:
            return "partial"
    return "available"


# ---------------------------------------------------------------------------
# Main assessment function
# ---------------------------------------------------------------------------

def assess_forecast_confidence(
    data_quality_summary: Dict[str, str],
    data_mode: str,
    horizon_hours: int,
) -> Dict:
    """
    Assess forecast confidence from data quality, mode, and horizon.

    Args:
        data_quality_summary: dict from pipeline (e.g. {"sea_ice": "available", ...})
        data_mode: "SYNTHETIC_DEMO" | "FIXTURE" | "LIVE"
        horizon_hours: forecast horizon used (0..120)

    Returns:
        dict matching ForecastConfidence schema fields.

    Confidence levels:
        HIGH    — all sources available, short horizon, live data
        MEDIUM  — SYNTHETIC_DEMO baseline, or moderate horizon (48-72h)
        LOW     — extended horizon (>72h), or stale/partial data
        UNKNOWN — invalid or unavailable source data

    Score: 0.85 (HIGH) / 0.60 (MEDIUM) / 0.35 (LOW) / None (UNKNOWN).
    These are not validated empirical accuracy values — they are ordinal
    descriptors mapped to a 0-1 range for display purposes only.
    Do not present these as calibrated probability scores.
    """
    flags: List[str] = []
    level = "HIGH"

    # ── 1. Check each data source ────────────────────────────────────────────
    invalid_sources = 0
    stale_sources = 0
    partial_sources = 0

    for source_name, quality_str in data_quality_summary.items():
        status = _classify_quality_string(quality_str)
        if status == "invalid":
            invalid_sources += 1
            flags.append(f"INVALID_DATA_{source_name.upper()}")
        elif status == "stale":
            stale_sources += 1
            flags.append(f"STALE_DATA_{source_name.upper()}")
        elif status == "partial":
            partial_sources += 1
            flags.append(f"PARTIAL_DATA_{source_name.upper()}")

    # ── 2. Determine base level from data quality ────────────────────────────
    if invalid_sources > 0:
        level = "UNKNOWN"
    elif stale_sources > 0:
        level = "LOW"
        if "STALE_DATA_SOURCE" not in flags:
            flags.append("STALE_DATA_SOURCE")
    elif partial_sources > 0:
        level = "LOW"
        flags.append("PARTIAL_DATA")
    else:
        # All sources available — start from data_mode baseline
        if data_mode == "SYNTHETIC_DEMO":
            level = "MEDIUM"
            flags.append("SYNTHETIC_DEMO_DATA")
        elif data_mode == "FIXTURE":
            level = "MEDIUM"
            flags.append("FIXTURE_DATA")
        else:
            level = "HIGH"

    # ── 3. Apply horizon degradation (only if not already UNKNOWN) ───────────
    if level != "UNKNOWN" and horizon_hours > 72:
        flags.append("EXTENDED_HORIZON_REDUCED_CONFIDENCE")
        if level == "HIGH":
            level = "MEDIUM"
        elif level == "MEDIUM":
            level = "LOW"
        # Already LOW stays LOW

    if horizon_hours > 120:
        flags.append("INSUFFICIENT_VALIDATION")
        level = "UNKNOWN"

    # ── 4. Map level to score ────────────────────────────────────────────────
    # NOTE: These are ordinal descriptors, not calibrated probabilities.
    _LEVEL_SCORE = {
        "HIGH":    0.85,
        "MEDIUM":  0.60,
        "LOW":     0.35,
        "UNKNOWN": None,
    }
    score = _LEVEL_SCORE.get(level)

    # ── 5. Choose horizon policy ─────────────────────────────────────────────
    if invalid_sources > 0 or horizon_hours > 120:
        horizon_policy = _HORIZON_POLICY_UNKNOWN
    else:
        horizon_policy = dict(_HORIZON_POLICY_SYNTHETIC)
        # Degrade individual steps based on overall level
        if level in ("LOW", "UNKNOWN"):
            for k in ["96h", "120h"]:
                horizon_policy[k] = "LOW"
        if level == "UNKNOWN":
            horizon_policy = _HORIZON_POLICY_UNKNOWN

    # ── 6. Build assessment basis ────────────────────────────────────────────
    basis_parts = []
    if data_mode == "SYNTHETIC_DEMO":
        basis_parts.append("SYNTHETIC_DEMO fixture data (not live satellite)")
    elif data_mode == "FIXTURE":
        basis_parts.append("Fixture data (not live)")
    else:
        basis_parts.append("Live data sources")

    if invalid_sources:
        basis_parts.append(f"{invalid_sources} source(s) invalid/unavailable")
    if stale_sources:
        basis_parts.append(f"{stale_sources} source(s) stale")
    if partial_sources:
        basis_parts.append(f"{partial_sources} source(s) partial")
    if horizon_hours > 72:
        basis_parts.append(f"{horizon_hours}h forecast horizon (extended)")

    basis_parts.append("No historical forecast error data available (not invented)")

    assessment_basis = "; ".join(basis_parts) + "."

    logger.debug(
        "Forecast confidence: level=%s score=%s flags=%s horizon=%dh",
        level, score, flags, horizon_hours,
    )

    return {
        "level": level,
        "score": score,
        "degradation_flags": flags,
        "horizon_policy": horizon_policy,
        "assessment_basis": assessment_basis,
    }
