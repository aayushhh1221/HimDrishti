"""
iceberg_drift.py
-----------------
Physics-based iceberg drift model (force-balance / equation-of-motion
approach), following the general family of models used in operational
iceberg forecasting (e.g. Bigg et al. 1997; Smith 1993; Keghouche et al.
2009). This is the "trustworthy backbone" of the forecasting stack: it
needs no training data, works from day 1, and every force it computes can
be inspected and explained.

SIMPLIFICATIONS FOR PROTOTYPE (read before extending):
- Local planar (x=east, y=north) coordinates in metres, not full spherical
  geometry. A production version should run on a proper polar-stereographic
  projection (the standard choice for Antarctic work).
- Three forces only: air drag, water drag, Coriolis. Wave radiation force
  and sea-surface-slope (geostrophic) force are real contributors in the
  literature and should be added for production use.
- Constant drag coefficients. A production system should calibrate these
  against observed drift tracks (GPS-tagged bergs, or repeat-pass SAR
  positions such as the BYU/NIC and Altiberg iceberg databases).
- No melt/deterioration coupling by default; a simple optional size-decay
  hook is provided since a shrinking berg changes its freeboard/draft and
  therefore its drag area over multi-week forecasts.

This module answers ONE question: "given a starting position and a
forecast of wind + current, where is this iceberg likely to go, and how
uncertain are we?" It deliberately does not try to be a full ocean-ice
numerical model - that is neither necessary nor buildable in a hackathon
timeframe, and a well-calibrated force-balance model plus an honest
uncertainty cone beats a black-box prediction nobody can explain.
"""

from dataclasses import dataclass, replace
import numpy as np

RHO_AIR = 1.225          # kg / m^3, sea-level air density
RHO_WATER = 1025.0       # kg / m^3, seawater density
OMEGA_EARTH = 7.2921e-5  # rad / s, Earth's rotation rate


@dataclass
class Iceberg:
    length_m: float = 500.0
    width_m: float = 300.0
    height_above_water_m: float = 30.0
    draft_m: float = 150.0            # depth below waterline
    density_kg_m3: float = 900.0
    drag_coeff_air: float = 1.3       # typical bluff-body value from the drift literature
    drag_coeff_water: float = 0.9

    @property
    def mass_kg(self) -> float:
        # 0.7 is a rough tabular-berg shape factor, not a full rectangular box.
        volume = self.length_m * self.width_m * (self.height_above_water_m + self.draft_m)
        return 0.7 * volume * self.density_kg_m3

    @property
    def area_air_m2(self) -> float:
        return self.length_m * self.height_above_water_m

    @property
    def area_water_m2(self) -> float:
        return self.length_m * self.draft_m


def coriolis_parameter(latitude_deg: float) -> float:
    """f = 2 * Omega * sin(latitude). Negative in the Southern Hemisphere,
    which correctly reverses the deflection direction versus the Northern
    Hemisphere (deflection to the left of motion, not the right)."""
    return 2.0 * OMEGA_EARTH * np.sin(np.radians(latitude_deg))


def _acceleration(velocity, wind, current, berg: Iceberg, f: float) -> np.ndarray:
    vx, vy = velocity
    wx, wy = wind
    cx, cy = current

    rel_air = np.array([wx - vx, wy - vy])
    rel_water = np.array([cx - vx, cy - vy])

    f_air = 0.5 * RHO_AIR * berg.drag_coeff_air * berg.area_air_m2 * np.linalg.norm(rel_air) * rel_air
    f_water = 0.5 * RHO_WATER * berg.drag_coeff_water * berg.area_water_m2 * np.linalg.norm(rel_water) * rel_water

    # Coriolis acceleration per unit mass: a = (f*vy, -f*vx). Standard
    # geophysical-fluid-dynamics convention; f<0 in the Southern Hemisphere
    # already reverses the turning sense correctly.
    a_cor = np.array([f * vy, -f * vx])

    mass = berg.mass_kg
    return f_air / mass + f_water / mass + a_cor


