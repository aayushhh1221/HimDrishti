/**
 * RouteProfilePanel.tsx
 * SIH 2026 · PS 26188
 *
 * Route Profile (Selected Route) cross-section chart matching reference.png bottom-right.
 * Features selectable profile dimensions:
 *   - Risk (POLARIS)
 *   - Ice Concentration
 *   - Elevation (Bathymetry)
 *   - Speed
 * Plots distance (0–3,000 NM) vs score with safety color bands.
 */

import { useState } from 'react'
import { useVoyageSession } from '../../contexts/VoyageSessionContext'
import styles from './RouteProfilePanel.module.css'

type ProfileTab = 'Risk (POLARIS)' | 'Ice Concentration' | 'Elevation' | 'Speed'

export default function RouteProfilePanel() {
  const { selectedRouteId } = useVoyageSession()
  const [activeTab, setActiveTab] = useState<ProfileTab>('Risk (POLARIS)')

  // Dynamic profile curves based on selected route and active dimension
  const pointsRisk = selectedRouteId === 'higher-risk'
    ? [[0, 15], [500, 28], [1000, 45], [1500, 68], [2000, 78], [2500, 85], [3000, 73]]
    : selectedRouteId === 'alternative1'
      ? [[0, 12], [500, 22], [1000, 35], [1500, 48], [2000, 55], [2500, 42], [3000, 42]]
      : [[0, 8], [500, 14], [1000, 25], [1500, 28], [2000, 35], [2500, 22], [3000, 18]]

  const pointsIce = selectedRouteId === 'higher-risk'
    ? [[0, 0], [500, 0], [1000, 15], [1500, 45], [2000, 70], [2500, 85], [3000, 80]]
    : selectedRouteId === 'alternative1'
      ? [[0, 0], [500, 0], [1000, 5], [1500, 25], [2000, 40], [2500, 50], [3000, 45]]
      : [[0, 0], [500, 0], [1000, 0], [1500, 10], [2000, 18], [2500, 25], [3000, 20]]

  const pointsSpeed = selectedRouteId === 'higher-risk'
    ? [[0, 14], [500, 14], [1000, 12], [1500, 10], [2000, 8], [2500, 7], [3000, 8]]
    : selectedRouteId === 'alternative1'
      ? [[0, 13], [500, 13], [1000, 12], [1500, 11], [2000, 9], [2500, 9], [3000, 9]]
      : [[0, 12], [500, 12], [1000, 12], [1500, 11.5], [2000, 11], [2500, 10.5], [3000, 10]]

  const pointsBathymetry = [
    [0, 150], [500, 4200], [1000, 4800], [1500, 4500], [2000, 3800], [2500, 1200], [3000, 280]
  ]

  // Map coordinates to SVG viewbox (W: 320, H: 80, padding: L:26, R:10, T:8, B:18)
  const W = 320
  const H = 84
  const pL = 26
  const pR = 10
  const pT = 6
  const pB = 16

  const plotW = W - pL - pR
  const plotH = H - pT - pB

  let activeData = pointsRisk
  let maxY = 100
  let yLabel = 'Risk Score'

  if (activeTab === 'Ice Concentration') {
    activeData = pointsIce
    maxY = 100
    yLabel = 'SIC (%)'
  } else if (activeTab === 'Speed') {
    activeData = pointsSpeed
    maxY = 20
    yLabel = 'Speed (kt)'
  } else if (activeTab === 'Elevation') {
    activeData = pointsBathymetry
    maxY = 5000
    yLabel = 'Depth (m)'
  }

  const svgPoints = activeData.map(([d, val]) => {
    const x = pL + (d / 3000) * plotW
    const y = pT + plotH - (val / maxY) * plotH
    return [x, y]
  })

  // Build SVG path
  const pathD = svgPoints.reduce((acc, [x, y], idx) => {
    return idx === 0 ? `M ${x},${y}` : `${acc} L ${x},${y}`
  }, '')

  // Area path
  const areaD = `${pathD} L ${pL + plotW},${pT + plotH} L ${pL},${pT + plotH} Z`

  return (
    <div className={styles.container} aria-label="Selected route profile along voyage distance">
      <div className={styles.header}>
        <h3 className={styles.title}>Route Profile (Selected Route)</h3>
        <div className={styles.tabGroup} role="tablist">
          {(['Risk (POLARIS)', 'Ice Concentration', 'Elevation', 'Speed'] as ProfileTab[]).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={activeTab === tab}
              className={`${styles.tabBtn} ${activeTab === tab ? styles.tabBtnActive : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.replace(' (POLARIS)', '')}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.chartWrapper}>
        <svg viewBox={`0 0 ${W} ${H}`} className={styles.chartSvg} preserveAspectRatio="none">
          {/* Background Safety Color Bands for Risk & Ice */}
          {(activeTab === 'Risk (POLARIS)' || activeTab === 'Ice Concentration') && (
            <>
              {/* High Risk (>66) */}
              <rect x={pL} y={pT} width={plotW} height={plotH * 0.34} fill="rgba(239, 68, 68, 0.08)" />
              {/* Medium Risk (33-66) */}
              <rect x={pL} y={pT + plotH * 0.34} width={plotW} height={plotH * 0.33} fill="rgba(245, 158, 11, 0.08)" />
              {/* Low Risk (0-33) */}
              <rect x={pL} y={pT + plotH * 0.67} width={plotW} height={plotH * 0.33} fill="rgba(34, 197, 94, 0.08)" />
            </>
          )}

          {/* Grid lines */}
          <line x1={pL} y1={pT} x2={pL + plotW} y2={pT} stroke="#e2e8f0" strokeWidth="0.8" strokeDasharray="2 2" />
          <line x1={pL} y1={pT + plotH * 0.25} x2={pL + plotW} y2={pT + plotH * 0.25} stroke="#e2e8f0" strokeWidth="0.8" strokeDasharray="2 2" />
          <line x1={pL} y1={pT + plotH * 0.50} x2={pL + plotW} y2={pT + plotH * 0.50} stroke="#e2e8f0" strokeWidth="0.8" strokeDasharray="2 2" />
          <line x1={pL} y1={pT + plotH * 0.75} x2={pL + plotW} y2={pT + plotH * 0.75} stroke="#e2e8f0" strokeWidth="0.8" strokeDasharray="2 2" />
          <line x1={pL} y1={pT + plotH} x2={pL + plotW} y2={pT + plotH} stroke="#cbd5e1" strokeWidth="1" />

          {/* Y Axis text */}
          <text x={pL - 4} y={pT + 6} fontSize="7" fill="#64748b" textAnchor="end" fontWeight="600">{maxY}</text>
          <text x={pL - 4} y={pT + plotH * 0.5 + 3} fontSize="7" fill="#64748b" textAnchor="end" fontWeight="600">{maxY / 2}</text>
          <text x={pL - 4} y={pT + plotH} fontSize="7" fill="#64748b" textAnchor="end" fontWeight="600">0</text>

          {/* Profile Area fill */}
          <path d={areaD} fill="rgba(249, 115, 22, 0.12)" />

          {/* Profile Line */}
          <path d={pathD} fill="none" stroke="#ea580c" strokeWidth="1.8" strokeLinecap="round" />

          {/* Dots on points */}
          {svgPoints.map(([x, y], i) => (
            <circle key={i} cx={x} cy={y} r="2.5" fill="#ea580c" stroke="#ffffff" strokeWidth="1" />
          ))}

          {/* X Axis distance ticks */}
          {[0, 500, 1000, 1500, 2000, 2500, 3000].map((d) => {
            const x = pL + (d / 3000) * plotW
            return (
              <text key={d} x={x} y={H - 4} fontSize="6.5" fill="#64748b" textAnchor="middle" fontWeight="500">
                {d === 0 ? '0' : d >= 1000 ? `${(d / 1000).toFixed(0)}k` : d}
              </text>
            )
          })}
        </svg>

        {/* Axis Labels */}
        <div className={styles.axisXLabel}>Distance (NM)</div>
        <div className={styles.axisYLabel}>{yLabel}</div>
      </div>
    </div>
  )
}
