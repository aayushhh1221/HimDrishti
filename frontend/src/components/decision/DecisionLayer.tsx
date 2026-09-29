/**
 * DecisionLayer.tsx — HimDrishti Phase 7
 * SIH 2026 · PS 26059
 *
 * Lower decision/information layer beneath the main Route Planner workspace.
 * Composes four panels in a horizontal row:
 *   3. Risk & Compliance (POLARIS)
 *   4. Captain Decision
 *   5. Key Alerts
 *   6. Data Provenance
 *
 * Phase 7: reads selectedRouteId from RoutePlannerContext — no props needed.
 * Alerts and Provenance now fetched from API via hooks.
 */

import RiskCompliancePanel from './RiskCompliancePanel'
import CaptainDecisionPanel from './CaptainDecisionPanel'
import KeyAlertsPanel from './KeyAlertsPanel'
import DataProvenancePanel from './DataProvenancePanel'
import { useVoyageSession } from '../../contexts/VoyageSessionContext'
import styles from './DecisionLayer.module.css'

export default function DecisionLayer() {
  const { selectedRouteId, activeRoute } = useVoyageSession()

  return (
    <div className={styles.layer} aria-label="Decision and information panels">
      <div className={styles.grid}>
        {/* 3. Risk & Compliance */}
        <RiskCompliancePanel selectedRouteId={selectedRouteId} activeRoute={activeRoute} />

        {/* 4. Captain Decision */}
        <CaptainDecisionPanel selectedRouteId={selectedRouteId} activeRoute={activeRoute} />

        {/* 5. Key Alerts */}
        <KeyAlertsPanel />

        {/* 6. Data Provenance */}
        <DataProvenancePanel />
      </div>
    </div>
  )
}