def simulate_drift(start_xy, wind_series, current_series, latitude_deg,
                    berg: Iceberg, dt_s: float = 900.0,
                    integration_substep_s: float = 60.0,
                    melt_rate_m_per_day: float = 0.0) -> np.ndarray:
    """
    Integrate the force-balance ODE with RK4 (4th-order Runge-Kutta).

    start_xy: (x, y) in metres, local planar frame.
    wind_series, current_series: arrays of shape (n_steps, 2), one (u, v)
        vector per dt_s step. dt_s is the *forcing update interval*
        (e.g. 3-6 hourly, matching a typical forecast cadence) - it is
        NOT the integrator step size. The water-drag term is numerically
        stiff (its restoring force grows with the square of the slip
        velocity), so explicit RK4 needs a much finer internal step to
        stay stable; this function automatically sub-steps at
        `integration_substep_s` (default 60 s) within each forcing
        interval and only returns the position at the end of each
        interval. Do not skip this - taking one large RK4 step per
        multi-hour forcing interval will silently blow up (velocity
        overflow) rather than raise an error.
    latitude_deg: used for the Coriolis parameter (treated as constant over
        the run - reasonable for a multi-day regional forecast).
    Returns: positions array of shape (n_steps + 1, 2), one row per
        forcing interval (not per integrator substep).
    """
    berg = replace(berg)  # local mutable copy so ensembles don't cross-contaminate
    f = coriolis_parameter(latitude_deg)
    n_steps = len(wind_series)
    n_substeps = max(1, int(round(dt_s / integration_substep_s)))
    h = dt_s / n_substeps

    pos = np.zeros((n_steps + 1, 2))
    pos[0] = start_xy
    cur_pos = np.array(start_xy, dtype=float)
    vel = np.zeros(2)

    for i in range(n_steps):
        wind = wind_series[i]
        current = current_series[i]

        for _ in range(n_substeps):
            k1v = _acceleration(vel, wind, current, berg, f)
            k1x = vel
            k2v = _acceleration(vel + 0.5 * h * k1v, wind, current, berg, f)
            k2x = vel + 0.5 * h * k1v
            k3v = _acceleration(vel + 0.5 * h * k2v, wind, current, berg, f)
            k3x = vel + 0.5 * h * k2v
            k4v = _acceleration(vel + h * k3v, wind, current, berg, f)
            k4x = vel + h * k3v

            vel = vel + (h / 6.0) * (k1v + 2 * k2v + 2 * k3v + k4v)
            cur_pos = cur_pos + (h / 6.0) * (k1x + 2 * k2x + 2 * k3x + k4x)

        pos[i + 1] = cur_pos

        if melt_rate_m_per_day > 0:
            shrink = melt_rate_m_per_day * dt_s / 86400.0
            berg.length_m = max(berg.length_m - shrink, 10.0)
            berg.width_m = max(berg.width_m - shrink, 10.0)

    return pos


def ensemble_drift(start_xy, wind_series, current_series, latitude_deg,
                    berg: Iceberg, n_members: int = 50,
                    wind_sigma_frac: float = 0.25, current_sigma_frac: float = 0.30,
                    dt_s: float = 900.0, seed: int = 0) -> np.ndarray:
    """
    Monte Carlo ensemble: perturbs the wind & current forcing to represent
    real forecast uncertainty, then re-runs the deterministic drift model
    for each member. This produces a *spread* of trajectories (the
    "uncertainty cone") rather than a single "the berg will be here" point,
    which would overstate confidence. The spread is the input to the
    probabilistic hazard field that route_search.py routes around.
    """
    rng = np.random.default_rng(seed)
    n_steps = len(wind_series)
    tracks = np.zeros((n_members, n_steps + 1, 2))

    wind_speed = np.linalg.norm(wind_series, axis=1, keepdims=True) + 1e-6
    current_speed = np.linalg.norm(current_series, axis=1, keepdims=True) + 1e-6

    for m in range(n_members):
        wind_noise = rng.normal(0.0, wind_sigma_frac, size=wind_series.shape) * wind_speed
        current_noise = rng.normal(0.0, current_sigma_frac, size=current_series.shape) * current_speed
        tracks[m] = simulate_drift(
            start_xy, wind_series + wind_noise, current_series + current_noise,
            latitude_deg, berg, dt_s=dt_s,
        )
    return tracks
