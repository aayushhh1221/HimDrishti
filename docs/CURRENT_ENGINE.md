# HimDrishti — Current Scientific Engine
**SIH 2026 · PS 26059**

> **READ BEFORE USE**: This document describes a prototype scientific engine
> intended for a hackathon demonstration. Every limitation is documented.
> This system is NOT certified for operational navigation decisions.
> The final decision always rests with the Master / Ice Pilot.

---

## Table of Contents
1. [iceberg_drift.py](#iceberg_driftpy)
2. [polaris_risk.py](#polaris_riskpy)
3. [route_search.py](#route_searchpy)
4. [demo_run.py](#demo_runpy)
5. [Known Prototype Shortcuts](#known-prototype-shortcuts)

---

## iceberg_drift.py

**Location**: `ai/iceberg_drift.py`

### Purpose
Physics-based iceberg drift model using a force-balance / equation-of-motion
approach, following the general family used in operational forecasting
(Bigg et al. 1997; Smith 1993; Keghouche et al. 2009).

Answers one question: *"Given a starting position and a forecast of wind +
current, where is this iceberg likely to go, and how uncertain are we?"*

### Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| `start_xy` | `(float, float)` | Starting position in metres, local planar frame |
| `wind_series` | `np.ndarray (n_steps, 2)` | Hourly wind vectors [u, v] in m/s |
| `current_series` | `np.ndarray (n_steps, 2)` | Hourly current vectors [u, v] in m/s |
| `latitude_deg` | `float` | Latitude for Coriolis parameter (treated as constant) |
| `berg` | `Iceberg` dataclass | Physical dimensions and drag coefficients |
| `dt_s` | `float` | Forcing update interval in seconds (e.g. 10800 = 3h) |

### Outputs
- `simulate_drift()` → `np.ndarray (n_steps+1, 2)` positions in metres
- `ensemble_drift()` → `np.ndarray (n_members, n_steps+1, 2)` ensemble tracks

### Physics Model
Three forces are computed at each substep:
1. **Air drag**: `F_air = 0.5 × ρ_air × C_d_air × A_air × |v_rel| × v_rel`
2. **Water drag**: `F_water = 0.5 × ρ_water × C_d_water × A_water × |v_rel| × v_rel`
3. **Coriolis**: `a_cor = [f × vy, -f × vx]` (f < 0 in Southern Hemisphere → left deflection)

Integration: **4th-order Runge-Kutta** with substep `integration_substep_s=60s`
within each forcing interval (water drag is stiff — single large steps blow up).

Ensemble: Monte Carlo perturbation of wind and current forcing.

### Assumptions
| Assumption | Justification | Production requirement |
|------------|---------------|----------------------|
| Local planar x/y coordinates | Adequate for small-domain hackathon grids | Polar-stereographic projection (standard for Antarctic work) |
| Three forces only (air, water, Coriolis) | Dominant forces over days | Add wave radiation + geostrophic/sea-surface-slope for production |
| Constant drag coefficients | No calibration data available | Calibrate against GPS-tagged berg tracks or repeat-pass SAR (BYU/NIC, Altiberg) |
| No melt coupling by default | Simplification for short windows | Add melt + size decay for multi-week forecasts |
| Constant latitude for Coriolis | Reasonable for regional multi-day forecast | Re-compute f at each position for basin-scale runs |

### Constants
```python
RHO_AIR = 1.225        # kg/m³
RHO_WATER = 1025.0     # kg/m³
OMEGA_EARTH = 7.2921e-5  # rad/s
C_d_air = 1.3          # bluff-body value from drift literature
C_d_water = 0.9        # bluff-body value from drift literature
```

---

## polaris_risk.py

**Location**: `ai/polaris_risk.py`

### Purpose
Deterministic, auditable ice-navigation risk scoring based on the IMO POLARIS
methodology (Polar Operational Limit Assessment Risk Indexing System).

Reference: IMO MSC.1/Circ.1519 / IACS Unified Requirement PCSR (Polar Code
Structural Requirements), Risk Index Values published by IACS.

### Formula
```
RIO = Σᵢ (Cᵢ × RVᵢ)
```
- `Cᵢ` = concentration in tenths (0–10) of ice type i
- `RVᵢ` = Risk Index Value for ice type i, given the vessel's polar/ice class

### Risk Categories
| RIO | Category | Guidance |
|-----|----------|----------|
| ≥ 0 | Normal operation | Standard ice watch |
| [-10, 0) | Elevated risk | Reduced speed, extra caution |
| < -10 | Special consideration | Avoid; extreme caution if unavoidable |

### Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| `ice_regime_tenths` | `Dict[str, float]` | Ice type → tenths (sum ≤ 10) |
| `vessel_class` | `str` | Must match `RISK_INDEX_VALUES` key |

### Outputs
- `compute_rio()` → `RioResult(rio: float, category: str, speed_guidance: str)`
- `rio_to_cost()` → `float` (routing cost penalty, ∞ for special-consideration cells)
- `concentration_to_regime()` → `Dict[str, float]` (convenience helper)

### ⚠️ CRITICAL LIMITATION — RISK INDEX VALUES

> The `RISK_INDEX_VALUES` table in `polaris_risk.py` is an **ILLUSTRATIVE
> PLACEHOLDER** for demo purposes only.
>
> It is **NOT** the official IACS/IMO table.
>
> Before this module is used for any real-world purpose:
> - Replace `RISK_INDEX_VALUES` with the authoritative Risk Index Values
>   from **IMO MSC.1/Circ.1519** for the vessel's actual polar/ice class
> - This is a **safety-relevant regulatory constant** — it must come from
>   the source document, **not from an LLM and not from this codebase**
> - Do NOT label current output as "official POLARIS compliance"

### `concentration_to_regime()` Limitation
This helper collapses a single 0–1 concentration value into one of three ice
types (thin/medium/thick first-year ice). A production system should use the
**actual ice-type mix** from an ice chart or SAR-derived WMO classification,
since two regimes with the same concentration but different ice types can have
very different RIO values.

---

## route_search.py

**Location**: `ai/route_search.py`

### Purpose
Deterministic, explainable multi-objective route search over a time-varying
hazard field. Every route can be replayed edge-by-edge with a full cost breakdown.

### Why Not RL / LLM?
The route search is deliberately deterministic:
- Every route can be replayed and audited
- The exact cost breakdown is explainable to a judge, scientist, or captain
- The system recommends; the Master decides — auditability is required

### Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| `start`, `goal` | `(int, int)` | Grid cell indices (x, y) |
| `ice_concentration` | `np.ndarray (T, ny, nx)` | Time-varying concentration [0,1] |
| `hazard_cost` | `np.ndarray (T, ny, nx)` | Combined risk cost; `np.inf` = hard-blocked |
| `cell_size_m` | `float` | Grid cell size in metres |
| `weights` | `RouteWeights` | Time / fuel / risk objective weights |

### Outputs
- `find_route()` → `Optional[RouteResult]`

`RouteResult` contains:
- `path_cells`: list of (x, y) grid indices from start to goal
- `path_time_buckets`: hazard-field time index at each step
- `total_time_hours`, `total_fuel_tonnes`, `total_risk_cost`, `total_weighted_cost`

### Algorithm
Modified Dijkstra over a (time, y, x) state space. Each hop to an adjacent
cell advances the time index by 1 bucket. Diagonal moves are permitted
(cost factor 1.414). Hard-blocked cells (inf hazard cost) are skipped.

### Ship Performance Model
```python
speed_ms = max_speed × max(min_speed_frac, 1 - ice_speed_penalty × concentration)
fuel_t_h = base_fuel × (1 + ice_fuel_penalty × concentration)
```
Default values are illustrative — not calibrated to any specific vessel.

### Known Prototype Shortcuts
| Shortcut | Production requirement |
|----------|----------------------|
| One bucket per hop | Key priority queue on true elapsed time |
| 8-connected planar grid | Proper spherical/polar-stereographic graph |
| Constant speed/fuel model | Semi-empirical ice-resistance curve for actual vessel |
| No dynamic obstacle avoidance | Real-time update of hazard field as new observations arrive |
| Hard-block below RIO < -10 | Captain can always manually override |

---

## demo_run.py

**Location**: `demo/demo_run.py`

### Purpose
End-to-end integration test using fully synthetic data.
Proves the three-module pipeline coheres before any frontend exists.

### What it demonstrates
1. Synthetic ice field with time-varying ice tongue
2. Iceberg ensemble drift (48 members, RK4 physics)
3. Probabilistic hazard field construction
4. POLARIS RIO cost mapping per cell
5. Two route operating points (fast vs cautious)
6. Visualization: ice field + uncertainty cone + both routes

### Output
- Console: route time/fuel/risk costs + worst POLARIS RIO encountered
- File: `demo/toy_scenario_output.png`

### How to run
```bash
python demo/demo_run.py
```

> **ALL NUMBERS ARE SYNTHETIC.** Swap in real NSIDC/AMSR2 grids + CMEMS
> currents + ECMWF winds + real NIC iceberg position to turn this into a
> real forecast. The module interfaces do not change.

---

## Known Prototype Shortcuts

| Item | Current implementation | Required for production |
|------|----------------------|------------------------|
| Coordinate system | Local planar x/y metres | Polar-stereographic (EPSG:3031) |
| POLARIS RIV table | Illustrative placeholder | Official IMO MSC.1/Circ.1519 values |
| Ice type classification | Concentration-only heuristic | SAR or ice-chart WMO classification |
| Wave radiation force | Omitted | Required for multi-week forecasts |
| Geostrophic force | Omitted | Required for basin-scale accuracy |
| Drag coefficients | Literature defaults | Calibrated against GPS/SAR berg tracks |
| Ship performance | Simple linear model | Certified ice-resistance curve |
| Route time-stepping | One bucket per hop | True elapsed time in priority queue |
| Melt coupling | Optional hook only | Active for multi-week runs |
| Ensemble size | 48 members | 100+ for operational confidence intervals |
