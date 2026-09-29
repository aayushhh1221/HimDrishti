/**
 * PrototypeBadge
 * SIH 2026 · PS 26059
 *
 * Small badge that clearly identifies HimDrishti as an SIH prototype.
 * Required by design.md §2 (Authenticity Safeguard) and §9.3.
 * Appears in the institutional header next to the HimDrishti wordmark.
 */

import styles from './PrototypeBadge.module.css'

interface PrototypeBadgeProps {
  /** Compact label for tight spaces. Default: false */
  compact?: boolean
}

export default function PrototypeBadge({ compact = false }: PrototypeBadgeProps) {
  return (
    <span
      className={styles.badge}
      title="SIH 2026 Smart India Hackathon Prototype · Problem Statement 26188"
      aria-label="Prototype — SIH 2026 demonstration system"
    >
      {compact ? 'Prototype' : 'Prototype'}
    </span>
  )
}
