/**
 * AuditLog — Phase 10 (Session Audit Events)
 * SIH 2026 · PS 26059
 *
 * Reads from the append-only auditEvents array in VoyageSessionContext.
 * Events are pushed by: generateRoutes, setSelectedRouteId,
 * setCaptainDecision, setLastReplay, and report export.
 * No events are fabricated or reconstructed at render time.
 */

import { useVoyageSession } from '../contexts/VoyageSessionContext'
import styles from './shared-page.module.css'

const ROLE_COLOR: Record<string, string> = {
  SYSTEM:   '#2b6cb0',
  OPERATOR: '#276749',
  PIPELINE: '#92400e',
  CAPTAIN:  '#702459',
}

export default function AuditLog() {
  const { auditEvents, dataMode, routeState } = useVoyageSession()

  const hasRoutes = routeState.status === 'success'

  // Convergence warnings from pipeline (routes with is_distinct=false)
  const convergenceWarnings = routeState.data?.routes
    .filter((r) => !r.is_distinct && r.convergence_note)
    .map((r) => ({ route_id: r.route_id, note: r.convergence_note! })) ?? []

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.heading}>Decision Audit Log</h1>
          <p className={styles.sub}>
            Timestamped record of all system, operator, pipeline, and captain
            decisions in this prototype session. Events are appended as they occur —
            no fabricated history.
          </p>
        </div>
        <div className={styles.modeBadge}>{dataMode}</div>
      </div>

      {!hasRoutes && auditEvents.length === 0 && (
        <div className={styles.warnBanner} role="status" aria-live="polite">
          No session events recorded yet. Navigate to <strong>Route Planner</strong> and
          generate routes to begin the audit log.
        </div>
      )}

      {convergenceWarnings.length > 0 && (
        <div className={styles.noticeBox} role="note">
          <strong>Route Convergence Notice:</strong>{' '}
          {convergenceWarnings.map((w) => (
            <div key={w.route_id}><em>{w.route_id}:</em> {w.note}</div>
          ))}
        </div>
      )}

      {auditEvents.length > 0 && (
        <div className={styles.card}>
          <div className={styles.cardTitle}>Session Events ({auditEvents.length})</div>
          <ol className={styles.timeline} aria-label="Decision audit timeline">
            {auditEvents.map((e) => (
              <li key={e.id} className={styles.timelineItem}>
                <div className={styles.timelineMarker} aria-hidden="true" />
                <div className={styles.timelineContent}>
                  <div className={styles.timelineHeader}>
                    <span
                      className={styles.timelineRole}
                      style={{ color: ROLE_COLOR[e.role] ?? '#4a5568' }}
                    >
                      {e.role}
                    </span>
                    <span className={styles.timelineAction}>{e.action}</span>
                    <span className={styles.timelineTime}>
                      {e.timestamp.replace('T', ' ').slice(0, 19)} UTC
                    </span>
                  </div>
                  <div className={styles.timelineDetail}>{e.detail}</div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className={styles.noticeBox} role="note">
        <strong>Audit Notice:</strong> This log captures prototype session state only.
        It is not a cryptographically signed audit trail and must not be used for
        operational compliance recording.
      </div>

      <div className={styles.tag}>SIH 2026 · PS 26188</div>
    </div>
  )
}
