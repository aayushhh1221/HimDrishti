/**
 * AlertItem.tsx — HimDrishti Phase 5
 * SIH 2026 · PS 26059
 *
 * Individual expandable alert row for the Key Alerts panel.
 * Severity communicated via icon + text + restrained colour — never colour alone.
 */

import { useState } from 'react'
import { TriangleAlert, Info, ShieldAlert, ChevronDown } from 'lucide-react'
import type { DemoAlert } from '../../data/demoAlerts'
import styles from './AlertItem.module.css'

interface AlertItemProps {
  alert: DemoAlert
}

const SEVERITY_CONFIG = {
  info:     { borderColor: '#60a5fa', iconColor: '#2563eb', bgColor: '#eff6ff', Icon: Info },
  warning:  { borderColor: '#fbbf24', iconColor: '#d97706', bgColor: '#fffbeb', Icon: TriangleAlert },
  critical: { borderColor: '#f87171', iconColor: '#dc2626', bgColor: '#fff5f5', Icon: ShieldAlert },
} as const

export default function AlertItem({ alert }: AlertItemProps) {
  const [expanded, setExpanded] = useState(false)
  const cfg = SEVERITY_CONFIG[alert.severity]
  const Icon = cfg.Icon

  return (
    <article
      className={styles.item}
      style={{ borderLeftColor: cfg.borderColor }}
      aria-label={`${alert.severity} alert: ${alert.title}`}
    >
      {/* Summary row — always visible */}
      <button
        className={styles.summaryBtn}
        type="button"
        aria-expanded={expanded}
        aria-controls={`alert-details-${alert.id}`}
        onClick={() => setExpanded((v) => !v)}
      >
        {/* Icon */}
        <span
          className={styles.iconWrap}
          style={{ background: cfg.bgColor, color: cfg.iconColor }}
          aria-hidden="true"
        >
          <Icon size={13} />
        </span>

        {/* Text */}
        <span className={styles.textWrap}>
          <span className={styles.title}>{alert.title}</span>
          <span className={styles.desc}>{alert.description}</span>
        </span>

        {/* Chevron */}
        <ChevronDown
          size={13}
          className={`${styles.chevron} ${expanded ? styles.chevronOpen : ''}`}
          aria-hidden="true"
        />
      </button>

      {/* Expanded details */}
      {expanded && (
        <dl
          id={`alert-details-${alert.id}`}
          className={styles.details}
          role="region"
          aria-label={`Details for ${alert.title}`}
        >
          {alert.details.map((d) => (
            <div key={d.label} className={styles.detailRow}>
              <dt className={styles.detailLabel}>{d.label}</dt>
              <dd className={styles.detailValue}>{d.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </article>
  )
}
