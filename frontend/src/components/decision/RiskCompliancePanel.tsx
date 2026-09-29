/**
 * RiskCompliancePanel.tsx — HimDrishti Phase 8
 * SIH 2026 · PS 26059
 *
 * "3. Risk & Compliance (POLARIS)" panel.
 *
 * Phase 8 additions (no redesign):
 *   - Forecast Confidence badge (HIGH/MEDIUM/LOW/UNKNOWN)
 *   - Degradation flags shown as compact chips
 *   - WholeVoyageRisk integrated_risk display
 *   - Growler/bergy-bit limitation notice (one compact line at bottom)
 *
 * PROTOTYPE: POLARIS RIV table is illustrative, not from IMO MSC.1/Circ.1519.
 * All risk values are "modeled" — not operational safety guarantees.
 */

import { Info, AlertTriangle, ShieldCheck } from 'lucide-react'
import RiskGauge from './RiskGauge'
import RiskBreakdown from './RiskBreakdown'
import { getRiskProfile } from '../../data/demoRisk'
import { useVoyageSession } from '../../contexts/VoyageSessionContext'
import type { ApiRoute, ForecastConfidence, ConfidenceLevel } from '../../services/api'
import styles from './RiskCompliancePanel.module.css'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function apiLevelToLabel(level: string): string {
  const map: Record<string, string> = {
    LOW: 'LOW RISK',
    MEDIUM: 'MEDIUM RISK',
    HIGH: 'HIGH RISK',
  }
  return map[level] ?? level
}

function apiCategoryToRoman(category: string): string {
  const map: Record<string, string> = {
    normal_operation: 'II',
    elevated_risk: 'IV',
    special_consideration: 'VI',
  }
  return map[category] ?? 'II'
}

// ---------------------------------------------------------------------------
// Phase 8: Forecast Confidence badge
// ---------------------------------------------------------------------------

const CONFIDENCE_COLORS: Record<ConfidenceLevel, { bg: string; border: string; text: string }> = {
  HIGH:    { bg: '#0f2a1e', border: '#276749', text: '#68d391' },
  MEDIUM:  { bg: '#1a2a0a', border: '#2f6627', text: '#9ae69a' },
  LOW:     { bg: '#2d1b00', border: '#744210', text: '#f6ad55' },
  UNKNOWN: { bg: '#1a1a2e', border: '#3730a3', text: '#a5b4fc' },
}

