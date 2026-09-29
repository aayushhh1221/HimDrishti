"""
polaris_risk.py
-----------------
Deterministic, auditable ice-navigation risk scoring based on the IMO's
POLARIS methodology (Polar Operational Limit Assessment Risk Indexing
System), referenced by the Polar Code and documented in IMO
MSC.1/Circ.1519, built on Risk Index Values (RIVs) published by the IACS.

    RIO = sum_i ( C_i * RV_i )

  C_i  = concentration, in tenths (0-10), of ice type i present in the
         local ice regime (open water, new ice, grey ice, first-year
         thin/medium/thick ice, multi-year ice, iceberg-affected areas...)
  RV_i = Risk Index Value for ice type i, given the *vessel's own* Polar/
         ice class (a Polar Class 6 icebreaker gets very different RVs
         than a non-ice-strengthened cargo ship for the same ice)

Operational categories (consistent across IMO / IACS / PAME / ABS sources
- see the "AI reliability layer" section of the accompanying blueprint for
citations):
    RIO >= 0        -> "normal operation"
    -10 <= RIO < 0  -> "elevated operational risk" (proceed with caution,
                        e.g. IACS-recommended reduced speed)
    RIO < -10       -> "special consideration" (avoid; if transit is
                        unavoidable, extreme caution / extra requirements)

*** IMPORTANT - READ BEFORE ANY REAL-WORLD USE ***
The RISK_INDEX_VALUES table below is a small, ILLUSTRATIVE placeholder for
demo purposes only. It is NOT the official IACS/IMO table. Before this
module is used for anything beyond a hackathon demo, replace the table
with the authoritative Risk Index Values published in IMO MSC.1/Circ.1519
for the vessel's actual Polar/ice class. This is a safety-relevant
regulatory constant, not a model-tunable parameter - it must come from the
source document, not from an LLM, and not from this codebase.
"""

from dataclasses import dataclass
from typing import Dict

OPEN_WATER = "open_water"
NEW_ICE = "new_ice"
GREY_ICE = "grey_ice"
FIRST_YEAR_THIN = "first_year_thin"
FIRST_YEAR_MEDIUM = "first_year_medium"
FIRST_YEAR_THICK = "first_year_thick"
MULTI_YEAR = "multi_year"
ICEBERG_AFFECTED = "iceberg_affected"

# PLACEHOLDER ONLY - see module docstring.
RISK_INDEX_VALUES: Dict[str, Dict[str, int]] = {
    "PC3_PC5": {  # polar class 3-5, medium ice-strengthened
        OPEN_WATER: 3, NEW_ICE: 3, GREY_ICE: 2, FIRST_YEAR_THIN: 2,
        FIRST_YEAR_MEDIUM: 1, FIRST_YEAR_THICK: -1, MULTI_YEAR: -3,
        ICEBERG_AFFECTED: -4,
    },
    "IA_SUPER_1A": {  # Baltic-class ice-strengthened, no formal polar class
        OPEN_WATER: 3, NEW_ICE: 2, GREY_ICE: 1, FIRST_YEAR_THIN: 0,
        FIRST_YEAR_MEDIUM: -2, FIRST_YEAR_THICK: -4, MULTI_YEAR: -6,
        ICEBERG_AFFECTED: -8,
    },
    "NON_ICE_STRENGTHENED": {
        OPEN_WATER: 3, NEW_ICE: 1, GREY_ICE: -2, FIRST_YEAR_THIN: -4,
        FIRST_YEAR_MEDIUM: -6, FIRST_YEAR_THICK: -8, MULTI_YEAR: -10,
        ICEBERG_AFFECTED: -10,
    },
}


@dataclass
class RioResult:
    rio: float
    category: str
    speed_guidance: str


def compute_rio(ice_regime_tenths: Dict[str, float], vessel_class: str) -> RioResult:
    """
    ice_regime_tenths: e.g. {"open_water": 4, "first_year_medium": 6}
                        concentrations in tenths; should sum to <= 10.
    vessel_class: one of RISK_INDEX_VALUES.keys().
    """
    if vessel_class not in RISK_INDEX_VALUES:
        raise ValueError(f"Unknown vessel_class '{vessel_class}'. Add it to RISK_INDEX_VALUES.")

    total_tenths = sum(ice_regime_tenths.values())
    if total_tenths > 10.0001:
        raise ValueError(f"Ice regime concentrations sum to {total_tenths}, must be <= 10 tenths.")

    rv_table = RISK_INDEX_VALUES[vessel_class]
    rio = 0.0
    for ice_type, tenths in ice_regime_tenths.items():
        if ice_type not in rv_table:
            raise ValueError(f"Ice type '{ice_type}' has no Risk Index Value for {vessel_class}.")
        rio += tenths * rv_table[ice_type]

    if rio >= 0:
        category, speed_guidance = "normal_operation", "No POLARIS-based restriction; normal ice watch."
    elif rio >= -10:
        category, speed_guidance = "elevated_risk", "Proceed with caution at reduced, ice-class-appropriate speed."
    else:
        category, speed_guidance = "special_consideration", "Avoid; if unavoidable, extreme caution only."

    return RioResult(rio=rio, category=category, speed_guidance=speed_guidance)


def rio_to_cost(rio: float, hard_block_below: float = -10.0, scale: float = 50.0) -> float:
    """
    Converts a RIO value into a routing cost penalty, used by
    route_search.py to steer the optimiser away from high-risk cells
    without necessarily hard-blocking them. Cost rises smoothly (quadratically)
    from 0 at RIO=0 to `scale` as RIO approaches the hard-block threshold from
    above; a cell strictly below that threshold ('special consideration',
    RIO < -10 by default) is treated as effectively impassable by the
    automated router, matching the operational guidance to avoid it - the
    captain can always override in practice, but the automated route
    proposal should not.
    """
    if rio < hard_block_below:
        return float("inf")
    if rio >= 0:
        return 0.0
    danger_fraction = rio / hard_block_below  # both <= 0, so this lands in (0, 1]
    return scale * danger_fraction ** 2


def concentration_to_regime(total_concentration: float) -> Dict[str, float]:
    """
    Small convenience helper for the prototype: collapses a single 0-1 sea
    ice concentration value (e.g. from an NSIDC/AMSR2-style grid) into a
    plausible ice-regime tenths dict for compute_rio(). A production
    system should instead use the *actual* ice-type mix from an ice chart
    or SAR-derived classification (WMO ice type categories), since two
    regimes with the same concentration but different ice types can have
    very different RIO values.
    """
    total_concentration = max(0.0, min(1.0, total_concentration))
    ice_tenths = round(total_concentration * 10, 4)
    open_water_tenths = round(10 - ice_tenths, 4)
    if ice_tenths < 4:
        ice_type = FIRST_YEAR_THIN
    elif ice_tenths < 7:
        ice_type = FIRST_YEAR_MEDIUM
    else:
        ice_type = FIRST_YEAR_THICK
    regime = {OPEN_WATER: open_water_tenths}
    if ice_tenths > 0:
        regime[ice_type] = ice_tenths
    return regime
