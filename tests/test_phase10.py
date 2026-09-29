"""
tests/test_phase10.py
Phase 10 hardening regression tests for HimDrishti.
SIH 2026 - PS 26059

Covers every finding fixed in Phase 10 (H1-H7):
  H5  - forecast_horizon_hours must be multiple of 24 (backend validation)
  H6  - empty pipeline result: structured failure not silent empty list
  H4  - FastAPI validation error arrays render as readable strings (contract)
  Schema integrity - data_mode, prototype_notice, recommended_route_id,
                     risk_budget_status, forecast_confidence always valid
  Departure-window - naive timestamp rejected with 422

H1 (AbortController), H2 (UTC normalizer), H3 (Captain reset) are
frontend-only; verified via npm run build.

Run with:
    pytest tests/test_phase10.py -v
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

# Shared valid request payload
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


def _req(**overrides):
    """Return a deep copy of _VALID with overrides applied."""
    r = copy.deepcopy(_VALID)
    r.update(overrides)
    return r


# ---------------------------------------------------------------------------
# H5: forecast_horizon_hours must be a multiple of 24
# ---------------------------------------------------------------------------

class TestForecastHorizonValidation:
    """H5 - forecast_horizon_hours % 24 == 0 is now enforced (was description-only)."""

    def test_non_multiple_25_rejected(self):
        resp = client.post("/api/v1/routes/generate", json=_req(forecast_horizon_hours=25))
        assert resp.status_code == 422, f"Expected 422 for horizon=25, got {resp.status_code}"

    def test_non_multiple_37_rejected(self):
        resp = client.post("/api/v1/routes/generate", json=_req(forecast_horizon_hours=37))
        assert resp.status_code == 422

    def test_non_multiple_100_rejected(self):
        resp = client.post("/api/v1/routes/generate", json=_req(forecast_horizon_hours=100))
        assert resp.status_code == 422

    def test_valid_120_accepted(self):
        resp = client.post("/api/v1/routes/generate", json=_req(forecast_horizon_hours=120))
        assert resp.status_code == 200

    def test_boundary_24_accepted(self):
        resp = client.post("/api/v1/routes/generate", json=_req(forecast_horizon_hours=24))
        assert resp.status_code == 200

    def test_boundary_240_accepted(self):
        resp = client.post("/api/v1/routes/generate", json=_req(forecast_horizon_hours=240))
        assert resp.status_code == 200

    def test_below_24_rejected(self):
        resp = client.post("/api/v1/routes/generate", json=_req(forecast_horizon_hours=12))
        assert resp.status_code == 422

    def test_above_240_rejected(self):
        resp = client.post("/api/v1/routes/generate", json=_req(forecast_horizon_hours=264))
        assert resp.status_code == 422

    def test_error_message_mentions_24(self):
        """422 detail must be human-readable and reference the constraint."""
        resp = client.post("/api/v1/routes/generate", json=_req(forecast_horizon_hours=25))
        detail_str = str(resp.json().get("detail", "")).lower()
        assert "24" in detail_str, f"422 should mention '24', got: {resp.json()}"


# ---------------------------------------------------------------------------
# H4: FastAPI validation error arrays are structured and readable
# ---------------------------------------------------------------------------

class TestValidationErrorReadability:
    """H4 - FastAPI returns detail as list of loc/msg/type objects."""

    def test_missing_origin_detail_is_array(self):
        bad = copy.deepcopy(_VALID)
        del bad["origin"]
        resp = client.post("/api/v1/routes/generate", json=bad)
        assert resp.status_code == 422
        detail = resp.json().get("detail")
        assert isinstance(detail, list), f"Expected list detail, got: {type(detail)}"
        for item in detail:
            assert "msg" in item, f"Validation error missing 'msg': {item}"
            assert "loc" in item, f"Validation error missing 'loc': {item}"

    def test_invalid_lat_detail_is_array(self):
        bad = copy.deepcopy(_VALID)
        bad["origin"]["lat"] = 999.0
        resp = client.post("/api/v1/routes/generate", json=bad)
        assert resp.status_code == 422
        assert isinstance(resp.json().get("detail"), list)

    def test_naive_timestamp_detail_mentions_tz(self):
        """Naive timestamp must produce a 422 mentioning timezone."""
        resp = client.post(
            "/api/v1/routes/generate",
            json=_req(departure_time="2026-05-21T12:00:00"),  # no Z
        )
        assert resp.status_code == 422
        body_str = str(resp.json()).lower()
        assert any(kw in body_str for kw in ("timezone", "utc", "aware")), (
            f"422 for naive timestamp should mention timezone: {resp.json()}"
        )


# ---------------------------------------------------------------------------
# H6: Structured failure when pipeline returns no routes
# ---------------------------------------------------------------------------

class TestEmptyPipelineStructuredFailure:
    """
    H6 - recommended_route_id is now Optional[str]; run_log has diagnostics.
    On normal fixture data the pipeline succeeds; we verify the schema contract.
    """

    @pytest.fixture(scope="class")
    def body(self):
        resp = client.post("/api/v1/routes/generate", json=_VALID)
        assert resp.status_code == 200
        return resp.json()

    def test_recommended_route_id_not_none_on_success(self, body):
        rec_id = body.get("recommended_route_id")
        assert rec_id is not None
        assert isinstance(rec_id, str) and len(rec_id) > 0

    def test_routes_not_empty_on_success(self, body):
        assert len(body.get("routes", [])) > 0

    def test_run_log_present(self, body):
        assert "run_log" in body, "run_log missing from 200 response"

    def test_run_log_has_required_keys(self, body):
        log = body.get("run_log", {})
        for key in ("run_id", "operating_mode", "risk_budget_limit",
                    "forecast_horizon_hours", "data_mode", "pipeline_success"):
            assert key in log, f"run_log missing key: {key}"

    def test_pipeline_warnings_is_list(self, body):
        assert isinstance(body.get("pipeline_warnings"), list)


# ---------------------------------------------------------------------------
# Schema integrity
# ---------------------------------------------------------------------------

class TestResponseSchemaIntegrity:
    """Every required field must be present and valid in a 200 response."""

    @pytest.fixture(scope="class")
    def body(self):
        resp = client.post("/api/v1/routes/generate", json=_VALID)
        assert resp.status_code == 200
        return resp.json()

    def test_data_mode_is_valid_enum(self, body):
        assert body.get("data_mode") in ("SYNTHETIC_DEMO", "FIXTURE", "LIVE")

    def test_prototype_notice_non_empty(self, body):
        notice = body.get("prototype_notice", "")
        assert isinstance(notice, str) and len(notice) > 0

    def test_recommended_route_id_in_routes_list(self, body):
        rec_id = body.get("recommended_route_id")
        route_ids = [r["route_id"] for r in body.get("routes", [])]
        assert rec_id in route_ids, f"recommended_route_id '{rec_id}' not in {route_ids}"

    def test_risk_budget_status_on_all_routes(self, body):
        for route in body.get("routes", []):
            rbs = route.get("risk_budget_status")
            assert rbs is not None, f"Route '{route.get('route_id')}' missing risk_budget_status"
            assert rbs.get("status") in (
                "WITHIN_BUDGET", "EXCEEDS_BUDGET", "NO_ROUTE_WITHIN_RISK_BUDGET"
            ), f"Unexpected risk_budget_status: {rbs}"

    def test_forecast_confidence_level_valid(self, body):
        fc = body.get("forecast_confidence")
        if fc is None:
            pytest.skip("forecast_confidence not in response")
        assert fc.get("level") in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"), (
            f"forecast_confidence.level not valid: {fc.get('level')}"
        )

    def test_system_explanation_non_empty_on_all_routes(self, body):
        for route in body.get("routes", []):
            expl = route.get("system_explanation", "")
            assert isinstance(expl, str) and len(expl) > 0, (
                f"Route '{route.get('route_id')}' has empty system_explanation"
            )

    def test_no_prohibited_language_in_route_names(self, body):
        prohibited = ("safe route", "certified", "guaranteed", "ai selected")
        for route in body.get("routes", []):
            name_lower = (route.get("name") or "").lower()
            for term in prohibited:
                assert term not in name_lower, (
                    f"Prohibited term '{term}' in route name: {route.get('name')}"
                )

    def test_operating_mode_valid(self, body):
        assert body.get("operating_mode") in ("SAFETY_FIRST", "BALANCED", "FUEL_SAVER")

    def test_request_id_present(self, body):
        assert len(body.get("request_id", "")) > 0

    def test_generated_at_is_utc(self, body):
        ts = body.get("generated_at", "")
        assert "T" in ts
        assert ts.endswith("Z") or ts.endswith("+00:00"), f"generated_at not UTC: {ts}"


# ---------------------------------------------------------------------------
# Departure-window endpoint validation
# ---------------------------------------------------------------------------

class TestDepartureWindowValidation:

    _BASE = {
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
        "candidate_offsets_hours": [0, 6, 12, 24],
    }

    def test_naive_base_departure_time_rejected(self):
        bad = copy.deepcopy(self._BASE)
        bad["base_departure_time"] = "2026-05-21T12:00:00"  # no Z
        resp = client.post("/api/v1/planning/departure-windows", json=bad)
        assert resp.status_code == 422, (
            f"Expected 422 for naive departure_time, got {resp.status_code}"
        )

    def test_non_multiple_horizon_rejected(self):
        bad = copy.deepcopy(self._BASE)
        bad["forecast_horizon_hours"] = 50  # not multiple of 24
        resp = client.post("/api/v1/planning/departure-windows", json=bad)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Phase 6-9 regression guard
# ---------------------------------------------------------------------------

class TestPhase69RegressionGuard:
    """Confirm Phase 10 changes introduced no regressions in existing endpoints."""

    def test_health_200(self):
        assert client.get("/health").status_code == 200

    def test_forecast_200(self):
        assert client.get("/api/v1/forecast?horizon_hours=48").status_code == 200

    def test_provenance_200(self):
        assert client.get("/api/v1/provenance").status_code == 200

    def test_alerts_200(self):
        assert client.get("/api/v1/alerts").status_code == 200

    def test_risk_recommended_200(self):
        assert client.get("/api/v1/risk/recommended").status_code == 200

    def test_risk_unknown_404(self):
        assert client.get("/api/v1/risk/does_not_exist").status_code == 404

    def test_routes_generate_200(self):
        assert client.post("/api/v1/routes/generate", json=_VALID).status_code == 200

    def test_forecast_invalid_422(self):
        assert client.get("/api/v1/forecast?horizon_hours=abc").status_code == 422
