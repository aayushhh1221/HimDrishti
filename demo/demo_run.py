"""
demo_run.py
-------------
Ties the three core modules together on a SYNTHETIC toy scenario and
proves the architecture coheres end to end:

    ice + iceberg forecast  -->  probabilistic hazard field  -->
    multi-objective route search  -->  POLARIS-scored, explainable route

This is the literal "does the architecture actually work" artifact - run
it, look at the PNG and the printed cost breakdown, and you have a working
proof of the pipeline before a single line of frontend code exists.

ALL NUMBERS BELOW ARE SYNTHETIC / ILLUSTRATIVE. Swap in real NSIDC/AMSR2
concentration grids, CMEMS current & ECMWF wind forecasts, and a real
start iceberg position (e.g. from the NIC/BYU or Altiberg databases) to
turn this into a real forecast - the module interfaces do not change.

Run with:  python3 demo_run.py
Requires:  numpy, matplotlib (pip install numpy matplotlib --break-system-packages)
"""

import os
import sys

_project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "ai"))  # iceberg_drift, polaris_risk, route_search live here

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from iceberg_drift import Iceberg, ensemble_drift
from polaris_risk import compute_rio, rio_to_cost, concentration_to_regime
from route_search import RouteWeights, find_route

# ---------------------------------------------------------------------------
# 1. SYNTHETIC DOMAIN SET-UP
# ---------------------------------------------------------------------------
NX, NY = 26, 20                 # grid cells (east-west, north-south)
CELL_SIZE_M = 15_000.0          # 15 km cells  ->  ~390 km x 300 km domain
N_TIME_BUCKETS = 30             # 30 layers = 29 hops available (see route_search
                                 # docstring: 1 hop = 1 hazard-field time bucket).
                                 # Straight-line start->goal distance below is 21
                                 # cells, so this leaves real slack to detour.
DT_HOURS = 3.0                  # hazard-field cadence
LATITUDE_DEG = -68.0            # representative latitude of the transit corridor
VESSEL_CLASS = "PC3_PC5"        # try "NON_ICE_STRENGTHENED" to see routes change sharply

rng = np.random.default_rng(42)


def moving_ice_tongue(t_frac, ny=NY, nx=NX):
    """A compact, moderate-concentration pack-ice tongue sitting south of the
    direct transit line (rather than covering the whole domain or blocking
    the corridor outright). t_frac in [0, 1] over the forecast horizon.
    Drift is EXAGGERATED for a demo window so the router visibly reacts to
    a *moving* hazard field; real large-scale ice-edge motion over a few
    days is normally more subtle. The interesting routing decision in this
    scenario is about the drifting ICEBERG that calves off this tongue and
    crosses the corridor - not the tongue itself, which a PC3-PC5 vessel
    can approach without being blocked outright."""
    yy, xx = np.mgrid[0:ny, 0:nx]
    center_y = 5.0 + 1.0 * t_frac
    center_x = 9.0 + 3.0 * t_frac
    spread_y, spread_x = 2.3, 4.2
    blob = np.exp(-(((yy - center_y) / spread_y) ** 2 + ((xx - center_x) / spread_x) ** 2))
    conc = np.clip(0.65 * blob, 0.0, 1.0)
    conc[conc < 0.04] = 0.0
    return conc


ice_concentration = np.stack([moving_ice_tongue(t / (N_TIME_BUCKETS - 1)) for t in range(N_TIME_BUCKETS)])

# ---------------------------------------------------------------------------
# 2. ICEBERG DRIFT ENSEMBLE
# ---------------------------------------------------------------------------
berg = Iceberg(length_m=450, width_m=280, height_above_water_m=25, draft_m=120)

n_steps = N_TIME_BUCKETS - 1
dt_s = DT_HOURS * 3600.0

# Dominant Southern-Ocean westerly wind with noise, plus a steady coastal current.
base_wind = np.array([10.0, 6.0])      # m/s, ENE-ish - typical strong Southern Ocean westerly-with-a-twist
base_current = np.array([0.30, 0.28])  # m/s, a modest north-eastward coastal-current component
wind_series = base_wind + rng.normal(0, 1.5, size=(n_steps, 2))
current_series = np.tile(base_current, (n_steps, 1)) + rng.normal(0, 0.05, size=(n_steps, 2))

berg_start_xy = np.array([7.0 * CELL_SIZE_M, 7.0 * CELL_SIZE_M])  # calved off the pack-ice tongue
tracks_m = ensemble_drift(
    berg_start_xy, wind_series, current_series, LATITUDE_DEG, berg,
    n_members=48, dt_s=dt_s, seed=7,
)  # shape (members, n_steps+1, 2), in metres

# ---------------------------------------------------------------------------
# 3. BUILD THE PROBABILISTIC HAZARD FIELD
# ---------------------------------------------------------------------------
tracks_cells = tracks_m / CELL_SIZE_M  # (members, T, 2) in fractional (x, y) cell units

berg_density = np.zeros((N_TIME_BUCKETS, NY, NX))
yy, xx = np.mgrid[0:NY, 0:NX]
sigma_cells = 1.4
for t in range(N_TIME_BUCKETS):
    for m in range(tracks_cells.shape[0]):
        cx, cy = tracks_cells[m, t]
        berg_density[t] += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma_cells ** 2)))
berg_density /= berg_density.max()

ice_rio_cost = np.zeros_like(ice_concentration)
for t in range(N_TIME_BUCKETS):
    for iy in range(NY):
        for ix in range(NX):
            regime = concentration_to_regime(ice_concentration[t, iy, ix])
            rio = compute_rio(regime, VESSEL_CLASS).rio
            ice_rio_cost[t, iy, ix] = rio_to_cost(rio)

