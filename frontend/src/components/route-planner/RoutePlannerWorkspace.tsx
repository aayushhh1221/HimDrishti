/**
 * RoutePlannerWorkspace
 * SIH 2026 · PS 26059
 *
 * Three-column layout: VoyageScenarioPanel | AntarcticMap | RouteComparisonPanel
 *
 * Phase 10: reads selectedRouteId from VoyageSessionContext (single source of truth).
 * forecastIndex remains internal — only used by AntarcticMap / ForecastTimeline.
 */

import { useState } from 'react'
import VoyageScenarioPanel from './VoyageScenarioPanel'
import AntarcticMap from './AntarcticMap'
import RouteComparisonPanel from './RouteComparisonPanel'
import { useVoyageSession } from '../../contexts/VoyageSessionContext'
import type { ForecastHourIndex } from '../../data/demoForecastStates'
import styles from './RoutePlannerWorkspace.module.css'

export default function RoutePlannerWorkspace() {
  const { selectedRouteId, setSelectedRouteId } = useVoyageSession()
  // forecastIndex remains local — only map and timeline need it
  const [forecastIndex, setForecastIndex] = useState<ForecastHourIndex>(2)

  return (
    <div className={styles.workspace}>
      {/* ── Left: Voyage Scenario ─────────────────── */}
      <div className={styles.leftPanel}>
        <VoyageScenarioPanel />
      </div>

      {/* ── Center: Antarctic Map ─────────────────── */}
      <div className={styles.centerPanel}>
        <AntarcticMap
          forecastIndex={forecastIndex}
          selectedRouteId={selectedRouteId}
          onForecastChange={setForecastIndex}
          onRouteSelect={setSelectedRouteId}
        />
      </div>

      {/* ── Right: Route Comparison ───────────────── */}
      <div className={styles.rightPanel}>
        <RouteComparisonPanel
          selectedRouteId={selectedRouteId}
          onRouteSelect={setSelectedRouteId}
        />
      </div>
    </div>
  )
}
