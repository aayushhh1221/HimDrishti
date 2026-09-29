/**
 * RoutePlanner page — HimDrishti
 * SIH 2026 · PS 26059 / PS 26188
 *
 * Renders:
 * 1. Main Route Planner Workspace (Voyage Scenario | Antarctic Map & Routing Overview | Route Comparison)
 * 2. Decision Layer (Risk & Compliance | Captain Decision | Key Alerts | Data Provenance)
 */

import RoutePlannerWorkspace from '../components/route-planner/RoutePlannerWorkspace'
import DecisionLayer from '../components/decision/DecisionLayer'

export default function RoutePlanner() {
  return (
    <>
      <RoutePlannerWorkspace />
      <DecisionLayer />
    </>
  )
}
