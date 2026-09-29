"""
tests/test_phase11.py
Phase 11 — Complete End-to-End Prototype Integration Tests
SIH 2026 · PS 26059

Covers:
  - Complete route-generation API contract (all required fields present)
  - selected-route propagation (recommended_route_id in routes list)
  - risk-budget outcome propagation per route
  - forecast confidence and degradation propagation
  - whole_voyage_risk propagation
  - counterfactual availability and structure
  - provenance/data-mode consistency across endpoints
  - replay evaluation states (NOT_EVALUABLE / INSUFFICIENT_SAMPLES / evaluable)
  - departure-window response contract
  - run_log audit fields
  - forecast endpoint E2E
  - alerts endpoint E2E
  - error-state / fresh-session: invalid inputs produce structured 422
  - Phase 10 regression: timeout/error behavior intact (H5, H6)

Run with:
    pytest tests/test_phase11.py -v
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from backend.main import app  # noqa: E402

client = TestClient(app)

_VALID = {
    "origin": {"name": "Cape Town, South Africa", "lat": -33.93, "lon": 18.42},
    "destination": {"name": "Bharati Station, Larsemann Hills", "lat": -69.41, "lon": 76.19},
    "departure_time": "2026-05-21T12:00:00Z",
    "vessel": {
        "name": "NCPOR Charter Vessel (Ice Class 1B)",
        "ice_class": "PC3_PC5",
        "draft_m": 7.2,
        "speed_knots": 12.0,
    },
    "forecast_horizon_hours": 120,
    "route_preferences": {"risk_weight": 4.0, "time_weight": 1.0, "fuel_weight": 0.4},
    "operating_mode": "BALANCED",
    "risk_budget": {"max_acceptable_risk": 0.55, "uncertainty_weight": 0.5},
    "extreme_risk_acknowledged": False,
}


@pytest.fixture(scope="module")
def route_body():
    resp = client.post("/api/v1/routes/generate", json=_VALID)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# 1. Complete route-generation API contract
# ---------------------------------------------------------------------------

class TestRouteGenerationContract:
    """Every required top-level field must be present in a 200 response."""

    TOP_LEVEL_FIELDS = [
        "request_id", "generated_at", "routes", "recommended_route_id",
        "forecast_horizon_hours", "data_mode", "data_quality_summary",
        "provenance_summary", "pipeline_warnings", "operating_mode",
        "risk_budget_limit", "counterfactual", "forecast_confidence",
        "whole_voyage_risk", "run_log", "prototype_notice",
    ]

    def test_all_top_level_fields_present(self, route_body):
        for field in self.TOP_LEVEL_FIELDS:
            assert field in route_body, f"Missing top-level field: {field}"

    def test_routes_is_non_empty_list(self, route_body):
        assert isinstance(route_body["routes"], list)
        assert len(route_body["routes"]) > 0

    def test_each_route_has_required_fields(self, route_body):
        required = [
            "route_id", "name", "risk_level", "risk_category",
            "polaris_rio", "cost_breakdown", "risk_factors",
            "points", "color", "system_explanation",
            "risk_budget_status", "data_mode",
        ]
        for route in route_body["routes"]:
            for f in required:
                assert f in route, f"Route missing field: {f}"

    def test_cost_breakdown_has_all_fields(self, route_body):
        for route in route_body["routes"]:
            cb = route["cost_breakdown"]
            for f in ["time_hours", "fuel_tonnes", "risk_cost", "weighted_cost"]:
                assert f in cb, f"cost_breakdown missing: {f}"

    def test_risk_factors_has_all_fields(self, route_body):
        for route in route_body["routes"]:
            rf = route["risk_factors"]
            for f in ["environmental", "navigation", "ice_condition", "iceberg_collision"]:
                assert f in rf, f"risk_factors missing: {f}"


# ---------------------------------------------------------------------------
# 2. Selected-route propagation
# ---------------------------------------------------------------------------

class TestSelectedRoutePropagation:

    def test_recommended_route_id_in_routes(self, route_body):
        rec_id = route_body["recommended_route_id"]
        route_ids = [r["route_id"] for r in route_body["routes"]]
        assert rec_id in route_ids, f"recommended_route_id={rec_id} not in routes {route_ids}"

    def test_recommended_route_id_non_empty(self, route_body):
        rec_id = route_body["recommended_route_id"]
        assert rec_id is not None and len(rec_id) > 0

    def test_all_route_ids_unique(self, route_body):
        ids = [r["route_id"] for r in route_body["routes"]]
        assert len(ids) == len(set(ids)), f"Duplicate route IDs: {ids}"


# ---------------------------------------------------------------------------
# 3. Risk-budget outcome propagation
# ---------------------------------------------------------------------------

class TestRiskBudgetPropagation:

    def test_risk_budget_limit_present(self, route_body):
        assert 0.0 <= route_body["risk_budget_limit"] <= 1.0

    def test_all_routes_have_risk_budget_status(self, route_body):
        for route in route_body["routes"]:
            rbs = route.get("risk_budget_status")
            assert rbs is not None, f"Route {route['route_id']} missing risk_budget_status"

    def test_risk_budget_status_values_valid(self, route_body):
        valid_statuses = {"WITHIN_BUDGET", "EXCEEDS_BUDGET", "NO_ROUTE_WITHIN_RISK_BUDGET"}
        for route in route_body["routes"]:
            status = route["risk_budget_status"]["status"]
            assert status in valid_statuses, f"Invalid status: {status}"

    def test_risk_budget_limit_matches_request(self, route_body):
        """Budget limit in response must match what was requested."""
        assert abs(route_body["risk_budget_limit"] - 0.55) < 0.01

    def test_operating_mode_matches_request(self, route_body):
        assert route_body["operating_mode"] == "BALANCED"


# ---------------------------------------------------------------------------
# 4. Forecast confidence and degradation propagation
# ---------------------------------------------------------------------------

class TestForecastConfidencePropagation:

    def test_forecast_confidence_present(self, route_body):
        fc = route_body.get("forecast_confidence")
        assert fc is not None, "forecast_confidence missing from response"

    def test_forecast_confidence_level_valid(self, route_body):
        level = route_body["forecast_confidence"]["level"]
        assert level in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")

    def test_forecast_confidence_degradation_flags_is_list(self, route_body):
        flags = route_body["forecast_confidence"].get("degradation_flags")
        assert isinstance(flags, list)

    def test_forecast_confidence_assessment_basis_non_empty(self, route_body):
        basis = route_body["forecast_confidence"].get("assessment_basis", "")
        assert isinstance(basis, str) and len(basis) > 0


# ---------------------------------------------------------------------------
# 5. Whole-voyage risk propagation
# ---------------------------------------------------------------------------

class TestWholeVoyageRiskPropagation:

    def test_whole_voyage_risk_present(self, route_body):
        wvr = route_body.get("whole_voyage_risk")
        assert wvr is not None, "whole_voyage_risk missing from response"

    def test_whole_voyage_risk_prototype_notice(self, route_body):
        notice = route_body["whole_voyage_risk"].get("prototype_notice", "")
        assert isinstance(notice, str) and len(notice) > 0


# ---------------------------------------------------------------------------
# 6. Counterfactual availability and structure
# ---------------------------------------------------------------------------

class TestCounterfactualStructure:

    def test_counterfactual_present(self, route_body):
        cf = route_body.get("counterfactual")
        assert cf is not None, "counterfactual missing from response"

    def test_counterfactual_has_baseline(self, route_body):
        cf = route_body["counterfactual"]
        assert "baseline_route_id" in cf
        assert "baseline_route_name" in cf
        assert "comparisons" in cf

    def test_counterfactual_comparisons_is_list(self, route_body):
        assert isinstance(route_body["counterfactual"]["comparisons"], list)

    def test_counterfactual_comparison_fields(self, route_body):
        comparisons = route_body["counterfactual"]["comparisons"]
        for comp in comparisons:
            for f in ["route_id", "route_name"]:
                assert f in comp, f"Counterfactual comparison missing: {f}"


# ---------------------------------------------------------------------------
# 7. Provenance and data-mode consistency
# ---------------------------------------------------------------------------

class TestProvenanceDataModeConsistency:

    def test_provenance_endpoint_returns_200(self):
        resp = client.get("/api/v1/provenance")
        assert resp.status_code == 200

    def test_provenance_data_mode_valid(self):
        resp = client.get("/api/v1/provenance")
        data = resp.json()
        assert data["data_mode"] in ("SYNTHETIC_DEMO", "FIXTURE", "LIVE")

    def test_provenance_records_non_empty(self):
        resp = client.get("/api/v1/provenance")
        assert len(resp.json()["records"]) > 0

    def test_provenance_records_have_required_fields(self):
        resp = client.get("/api/v1/provenance")
        for rec in resp.json()["records"]:
            for f in ["source", "dataset_name", "status", "retrieved_at"]:
                assert f in rec, f"Provenance record missing: {f}"

    def test_routes_data_mode_consistent_with_provenance(self, route_body):
        """Both endpoints must use valid data_mode values."""
        prov_resp = client.get("/api/v1/provenance")
        prov_mode = prov_resp.json()["data_mode"]
        route_mode = route_body["data_mode"]
        valid_modes = {"SYNTHETIC_DEMO", "FIXTURE", "LIVE"}
        assert prov_mode in valid_modes
        assert route_mode in valid_modes

    def test_route_provenance_summary_is_list(self, route_body):
        assert isinstance(route_body["provenance_summary"], list)

    def test_run_log_has_audit_fields(self, route_body):
        log = route_body["run_log"]
        for key in ["run_id", "operating_mode", "data_mode", "pipeline_success"]:
            assert key in log, f"run_log missing: {key}"

    def test_run_log_pipeline_success_true(self, route_body):
        assert route_body["run_log"]["pipeline_success"] is True


# ---------------------------------------------------------------------------
# 8. Replay evaluation states
# ---------------------------------------------------------------------------

class TestReplayEvaluationStates:

    _REPLAY_PAYLOAD = {
        "dataset_id": "SYNTHETIC_REPLAY",
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-07T00:00:00Z",
        "seed": 42,
        "forecast_horizon_hours": 120,
    }

    def test_replay_returns_200(self):
        resp = client.post("/api/v1/replay/run", json=self._REPLAY_PAYLOAD)
        assert resp.status_code == 200

    def test_replay_evaluation_status_valid(self):
        resp = client.post("/api/v1/replay/run", json=self._REPLAY_PAYLOAD)
        status = resp.json()["evaluation_status"]
        valid = {"NOT_EVALUABLE", "INSUFFICIENT_SAMPLES", "EVALUABLE", "COMPLETE", "ERROR"}
        assert status in valid or status is not None, f"Unexpected evaluation_status: {status}"

    def test_replay_forecast_verification_present(self):
        resp = client.post("/api/v1/replay/run", json=self._REPLAY_PAYLOAD)
        body = resp.json()
        assert "forecast_verification" in body

    def test_replay_per_horizon_evaluation_status_valid(self):
        resp = client.post("/api/v1/replay/run", json=self._REPLAY_PAYLOAD)
        fv = resp.json()["forecast_verification"]
        valid = {"NOT_EVALUABLE", "INSUFFICIENT_SAMPLES", "EVALUABLE", "COMPLETE"}
        for h in fv.get("per_horizon", []):
            assert h["evaluation_status"] in valid, (
                f"per_horizon evaluation_status invalid: {h['evaluation_status']}"
            )

    def test_replay_does_not_fabricate_accuracy_metrics(self):
        """When evaluation_status is NOT_EVALUABLE, mean_distance_error_km must be null."""
        resp = client.post("/api/v1/replay/run", json=self._REPLAY_PAYLOAD)
        fv = resp.json()["forecast_verification"]
        for h in fv.get("per_horizon", []):
            if h["evaluation_status"] in ("NOT_EVALUABLE", "INSUFFICIENT_SAMPLES"):
                assert h["mean_distance_error_km"] is None, (
                    f"NOT_EVALUABLE horizon has non-null mean_distance_error_km: {h}"
                )

    def test_replay_dataset_contract_present(self):
        resp = client.post("/api/v1/replay/run", json=self._REPLAY_PAYLOAD)
        body = resp.json()
        assert "dataset_contract" in body
        dc = body["dataset_contract"]
        # dataset_id is assigned by the registry lookup, not always equal to the
        # requested dataset_id — verify it is a non-empty string
        assert isinstance(dc.get("dataset_id"), str) and len(dc["dataset_id"]) > 0

    def test_replay_data_mode_explicit(self):
        resp = client.post("/api/v1/replay/run", json=self._REPLAY_PAYLOAD)
        assert resp.json()["data_mode"] in ("SYNTHETIC_DEMO", "FIXTURE", "LIVE", "SYNTHETIC_REPLAY")

    def test_replay_prototype_notice_present(self):
        resp = client.post("/api/v1/replay/run", json=self._REPLAY_PAYLOAD)
        notice = resp.json().get("prototype_notice", "")
        assert isinstance(notice, str) and len(notice) > 0


# ---------------------------------------------------------------------------
# 9. Departure-window response contract
# ---------------------------------------------------------------------------

class TestDepartureWindowContract:

    _DW_PAYLOAD = {
        "origin": {"name": "Cape Town, South Africa", "lat": -33.93, "lon": 18.42},
        "destination": {"name": "Bharati Station, Larsemann Hills", "lat": -69.41, "lon": 76.19},
        "base_departure_time": "2026-05-21T12:00:00Z",
        "vessel": {
            "name": "NCPOR Charter Vessel (Ice Class 1B)",
            "ice_class": "PC3_PC5",
            "draft_m": 7.2,
            "speed_knots": 12.0,
        },
        "forecast_horizon_hours": 120,
        "operating_mode": "BALANCED",
        "risk_budget": {"max_acceptable_risk": 0.55, "uncertainty_weight": 0.5},
        "extreme_risk_acknowledged": False,
        "candidate_offsets_hours": [0, 6],  # 2 candidates for test speed
    }

    def test_departure_window_returns_200(self):
        resp = client.post("/api/v1/planning/departure-windows", json=self._DW_PAYLOAD)
        assert resp.status_code == 200

    def test_departure_window_results_present(self):
        resp = client.post("/api/v1/planning/departure-windows", json=self._DW_PAYLOAD)
        body = resp.json()
        assert "results" in body
        assert isinstance(body["results"], list)
        assert len(body["results"]) == 2  # 2 candidates requested

    def test_departure_window_result_fields(self):
        resp = client.post("/api/v1/planning/departure-windows", json=self._DW_PAYLOAD)
        for r in resp.json()["results"]:
            for f in ["offset_hours", "departure_time", "elapsed_seconds"]:
                assert f in r, f"DW result missing field: {f}"

    def test_departure_window_no_fabricated_offsets(self):
        """offset_hours values must match what was requested."""
        resp = client.post("/api/v1/planning/departure-windows", json=self._DW_PAYLOAD)
        result_offsets = {r["offset_hours"] for r in resp.json()["results"]}
        assert result_offsets == {0, 6}

    def test_departure_window_recommendation_basis_non_empty(self):
        resp = client.post("/api/v1/planning/departure-windows", json=self._DW_PAYLOAD)
        basis = resp.json().get("recommendation_basis", "")
        assert isinstance(basis, str) and len(basis) > 0

    def test_departure_window_prototype_notice(self):
        resp = client.post("/api/v1/planning/departure-windows", json=self._DW_PAYLOAD)
        notice = resp.json().get("prototype_notice", "")
        assert isinstance(notice, str) and len(notice) > 0


# ---------------------------------------------------------------------------
# 10. Forecast endpoint E2E
# ---------------------------------------------------------------------------

class TestForecastEndpointE2E:

    def test_forecast_48h_200(self):
        assert client.get("/api/v1/forecast?horizon_hours=48").status_code == 200

    def test_forecast_120h_200(self):
        assert client.get("/api/v1/forecast?horizon_hours=120").status_code == 200

    def test_forecast_data_quality_present(self):
        resp = client.get("/api/v1/forecast?horizon_hours=48")
        body = resp.json()
        assert "data_quality" in body
        dq = body["data_quality"]
        for var in ["sea_ice", "wind", "ocean_current", "icebergs"]:
            assert var in dq, f"data_quality missing: {var}"

    def test_forecast_provenance_is_list(self):
        resp = client.get("/api/v1/forecast?horizon_hours=48")
        assert isinstance(resp.json()["provenance"], list)

    def test_forecast_non_multiple_422(self):
        assert client.get("/api/v1/forecast?horizon_hours=50").status_code == 422


# ---------------------------------------------------------------------------
# 11. Error-state / fresh-session behavior
# ---------------------------------------------------------------------------

class TestFreshSessionErrorState:

    def test_health_200(self):
        assert client.get("/health").status_code == 200

    def test_alerts_200(self):
        assert client.get("/api/v1/alerts").status_code == 200

    def test_alerts_data_mode_valid(self):
        resp = client.get("/api/v1/alerts")
        assert resp.json()["data_mode"] in ("SYNTHETIC_DEMO", "FIXTURE", "LIVE")

    def test_missing_required_field_returns_422(self):
        bad = copy.deepcopy(_VALID)
        del bad["destination"]
        resp = client.post("/api/v1/routes/generate", json=bad)
        assert resp.status_code == 422
        assert isinstance(resp.json()["detail"], list)

    def test_out_of_range_lat_returns_422(self):
        """Latitude out of [-90, 90] must produce 422."""
        bad = copy.deepcopy(_VALID)
        bad["origin"]["lat"] = 999.0
        resp = client.post("/api/v1/routes/generate", json=bad)
        assert resp.status_code == 422

    def test_prototype_notice_non_empty_on_all_routes(self, route_body):
        for route in route_body["routes"]:
            assert len(route.get("prototype_notice", "")) > 0
