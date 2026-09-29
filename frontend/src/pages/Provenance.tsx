/**
 * Provenance — PS 26059 Full-Alignment Upgrade
 * SIH 2026 · PS 26059
 *
 * Data Provenance page: pipeline data source records from GET /api/v1/provenance.
 * Shows full data lineage: dataset → forecast → route → report.
 * Traceability chain required by PS 26059.
 */

import { useEffect, useState } from 'react'
import { useProvenance } from '../hooks/useApi'
import { getDataStatus, type DataStatusResponse, type ApiState } from '../services/api/client'
import styles from './shared-page.module.css'

const STATUS_CLASS: Record<string, string> = {
  available: 'statusOk',
  stale:     'statusWarn',
  unavailable: 'statusError',
  invalid:   'statusError',
}

const CHAIN_STEPS = [
  'Satellite / Environmental Data',
  'Sea-Ice Observation',
  'Sea-Ice Forecast',
  'Iceberg Trajectory',
  'POLARIS / RIO',
  'Route Optimisation',
  'Captain Decision',
  'Replay + Audit + Report',
]

export default function Provenance() {
  const provState = useProvenance()
  const isLoading = provState.status === 'loading'
  const isSuccess = provState.status === 'success'
  const isError   = provState.status === 'error'
  const isUnavail = provState.status === 'unavailable'
  const data      = provState.data

  const [dataStatus, setDataStatus] = useState<ApiState<DataStatusResponse>>({ status: 'idle', data: null, error: null })
  useEffect(() => {
    setDataStatus({ status: 'loading', data: null, error: null })
    getDataStatus().then(setDataStatus)
  }, [])
  const dsData = dataStatus.status === 'success' ? dataStatus.data : null

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.heading}>Data Provenance</h1>
          <p className={styles.sub}>
            Complete data lineage: dataset → forecast → hazard field → route → report.
            Every environmental input is traceable to its source. PS 26059 traceability chain.
          </p>
        </div>
        {data && <div className={styles.modeBadge}>{data.data_mode}</div>}
      </div>

      {isLoading && (
        <div className={styles.statusBanner} role="status" aria-live="polite">
          Loading provenance records…
        </div>
      )}
      {isUnavail && (
        <div className={styles.warnBanner} role="status" aria-live="polite">
          Backend unavailable — the data pipeline service is not running.
          Provenance records cannot be displayed without the backend.
        </div>
      )}
      {isError && (
        <div className={styles.errorBanner} role="alert">
          {provState.error ?? 'Error loading provenance data.'}
        </div>
      )}

      {/* PS 26059 traceability chain */}
      <div className={styles.card}>
        <div className={styles.cardTitle}>PS 26059 Traceability Chain</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', marginTop: 8 }}>
          {CHAIN_STEPS.map((step, i) => (
            <span key={step} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                background: '#0f3460',
                border: '1px solid #00c89640',
                borderRadius: 6,
                padding: '4px 10px',
                fontSize: '0.78rem',
                color: '#e0e6ff',
              }}>
                {step}
              </span>
              {i < CHAIN_STEPS.length - 1 && (
                <span style={{ color: '#00c896', fontSize: '1rem' }}>→</span>
              )}
            </span>
          ))}
        </div>
        <div style={{ marginTop: 10, fontSize: '0.78rem', color: '#8899aa' }}>
          Each stage carries a DataProvenance record (source, dataset, retrieved_at,
          valid_time, units, spatial_coverage, status). See records below.
        </div>
      </div>

      {isSuccess && data && (
        <>
          <div className={styles.metaRow} aria-label="Provenance generation time">
            Generated: <span className={styles.mono}>{data.generated_at}</span>
          </div>

          <div className={styles.card}>
            <div className={styles.cardTitle}>Data Source Records</div>
            <table className={styles.table} aria-label="Pipeline data source provenance">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Dataset</th>
                  <th>Retrieved</th>
                  <th>Valid Period</th>
                  <th>Coverage</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.records.map((rec, i) => (
                  <tr key={i}>
                    <td>{rec.source}</td>
                    <td>{rec.dataset_name}</td>
                    <td className={styles.mono}>{rec.retrieved_at.slice(0, 16).replace('T', ' ')}</td>
                    <td className={styles.mono}>
                      {rec.valid_time_start.slice(0, 10)} → {rec.valid_time_end.slice(0, 10)}
                    </td>
                    <td>{rec.spatial_coverage}</td>
                    <td>
                      <span className={`${styles.statusPill} ${styles[STATUS_CLASS[rec.status] ?? 'statusOk']}`}>
                        {rec.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.records.some(r => r.notes) && (
            <div className={styles.card}>
              <div className={styles.cardTitle}>Notes</div>
              {data.records.filter(r => r.notes).map((rec, i) => (
                <div key={i} className={styles.noteRow}>
                  <span className={styles.noteSource}>{rec.source}</span>
                  <span className={styles.noteText}>{rec.notes}</span>
                </div>
              ))}
            </div>
          )}

          <div className={styles.noticeBox} role="note">
            <strong>Prototype Notice:</strong> {data.prototype_notice}
          </div>
        </>
      )}

      {/* Active data sources status */}
      {dsData && (
        <div className={styles.card} style={{ marginTop: '1.5rem' }}>
          <div className={styles.cardTitle}>Active Data Mode</div>
          <dl className={styles.dl}>
            <div className={styles.dlRow}>
              <dt>Active mode</dt>
              <dd>
                <span className={styles.modeBadge} style={{ fontSize: '0.75rem', padding: '2px 8px' }}>
                  {dsData.active_mode}
                </span>
              </dd>
            </div>
          </dl>
          <div style={{ marginTop: 8, fontSize: '0.8rem', color: '#8899aa' }}>
            To enable RESEARCH_DATA mode, set{' '}
            <code style={{ background: '#1a2332', padding: '1px 4px', borderRadius: 3 }}>
              HIMDRISHTI_DATA_MODE=RESEARCH_DATA
            </code>{' '}
            plus the credential env vars. See DEPLOYMENT.md. No credentials are
            exposed through this interface.
          </div>
        </div>
      )}

      <div className={styles.tag}>SIH 2026 · PS 26059</div>
    </div>
  )
}
