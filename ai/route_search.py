"""
route_search.py
------------------
Deterministic, explainable multi-objective route search over a moving
hazard field (time-varying sea-ice cost + iceberg-risk cost).

Algorithm: Dijkstra's algorithm (Uniform-Cost Search) over a 3-D
state space (time-bucket × y × x).  The priority queue is ordered
solely by cumulative weighted cost g(n) — there is NO admissible
heuristic h(n), so this is NOT A*.  It is Dijkstra / UCS, which
guarantees the globally-optimal weighted-cost path given the discrete
hazard field.

Deliberately NOT a black-box RL agent: every route this returns can be
replayed edge-by-edge, and the exact cost breakdown (time / fuel / risk)
for each segment can be shown to a judge, an NCPOR scientist, or a ship's
captain. That auditability is a first-class requirement here, not an
afterthought - see the "AI reliability layer" section of the accompanying
blueprint document for why an LLM never touches this computation.

Simplification for the prototype: one "hop" to an adjacent grid cell
always advances the hazard-field time index by exactly one bucket
(regardless of the hop's own computed transit time). This keeps the
search space to nx * ny * n_time_buckets, small enough to solve in
milliseconds on a hackathon demo grid, while the *reported* time and fuel
numbers still come from a proper speed/resistance model rather than a
simple hop count. A production version should key the priority queue on
true elapsed time instead of a bucket index.
"""

import heapq
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

KN_TO_MS = 0.514444


@dataclass
class RouteWeights:
    time_weight: float = 1.0     # cost per hour underway
    fuel_weight: float = 1.0     # cost per tonne of fuel burned
    risk_weight: float = 1.0     # cost per unit of hazard exposure (the "risk slider")

    # Ship performance model (deliberately simple - swap in a real
    # ice-resistance curve calibrated to the actual charter vessel for
    # production use; e.g. a semi-empirical resistance-in-ice formula).
    max_speed_kn: float = 12.0
    min_speed_frac: float = 0.15      # floor speed as a fraction of max, in heavy ice
    ice_speed_penalty: float = 0.9    # how strongly concentration slows the ship
    base_fuel_tonnes_per_hour: float = 3.0
    ice_fuel_penalty: float = 2.5     # extra fuel-burn multiplier in heavy ice


@dataclass
class RouteResult:
    path_cells: List[Tuple[int, int]]        # (x, y) grid indices, start to goal
    path_time_buckets: List[int]
    total_time_hours: float
    total_fuel_tonnes: float
    total_risk_cost: float
    total_weighted_cost: float


def _effective_speed_ms(weights: RouteWeights, concentration: float) -> float:
    max_speed_ms = weights.max_speed_kn * KN_TO_MS
    factor = max(weights.min_speed_frac, 1.0 - weights.ice_speed_penalty * concentration)
    return max_speed_ms * factor


def _fuel_rate_tph(weights: RouteWeights, concentration: float) -> float:
    return weights.base_fuel_tonnes_per_hour * (1.0 + weights.ice_fuel_penalty * concentration)


def find_route(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    ice_concentration: np.ndarray,   # shape (T, ny, nx), values in [0, 1]
    hazard_cost: np.ndarray,         # shape (T, ny, nx), extra risk cost; np.inf = hard-blocked
    cell_size_m: float,
    weights: Optional[RouteWeights] = None,
    max_time_buckets: Optional[int] = None,
) -> Optional[RouteResult]:
    """
    start, goal: (x, y) grid indices, i.e. (column, row).
    Returns the lowest-weighted-cost route, or None if no route is found
    within max_time_buckets.
    """
    weights = weights or RouteWeights()
    T, ny, nx = ice_concentration.shape
    max_time_buckets = max_time_buckets or T

    neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    start_state = (0, start[1], start[0])   # (t, y, x)
    goal_yx = (goal[1], goal[0])

    dist = {start_state: 0.0}
    breakdown = {start_state: (0.0, 0.0, 0.0)}  # (time_h, fuel_t, risk)
    prev = {}
    visited = set()
    pq = [(0.0, start_state)]

    while pq:
        cost, state = heapq.heappop(pq)
        if state in visited:
            continue
        visited.add(state)
        t, y, x = state

        if (y, x) == goal_yx:
            return _reconstruct(state, prev, breakdown, weights)

        if t + 1 >= min(T, max_time_buckets):
            continue

        conc_here = float(ice_concentration[t, y, x])
        for dy, dx in neighbors:
            ny_, nx_ = y + dy, x + dx
            if not (0 <= ny_ < ny and 0 <= nx_ < nx):
                continue

            hz = float(hazard_cost[t + 1, ny_, nx_])
            if not np.isfinite(hz):
                continue  # hard-blocked cell (e.g. RIO below special-consideration threshold)

            conc_there = float(ice_concentration[t + 1, ny_, nx_])
            conc_edge = 0.5 * (conc_here + conc_there)
            distance_m = cell_size_m * (1.4142135 if (dx != 0 and dy != 0) else 1.0)

            speed_ms = _effective_speed_ms(weights, conc_edge)
            transit_h = (distance_m / speed_ms) / 3600.0
            fuel_t = _fuel_rate_tph(weights, conc_edge) * transit_h

            edge_cost = (weights.time_weight * transit_h
                         + weights.fuel_weight * fuel_t
                         + weights.risk_weight * hz)

            new_state = (t + 1, ny_, nx_)
            new_cost = cost + edge_cost
            if new_cost < dist.get(new_state, float("inf")):
                dist[new_state] = new_cost
                old_time, old_fuel, old_risk = breakdown[state]
                breakdown[new_state] = (old_time + transit_h, old_fuel + fuel_t, old_risk + hz)
                prev[new_state] = state
                heapq.heappush(pq, (new_cost, new_state))

    return None


def _reconstruct(state, prev, breakdown, weights: RouteWeights) -> RouteResult:
    path = [state]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()

    cells = [(s[2], s[1]) for s in path]   # back to (x, y)
    buckets = [s[0] for s in path]
    time_h, fuel_t, risk = breakdown[state]
    weighted = weights.time_weight * time_h + weights.fuel_weight * fuel_t + weights.risk_weight * risk

    return RouteResult(
        path_cells=cells, path_time_buckets=buckets,
        total_time_hours=time_h, total_fuel_tonnes=fuel_t,
        total_risk_cost=risk, total_weighted_cost=weighted,
    )