ICEBERG_RISK_SCALE = 40.0  # tunable: how much a fully-dense berg-probability cell costs


def build_hazard_cost(iceberg_risk_weight: float) -> np.ndarray:
    combined = ice_rio_cost + iceberg_risk_weight * ICEBERG_RISK_SCALE * berg_density
    return combined


# ---------------------------------------------------------------------------
# 4. ROUTE SEARCH - TWO OPERATING POINTS ON THE SAME PARETO FRONTIER
# ---------------------------------------------------------------------------
start_xy = (2, 10)     # open water, west side of the corridor
goal_xy = (23, 10)     # toward the coast / station approach, same latitude -
                        # the direct line runs close to the iceberg's drift path

fast_weights = RouteWeights(time_weight=1.0, fuel_weight=0.4, risk_weight=0.3)
safe_weights = RouteWeights(time_weight=1.0, fuel_weight=0.4, risk_weight=4.0)

route_fast = find_route(start_xy, goal_xy, ice_concentration, build_hazard_cost(1.0), CELL_SIZE_M, fast_weights)
route_safe = find_route(start_xy, goal_xy, ice_concentration, build_hazard_cost(1.0), CELL_SIZE_M, safe_weights)


def summarize(name, route):
    if route is None:
        print(f"{name}: NO ROUTE FOUND within the time horizon.")
        return
    print(f"{name}:")
    print(f"    time     = {route.total_time_hours:6.1f} h")
    print(f"    fuel     = {route.total_fuel_tonnes:6.1f} t")
    print(f"    risk sum = {route.total_risk_cost:6.1f}")
    # POLARIS category actually encountered along the route (worst point)
    worst_rio = None
    for (x, y), t in zip(route.path_cells, route.path_time_buckets):
        regime = concentration_to_regime(ice_concentration[t, y, x])
        rio = compute_rio(regime, VESSEL_CLASS).rio
        if worst_rio is None or rio < worst_rio:
            worst_rio = rio
    result = compute_rio(concentration_to_regime(0.0), VESSEL_CLASS)  # placeholder to reuse category text
    if worst_rio is not None:
        if worst_rio >= 0:
            cat = "normal_operation"
        elif worst_rio >= -10:
            cat = "elevated_risk"
        else:
            cat = "special_consideration"
        print(f"    worst POLARIS RIO encountered = {worst_rio:5.1f}  ({cat})")


print("=" * 60)
print("SIH26059 prototype - toy end-to-end run")
print("=" * 60)
summarize("Fast/efficient route  (low risk_weight)", route_fast)
summarize("Cautious route        (high risk_weight)", route_safe)
print("=" * 60)

# ---------------------------------------------------------------------------
# 5. VISUALISE: ice field + iceberg uncertainty cone + both candidate routes
# ---------------------------------------------------------------------------
mid_t = N_TIME_BUCKETS // 2
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

ice_cmap = LinearSegmentedColormap.from_list("ice", ["#0b2545", "#8ecae6", "#ffffff"])

for ax, t_show, title in [(axes[0], 2, "Early in the forecast window"),
                           (axes[1], N_TIME_BUCKETS - 2, "Near the end of the forecast window")]:
    ax.imshow(ice_concentration[t_show], origin="lower", cmap=ice_cmap, vmin=0, vmax=1,
              extent=[0, NX, 0, NY], alpha=0.9)
    ax.contour(xx, yy, berg_density[t_show], levels=[0.05, 0.15, 0.35, 0.6],
               colors="#d62828", linewidths=1.2, alpha=0.85)

    if route_fast:
        fx = [c[0] + 0.5 for c, tb in zip(route_fast.path_cells, route_fast.path_time_buckets) if tb <= t_show]
        fy = [c[1] + 0.5 for c, tb in zip(route_fast.path_cells, route_fast.path_time_buckets) if tb <= t_show]
        ax.plot(fx, fy, color="#f4a261", linewidth=2.5, label="Fast / efficient route")
    if route_safe:
        sx = [c[0] + 0.5 for c, tb in zip(route_safe.path_cells, route_safe.path_time_buckets) if tb <= t_show]
        sy = [c[1] + 0.5 for c, tb in zip(route_safe.path_cells, route_safe.path_time_buckets) if tb <= t_show]
        ax.plot(sx, sy, color="#2a9d8f", linewidth=2.5, linestyle="--", label="Cautious route")

    ax.scatter([start_xy[0] + 0.5], [start_xy[1] + 0.5], marker="o", color="black", zorder=5, label="Start")
    ax.scatter([goal_xy[0] + 0.5], [goal_xy[1] + 0.5], marker="*", color="black", s=160, zorder=5, label="Station approach")
    ax.set_title(f"{title}\n(white/blue = sea-ice concentration, red contours = iceberg probability)", fontsize=9)
    ax.set_xlabel("grid cell (east)")
    ax.set_ylabel("grid cell (north)")
    ax.set_xlim(0, NX)
    ax.set_ylim(0, NY)

axes[0].legend(loc="upper left", fontsize=8, framealpha=0.9)
fig.suptitle("SIH26059 prototype: ice + iceberg hazard field with two POLARIS-aware candidate routes", fontsize=11)
fig.tight_layout()

out_path = os.path.join(os.path.dirname(__file__), "toy_scenario_output.png")
fig.savefig(out_path, dpi=150)
print(f"Saved figure to {out_path}")
