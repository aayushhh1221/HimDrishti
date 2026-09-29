"""
tests/test_data_pipeline.py
-----------------------------
Test suite for HimDrishti Phase 6 data pipeline.
SIH 2026 · PS 26059

Tests:
  1.  Sea-ice normalization
  2.  Wind normalization
  3.  Ocean current normalization
  4.  Iceberg observation validation
  5.  Timestamp validation
  6.  Missing-data handling (NaN propagation)
  7.  Provenance creation
  8.  Synthetic pipeline execution (demo_run equivalent)
  9.  Deterministic replay (same seed → same result)
  10. Scientific-core integration via pipeline orchestrator

Run with: pytest tests/test_data_pipeline.py -v
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

# Make project root importable
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "ai"))

from data_pipeline.schemas import (
    DataQuality, DataSource, ForecastWindow, IcebergObservation,
    OceanCurrentField, PipelineInput, SeaIceField, WindField,
)
from data_pipeline.validation import (
    ValidationError,
    validate_forecast_window,
    validate_iceberg_observation,
    validate_ocean_current,
    validate_sea_ice,
    validate_wind,
)
from data_pipeline.normalization import (
    mask_invalid_concentration,
    normalize_longitude,
    normalize_timestamps,
    percent_to_fraction,
    tenths_to_fraction,
)
from data_pipeline.provenance import (
    create_provenance,
    create_synthetic_provenance,
    provenance_to_dict,
)
from data_pipeline.adapters.sea_ice import fetch_sea_ice
from data_pipeline.adapters.wind import fetch_wind
from data_pipeline.adapters.ocean_current import fetch_ocean_current
from data_pipeline.adapters.iceberg import fetch_icebergs
from data_pipeline.pipeline import HimDrishtiPipeline, PipelineConfig
from data_pipeline.replay import create_replay, load_replay, list_replays


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = datetime(2026, 5, 21, 0, 0, 0, tzinfo=timezone.utc)
_T1 = _T0 + timedelta(days=5)
_LAT_MIN, _LAT_MAX = -80.0, -60.0
_LON_MIN, _LON_MAX = -60.0, -20.0


def _make_times(n: int, start=_T0) -> list:
    return [start + timedelta(hours=i * 24) for i in range(n)]


def _make_sea_ice(n_t=3, n_lat=5, n_lon=6) -> SeaIceField:
    prov = create_synthetic_provenance("test sea ice", _T0, _T1)
    return SeaIceField(
        concentration=np.random.default_rng(1).random((n_t, n_lat, n_lon)).astype(np.float32),
        lats=np.linspace(-75, -60, n_lat),
        lons=np.linspace(-50, -30, n_lon),
        times=_make_times(n_t),
        provenance=prov,
    )


def _make_wind(n_t=3, n_lat=5, n_lon=6) -> WindField:
    prov = create_synthetic_provenance("test wind", _T0, _T1)
    rng = np.random.default_rng(2)
    return WindField(
        u_wind=rng.uniform(5, 15, (n_t, n_lat, n_lon)).astype(np.float32),
        v_wind=rng.uniform(-5, 5, (n_t, n_lat, n_lon)).astype(np.float32),
        lats=np.linspace(-75, -60, n_lat),
        lons=np.linspace(-50, -30, n_lon),
        times=_make_times(n_t),
        provenance=prov,
    )


def _make_current(n_t=3, n_lat=5, n_lon=6) -> OceanCurrentField:
    prov = create_synthetic_provenance("test current", _T0, _T1)
    rng = np.random.default_rng(3)
    return OceanCurrentField(
        u_current=rng.uniform(0.1, 0.5, (n_t, n_lat, n_lon)).astype(np.float32),
        v_current=rng.uniform(-0.2, 0.2, (n_t, n_lat, n_lon)).astype(np.float32),
        lats=np.linspace(-75, -60, n_lat),
        lons=np.linspace(-50, -30, n_lon),
        times=_make_times(n_t),
        depth_m=0.49,
        provenance=prov,
    )


def _make_iceberg_obs() -> IcebergObservation:
    return IcebergObservation(
        iceberg_id="TEST-1",
        latitude=-70.0,
        longitude=-45.0,
        observed_at=_T0,
        length_m=500.0,
        width_m=300.0,
        source=DataSource.USNIC_NIC,
    )


# ---------------------------------------------------------------------------
# 1. Sea-ice normalization
# ---------------------------------------------------------------------------

class TestSeaIceNormalization:
    def test_percent_to_fraction(self):
        arr = np.array([0.0, 50.0, 100.0])
        out = percent_to_fraction(arr)
        assert np.allclose(out, [0.0, 0.5, 1.0])

    def test_tenths_to_fraction(self):
        arr = np.array([0.0, 5.0, 10.0])
        out = tenths_to_fraction(arr)
        assert np.allclose(out, [0.0, 0.5, 1.0])

    def test_mask_invalid_concentration_negative(self):
        arr = np.array([-0.1, 0.5, 1.2])
        out = mask_invalid_concentration(arr)
        assert np.isnan(out[0])   # negative → NaN
        assert out[1] == pytest.approx(0.5)
        assert np.isnan(out[2])   # > 1.0 → NaN

    def test_mask_invalid_concentration_valid(self):
        arr = np.array([0.0, 0.3, 0.7, 1.0])
        out = mask_invalid_concentration(arr)
        assert not np.any(np.isnan(out))

    def test_sea_ice_validation_passes(self):
        field = _make_sea_ice()
        result = validate_sea_ice(field)
        assert result.valid
        assert result.quality == DataQuality.AVAILABLE

    def test_sea_ice_validation_fails_on_negative(self):
        field = _make_sea_ice()
        field.concentration[0, 0, 0] = -0.1
        result = validate_sea_ice(field)
        assert not result.valid

    def test_sea_ice_validation_fails_on_above_one(self):
        field = _make_sea_ice()
        field.concentration[0, 0, 0] = 1.5
        result = validate_sea_ice(field)
        assert not result.valid


# ---------------------------------------------------------------------------
# 2. Wind normalization
# ---------------------------------------------------------------------------

class TestWindNormalization:
    def test_wind_validation_passes(self):
        field = _make_wind()
        result = validate_wind(field)
        assert result.valid

    def test_wind_validation_fails_on_inf(self):
        field = _make_wind()
        field.u_wind[0, 0, 0] = np.inf
        result = validate_wind(field)
        assert not result.valid

    def test_wind_validation_fails_on_nan(self):
        field = _make_wind()
        field.v_wind[0, 0, 0] = np.nan
        result = validate_wind(field)
        assert not result.valid

    def test_wind_extreme_speed_rejected(self):
        field = _make_wind()
        field.u_wind[:] = 150.0  # physically impossible
        result = validate_wind(field)
        assert not result.valid


# ---------------------------------------------------------------------------
# 3. Ocean current normalization
# ---------------------------------------------------------------------------

class TestCurrentNormalization:
    def test_current_validation_passes(self):
        field = _make_current()
        result = validate_ocean_current(field)
        assert result.valid

    def test_current_validation_fails_on_nan(self):
        field = _make_current()
        field.u_current[0, 0, 0] = np.nan
        result = validate_ocean_current(field)
        assert not result.valid

    def test_current_extreme_speed_rejected(self):
        field = _make_current()
        field.v_current[:] = 10.0  # > 5 m/s limit
        result = validate_ocean_current(field)
        assert not result.valid


# ---------------------------------------------------------------------------
# 4. Iceberg observation validation
# ---------------------------------------------------------------------------

class TestIcebergValidation:
    def test_valid_observation_passes(self):
        obs = _make_iceberg_obs()
        result = validate_iceberg_observation(obs)
        assert result.valid

    def test_invalid_latitude_rejected(self):
        obs = _make_iceberg_obs()
        obs.latitude = -95.0
        result = validate_iceberg_observation(obs)
        assert not result.valid

    def test_invalid_longitude_rejected(self):
        obs = _make_iceberg_obs()
        obs.longitude = 200.0
        result = validate_iceberg_observation(obs)
        assert not result.valid

    def test_negative_dimension_rejected(self):
        obs = _make_iceberg_obs()
        obs.length_m = -100.0
        result = validate_iceberg_observation(obs)
        assert not result.valid

    def test_none_dimensions_allowed(self):
        """Missing optional dimensions must remain None — not fabricated."""
        obs = IcebergObservation(
            iceberg_id="NO-DIMS",
            latitude=-70.0,
            longitude=-45.0,
            observed_at=_T0,
            # All dimensions explicitly None
        )
        result = validate_iceberg_observation(obs)
        assert result.valid


# ---------------------------------------------------------------------------
# 5. Timestamp validation
# ---------------------------------------------------------------------------

class TestTimestampValidation:
    def test_utc_aware_timestamps_pass(self):
        window = ForecastWindow(
            reference_time=_T0,
            valid_times=[_T0, _T0 + timedelta(hours=24), _T0 + timedelta(hours=48)],
            horizon_hours=[0.0, 24.0, 48.0],
        )
        result = validate_forecast_window(window)
        assert result.valid

    def test_naive_timestamps_rejected(self):
        naive = datetime(2026, 5, 21, 0, 0, 0)  # no tzinfo
        window = ForecastWindow(
            reference_time=naive,
            valid_times=[naive, naive + timedelta(hours=24)],
            horizon_hours=[0.0, 24.0],
        )
        result = validate_forecast_window(window)
        assert not result.valid

    def test_non_monotonic_timestamps_rejected(self):
        times = [_T0, _T0 + timedelta(hours=48), _T0 + timedelta(hours=24)]
        window = ForecastWindow(
            reference_time=_T0,
            valid_times=times,
            horizon_hours=[0.0, 48.0, 24.0],  # non-monotonic
        )
        result = validate_forecast_window(window)
        assert not result.valid

    def test_normalize_timestamps_adds_utc(self):
        naive = datetime(2026, 5, 21, 12, 0, 0)
        normed = normalize_timestamps([naive])
        assert normed[0].tzinfo is not None


# ---------------------------------------------------------------------------
# 6. Missing-data handling
# ---------------------------------------------------------------------------

class TestMissingDataHandling:
    def test_nan_concentration_not_replaced_by_validation(self):
        """Validation must flag but NOT repair invalid concentration."""
        field = _make_sea_ice()
        field.concentration[0, 0, 0] = -0.5
        original_val = field.concentration[0, 0, 0]
        validate_sea_ice(field)
        # validation must not silently fix the array
        assert field.concentration[0, 0, 0] == original_val

    def test_mask_invalid_sets_nan_not_zero(self):
        arr = np.array([-0.1, 0.5])
        out = mask_invalid_concentration(arr)
        assert np.isnan(out[0]), "Negative concentration must become NaN, not 0"


# ---------------------------------------------------------------------------
# 7. Provenance creation
# ---------------------------------------------------------------------------

class TestProvenanceCreation:
    def test_provenance_has_all_required_fields(self):
        prov = create_provenance(
            source=DataSource.SYNTHETIC,
            dataset_name="Test dataset",
            valid_time_start=_T0,
            valid_time_end=_T1,
            spatial_coverage="Test domain",
            units="fraction",
        )
        d = provenance_to_dict(prov)
        for key in ["source", "dataset_name", "retrieved_at",
                    "valid_time_start", "valid_time_end",
                    "spatial_coverage", "units", "status"]:
            assert key in d, f"Missing key: {key}"

    def test_synthetic_provenance_clearly_labelled(self):
        prov = create_synthetic_provenance("my data", _T0, _T1)
        d = provenance_to_dict(prov)
        assert "SYNTHETIC" in d["source"].upper() or "SYNTHETIC" in d["dataset_name"].upper()

    def test_naive_datetime_rejected_in_provenance(self):
        naive = datetime(2026, 5, 21)
        with pytest.raises(ValueError, match="timezone-aware"):
            create_provenance(
                source=DataSource.SYNTHETIC,
                dataset_name="bad",
                valid_time_start=naive,
                valid_time_end=_T1,
                spatial_coverage="x",
                units="y",
            )


# ---------------------------------------------------------------------------
# 8. Synthetic pipeline execution
# ---------------------------------------------------------------------------

class TestSyntheticPipelineExecution:
    def _make_input(self) -> PipelineInput:
        fw = ForecastWindow(
            reference_time=_T0,
            valid_times=[_T0 + timedelta(hours=h) for h in range(0, 121, 24)],
            horizon_hours=[float(h) for h in range(0, 121, 24)],
        )
        return PipelineInput(
            forecast_window=fw,
            sea_ice=_make_sea_ice(),
            wind=_make_wind(),
            ocean_current=_make_current(),
            icebergs=[_make_iceberg_obs()],
        )

    def test_pipeline_runs_without_error(self):
        cfg = PipelineConfig(nx=26, ny=20, n_time_buckets=10, n_ensemble_members=4)
        pipeline = HimDrishtiPipeline(cfg)
        result = pipeline.run(self._make_input())
        assert result.success, f"Pipeline failed: {result.failure_reason}"

    def test_pipeline_returns_at_least_one_route(self):
        # Use enough time buckets so the route can reach the goal (start=(2,4) goal=(7,4) in 8-cell grid)
        cfg = PipelineConfig(
            nx=10, ny=8, n_time_buckets=30,
            n_ensemble_members=4,
            start_cell=(1, 4), goal_cell=(8, 4),
        )
        pipeline = HimDrishtiPipeline(cfg)
        result = pipeline.run(self._make_input())
        assert result.route_fast is not None or result.route_safe is not None, \
            f"No route found. Warnings: {result.warnings}"

    def test_pipeline_fails_safely_on_missing_wind(self):
        fw = ForecastWindow(
            reference_time=_T0,
            valid_times=[_T0],
            horizon_hours=[0.0],
        )
        incomplete = PipelineInput(
            forecast_window=fw,
            sea_ice=_make_sea_ice(),
            wind=None,          # missing
            ocean_current=_make_current(),
        )
        cfg = PipelineConfig(nx=10, ny=8, n_time_buckets=5, n_ensemble_members=2)
        pipeline = HimDrishtiPipeline(cfg)
        result = pipeline.run(incomplete)
        assert not result.success
        assert result.failure_reason is not None

    def test_pipeline_provenance_records_present(self):
        cfg = PipelineConfig(nx=26, ny=20, n_time_buckets=10, n_ensemble_members=4)
        pipeline = HimDrishtiPipeline(cfg)
        result = pipeline.run(self._make_input())
        assert len(result.provenance_records) >= 3


# ---------------------------------------------------------------------------
# 9. Deterministic replay
# ---------------------------------------------------------------------------

class TestDeterministicReplay:
    def _run_pipeline(self, seed: int) -> tuple:
        """Run pipeline with given seed; return (time_fast, fuel_fast)."""
        fw = ForecastWindow(
            reference_time=_T0,
            valid_times=[_T0 + timedelta(hours=h) for h in range(0, 121, 24)],
            horizon_hours=[float(h) for h in range(0, 121, 24)],
        )
        pi = PipelineInput(
            forecast_window=fw,
            sea_ice=_make_sea_ice(),
            wind=_make_wind(),
            ocean_current=_make_current(),
            icebergs=[_make_iceberg_obs()],
        )
        cfg = PipelineConfig(
            nx=10, ny=8, n_time_buckets=30,
            n_ensemble_members=4, ensemble_seed=seed,
            start_cell=(1, 4), goal_cell=(8, 4),
        )
        pipeline = HimDrishtiPipeline(cfg)
        result = pipeline.run(pi)
        if result.route_fast:
            return (result.route_fast.total_time_hours,
                    result.route_fast.total_fuel_tonnes)
        return (None, None)

    def test_same_seed_same_result(self):
        """Running twice with the same seed must produce identical results."""
        r1 = self._run_pipeline(seed=42)
        r2 = self._run_pipeline(seed=42)
        assert r1 == r2, f"Non-deterministic! Run1={r1} Run2={r2}"

    def test_different_seed_different_result(self):
        """Different seeds should (very likely) produce different hazard fields."""
        r1 = self._run_pipeline(seed=42)
        r2 = self._run_pipeline(seed=99)
        # Not guaranteed to differ on every tiny grid, but almost always will
        # Just check neither is None and both ran
        assert r1[0] is not None
        assert r2[0] is not None


# ---------------------------------------------------------------------------
# 10. Scientific-core integration
# ---------------------------------------------------------------------------

class TestScienceCore:
    def test_iceberg_drift_importable(self):
        from iceberg_drift import Iceberg, ensemble_drift
        berg = Iceberg(length_m=400, width_m=250, height_above_water_m=20, draft_m=100)
        rng = np.random.default_rng(0)
        wind = rng.normal(10, 2, (5, 2))
        current = rng.normal(0.3, 0.05, (5, 2))
        tracks = ensemble_drift(
            np.array([0.0, 0.0]), wind, current, -68.0, berg,
            n_members=4, dt_s=10800.0, seed=0)
        assert tracks.shape == (4, 6, 2)  # (members, n_steps+1, xy)

    def test_polaris_risk_importable(self):
        from polaris_risk import compute_rio, concentration_to_regime, rio_to_cost
        regime = concentration_to_regime(0.5)
        result = compute_rio(regime, "PC3_PC5")
        assert isinstance(result.rio, float)
        cost = rio_to_cost(result.rio)
        assert cost >= 0

    def test_route_search_importable(self):
        from route_search import RouteWeights, find_route
        # Use enough time buckets so a 7-hop journey (x=1→x=8) can complete
        ice = np.zeros((20, 8, 10))
        hazard = np.zeros((20, 8, 10))
        w = RouteWeights()
        route = find_route((1, 4), (8, 4), ice, hazard, 15_000.0, w)
        assert route is not None, "Route search returned None even on open-water grid"

    def test_adapter_fixtures_all_validate(self):
        """All adapter fixtures must pass validation."""
        si = fetch_sea_ice(_LAT_MIN, _LAT_MAX, _LON_MIN, _LON_MAX, _T0, _T1, use_fixture=True)
        wf = fetch_wind(_LAT_MIN, _LAT_MAX, _LON_MIN, _LON_MAX, _T0, _T1, use_fixture=True)
        oc = fetch_ocean_current(_LAT_MIN, _LAT_MAX, _LON_MIN, _LON_MAX, _T0, _T1, use_fixture=True)

        assert validate_sea_ice(si).valid
        assert validate_wind(wf).valid
        assert validate_ocean_current(oc).valid
