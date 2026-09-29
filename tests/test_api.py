"""
tests/test_api.py
-------------------
Backend API tests for HimDrishti Phase 7.
SIH 2026 · PS 26059

Tests:
  1.  GET /health
  2.  POST /api/v1/routes/generate — invalid request
  3.  POST /api/v1/routes/generate — valid request
  4.  Route response schema validation
  5.  GET /api/v1/risk/recommended
  6.  GET /api/v1/risk/alternative1
  7.  GET /api/v1/risk/higher-risk
  8.  GET /api/v1/risk/unknown → 404
  9.  GET /api/v1/forecast
  10. GET /api/v1/forecast?horizon_hours=invalid → 422
  11. GET /api/v1/provenance
  12. GET /api/v1/alerts
  13. Synthetic/demo mode — all responses carry data_mode
  14. Route response carries prototype_notice
  15. No "safe" / "certified" / "approved" language in route names

Run with:
    pytest tests/test_api.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so backend imports work
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from backend.main import app  # noqa: E402

client = TestClient(app)

_VALID_ROUTE_REQUEST = {
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
    # Phase 8 required fields
    "operating_mode": "BALANCED",
    "risk_budget": {
        "max_acceptable_risk": 0.55,
        "uncertainty_weight": 0.5,
    },
    "extreme_risk_acknowledged": False,
}



# ---------------------------------------------------------------------------
# 1. Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_status_ok(self):
        body = client.get("/health").json()
        assert body["status"] == "ok"

    def test_health_service_name(self):
        body = client.get("/health").json()
        assert body["service"] == "HimDrishti API"

    def test_health_version(self):
        body = client.get("/health").json()
        assert body["version"] == "0.1.0"

    def test_health_prototype_notice_present(self):
        body = client.get("/health").json()
        assert "prototype_notice" in body
        assert len(body["prototype_notice"]) > 10


# ---------------------------------------------------------------------------
# 2. Invalid route request
# ---------------------------------------------------------------------------

class TestInvalidRouteRequest:
    def test_missing_departure_time_returns_422(self):
        payload = dict(_VALID_ROUTE_REQUEST)
        payload.pop("departure_time")
        resp = client.post("/api/v1/routes/generate", json=payload)
        assert resp.status_code == 422

    def test_naive_datetime_returns_422(self):
        payload = {**_VALID_ROUTE_REQUEST, "departure_time": "2026-05-21T12:00:00"}
        resp = client.post("/api/v1/routes/generate", json=payload)
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_invalid_lat_returns_422(self):
        payload = dict(_VALID_ROUTE_REQUEST)
        payload["origin"] = {"name": "Bad", "lat": -100.0, "lon": 0.0}
        resp = client.post("/api/v1/routes/generate", json=payload)
        assert resp.status_code == 422

    def test_invalid_lon_returns_422(self):
        payload = dict(_VALID_ROUTE_REQUEST)
        payload["origin"] = {"name": "Bad", "lat": -33.0, "lon": 200.0}
        resp = client.post("/api/v1/routes/generate", json=payload)
        assert resp.status_code == 422

    def test_negative_draft_returns_422(self):
        payload = dict(_VALID_ROUTE_REQUEST)
        payload["vessel"] = {**_VALID_ROUTE_REQUEST["vessel"], "draft_m": -1.0}
        resp = client.post("/api/v1/routes/generate", json=payload)
        assert resp.status_code == 422

    def test_zero_speed_returns_422(self):
        payload = dict(_VALID_ROUTE_REQUEST)
        payload["vessel"] = {**_VALID_ROUTE_REQUEST["vessel"], "speed_knots": 0.0}
        resp = client.post("/api/v1/routes/generate", json=payload)
        assert resp.status_code == 422

    def test_horizon_below_minimum_returns_422(self):
        payload = {**_VALID_ROUTE_REQUEST, "forecast_horizon_hours": 12}
        resp = client.post("/api/v1/routes/generate", json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 3. Valid route request
# ---------------------------------------------------------------------------

class TestValidRouteRequest:
    def test_returns_200(self):
        resp = client.post("/api/v1/routes/generate", json=_VALID_ROUTE_REQUEST)
        assert resp.status_code == 200, resp.text

    def test_returns_three_routes(self):
        body = client.post("/api/v1/routes/generate", json=_VALID_ROUTE_REQUEST).json()
        assert len(body["routes"]) == 3

    def test_route_ids_present(self):
        body = client.post("/api/v1/routes/generate", json=_VALID_ROUTE_REQUEST).json()
        ids = {r["route_id"] for r in body["routes"]}
        assert "recommended" in ids
        assert "alternative1" in ids
        assert "higher-risk" in ids

    def test_recommended_route_id_set(self):
        body = client.post("/api/v1/routes/generate", json=_VALID_ROUTE_REQUEST).json()
        assert body["recommended_route_id"] == "recommended"

    def test_request_id_present(self):
        body = client.post("/api/v1/routes/generate", json=_VALID_ROUTE_REQUEST).json()
        assert "request_id" in body and len(body["request_id"]) > 0

    def test_generated_at_present(self):
        body = client.post("/api/v1/routes/generate", json=_VALID_ROUTE_REQUEST).json()
        assert "generated_at" in body


# ---------------------------------------------------------------------------
# 4. Route response schema
# ---------------------------------------------------------------------------

class TestRouteResponseSchema:
    def _routes(self):
        return client.post("/api/v1/routes/generate", json=_VALID_ROUTE_REQUEST).json()["routes"]

    def test_each_route_has_points(self):
        for route in self._routes():
            assert len(route["points"]) >= 2, f"Route {route['route_id']} has no geometry"

    def test_each_point_has_lat_lon(self):
        for route in self._routes():
            for pt in route["points"]:
                assert "lat" in pt and "lon" in pt

    def test_each_route_has_cost_breakdown(self):
        for route in self._routes():
            cb = route["cost_breakdown"]
            assert cb["time_hours"] > 0
            assert cb["fuel_tonnes"] > 0

    def test_each_route_has_risk_factors(self):
        for route in self._routes():
            rf = route["risk_factors"]
            for key in ["environmental", "navigation", "ice_condition", "iceberg_collision"]:
                assert key in rf

    def test_each_route_has_color(self):
        for route in self._routes():
            assert route["color"].startswith("#")

    def test_each_route_has_data_mode(self):
        for route in self._routes():
            assert route["data_mode"] in ("SYNTHETIC_DEMO", "FIXTURE", "LIVE")

    def test_each_route_has_prototype_notice(self):
        for route in self._routes():
            assert len(route["prototype_notice"]) > 10

    def test_polaris_rio_is_numeric(self):
        for route in self._routes():
            assert isinstance(route["polaris_rio"], (int, float))


# ---------------------------------------------------------------------------
# 5–7. Risk endpoint — known route IDs
# ---------------------------------------------------------------------------

class TestRiskEndpoint:
    def test_recommended_risk_returns_200(self):
        assert client.get("/api/v1/risk/recommended").status_code == 200

    def test_alternative1_risk_returns_200(self):
        assert client.get("/api/v1/risk/alternative1").status_code == 200

    def test_higher_risk_returns_200(self):
        assert client.get("/api/v1/risk/higher-risk").status_code == 200

    def test_risk_has_polaris_status(self):
        body = client.get("/api/v1/risk/recommended").json()
        assert "ILLUSTRATIVE" in body["polaris_status"].upper()

    def test_risk_has_data_mode(self):
        body = client.get("/api/v1/risk/recommended").json()
        assert body["data_mode"] in ("SYNTHETIC_DEMO", "FIXTURE", "LIVE")

    def test_risk_has_prototype_notice(self):
        body = client.get("/api/v1/risk/recommended").json()
        assert len(body["prototype_notice"]) > 10

    def test_risk_factors_all_present(self):
        body = client.get("/api/v1/risk/recommended").json()
        rf = body["risk_factors"]
        for key in ["environmental", "navigation", "ice_condition", "iceberg_collision"]:
            assert key in rf


# ---------------------------------------------------------------------------
# 8. Risk endpoint — unknown route_id → 404
# ---------------------------------------------------------------------------

class TestRiskEndpointUnknown:
    def test_unknown_route_returns_404(self):
        assert client.get("/api/v1/risk/nonexistent-route").status_code == 404

    def test_404_has_structured_detail(self):
        body = client.get("/api/v1/risk/nonexistent-route").json()
        assert "detail" in body


# ---------------------------------------------------------------------------
# 9. Forecast endpoint
# ---------------------------------------------------------------------------

class TestForecastEndpoint:
    def test_default_returns_200(self):
        assert client.get("/api/v1/forecast").status_code == 200

    def test_horizon_48_returns_200(self):
        assert client.get("/api/v1/forecast?horizon_hours=48").status_code == 200

    def test_horizon_steps_present(self):
        body = client.get("/api/v1/forecast").json()
        assert 0 in body["horizon_steps"]
        assert 120 in body["horizon_steps"]

    def test_data_quality_fields_present(self):
        body = client.get("/api/v1/forecast").json()
        dq = body["data_quality"]
        for key in ["sea_ice", "wind", "ocean_current", "icebergs"]:
            assert key in dq

    def test_data_mode_present(self):
        body = client.get("/api/v1/forecast").json()
        assert body["data_mode"] in ("SYNTHETIC_DEMO", "FIXTURE", "LIVE")


# ---------------------------------------------------------------------------
# 10. Forecast endpoint — invalid horizon → 422
# ---------------------------------------------------------------------------

class TestForecastInvalidHorizon:
    def test_horizon_13_returns_422(self):
        assert client.get("/api/v1/forecast?horizon_hours=13").status_code == 422

    def test_horizon_200_returns_422(self):
        assert client.get("/api/v1/forecast?horizon_hours=200").status_code == 422

    def test_horizon_negative_returns_422(self):
        assert client.get("/api/v1/forecast?horizon_hours=-1").status_code == 422


# ---------------------------------------------------------------------------
# 11. Provenance endpoint
# ---------------------------------------------------------------------------

class TestProvenanceEndpoint:
    def test_returns_200(self):
        assert client.get("/api/v1/provenance").status_code == 200

    def test_records_present(self):
        body = client.get("/api/v1/provenance").json()
        assert len(body["records"]) >= 1

    def test_each_record_has_source(self):
        body = client.get("/api/v1/provenance").json()
        for rec in body["records"]:
            assert "source" in rec and len(rec["source"]) > 0

    def test_each_record_has_dataset_name(self):
        body = client.get("/api/v1/provenance").json()
        for rec in body["records"]:
            assert "dataset_name" in rec

    def test_each_record_has_status(self):
        body = client.get("/api/v1/provenance").json()
        for rec in body["records"]:
            assert "status" in rec

    def test_data_mode_synthetic_demo(self):
        body = client.get("/api/v1/provenance").json()
        assert body["data_mode"] == "SYNTHETIC_DEMO"


# ---------------------------------------------------------------------------
# 12. Alerts endpoint
# ---------------------------------------------------------------------------

class TestAlertsEndpoint:
    def test_returns_200(self):
        assert client.get("/api/v1/alerts").status_code == 200

    def test_alerts_list_present(self):
        body = client.get("/api/v1/alerts").json()
        assert len(body["alerts"]) >= 1

    def test_each_alert_has_severity(self):
        body = client.get("/api/v1/alerts").json()
        for alert in body["alerts"]:
            assert alert["severity"] in ("info", "warning", "critical")

    def test_each_alert_has_data_mode(self):
        body = client.get("/api/v1/alerts").json()
        for alert in body["alerts"]:
            assert "data_mode" in alert

    def test_data_mode_synthetic_demo(self):
        body = client.get("/api/v1/alerts").json()
        assert body["data_mode"] == "SYNTHETIC_DEMO"

    def test_prototype_notice_present(self):
        body = client.get("/api/v1/alerts").json()
        assert len(body["prototype_notice"]) > 10


# ---------------------------------------------------------------------------
# 13. Synthetic/demo mode — all responses carry data_mode
# ---------------------------------------------------------------------------

class TestDataModeEnforcement:
    def test_forecast_has_data_mode(self):
        body = client.get("/api/v1/forecast").json()
        assert "data_mode" in body

    def test_provenance_has_data_mode(self):
        body = client.get("/api/v1/provenance").json()
        assert "data_mode" in body

    def test_alerts_has_data_mode(self):
        body = client.get("/api/v1/alerts").json()
        assert "data_mode" in body

    def test_routes_has_data_mode(self):
        body = client.post("/api/v1/routes/generate", json=_VALID_ROUTE_REQUEST).json()
        assert "data_mode" in body


# ---------------------------------------------------------------------------
# 14. Prototype notice always present
# ---------------------------------------------------------------------------

class TestPrototypeNoticeEnforcement:
    def test_health_has_notice(self):
        assert "prototype_notice" in client.get("/health").json()

    def test_routes_response_has_notice(self):
        body = client.post("/api/v1/routes/generate", json=_VALID_ROUTE_REQUEST).json()
        assert "prototype_notice" in body

    def test_risk_has_notice(self):
        assert "prototype_notice" in client.get("/api/v1/risk/recommended").json()

    def test_provenance_has_notice(self):
        assert "prototype_notice" in client.get("/api/v1/provenance").json()

    def test_alerts_has_notice(self):
        assert "prototype_notice" in client.get("/api/v1/alerts").json()


# ---------------------------------------------------------------------------
# 15. Language convention — no "safe" / "certified" / "approved" in names
# ---------------------------------------------------------------------------

class TestLanguageConvention:
    FORBIDDEN = {"safe route", "certified", "approved", "officially safe", "operationally safe"}

    def _all_route_text(self) -> str:
        body = client.post("/api/v1/routes/generate", json=_VALID_ROUTE_REQUEST).json()
        import json
        return json.dumps(body).lower()

    def test_no_certified_language(self):
        text = self._all_route_text()
        for banned in self.FORBIDDEN:
            assert banned not in text, f"Forbidden phrase '{banned}' found in route response"
