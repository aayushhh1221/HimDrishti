/**
 * RiskBreakdown.tsx — HimDrishti Phase 5
 * SIH 2026 · PS 26059
 *
 * Compact table of four POLARIS risk sub-factors.
 * DEMO DATA ONLY.
 */

import type { RiskFactors } from '../../data/demoRisk'
import styles from './RiskBreakdown.module.css'

interface RiskBreakdownProps {
  factors: RiskFactors
}

const FACTOR_ROWS: { label: string; key: keyof RiskFactors }[] = [
  { label: 'Environmental Risk',    key: 'environmental' },
  { label: 'Navigational Risk',     key: 'navigation' },
  { label: 'Ice Condition Risk',    key: 'iceCondition' },
  { label: 'Iceberg Collision Risk', key: 'icebergCollision' },
]

export default function RiskBreakdown({ factors }: RiskBreakdownProps) {
  return (
    <dl className={styles.breakdown} aria-label="Risk factor breakdown">
      {FACTOR_ROWS.map(({ label, key }) => {
        const value = factors[key]
        return (
          <div key={key} className={styles.row}>
            <dt className={styles.label}>{label}</dt>
            <dd className={styles.value}>
              <span
                className={styles.score}
                aria-label={`${value} out of 100`}
              >
                {value}
              </span>
              <span className={styles.denom}> /100</span>
            </dd>
          </div>
        )
      })}
    </dl>
  )
}
