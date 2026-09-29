/**
 * RouteCard.tsx
 * SIH 2026 · PS 26059 / PS 26188
 *
 * Professional institutional route card matching reference-ui2.png:
 * - Simple clean white card with thin border
 * - Semantic risk colors for title and risk badge
 * - 3 clean metric columns: Time, Fuel, Risk (POLARIS)
 * - Compact spacing, consistent typography
 * - No check icons, no AI images, no extra progress bars or clutter
 */

import type { DemoRoute } from '../../data/demoRoutes'
import styles from './RouteCard.module.css'

interface RouteCardProps {
  route: DemoRoute
  isSelected: boolean
  onSelect: (id: string) => void
  isRecommended?: boolean
  riskBudgetLimit?: number
  confidenceLabel?: string
  confidenceScore?: number
  counterfactual?: {
    timeDelta: string
    fuelDelta: string
    riskDelta: string
  }
}

export default function RouteCard({
  route,
  isSelected,
  onSelect,
}: RouteCardProps) {
  const isLow = route.riskLevel === 'LOW'
  const isMed = route.riskLevel === 'MEDIUM'

  const cardBorderClass = isLow
    ? styles.cardGreen
    : isMed
      ? styles.cardAmber
      : styles.cardRed

  const titleClass = isLow
    ? styles.titleGreen
    : isMed
      ? styles.titleAmber
      : styles.titleRed

  const badgeClass = isLow
    ? styles.badgeGreen
    : isMed
      ? styles.badgeAmber
      : styles.badgeRed

  return (
    <article
      className={`${styles.card} ${cardBorderClass} ${isSelected ? styles.cardSelected : ''}`}
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      aria-label={`${route.name} — ${route.riskLevel} Risk, Time ${route.etaLabel}, Fuel ${route.fuelMT.toFixed(1)} MT, Risk ${route.polarisRIO}/100`}
      onClick={() => onSelect(route.id)}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(route.id)}
    >
      {/* ── Card Header ────────────────────────────── */}
      <div className={styles.header}>
        <h3 className={`${styles.routeName} ${titleClass}`}>{route.name}</h3>
        <span className={`${styles.badge} ${badgeClass}`}>
          {route.riskLevel} RISK
        </span>
      </div>

      {/* ── 3 Primary Metrics Grid ─────────────────── */}
      <div className={styles.metricsGrid}>
        {/* Time */}
        <div className={styles.metricItem}>
          <div className={styles.metricLabel}>Time</div>
          <div className={styles.metricVal}>{route.etaLabel}</div>
        </div>

        {/* Fuel */}
        <div className={styles.metricItem}>
          <div className={styles.metricLabel}>Fuel</div>
          <div className={styles.metricVal}>{route.fuelMT.toFixed(1)} MT</div>
        </div>

        {/* Risk (POLARIS) */}
        <div className={styles.metricItem}>
          <div className={styles.metricLabel}>Risk (POLARIS)</div>
          <div className={styles.metricVal}>
            {route.polarisRIO} <span className={styles.valSub}>/ 100</span>
          </div>
        </div>
      </div>

      {/* ── Convergence notice (only when is_distinct=false) ── */}
      {!route.is_distinct && (
        <div
          style={{
            marginTop: '6px',
            padding: '4px 8px',
            background: '#fffbeb',
            border: '1px solid #fbbf24',
            borderRadius: '3px',
            fontSize: '10px',
            color: '#92400e',
            lineHeight: 1.4,
            cursor: 'help',
          }}
          title={route.convergence_note ?? 'This path is identical to another route in this run.'}
          role="note"
          aria-label="Path convergence warning"
        >
          ⚠ Path convergence — same geometry as recommended route
        </div>
      )}
    </article>
  )
}
