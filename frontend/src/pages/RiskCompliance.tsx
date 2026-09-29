/**
 * RiskCompliance — Phase 10
 * SIH 2026 · PS 26059
 *
 * POLARIS/RIO risk assessment from VoyageSessionContext.
 * Shows convergence warnings when route paths are not meaningfully distinct.
 */

import { useVoyageSession } from '../contexts/VoyageSessionContext'
import styles from './shared-page.module.css'

export default function RiskCompliance() {
  const { routeState, selectedRouteId, dataMode } = useVoyageSession()
  const isSuccess = routeState.status === 'success'
  const data = routeState.data
  const activeRoute = data?.routes.find(r => r.route_id === selectedRouteId) ?? null

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.heading}>Risk &amp; Compliance</h1>
          <p className={styles.sub}>
            POLARIS/RIO risk assessment, operating mode, and risk budget outcome
            for the current route generation. Generate routes in Route Planner first.
          </p>
        </div>
        <div className={styles.modeBadge}>{dataMode}</div>
      </div>

      {!isSuccess && (
        <div className={styles.warnBanner} role="status" aria-live="polite">
          No route data available. Navigate to <strong>Route Planner</strong> and
          generate routes to populate this view.
        </div>
      )}

      {isSuccess && data && (
        <>
          <div className={styles.card}>
            <div className={styles.cardTitle}>Run Configuration</div>
            <dl className={styles.dl}>
              <div className={styles.dlRow}><dt>Operating Mode</dt><dd>{data.operating_mode}</dd></div>
              <div className={styles.dlRow}><dt>Risk Budget Limit</dt><dd>{(data.risk_budget_limit * 100).toFixed(0)}%</dd></div>
              <div className={styles.dlRow}><dt>Forecast Horizon</dt><dd>{data.forecast_horizon_hours} h</dd></div>
              <div className={styles.dlRow}><dt>Request ID</dt><dd className={styles.mono}>{data.request_id}</dd></div>
              <div className={styles.dlRow}><dt>Generated At</dt><dd className={styles.mono}>{data.generated_at}</dd></div>
            </dl>
          </div>

          {activeRoute && (
            <div className={styles.card}>
              <div className={styles.cardTitle}>Selected Route: {activeRoute.name}</div>
              <dl className={styles.dl}>
                <div className={styles.dlRow}><dt>Risk Level</dt><dd>{activeRoute.risk_level}</dd></div>
                <div className={styles.dlRow}><dt>Risk Category</dt><dd>{activeRoute.risk_category}</dd></div>
                <div className={styles.dlRow}><dt>POLARIS RIO</dt><dd>{activeRoute.polaris_rio}</dd></div>
                <div className={styles.dlRow}><dt>Budget Status</dt><dd>{activeRoute.risk_budget_status?.status ?? '—'}</dd></div>
                <div className={styles.dlRow}><dt>Actual Risk</dt><dd>{activeRoute.risk_budget_status?.actual_risk?.toFixed(3) ?? '—'}</dd></div>
                <div className={styles.dlRow}><dt>ETA</dt><dd>{activeRoute.cost_breakdown.time_hours.toFixed(1)} h</dd></div>
                <div className={styles.dlRow}><dt>Fuel</dt><dd>{activeRoute.cost_breakdown.fuel_tonnes.toFixed(1)} t</dd></div>
              </dl>
              <div className={styles.explanation}>{activeRoute.system_explanation}</div>
            </div>
          )}

          <div className={styles.card}>
            <div className={styles.cardTitle}>All Routes — Risk Budget Outcome</div>
            <table className={styles.table} aria-label="Route risk budget outcomes">
              <thead>
                <tr><th>Route</th><th>Risk Level</th><th>POLARIS RIO</th><th>Budget Status</th><th>Actual Risk</th><th>Distinct Path</th></tr>
              </thead>
              <tbody>
                {data.routes.map(r => (
                  <tr key={r.route_id} className={r.route_id === selectedRouteId ? styles.rowSelected : ''}>
                    <td>{r.name}</td>
                    <td>{r.risk_level}</td>
                    <td>{r.polaris_rio}</td>
                    <td>{r.risk_budget_status?.status ?? '—'}</td>
                    <td>{r.risk_budget_status?.actual_risk?.toFixed(3) ?? '—'}</td>
                    <td>
                      {r.is_distinct
                        ? <span style={{ color: '#16a34a', fontWeight: 600 }}>✓ Yes</span>
                        : <span
                            style={{ color: '#d97706', fontWeight: 600, cursor: 'help' }}
                            title={r.convergence_note ?? 'Path identical to another route in this run'}
                          >
                            ⚠ No
                          </span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.routes.some(r => !r.is_distinct) && (
              <div className={styles.noticeBox} style={{ marginTop: '0.75rem' }} role="note">
                <strong>Path Convergence:</strong>{' '}
                {data.routes
                  .filter(r => !r.is_distinct && r.convergence_note)
                  .map(r => <span key={r.route_id}><em>{r.name}:</em> {r.convergence_note} </span>)
                }
                The synthetic pipeline hazard field at 26×20 resolution produces identical
                Dijkstra / UCS paths for balanced and safe weight profiles in this fixture.
                The aggressive route uses distinct time-priority weights and finds a different path.
              </div>
            )}
          </div>

          <div className={styles.noticeBox} role="note">
            <strong>POLARIS Notice:</strong> Values shown are illustrative prototype
            calculations only. Authoritative RIV values must come from IMO
            MSC.1/Circ.1519. Final authority rests with the Master/Captain/Ice Pilot.
          </div>

          <div className={styles.noticeBox} role="note">
            <strong>Prototype Notice:</strong> {data.prototype_notice}
          </div>
        </>
      )}

      <div className={styles.tag}>SIH 2026 · PS 26188</div>
    </div>
  )
}