function ConfidenceBadge({ confidence }: { confidence: ForecastConfidence }) {
  const level = confidence.level as ConfidenceLevel
  const colors = CONFIDENCE_COLORS[level] ?? CONFIDENCE_COLORS.UNKNOWN
  const score = confidence.score != null ? ` (${(confidence.score * 100).toFixed(0)}%)` : ''

  // Compact, human-readable flag labels
  const flagLabels: Record<string, string> = {
    SYNTHETIC_DEMO_DATA:                  'SYNTH',
    FIXTURE_DATA:                         'FIXTURE',
    STALE_DATA_SOURCE:                    'STALE',
    PARTIAL_DATA:                         'PARTIAL',
    EXTENDED_HORIZON_REDUCED_CONFIDENCE:  'EXT HORIZON',
    INSUFFICIENT_VALIDATION:              'INSUFF VALID',
  }

  const visibleFlags = confidence.degradation_flags
    .map(f => {
      // strip per-source suffix for generic flags like STALE_DATA_SEA_ICE
      const base = Object.keys(flagLabels).find(k => f.startsWith(k))
      return base ? flagLabels[base] : f.replace(/_/g, ' ')
    })
    .filter((v, i, a) => a.indexOf(v) === i)  // deduplicate
    .slice(0, 3)                                // max 3 chips

  return (
    <div
      style={{
        marginBottom: '8px',
        padding: '5px 7px',
        background: colors.bg,
        border: `1px solid ${colors.border}`,
        borderRadius: '4px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
      }}
      aria-label={`Forecast confidence: ${level}${score}`}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '9px', color: '#9aa5b1', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Forecast Confidence
        </span>
        <span style={{ fontSize: '10px', fontWeight: 700, color: colors.text }}>
          {level}{score}
        </span>
      </div>
      {visibleFlags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px' }}>
          {visibleFlags.map(f => (
            <span
              key={f}
              style={{
                fontSize: '8px',
                padding: '1px 4px',
                borderRadius: '2px',
                background: colors.border,
                color: colors.text,
                fontWeight: 600,
              }}
              title={confidence.assessment_basis}
            >
              {f}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Phase 8: Whole-voyage integrated risk bar
// ---------------------------------------------------------------------------

function WholeVoyageRiskBar({ integratedRisk, budgetStatus }: {
  integratedRisk: number | null
  budgetStatus: string | null
}) {
  if (integratedRisk == null) return null
  const pct = Math.round(integratedRisk * 100)
  const color = budgetStatus === 'WITHIN_BUDGET' ? '#68d391' : '#fc8181'

  return (
    <div style={{ marginBottom: '6px' }} aria-label={`Whole-voyage integrated modeled risk: ${pct}%`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '8px', color: '#9aa5b1', marginBottom: '3px' }}>
        <span>Whole-voyage integrated risk (modeled)</span>
        <span style={{ color, fontWeight: 700 }}>{pct}%</span>
      </div>
      <div style={{ background: '#1e293b', borderRadius: '2px', height: '4px', overflow: 'hidden' }}>
        <div style={{ width: `${Math.min(pct, 100)}%`, height: '100%', background: color, borderRadius: '2px' }} />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface RiskCompliancePanelProps {
  selectedRouteId: string
  activeRoute: ApiRoute | null
}

export default function RiskCompliancePanel({
  selectedRouteId,
  activeRoute,
}: RiskCompliancePanelProps) {
  const { routeState } = useVoyageSession()

  const demo = getRiskProfile(selectedRouteId)

  const rio        = activeRoute?.polaris_rio ?? demo.rio
  const level      = (activeRoute?.risk_level ?? demo.level) as 'LOW' | 'MEDIUM' | 'HIGH'
  const levelLabel = activeRoute ? apiLevelToLabel(activeRoute.risk_level) : demo.levelLabel
  const category   = activeRoute
    ? (apiCategoryToRoman(activeRoute.risk_category) as 'I'|'II'|'III'|'IV'|'V'|'VI'|'VII')
    : demo.category

  const factors = activeRoute?.risk_factors
    ? {
        environmental: activeRoute.risk_factors.environmental,
        navigation: activeRoute.risk_factors.navigation,
        iceCondition: activeRoute.risk_factors.ice_condition,
        icebergCollision: activeRoute.risk_factors.iceberg_collision,
      }
    : demo.factors

  const isApiData = !!activeRoute

  // Phase 8 data
  const forecastConfidence = routeState.data?.forecast_confidence ?? null
  const wholeVoyageRisk    = routeState.data?.whole_voyage_risk ?? null

  return (
    <section className={styles.panel} aria-labelledby="risk-panel-heading">
      {/* Panel header */}
      <div className={styles.header}>
        <span id="risk-panel-heading" className={styles.headerTitle}>
          3. Risk &amp; Compliance (POLARIS)
        </span>
        <Info
          size={13}
          className={styles.infoIcon}
          aria-label="Prototype POLARIS RIO values — not from IMO MSC.1/Circ.1519"
          role="img"
        />
      </div>

      {/* Phase 8: Forecast Confidence badge */}
      {forecastConfidence && isApiData && (
        <div style={{ padding: '0 8px', marginTop: '4px' }}>
          <ConfidenceBadge confidence={forecastConfidence} />
        </div>
      )}

      {/* Phase 8: Whole-voyage risk bar */}
      {wholeVoyageRisk && isApiData && (
        <div style={{ padding: '0 8px' }}>
          <WholeVoyageRiskBar
            integratedRisk={wholeVoyageRisk.integrated_risk_recommended}
            budgetStatus={wholeVoyageRisk.risk_budget_status_recommended}
          />
        </div>
      )}

      {/* Body: gauge left, breakdown right */}
      <div className={styles.body}>
        {/* Left: gauge */}
        <div className={styles.gaugeCol}>
          <RiskGauge
            rio={rio}
            level={level}
            levelLabel={levelLabel}
            category={category}
          />
        </div>

        {/* Right: factor breakdown + RIO Category badge in bottom-right */}
        <div className={styles.breakdownCol}>
          <RiskBreakdown factors={factors} />
          <div className={styles.categoryBadge} aria-label={`RIO Category: ${category}`}>
            <ShieldCheck size={14} className={styles.categoryIcon} aria-hidden="true" />
            <span>RIO Category: {category}</span>
          </div>
        </div>
      </div>

      {/* Prototype notice */}
      <div className={styles.protoNote} aria-label="Prototype data notice">
        {isApiData
          ? 'Pipeline estimate · Illustrative POLARIS RIV values · Not operational'
          : 'Prototype demo values · POLARIS RIV table illustrative only'}
      </div>

      {/* Phase 8: Growler / bergy-bit limitation notice */}
      <div
        style={{
          padding: '5px 10px',
          background: '#f1f5f9',
          borderTop: '1px solid #d9e1e8',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}
        role="note"
        aria-label="Iceberg detection limitation"
      >
        <AlertTriangle size={12} style={{ color: '#b45309', flexShrink: 0 }} aria-hidden="true" />
        <span style={{ fontSize: '9px', color: '#1e293b', lineHeight: 1.35, fontWeight: 500 }}>
          Satellite detection may miss small growlers/bergy bits. Radar watch and visual lookout remain necessary.
        </span>
      </div>
    </section>
  )
}
