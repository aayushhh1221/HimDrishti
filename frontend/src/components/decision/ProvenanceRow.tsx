/**
 * ProvenanceRow.tsx — HimDrishti Phase 5
 * SIH 2026 · PS 26059
 *
 * Single data source row for the Data Provenance panel.
 */

import { CheckCircle, Clock, AlertCircle } from 'lucide-react'
import type { ProvenanceRecord, ProvenanceStatus } from '../../data/demoProvenance'
import styles from './ProvenanceRow.module.css'

interface ProvenanceRowProps {
  record: ProvenanceRecord
}

const STATUS_CONFIG: Record<ProvenanceStatus, {
  icon: typeof CheckCircle
  label: string
  color: string
}> = {
  synced:      { icon: CheckCircle, label: 'Synced',      color: '#16a34a' },
  stale:       { icon: Clock,       label: 'Stale',       color: '#d97706' },
  unavailable: { icon: AlertCircle, label: 'Unavailable', color: '#dc2626' },
}

export default function ProvenanceRow({ record }: ProvenanceRowProps) {
  const cfg = STATUS_CONFIG[record.status]
  const StatusIcon = cfg.icon

  return (
    <div
      className={styles.row}
      role="row"
      aria-label={`${record.category}: ${record.source}, ${cfg.label}, updated ${record.updatedAtShort}`}
    >
      {/* Category + source */}
      <div className={styles.meta}>
        <span className={styles.category}>{record.category}</span>
        <span className={styles.source}>{record.source}</span>
      </div>

      {/* Status */}
      <div className={styles.status}>
        <StatusIcon
          size={11}
          style={{ color: cfg.color, flexShrink: 0 }}
          aria-hidden="true"
        />
        <span className={styles.statusLabel} style={{ color: cfg.color }}>
          {cfg.label}
        </span>
      </div>

      {/* Timestamp */}
      <span className={styles.timestamp}>{record.updatedAtShort}</span>
    </div>
  )
}
