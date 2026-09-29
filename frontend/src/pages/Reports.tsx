/**
 * Reports -- Mission decision & environmental audit reporting
 * SIH 2026 · PS 26188
 *
 * Phase 10: fully wired to VoyageSessionContext.
 * - Reads active route metrics, captain decision, voyage config, audit events
 * - Calls POST /api/v1/reports/export (Jinja2+WeasyPrint server-side PDF)
 * - Downloads the server PDF blob directly (no window.print())
 * - Falls back to JSON dossier download if WeasyPrint native libs unavailable
 */

import { useState } from 'react'
import { FileText, Download, ShieldCheck, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react'
import { useVoyageSession } from '../contexts/VoyageSessionContext'
import { exportReportPDF, exportReportEnvironmental } from '../services/api/client'
import type { PdfExportResult } from '../services/api/client'
import styles from './shared-page.module.css'

const DECISION_ICON = {
  accepted:  { icon: CheckCircle,    color: '#16a34a', label: 'Accepted by Master' },
  modified:  { icon: AlertTriangle,  color: '#d97706', label: 'Modification Requested' },
  rejected:  { icon: XCircle,        color: '#dc2626', label: 'Rejected' },
  pending:   { icon: Clock,          color: '#64748b', label: 'Awaiting Captain Decision' },
}

export default function Reports() {
  const {
    routeState,
    activeRoute,
    captainDecision,
    voyageConfig,
    auditEvents,
    sessionId,
    dataMode,
    pushAuditEvent,
  } = useVoyageSession()

  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [lastExport, setLastExport] = useState<PdfExportResult | null>(null)
  const [exportingEnv, setExportingEnv] = useState(false)
  const [exportEnvError, setExportEnvError] = useState<string | null>(null)
  const [lastEnvExport, setLastEnvExport] = useState<PdfExportResult | null>(null)

  const hasRoutes = routeState.status === 'success'
  const route = activeRoute

  // Captain decision display
  const decState = (captainDecision?.state ?? 'pending') as keyof typeof DECISION_ICON
  const decMeta = DECISION_ICON[decState] ?? DECISION_ICON.pending
  const DecIcon = decMeta.icon

  // Build payload from live session state and call PDF export endpoint
  async function handleExport() {
    if (!hasRoutes || !route) {
      setExportError('Generate routes first before exporting a dossier.')
      return
    }
    setExporting(true)
    setExportError(null)
    setLastExport(null)

    try {
      const cfg = voyageConfig as any
      const result = await exportReportPDF({
        session_id: sessionId,
        voyage_config: {
          origin_name:          cfg?.origin?.name        ?? 'Cape Town',
          destination_name:     cfg?.destination?.name   ?? 'Bharati Station',
          departure_time:       cfg?.departure_time       ?? new Date().toISOString(),
          vessel_name:          cfg?.vessel?.name         ?? 'Unknown Vessel',
          operating_mode:       cfg?.operating_mode       ?? 'BALANCED',
          max_acceptable_risk:  cfg?.risk_budget?.max_acceptable_risk ?? 0.30,
        },
        selected_route: {
          route_id:                 route.route_id,
          name:                     route.name,
          total_distance_nm:        route.metrics?.total_distance_nm ?? null,
          estimated_duration_hours: route.metrics?.estimated_duration_hours ?? null,
          polaris_rio:              route.polaris_rio ?? null,
          risk_level:               route.risk_level ?? null,
          data_mode:                route.data_mode,
          is_distinct:              route.is_distinct,
          convergence_note:         route.convergence_note ?? null,
          prototype_notice:         route.prototype_notice,
        },
        captain_decision: captainDecision
          ? {
              state:       captainDecision.state,
              route_id:    captainDecision.routeId,
              route_name:  captainDecision.routeName,
              timestamp:   captainDecision.timestamp,
              remarks:     captainDecision.remarks,
            }
          : null,
        audit_events: auditEvents.map((e) => ({
          id:        e.id,
          timestamp: e.timestamp,
          role:      e.role,
          action:    e.action,
          detail:    e.detail,
          sessionId: e.sessionId,
        })),
        sea_ice_forecast: (routeState.data?.run_log?.sea_ice_forecast as Record<string, unknown> | undefined) ?? null,
      })

      // Trigger immediate browser download of the blob
      const url = URL.createObjectURL(result.blob)
      const a = document.createElement('a')
      a.href = url
      a.download = result.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      setLastExport(result)
      pushAuditEvent(
        'OPERATOR',
        result.isPdf ? 'DOSSIER_PDF_DOWNLOADED' : 'DOSSIER_JSON_DOWNLOADED',
        `route_id=${route.route_id} file=${result.filename} events=${auditEvents.length}`,
      )
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Unknown export error')
    } finally {
      setExporting(false)
    }
  }

  // CSV coordinate download (separate from dossier)
  function handleDownloadCSV() {
    if (!route?.points?.length) return
    const header = 'lon,lat,segment'
    const rows = route.points.map((p: any) => `${p.lon},${p.lat},${p.segment}`)
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `himdrishti_route_${route.route_id}_${sessionId.slice(0, 8)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    pushAuditEvent('OPERATOR', 'ROUTE_CSV_DOWNLOADED', `route_id=${route.route_id}`)
  }

  // Environmental Exposure Summary PDF export
  async function handleExportEnvironmental() {
    if (!hasRoutes || !route) {
      setExportEnvError('Generate routes first before exporting an environmental summary.')
      return
    }
    setExportingEnv(true)
    setExportEnvError(null)
    setLastEnvExport(null)

    try {
      const cfg = voyageConfig as any
      const forecastData = routeState.data

      const result = await exportReportEnvironmental({
        session_id: sessionId,
        voyage_config: {
          origin_name:          cfg?.origin?.name        ?? 'Cape Town',
          destination_name:     cfg?.destination?.name   ?? 'Bharati Station',
          departure_time:       cfg?.departure_time       ?? new Date().toISOString(),
          vessel_name:          cfg?.vessel?.name         ?? 'Unknown Vessel',
          operating_mode:       cfg?.operating_mode       ?? 'BALANCED',
          max_acceptable_risk:  cfg?.risk_budget?.max_acceptable_risk ?? 0.30,
        },
        selected_route: {
          route_id:                 route.route_id,
          name:                     route.name,
          total_distance_nm:        route.metrics?.total_distance_nm ?? null,
          estimated_duration_hours: route.metrics?.estimated_duration_hours ?? null,
          polaris_rio:              route.polaris_rio ?? null,
          risk_level:               route.risk_level ?? null,
          data_mode:                route.data_mode,
          is_distinct:              route.is_distinct,
          convergence_note:         route.convergence_note ?? null,
          prototype_notice:         route.prototype_notice,
        },
        captain_decision: captainDecision
          ? {
              state:       captainDecision.state,
              route_id:    captainDecision.routeId,
              route_name:  captainDecision.routeName,
              timestamp:   captainDecision.timestamp,
              remarks:     captainDecision.remarks,
            }
          : null,
        audit_events: auditEvents.map((e) => ({
          id: e.id, timestamp: e.timestamp, role: e.role,
          action: e.action, detail: e.detail, sessionId: e.sessionId,
        })),
        // Only pipeline-available fields — no fabricated observations
        forecast_horizon_hours:   forecastData?.forecast_confidence ? 120 : undefined,
        forecast_data_mode:       route.data_mode,
        forecast_prototype_notice: route.prototype_notice,
        sea_ice_forecast:         (routeState.data?.run_log?.sea_ice_forecast as Record<string, unknown> | undefined) ?? null,
      })

      const url = URL.createObjectURL(result.blob)
      const a = document.createElement('a')
      a.href = url
      a.download = result.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      setLastEnvExport(result)
      pushAuditEvent(
        'OPERATOR',
        result.isPdf ? 'ENV_SUMMARY_PDF_DOWNLOADED' : 'ENV_SUMMARY_JSON_DOWNLOADED',
        `file=${result.filename}`,
      )
    } catch (err) {
      setExportEnvError(err instanceof Error ? err.message : 'Unknown export error')
    } finally {
      setExportingEnv(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.heading}>Mission Reports &amp; Voyage Dossiers</h1>
          <p className={styles.sub}>
            Generate authoritative voyage planning dossiers, POLARIS risk compliance
            assessments, and environmental exposure summaries for vessel masters and
            NCPOR mission planners.
          </p>
        </div>
        <div className={styles.modeBadge}>{dataMode}</div>
      </div>

      {/* ── Pre-flight status ────────────────────────────── */}
      {!hasRoutes && (
        <div className={styles.warnBanner} role="status">
          No routes generated yet. Navigate to <strong>Route Planner</strong> and generate
          routes before exporting a dossier.
        </div>
      )}

      {hasRoutes && route && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.25rem' }}>

          {/* ── Voyage Plan & POLARIS Dossier ──────────── */}
          <div className={styles.card}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.75rem', color: '#1e3a8a' }}>
              <FileText size={20} />
              <h2 className={styles.cardTitle} style={{ margin: 0 }}>Voyage Plan &amp; POLARIS Dossier</h2>
            </div>
            <p style={{ fontSize: '0.85rem', color: '#475569', lineHeight: 1.5, marginBottom: '1rem' }}>
              Navigation package including route waypoints, POLARIS/RIO risk assessment,
              risk-budget adherence audit, and session decision log.
            </p>

            {/* Route metrics */}
            <div className={styles.noticeBox} style={{ marginBottom: '1rem' }}>
              <div><strong>Selected Track:</strong> {route.name}</div>
              <div>
                <strong>POLARIS RIO:</strong>{' '}
                {route.polaris_rio != null ? `${route.polaris_rio} / 100` : '—'}{' '}
                {route.risk_level ? `(${route.risk_level})` : ''}
              </div>
              {route.metrics && (
                <>
                  <div><strong>Distance:</strong> {route.metrics.total_distance_nm?.toFixed(0) ?? '—'} nm</div>
                  <div><strong>Est. Duration:</strong> {route.metrics.estimated_duration_hours?.toFixed(1) ?? '—'} hrs</div>
                </>
              )}
              {!route.is_distinct && (
                <div style={{ color: '#92400e', fontSize: '0.8rem', marginTop: '4px' }}>
                  ⚠ Path convergence detected — see Audit Log for details.
                </div>
              )}
            </div>

            {/* Captain decision badge */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', fontSize: '0.85rem' }}>
              <DecIcon size={16} color={decMeta.color} />
              <span style={{ color: decMeta.color, fontWeight: 600 }}>{decMeta.label}</span>
              {captainDecision && (
                <span style={{ color: '#64748b', fontSize: '0.78rem' }}>
                  — {captainDecision.routeName}
                </span>
              )}
            </div>

            {/* Export buttons */}
            {exportError && (
              <div className={styles.warnBanner} style={{ marginBottom: '0.75rem' }} role="alert">
                {exportError}
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                className={styles.tag}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                  background: exporting ? '#93c5fd' : '#1976d2', color: '#fff',
                  border: 'none', padding: '0.5rem 1rem', borderRadius: '4px',
                  fontWeight: 600, cursor: exporting ? 'wait' : 'pointer', fontSize: '0.85rem',
                }}
                onClick={handleExport}
                disabled={exporting}
                aria-busy={exporting}
                aria-label="Export voyage dossier as PDF"
              >
                <Download size={14} />
                {exporting ? 'Generating...' : 'Export Dossier (PDF)'}
              </button>

              {lastExport && (
                <button
                  type="button"
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                    background: 'transparent', color: '#1976d2',
                    border: '1px solid #1976d2', padding: '0.5rem 1rem',
                    borderRadius: '4px', fontWeight: 600, cursor: 'pointer', fontSize: '0.85rem',
                  }}
                  onClick={handleDownloadCSV}
                  aria-label="Download route coordinates as CSV"
                >
                  <Download size={14} />
                  Route CSV
                </button>
              )}
            </div>

            {lastExport && (
              <p style={{ marginTop: '0.5rem', fontSize: '0.78rem', color: '#64748b' }}>
                {lastExport.isPdf
                  ? `PDF dossier downloaded: ${lastExport.filename}`
                  : `JSON dossier downloaded (WeasyPrint unavailable on this server): ${lastExport.filename}`
                }
              </p>
            )}
          </div>

          {/* ---- Environmental Exposure Summary ---- */}
          <div className={styles.card}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.75rem', color: '#1e3a8a' }}>
              <FileText size={20} />
              <h2 className={styles.cardTitle} style={{ margin: 0 }}>Environmental Exposure Summary</h2>
            </div>
            <p style={{ fontSize: '0.85rem', color: '#475569', lineHeight: 1.5 }}>
              Government-style A4 PDF covering sea-ice concentration, iceberg ensemble,
              pipeline hazard field, provenance and alerts. Only pipeline-available values
              are included &mdash; no environmental observations are fabricated.
            </p>
            <div className={styles.noticeBox} style={{ margin: '1rem 0' }}>
              <div><strong>Corridor:</strong> {route.data_mode === 'SYNTHETIC_DEMO' ? 'SYNTHETIC DEMO' : 'Live'} &mdash; Cape Town &#8594; Bharati Station</div>
              <div><strong>Data Mode:</strong> {route.data_mode}</div>
              <div style={{ marginTop: '4px', color: '#92400e', fontSize: '0.8rem' }}>
                Temperature, waves, visibility, pressure are NOT shown &mdash; unavailable from this pipeline.
              </div>
            </div>

            {exportEnvError && (
              <div className={styles.warnBanner} style={{ marginBottom: '0.75rem' }} role="alert">
                {exportEnvError}
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                  background: exportingEnv ? '#7dd3fc' : '#0284c7', color: '#fff',
                  border: 'none', padding: '0.5rem 1rem', borderRadius: '4px',
                  fontWeight: 600, cursor: exportingEnv ? 'wait' : 'pointer', fontSize: '0.85rem',
                }}
                onClick={handleExportEnvironmental}
                disabled={exportingEnv}
                aria-busy={exportingEnv}
                aria-label="Export Environmental Exposure Summary as PDF"
              >
                <Download size={14} />
                {exportingEnv ? 'Generating...' : 'Export Summary (PDF)'}
              </button>

              <button
                type="button"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                  background: 'transparent', color: '#0284c7',
                  border: '1px solid #0284c7', padding: '0.5rem 1rem',
                  borderRadius: '4px', fontWeight: 600, cursor: 'pointer', fontSize: '0.85rem',
                }}
                onClick={handleDownloadCSV}
                aria-label="Export route coordinates as CSV"
              >
                <Download size={14} /> Route Points (CSV)
              </button>
            </div>

            {lastEnvExport && (
              <p style={{ marginTop: '0.5rem', fontSize: '0.78rem', color: '#64748b' }}>
                {lastEnvExport.isPdf
                  ? `PDF downloaded: ${lastEnvExport.filename}`
                  : `JSON downloaded (WeasyPrint unavailable): ${lastEnvExport.filename}`
                }
              </p>
            )}
          </div>

        </div>
      )}

      {/* ── Session audit summary ──────────────────────── */}
      {auditEvents.length > 0 && (
        <div className={styles.card} style={{ marginTop: '1.5rem' }}>
          <div className={styles.cardTitle}>Session Summary ({auditEvents.length} events)</div>
          <div style={{ fontSize: '0.82rem', color: '#475569' }}>
            {auditEvents.slice(-5).reverse().map(e => (
              <div key={e.id} style={{ padding: '4px 0', borderBottom: '1px solid #f1f5f9' }}>
                <span style={{ fontWeight: 600 }}>{e.role}</span> · {e.action} ·{' '}
                <span style={{ color: '#94a3b8' }}>{e.timestamp.replace('T', ' ').slice(0, 19)} UTC</span>
              </div>
            ))}
            {auditEvents.length > 5 && (
              <div style={{ color: '#94a3b8', paddingTop: '4px' }}>
                … {auditEvents.length - 5} earlier events — see Audit Log page.
              </div>
            )}
          </div>
        </div>
      )}

      <div style={{ marginTop: '2rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: '#64748b' }}>
        <ShieldCheck size={16} />
        <span>Ministry of Earth Sciences · NCPOR · SIH 2026 · PS 26188 · Prototype — Not for operational use</span>
      </div>
    </div>
  )
}
