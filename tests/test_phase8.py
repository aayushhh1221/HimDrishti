"""
tests/test_phase8.py
----------------------
Phase 8 tests: risk-budgeted decision intelligence.
SIH 2026 · PS 26059

16 test classes covering:
  1.  Risk budget schema
  2.  Safety-first mode weights
  3.  Balanced mode weights
  4.  Fuel-saver mode weights
  5.  Risk-budget constraint WITHIN_BUDGET
  6.  Risk-budget constraint EXCEEDS_BUDGET
  7.  No route within budget
  8.  Counterfactual deltas from actual values
  9.  Counterfactual missing metric → None, not fabricated
  10. Forecast confidence SYNTHETIC_DEMO baseline
  11. Forecast degradation — stale source
  12. Horizon policy — extended horizon
  13. Stale data handling
  14. Partial data handling
  15. Extreme risk acknowledgement gate
  16. API response schema — all Phase 8 fields present

CRITICAL: Phase 6 (test_data_pipeline.py) + Phase 7 (test_api.py) must
continue passing unmodified.

DESIGN NOTE:
  Tests that call POST /api/v1/routes/generate will invoke the full
  pipeline (~30s each). Tests that test the service functions directly
  are fast (< 1s). Fast tests use service functions directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from backend.main import app
from backend.schemas.requests import GenerateRoutesRequest, OperatingMode, RiskBudget
from backend.schemas.responses import (
    CounterfactualComparison,
    ForecastConfidence,
    GenerateRoutesResponse,
    WholeVoyageRisk,
)
from backend.services.risk_budget import (
    NO_ROUTE_WITHIN_RISK_BUDGET,
    apply_operating_mode,
    evaluate_risk_budget,
    normalize_risk,
)
from backend.services.counterfactual import compute_counterfactuals
from backend.services.forecast_confidence import assess_forecast_confidence

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared valid request payload
# ---------------------------------------------------------------------------

_VALID_REQUEST = {
    "origin": {"name": "Cape Town, South Africa", "lat": -33.93, "lon": 18.42},
    "destination": {"name": "Bharati Station", "lat": -69.41, "lon": 76.19},
    "departure_time": "2026-05-21T12:00:00Z",
    "vessel": {
        "name": "MV Sagar Nidhi",
        "ice_class": "PC3_PC5",
        "draft_m": 6.5,
        "speed_knots": 12.0,
    },
    "forecast_horizon_hours": 120,
    "operating_mode": "BALANCED",
    "risk_budget": {
        "max_acceptable_risk": 0.55,
        "uncertainty_weight": 0.5,
    },
    "extreme_risk_acknowledged": False,
}


# ===========================================================================
# 1. Risk budget schema
# ===========================================================================

class TestRiskBudgetSchema:
    """Risk budget Pydantic model parses correctly."""

    def test_valid_budget_parses(self):
        b = RiskBudget(max_acceptable_risk=0.40)
        assert b.max_acceptable_risk == 0.40
        assert b.uncertainty_weight == 0.5  # default

    def test_budget_below_zero_raises(self):
        with pytest.raises(Exception):
            RiskBudget(max_acceptable_risk=-0.1)

    def test_budget_above_one_raises(self):
        with pytest.raises(Exception):
            RiskBudget(max_acceptable_risk=1.1)

    def test_budget_zero_valid(self):
        b = RiskBudget(max_acceptable_risk=0.0)
        assert b.max_acceptable_risk == 0.0

    def test_budget_one_valid(self):
        b = RiskBudget(max_acceptable_risk=1.0)
        assert b.max_acceptable_risk == 1.0

    def test_operating_mode_enum_values(self):
        assert OperatingMode.SAFETY_FIRST.value == "SAFETY_FIRST"
        assert OperatingMode.BALANCED.value == "BALANCED"
        assert OperatingMode.FUEL_SAVER.value == "FUEL_SAVER"


# ===========================================================================
# 2. Safety-first mode
# ===========================================================================

class TestSafetyFirstMode:
    """SAFETY_FIRST mode has highest risk weight."""

    def test_safety_first_risk_weight_high(self):
        w = apply_operating_mode("SAFETY_FIRST")
        assert w.risk_weight >= 6.0, "SAFETY_FIRST must have high risk_weight"

    def test_safety_first_fuel_weight_low(self):
        w = apply_operating_mode("SAFETY_FIRST")
        assert w.fuel_weight <= 0.5, "SAFETY_FIRST must have low fuel_weight"

    def test_safety_first_risk_weight_exceeds_fuel_saver(self):
        sf = apply_operating_mode("SAFETY_FIRST")
        fs = apply_operating_mode("FUEL_SAVER")
        assert sf.risk_weight > fs.risk_weight


# ===========================================================================
# 3. Balanced mode
# ===========================================================================

class TestBalancedMode:
    """BALANCED mode uses moderate weights."""

    def test_balanced_is_default(self):
        w = apply_operating_mode("BALANCED")
        assert w.risk_weight == 4.0
        assert w.fuel_weight == 0.4
        assert w.time_weight == 1.0

    def test_balanced_risk_between_modes(self):
        sf = apply_operating_mode("SAFETY_FIRST")
        bal = apply_operating_mode("BALANCED")
        fs = apply_operating_mode("FUEL_SAVER")
        assert fs.risk_weight <= bal.risk_weight <= sf.risk_weight


# ===========================================================================
# 4. Fuel-saver mode
# ===========================================================================

class TestFuelSaverMode:
    """FUEL_SAVER mode prioritizes fuel but does not disable risk budget."""

    def test_fuel_saver_fuel_weight_high(self):
        w = apply_operating_mode("FUEL_SAVER")
        assert w.fuel_weight > 1.0, "FUEL_SAVER must have elevated fuel_weight"

    def test_fuel_saver_risk_weight_lower_than_safety_first(self):
        sf = apply_operating_mode("SAFETY_FIRST")
        fs = apply_operating_mode("FUEL_SAVER")
        assert fs.risk_weight < sf.risk_weight

    def test_fuel_saver_risk_weight_still_positive(self):
        w = apply_operating_mode("FUEL_SAVER")
        assert w.risk_weight > 0, "Risk is never zero — budget still enforced"


# ===========================================================================
# 5. Risk budget constraint — WITHIN_BUDGET
# ===========================================================================

class TestRiskBudgetWithin:
    """Route risk within budget → WITHIN_BUDGET status."""

    def test_low_risk_within_high_budget(self):
        result = evaluate_risk_budget("recommended", raw_risk_cost=0.5, max_acceptable_risk=0.55)
        assert result["status"] == "WITHIN_BUDGET"

    def test_zero_risk_within_any_budget(self):
        result = evaluate_risk_budget("recommended", raw_risk_cost=0.0, max_acceptable_risk=0.1)
        assert result["status"] == "WITHIN_BUDGET"

    def test_actual_risk_in_response(self):
        result = evaluate_risk_budget("recommended", raw_risk_cost=2.0, max_acceptable_risk=0.55)
        assert result["actual_risk"] is not None
        assert isinstance(result["actual_risk"], float)

    def test_budget_limit_echoed(self):
        result = evaluate_risk_budget("test", raw_risk_cost=1.0, max_acceptable_risk=0.40)
        assert result["budget_limit"] == 0.40


# ===========================================================================
# 6. Risk budget constraint — EXCEEDS_BUDGET
# ===========================================================================

class TestRiskBudgetExceeds:
    """Route risk exceeds budget → EXCEEDS_BUDGET status."""

    def test_high_risk_exceeds_tight_budget(self):
        result = evaluate_risk_budget("higher-risk", raw_risk_cost=6.0, max_acceptable_risk=0.35)
        assert result["status"] == "EXCEEDS_BUDGET"

    def test_normalized_risk_above_budget(self):
        result = evaluate_risk_budget("higher-risk", raw_risk_cost=8.0, max_acceptable_risk=0.50)
        assert result["actual_risk"] > result["budget_limit"]

    def test_exceeds_not_within(self):
        result = evaluate_risk_budget("r", raw_risk_cost=9.0, max_acceptable_risk=0.55)
        assert result["status"] != "WITHIN_BUDGET"


# ===========================================================================
# 7. No route within budget
# ===========================================================================

class TestNoRouteWithinBudget:
    """When no route found, response is structured — not fabricated."""

    def test_none_risk_returns_no_route_sentinel(self):
        result = evaluate_risk_budget("impossible", raw_risk_cost=None, max_acceptable_risk=0.1)
        assert result["status"] == NO_ROUTE_WITHIN_RISK_BUDGET

    def test_no_route_actual_risk_is_none(self):
        result = evaluate_risk_budget("impossible", raw_risk_cost=None, max_acceptable_risk=0.1)
        assert result["actual_risk"] is None

    def test_no_route_budget_limit_still_present(self):
        result = evaluate_risk_budget("impossible", raw_risk_cost=None, max_acceptable_risk=0.30)
        assert result["budget_limit"] == 0.30


# ===========================================================================
# 8. Counterfactual deltas from actual values
# ===========================================================================

class TestCounterfactualDeltas:
    """Deltas are calculated from actual route outputs — not invented."""

    _ROUTES = [
        {
            "route_id": "recommended",
            "name": "Recommended Route",
            "cost_breakdown": {"time_hours": 134.0, "fuel_tonnes": 142.0, "risk_cost": 1.5, "weighted_cost": 200.0},
            "metrics": {"distance_km": None, "uncertainty_contribution": 0.53},
            "risk_budget_status": {"status": "WITHIN_BUDGET"},
        },
        {
            "route_id": "alternative1",
            "name": "Alternative Route 1",
            "cost_breakdown": {"time_hours": 124.6, "fuel_tonnes": 127.8, "risk_cost": 3.45, "weighted_cost": 190.0},
            "metrics": {"distance_km": None, "uncertainty_contribution": 1.55},
            "risk_budget_status": {"status": "WITHIN_BUDGET"},
        },
        {
            "route_id": "higher-risk",
            "name": "Higher Risk Route",
            "cost_breakdown": {"time_hours": 112.6, "fuel_tonnes": 115.1, "risk_cost": 6.0, "weighted_cost": 165.0},
            "metrics": {"distance_km": None, "uncertainty_contribution": 3.6},
            "risk_budget_status": {"status": "EXCEEDS_BUDGET"},
        },
    ]

    def test_comparisons_count(self):
        cf = compute_counterfactuals(self._ROUTES, "recommended")
        assert len(cf["comparisons"]) == 2

    def test_fuel_delta_is_calculated(self):
        cf = compute_counterfactuals(self._ROUTES, "recommended")
        alt = next(c for c in cf["comparisons"] if c["route_id"] == "alternative1")
        assert alt["fuel_delta_pct"] is not None
        # alternative1 fuel 127.8 vs recommended 142.0 → negative (less fuel)
        assert alt["fuel_delta_pct"] < 0

    def test_eta_delta_is_calculated(self):
        cf = compute_counterfactuals(self._ROUTES, "recommended")
        alt = next(c for c in cf["comparisons"] if c["route_id"] == "alternative1")
        assert alt["eta_delta_hours"] is not None
        # alternative1 time 124.6 vs recommended 134.0 → negative (shorter)
        assert alt["eta_delta_hours"] < 0

    def test_risk_delta_is_calculated(self):
        cf = compute_counterfactuals(self._ROUTES, "recommended")
        higher = next(c for c in cf["comparisons"] if c["route_id"] == "higher-risk")
        assert higher["risk_delta_pct"] is not None
        # higher-risk risk 6.0 vs recommended 1.5 → positive (more risk)
        assert higher["risk_delta_pct"] > 0

    def test_baseline_excluded_from_comparisons(self):
        cf = compute_counterfactuals(self._ROUTES, "recommended")
        ids = [c["route_id"] for c in cf["comparisons"]]
        assert "recommended" not in ids

    def test_baseline_route_id_set(self):
        cf = compute_counterfactuals(self._ROUTES, "recommended")
        assert cf["baseline_route_id"] == "recommended"


# ===========================================================================
# 9. Counterfactual missing metric → None
# ===========================================================================

class TestCounterfactualMissingMetric:
    """Missing metrics are None — never fabricated."""

    _ROUTES_NO_DISTANCE = [
        {
            "route_id": "recommended",
            "name": "Recommended Route",
            "cost_breakdown": {"time_hours": 134.0, "fuel_tonnes": 142.0, "risk_cost": 1.5, "weighted_cost": 200.0},
            "metrics": {"distance_km": None, "uncertainty_contribution": None},
            "risk_budget_status": None,
        },
        {
            "route_id": "alternative1",
            "name": "Alternative Route 1",
            "cost_breakdown": {"time_hours": 124.0, "fuel_tonnes": 128.0, "risk_cost": 3.4, "weighted_cost": 190.0},
            "metrics": {"distance_km": None, "uncertainty_contribution": None},
            "risk_budget_status": None,
        },
    ]

    def test_distance_delta_none_when_unavailable(self):
        cf = compute_counterfactuals(self._ROUTES_NO_DISTANCE, "recommended")
        alt = cf["comparisons"][0]
        assert alt["distance_delta_km"] is None

    def test_uncertainty_delta_none_when_unavailable(self):
        cf = compute_counterfactuals(self._ROUTES_NO_DISTANCE, "recommended")
        alt = cf["comparisons"][0]
        assert alt["uncertainty_delta_pct"] is None

    def test_fuel_delta_still_computed_when_available(self):
        cf = compute_counterfactuals(self._ROUTES_NO_DISTANCE, "recommended")
        alt = cf["comparisons"][0]
        # fuel is available even though distance is not
        assert alt["fuel_delta_pct"] is not None

    def test_missing_baseline_returns_empty(self):
        cf = compute_counterfactuals(self._ROUTES_NO_DISTANCE, "nonexistent_id")
        assert cf["comparisons"] == []


# ===========================================================================
# 10. Forecast confidence — SYNTHETIC_DEMO baseline
# ===========================================================================

class TestForecastConfidenceSynthetic:
    """SYNTHETIC_DEMO data → MEDIUM baseline confidence."""

    def test_synthetic_demo_medium_level(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "available", "wind": "available"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=48,
        )
        assert result["level"] == "MEDIUM"

    def test_synthetic_flag_present(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "available"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=24,
        )
        assert "SYNTHETIC_DEMO_DATA" in result["degradation_flags"]

    def test_score_present_for_medium(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "available"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=24,
        )
        assert result["score"] == 0.60

    def test_horizon_policy_keys_present(self):
        result = assess_forecast_confidence(
            data_quality_summary={},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=120,
        )
        assert "0h" in result["horizon_policy"]
        assert "120h" in result["horizon_policy"]


# ===========================================================================
# 11. Forecast degradation — stale source
# ===========================================================================

class TestForecastDegradationStale:
    """Stale data source degrades confidence to LOW."""

    def test_stale_source_low_level(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "stale (12h old)", "wind": "available"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=48,
        )
        assert result["level"] == "LOW"

    def test_stale_flag_added(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "stale"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=24,
        )
        flags = result["degradation_flags"]
        assert any("STALE" in f for f in flags)

    def test_stale_score_lower_than_medium(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "stale"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=24,
        )
        assert result["score"] == 0.35


# ===========================================================================
# 12. Horizon policy — extended horizon
# ===========================================================================

class TestHorizonPolicy:
    """Extended horizon reduces confidence."""

    def test_120h_horizon_low_confidence(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "available"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=120,
        )
        assert result["level"] == "LOW"

    def test_extended_horizon_flag(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "available"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=96,
        )
        assert "EXTENDED_HORIZON_REDUCED_CONFIDENCE" in result["degradation_flags"]

    def test_24h_not_extended(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "available"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=24,
        )
        assert "EXTENDED_HORIZON_REDUCED_CONFIDENCE" not in result["degradation_flags"]

    def test_horizon_policy_120h_not_high(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "available"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=120,
        )
        assert result["horizon_policy"]["120h"] in ("LOW", "MEDIUM", "UNKNOWN")
        assert result["horizon_policy"]["120h"] != "HIGH"


# ===========================================================================
# 13. Stale data handling via data_quality_summary
# ===========================================================================

class TestStaleDataHandling:
    """Stale data quality string correctly detected."""

    def test_stale_string_detected(self):
        result = assess_forecast_confidence(
            data_quality_summary={"wind": "stale — last updated 18h ago"},
            data_mode="LIVE",
            horizon_hours=48,
        )
        assert result["level"] in ("LOW", "UNKNOWN")

    def test_available_string_not_stale(self):
        result = assess_forecast_confidence(
            data_quality_summary={"wind": "available (SYNTHETIC_DEMO fixture)"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=24,
        )
        # Should not add stale flag
        flags = result["degradation_flags"]
        assert not any("STALE" in f for f in flags if "SYNTHETIC" not in f)


# ===========================================================================
# 14. Partial data handling
# ===========================================================================

class TestPartialDataHandling:
    """Partial data degrades confidence and adds PARTIAL_DATA flag."""

    def test_partial_adds_flag(self):
        result = assess_forecast_confidence(
            data_quality_summary={"ocean_current": "partial (sparse coverage)"},
            data_mode="SYNTHETIC_DEMO",
            horizon_hours=48,
        )
        assert "PARTIAL_DATA" in result["degradation_flags"]

    def test_partial_degrades_level(self):
        result = assess_forecast_confidence(
            data_quality_summary={"sea_ice": "partial"},
            data_mode="LIVE",
            horizon_hours=24,
        )
        assert result["level"] in ("LOW", "UNKNOWN")


# ===========================================================================
# 15. Extreme risk acknowledgement gate
# ===========================================================================

class TestExtremeRiskAcknowledgement:
    """risk > 0.70 without acknowledgement → HTTP 422."""

    def test_high_risk_no_ack_returns_422(self):
        payload = dict(_VALID_REQUEST)
        payload["risk_budget"] = {"max_acceptable_risk": 0.80}
        payload["extreme_risk_acknowledged"] = False
        resp = client.post("/api/v1/routes/generate", json=payload)
        assert resp.status_code == 422

    def test_high_risk_with_ack_passes_validation(self):
        """With acknowledgement, the request should at least pass schema validation."""
        payload = dict(_VALID_REQUEST)
        payload["risk_budget"] = {"max_acceptable_risk": 0.80}
        payload["extreme_risk_acknowledged"] = True
        resp = client.post("/api/v1/routes/generate", json=payload)
        # The pipeline may succeed or return a server error, but NOT 422
        assert resp.status_code != 422

    def test_normal_risk_no_ack_ok(self):
        """Normal risk tolerance (≤ 0.70) does not require acknowledgement."""
        payload = dict(_VALID_REQUEST)
        payload["risk_budget"] = {"max_acceptable_risk": 0.55}
        payload["extreme_risk_acknowledged"] = False
        resp = client.post("/api/v1/routes/generate", json=payload)
        assert resp.status_code != 422

    def test_exactly_070_no_ack_ok(self):
        """Exactly 0.70 does not require acknowledgement (> 0.70 does)."""
        payload = dict(_VALID_REQUEST)
        payload["risk_budget"] = {"max_acceptable_risk": 0.70}
        payload["extreme_risk_acknowledged"] = False
        resp = client.post("/api/v1/routes/generate", json=payload)
        assert resp.status_code != 422


# ===========================================================================
# 16. API response schema — Phase 8 fields present
# ===========================================================================

class TestPhase8APIResponseSchema:
    """All Phase 8 fields are present in the API response."""

    @pytest.fixture(scope="class")
    def response_body(self):
        resp = client.post("/api/v1/routes/generate", json=_VALID_REQUEST)
        assert resp.status_code == 200
        return resp.json()

    def test_operating_mode_present(self, response_body):
        assert "operating_mode" in response_body
        assert response_body["operating_mode"] in ("SAFETY_FIRST", "BALANCED", "FUEL_SAVER")

    def test_risk_budget_limit_present(self, response_body):
        assert "risk_budget_limit" in response_body
        assert isinstance(response_body["risk_budget_limit"], float)

    def test_counterfactual_present(self, response_body):
        assert "counterfactual" in response_body
        cf = response_body["counterfactual"]
        assert cf is not None
        assert "baseline_route_id" in cf
        assert "comparisons" in cf

    def test_counterfactual_comparisons_not_empty(self, response_body):
        cf = response_body["counterfactual"]
        assert len(cf["comparisons"]) > 0

    def test_counterfactual_has_fuel_delta(self, response_body):
        cf = response_body["counterfactual"]
        comp = cf["comparisons"][0]
        assert "fuel_delta_pct" in comp

    def test_forecast_confidence_present(self, response_body):
        assert "forecast_confidence" in response_body
        fc = response_body["forecast_confidence"]
        assert fc is not None
        assert fc["level"] in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")

    def test_forecast_confidence_has_horizon_policy(self, response_body):
        fc = response_body["forecast_confidence"]
        assert "horizon_policy" in fc
        assert "0h" in fc["horizon_policy"]

    def test_whole_voyage_risk_present(self, response_body):
        assert "whole_voyage_risk" in response_body
        wvr = response_body["whole_voyage_risk"]
        assert wvr is not None

    def test_run_log_present(self, response_body):
        assert "run_log" in response_body
        rl = response_body["run_log"]
        assert "run_id" in rl
        assert "operating_mode" in rl
        assert "risk_budget_limit" in rl
        assert "timestamp_utc" in rl

    def test_routes_have_risk_budget_status(self, response_body):
        for route in response_body["routes"]:
            assert "risk_budget_status" in route
            rbs = route["risk_budget_status"]
            assert rbs is not None
            assert rbs["status"] in (
                "WITHIN_BUDGET", "EXCEEDS_BUDGET", NO_ROUTE_WITHIN_RISK_BUDGET
            )

    def test_routes_have_metrics(self, response_body):
        for route in response_body["routes"]:
            assert "metrics" in route
            assert route["metrics"] is not None

    def test_data_mode_still_present(self, response_body):
        assert response_body["data_mode"] == "SYNTHETIC_DEMO"

    def test_prototype_notice_still_present(self, response_body):
        assert "prototype_notice" in response_body
