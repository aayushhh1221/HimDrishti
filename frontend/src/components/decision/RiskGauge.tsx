/**
 * RiskGauge.tsx — HimDrishti Phase 5 / Phase 12.1
 * SIH 2026 · PS 26059
 *
 * Clean semicircular risk gauge displaying dynamic RIO score (0–100).
 * Matches visual reference:
 * - Upper semicircular gradient arch: green -> yellow -> red
 * - L / M / H labels positioned clearly without overlap
 * - Dynamic score (e.g. 18) and /100 cleanly centered inside arch
 * - LOW RISK label clearly below arc without overlap
 */

import styles from './RiskGauge.module.css'

interface RiskGaugeProps {
  rio: number            // 0–100
  level: 'LOW' | 'MEDIUM' | 'HIGH'
  levelLabel: string     // e.g. "LOW RISK"
  category?: string      // optional (rendered in parent or screen-reader)
}

const GAUGE_CX = 65
const GAUGE_CY = 70
const GAUGE_R = 47

const LEVEL_COLORS: Record<string, string> = {
  LOW:    '#16a34a',
  MEDIUM: '#d97706',
  HIGH:   '#dc2626',
}

export default function RiskGauge({ rio, level, levelLabel, category }: RiskGaugeProps) {
  const value = Math.max(0, Math.min(100, Math.round(rio)))
  const activeColor = LEVEL_COLORS[level] ?? '#16a34a'

  // Dynamic needle tick position along the arch (180° = 0%, 270° = 50%, 360° = 100%)
  const needleAngle = 180 + (value / 100) * 180
  const needleRad = (needleAngle * Math.PI) / 180
  const needleX1 = GAUGE_CX + (GAUGE_R - 5.5) * Math.cos(needleRad)
  const needleY1 = GAUGE_CY + (GAUGE_R - 5.5) * Math.sin(needleRad)
  const needleX2 = GAUGE_CX + (GAUGE_R + 5.5) * Math.cos(needleRad)
  const needleY2 = GAUGE_CY + (GAUGE_R + 5.5) * Math.sin(needleRad)

  // Semicircular arch path from left (18, 70) through top (65, 23) to right (112, 70)
  const trackPath = `M ${GAUGE_CX - GAUGE_R} ${GAUGE_CY} A ${GAUGE_R} ${GAUGE_R} 0 0 1 ${GAUGE_CX + GAUGE_R} ${GAUGE_CY}`

  return (
    <div
      className={styles.gaugeWrapper}
      role="img"
      aria-label={`RIO score ${value} out of 100. Risk level: ${levelLabel}. ${category ? `RIO Category: ${category}.` : ''}`}
    >
      <svg
        viewBox="0 0 130 80"
        className={styles.gaugeSvg}
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <linearGradient id="riskArcGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#16a34a" />
            <stop offset="38%" stopColor="#eab308" />
            <stop offset="72%" stopColor="#ea580c" />
            <stop offset="100%" stopColor="#dc2626" />
          </linearGradient>
        </defs>

        {/* Gradient arch track */}
        <path
          d={trackPath}
          fill="none"
          stroke="url(#riskArcGrad)"
          strokeWidth="8.5"
          strokeLinecap="round"
        />

        {/* L / M / H labels offset clearly from arc */}
        <text x="8" y="73" className={styles.scaleLabel} textAnchor="middle">L</text>
        <text x={GAUGE_CX} y="14" className={styles.scaleLabel} textAnchor="middle">M</text>
        <text x="122" y="73" className={styles.scaleLabel} textAnchor="middle">H</text>

        {/* Needle indicator tick on the arc */}
        <line
          x1={needleX1}
          y1={needleY1}
          x2={needleX2}
          y2={needleY2}
          stroke="#0f172a"
          strokeWidth="2.5"
          strokeLinecap="round"
          opacity="0.85"
        />

        {/* Dynamic score centered in clean white interior */}
        <text
          x={GAUGE_CX - 8}
          y="48"
          textAnchor="middle"
          className={styles.rioNumber}
          style={{ fill: activeColor }}
        >
          {value}
        </text>

        {/* /100 aligned under score in clean white interior */}
        <text
          x={GAUGE_CX + 6}
          y="46"
          textAnchor="start"
          className={styles.rioDenom}
        >
          /100
        </text>

        {/* LOW RISK label centered directly below score in clean white interior */}
        <text
          x={GAUGE_CX}
          y="63"
          textAnchor="middle"
          className={styles.levelSvgLabel}
          style={{ fill: activeColor }}
        >
          {levelLabel}
        </text>
      </svg>

      {/* Screen-reader accessible label */}
      <span className={styles.srOnly}>
        RIO score {value} out of 100. Level: {levelLabel}. {category ? `RIO Category: ${category}.` : ''}
      </span>
    </div>
  )
}
