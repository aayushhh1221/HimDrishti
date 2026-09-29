/**
 * RouteComparisonPanel.tsx
 * SIH 2026 · PS 26059 / PS 26188
 *
 * Route Comparison right panel matching reference-ui2.png:
 *   1. Header: "2. Route Comparison"
 *   2. The 3 Route Cards (Recommended, Alternative 1, Higher Risk)
 *   3. Clean "Compare All Routes" action button at the bottom
 */

import { useNavigate } from 'react-router-dom'
import { Info, BarChart2 } from 'lucide-react'
import RouteCard from './RouteCard'
import { DEMO_ROUTES, type DemoRoute } from '../../data/demoRoutes'
import { useVoyageSession } from '../../contexts/VoyageSessionContext'
import type { ApiRoute } from '../../services/api'
import styles from './RouteComparisonPanel.module.css'

interface RouteComparisonPanelProps {
  selectedRouteId: string
  onRouteSelect: (id: string) => void
}

function apiRouteToDemo(r: ApiRoute): DemoRoute {
  const colorSoftMap: Record<string, string> = {
    '#00c896': '#dcfce7',
    '#f5a623': '#fef3c7',
    '#e03131': '#fee2e2',
  }
  const badgeColorMap: Record<string, string> = {
    '#00c896': '#15803d',
    '#f5a623': '#b45309',
    '#e03131': '#b91c1c',
  }
  const dashMap: Record<string, number[] | undefined> = {
    recommended: undefined,
    alternative1: [5, 4],
    'higher-risk': [6, 3],
  }

  const etaH = r.cost_breakdown.time_hours
  const etaDays = Math.floor(etaH / 24)
  const etaRem  = Math.round(etaH % 24)
  const etaLabel = etaDays > 0 ? `${etaDays}d ${etaRem}h` : `${Math.round(etaH)}h`

  return {
    id: r.route_id,
    name: r.name,
    shortLabel: r.name,
    riskLevel: r.risk_level,
    etaLabel,
    etaHours: etaH,
    fuelMT: r.cost_breakdown.fuel_tonnes,
    polarisRIO: r.polaris_rio,
    color: r.color,
    colorSoft: colorSoftMap[r.color] ?? '#f0fdf4',
    badgeTextColor: badgeColorMap[r.color] ?? '#166534',
    lineStyle: r.route_id === 'recommended' ? 'solid' : 'dashed',
    dashArray: dashMap[r.route_id],
    coordinates: r.points.map((p) => [p.lon, p.lat] as [number, number]),
    labelCoord: r.label_coord ? [r.label_coord.lon, r.label_coord.lat] : [0, 0],
    is_distinct: r.is_distinct,
    convergence_note: r.convergence_note,
  }
}

export default function RouteComparisonPanel({
  selectedRouteId,
  onRouteSelect,
}: RouteComparisonPanelProps) {
  const navigate = useNavigate()
  const { routeState } = useVoyageSession()

  const isApiData = routeState.status === 'success' && !!routeState.data
  const apiRoutes = routeState.data?.routes ?? []
  const routes: DemoRoute[] = isApiData ? apiRoutes.map(apiRouteToDemo) : DEMO_ROUTES

  return (
    <div className={styles.panel} aria-label="Route Comparison">
      {/* ── Header ─────────────────────────────────── */}
      <div className={styles.header}>
        <div className={styles.headerTitleGroup}>
          <h2 className={styles.headerTitle}>2. Route Comparison</h2>
          <Info size={13} className={styles.infoIcon} aria-hidden="true" />
        </div>
      </div>

      {/* ── Route Cards List ───────────────────────── */}
      <div className={styles.cardsList}>
        {routes.map((route) => (
          <RouteCard
            key={route.id}
            route={route}
            isSelected={selectedRouteId === route.id}
            onSelect={onRouteSelect}
          />
        ))}
      </div>

      {/* ── Bottom Compare Button ───────────────────── */}
      <div className={styles.bottomAction}>
        <button
          type="button"
          className={styles.compareAllBtn}
          onClick={() => navigate('/risk-compliance')}
          title="Compare all routes in detail"
        >
          <BarChart2 size={13} />
          Compare All Routes
        </button>
      </div>
    </div>
  )
}
