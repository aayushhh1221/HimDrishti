/**
 * KeyAlertsPanel.tsx — HimDrishti Phase 7
 * SIH 2026 · PS 26059
 *
 * "5. Key Alerts" panel — displays operational alert items with expand/collapse.
 * Phase 7: fetches from GET /api/v1/alerts, falls back to DEMO_ALERTS if
 * backend is unavailable. Loading/error states handled gracefully.
 * Visual design unchanged.
 */

import { Info, ChevronRight } from 'lucide-react'
import AlertItem from './AlertItem'
import { DEMO_ALERTS, type DemoAlert } from '../../data/demoAlerts'
import { useAlerts } from '../../hooks/useApi'
import type { ApiAlert } from '../../services/api'
import styles from './KeyAlertsPanel.module.css'

/** Adapt API alert to DemoAlert shape so AlertItem works unchanged */
function apiAlertToDemo(a: ApiAlert): DemoAlert {
  const iconMap: Record<string, DemoAlert['icon']> = {
    warning: 'triangle-alert',
    critical: 'shield-alert',
    info: 'info',
  }
  return {
    id: a.id,
    severity: a.severity,
    icon: iconMap[a.severity] ?? 'info',
    title: a.title,
    description: a.description,
    details: a.details,
  }
}

export default function KeyAlertsPanel() {
  const alertState = useAlerts()

  // Determine which data to display
  const alerts: DemoAlert[] =
    alertState.status === 'success' && alertState.data
      ? alertState.data.alerts.map(apiAlertToDemo)
      : DEMO_ALERTS // demo fallback when loading / unavailable

  const isApiData = alertState.status === 'success'
  const isLoading = alertState.status === 'loading'

  return (
    <section className={styles.panel} aria-labelledby="alerts-panel-heading">
      {/* Header */}
      <div className={styles.header}>
        <span id="alerts-panel-heading" className={styles.headerTitle}>
          5. Key Alerts
          {isLoading && (
            <span style={{ fontSize: '10px', color: '#64748b', marginLeft: '6px' }}>
              Loading…
            </span>
          )}
        </span>
        <Info
          size={13}
          className={styles.infoIcon}
          aria-label={
            isApiData
              ? 'Pipeline-derived alert data — SYNTHETIC DEMO'
              : 'Demo alert data — not real operational threat assessment'
          }
          role="img"
        />
      </div>



      {/* Alert list */}
      <div className={styles.body} role="list" aria-label="Key operational alerts">
        {alerts.map((alert) => (
          <div key={alert.id} role="listitem">
            <AlertItem alert={alert} />
          </div>
        ))}


      </div>

      {/* View All link */}
      <div className={styles.footer}>
        <button
          className={styles.viewAllBtn}
          type="button"
          onClick={() =>
            console.info('[HimDrishti] View All Alerts — not implemented in this prototype')
          }
          aria-label="View all alerts — not implemented in this prototype"
        >
          View All Alerts
          <ChevronRight size={13} aria-hidden="true" />
        </button>
      </div>
    </section>
  )
}
