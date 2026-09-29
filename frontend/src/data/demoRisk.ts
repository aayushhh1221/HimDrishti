/**
 * demoRisk.ts — HimDrishti Phase 5
 * SIH 2026 · PS 26059
 *
 * Deterministic demo risk data per route selection.
 * DEMO DATA ONLY — these are NOT real POLARIS RIO calculations.
 * Real POLARIS integration is planned for Phase 8.
 */

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'
export type RioCategoryRoman = 'I' | 'II' | 'III' | 'IV' | 'V' | 'VI' | 'VII'

export interface RiskFactors {
  environmental: number
  navigation: number
  iceCondition: number
  icebergCollision: number
}

export interface RouteRiskProfile {
  routeId: string
  rio: number            // RIO score 0–100
  category: RioCategoryRoman
  level: RiskLevel
  levelLabel: string     // e.g. "LOW RISK"
  factors: RiskFactors
  /** Deterministic explanation for Captain Decision panel */
  systemExplanation: string
  /** Short rationale shown on the decision panel */
  rationale: string
}

export const ROUTE_RISK_PROFILES: RouteRiskProfile[] = [
  {
    routeId: 'recommended',
    rio: 18,
    category: 'II',
    level: 'LOW',
    levelLabel: 'LOW RISK',
    factors: {
      environmental: 12,
      navigation: 22,
      iceCondition: 18,
      icebergCollision: 17,
    },
    systemExplanation:
      'This route is recommended based on current forecast conditions and risk assessment. ' +
      'It avoids the high ice-concentration corridor and maintains safe clearance from tracked icebergs.',
    rationale:
      'Avoids Iceberg A/B uncertainty cones. Ice-class constraint satisfied. ' +
      'Expected 60% lower iceberg encounter probability vs. Higher Risk Route.',
  },
  {
    routeId: 'alternative1',
    rio: 42,
    category: 'IV',
    level: 'MEDIUM',
    levelLabel: 'MEDIUM RISK',
    factors: {
      environmental: 28,
      navigation: 45,
      iceCondition: 42,
      icebergCollision: 38,
    },
    systemExplanation:
      'Alternative Route 1 offers a shorter transit time at moderate risk. ' +
      'It passes through the Iceberg A uncertainty zone and approaches Iceberg B.',
    rationale:
      'Passes through Iceberg A cone. Moderate ice concentration corridor near 64°S. ' +
      'Reduced fuel burn versus Recommended Route.',
  },
  {
    routeId: 'higher-risk',
    rio: 73,
    category: 'VI',
    level: 'HIGH',
    levelLabel: 'HIGH RISK',
    factors: {
      environmental: 58,
      navigation: 72,
      iceCondition: 76,
      icebergCollision: 68,
    },
    systemExplanation:
      'The Higher Risk Route offers the shortest transit time but traverses a high ice-concentration corridor ' +
      'and passes through both Iceberg B and C uncertainty zones.',
    rationale:
      'Transits high ice-concentration zone (≥70% concentration). Iceberg B/C encounter risk elevated. ' +
      'Not recommended at current forecast confidence level.',
  },
]

/** Look up a risk profile by route ID, defaulting to recommended */
export function getRiskProfile(routeId: string): RouteRiskProfile {
  return (
    ROUTE_RISK_PROFILES.find((p) => p.routeId === routeId) ??
    ROUTE_RISK_PROFILES[0]
  )
}
