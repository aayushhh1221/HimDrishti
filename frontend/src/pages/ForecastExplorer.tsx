/**
 * ForecastExplorer — PS 26059 Full-Alignment Upgrade
 * SIH 2026 · PS 26059
 *
 * Displays:
 *   1. Existing forecast metadata from GET /api/v1/forecast (unchanged)
 *   2. NEW: Sea-ice forecast from GET /api/v1/sea-ice-forecast
 *      - Source, dataset, organisation, spatial resolution
 *      - Forecast method (PERSISTENCE | ML) + baseline
 *      - Per-horizon: valid time, confidence, mean/max concentration
 *      - Honest MAE/RMSE evaluation (persistence vs ML)
 *      - Evaluation status
 *   3. Data status (mode, credentials) from GET /api/v1/data-status
 *
 * IMPORTANT: Does NOT redesign existing UI.
 * New sections added BELOW existing forecast metadata.
 * All existing styles reused from shared-page.module.css.
 */

import { useState, useEffect } from 'react'
import { useForecast } from '../hooks/useApi'
import {
  getSeaIceForecast,
  getDataStatus,
  type SeaIceForecastResponse,
  type DataStatusResponse,
  type ApiState,
} from '../services/api/client'
import styles from './shared-page.module.css'

const HORIZON_OPTIONS = [24, 48, 72, 96, 120] as const

type FcMethod = 'persistence' | 'ml' | 'auto'
const METHOD_OPTIONS: { value: FcMethod; label: string }[] = [
  { value: 'auto',        label: 'Auto (ML → Persistence)' },
  { value: 'persistence', label: 'Persistence Baseline' },
  { value: 'ml',          label: 'ML Model' },
]

function confidenceBadge(conf: string) {
  const colors: Record<string, string> = {
    HIGH:    '#00c896',
    MEDIUM:  '#f5a623',
    LOW:     '#e03131',
    UNKNOWN: '#888',
  }
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 4,
      background: colors[conf] ?? '#888',
      color: '#fff',
      fontSize: '0.75rem',
      fontWeight: 600,
    }}>
      {conf}
    </span>
  )
}

export default function ForecastExplorer() {
  const [horizonHours, setHorizonHours] = useState<number>(120)
  const forecastState = useForecast(horizonHours)

  // Sea-ice forecast state
  const [seaIceMethod, setSeaIceMethod] = useState<FcMethod>('auto')
  const [seaIceFc, setSeaIceFc] = useState<ApiState<SeaIceForecastResponse>>({ status: 'idle', data: null, error: null })
  const [dataStatus, setDataStatus] = useState<ApiState<DataStatusResponse>>({ status: 'idle', data: null, error: null })

  // Fetch sea-ice forecast whenever horizon or method changes
  useEffect(() => {
    setSeaIceFc({ status: 'loading', data: null, error: null })
    getSeaIceForecast(horizonHours, seaIceMethod).then(setSeaIceFc)
  }, [horizonHours, seaIceMethod])

  // Fetch data status once on mount
  useEffect(() => {
    setDataStatus({ status: 'loading', data: null, error: null })
    getDataStatus().then(setDataStatus)
  }, [])

  const isLoading = forecastState.status === 'loading'
  const isSuccess = forecastState.status === 'success'
  const isError   = forecastState.status === 'error'
  const isUnavail = forecastState.status === 'unavailable'
  const data      = forecastState.data

  const fcData = seaIceFc.status === 'success' ? seaIceFc.data : null
  const dsData = dataStatus.status === 'success' ? dataStatus.data : null

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.heading}>Forecast Explorer</h1>
          <p className={styles.sub}>
            Sea-ice concentration forecast, environmental data quality, and provenance
            for the current pipeline run. PS 26059 — research-data chain.
          </p>
        </div>
        <div
          className={styles.modeBadge}
          aria-label={`Data mode: ${data?.data_mode ?? 'unknown'}`}
        >
          {data?.data_mode ?? (isLoading ? '…' : 'SYNTHETIC_DEMO')}
        </div>
      </div>

      {/* ── Horizon selector ─────────────────────────────────────────── */}
      <div className={styles.card}>
        <div className={styles.cardTitle}>Forecast Horizon</div>
        <div className={styles.selectorRow} role="group" aria-label="Select forecast horizon">
          {HORIZON_OPTIONS.map(h => (
            <button
              key={h}
              id={`horizon-${h}`}
              type="button"
              className={`${styles.selectorBtn} ${horizonHours === h ? styles.selectorBtnActive : ''}`}
              onClick={() => setHorizonHours(h)}
              aria-pressed={horizonHours === h}
            >
              {h}h
            </button>
          ))}
        </div>
        <p className={styles.selectorNote}>
          Select forecast horizon. Steps: 24 h, 48 h, 72 h, 96 h, 120 h.
        </p>
      </div>

      {/* ── Status banners ───────────────────────────────────────────── */}
      {isLoading && (
        <div className={styles.statusBanner} role="status" aria-live="polite">
          Fetching forecast metadata…
        </div>
      )}
      {isUnavail && (
        <div className={styles.warnBanner} role="status" aria-live="polite">
          Backend unavailable — the data pipeline service is not running.
        </div>
      )}
      {isError && (
        <div className={styles.errorBanner} role="alert">
          {forecastState.error ?? 'Error fetching forecast data.'}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          SECTION A — existing forecast metadata (unchanged)
         ═══════════════════════════════════════════════════════════════ */}
      {isSuccess && data && (
        <>
          <div className={styles.card}>
            <div className={styles.cardTitle}>Availability Summary</div>
            <dl className={styles.dl}>
              <div className={styles.dlRow}>
                <dt>Reference time</dt>
                <dd>{data.reference_time}</dd>
              </div>
              <div className={styles.dlRow}>
                <dt>Available horizon</dt>
                <dd>{data.available_horizon_hours} h</dd>
              </div>
              <div className={styles.dlRow}>
                <dt>Requested horizon</dt>
                <dd>{data.requested_horizon_hours} h</dd>
              </div>
              <div className={styles.dlRow}>
                <dt>Horizon steps available</dt>
                <dd>{data.horizon_steps.map(h => `${h}h`).join(', ')}</dd>
              </div>
            </dl>
          </div>

          <div className={styles.card}>
            <div className={styles.cardTitle}>Data Quality by Variable</div>
            <table className={styles.table} aria-label="Forecast data quality by variable">
              <thead>
                <tr>
                  <th>Variable</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.data_quality).map(([key, val]) => (
                  <tr key={key}>
                    <td>{key.replace(/_/g, ' ')}</td>
                    <td>{val}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.provenance.length > 0 && (
            <div className={styles.card}>
              <div className={styles.cardTitle}>Data Source Provenance</div>
              {data.provenance.map((rec, i) => (
                <div key={i} className={styles.provRecord}>
                  <div className={styles.provSource}>{String(rec.source ?? '—')}</div>
                  <div className={styles.provDataset}>{String(rec.dataset_name ?? '—')}</div>
                  {Boolean(rec.note) && <div className={styles.provNote}>{String(rec.note)}</div>}
                </div>
              ))}
            </div>
          )}

          <div className={styles.noticeBox} role="note">
            <strong>Prototype Notice:</strong> {data.prototype_notice}
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          SECTION B — PS 26059 Sea-Ice Forecast (NEW)
         ═══════════════════════════════════════════════════════════════ */}
      <div className={styles.card} style={{ marginTop: '2rem', borderTop: '2px solid #00c89640' }}>
        <div className={styles.cardTitle} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          Sea-Ice Concentration Forecast
          <span style={{ fontSize: '0.7rem', fontWeight: 400, color: '#8899aa', letterSpacing: 1 }}>
            PS 26059 · PERSISTENCE + ML
          </span>
        </div>

        {/* Method selector */}
        <div className={styles.selectorRow} role="group" aria-label="Forecast method">
          {METHOD_OPTIONS.map(opt => (
            <button
              key={opt.value}
              id={`fc-method-${opt.value}`}
              type="button"
              className={`${styles.selectorBtn} ${seaIceMethod === opt.value ? styles.selectorBtnActive : ''}`}
              onClick={() => setSeaIceMethod(opt.value)}
              aria-pressed={seaIceMethod === opt.value}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {seaIceFc.status === 'loading' && (
          <div className={styles.statusBanner} style={{ marginTop: 12 }}>
            Running sea-ice forecast…
          </div>
        )}
        {seaIceFc.status === 'error' && (
          <div className={styles.errorBanner} style={{ marginTop: 12 }}>
            {seaIceFc.error ?? 'Sea-ice forecast failed.'}
          </div>
        )}

        {fcData && (
          <>
            {/* Source information */}
            <dl className={styles.dl} style={{ marginTop: 16 }}>
              <div className={styles.dlRow}>
                <dt>Forecast method</dt>
                <dd><strong>{fcData.method}</strong> (baseline: {fcData.baseline_method})</dd>
              </div>
              <div className={styles.dlRow}>
                <dt>Data mode</dt>
                <dd>
                  <span className={styles.modeBadge} style={{ fontSize: '0.75rem', padding: '2px 8px' }}>
                    {fcData.data_mode}
                  </span>
                </dd>
              </div>
              <div className={styles.dlRow}>
                <dt>Source organisation</dt>
                <dd>{fcData.source_organisation || '—'}</dd>
              </div>
              <div className={styles.dlRow}>
                <dt>Dataset</dt>
                <dd style={{ fontSize: '0.82rem', maxWidth: 400, wordBreak: 'break-word' }}>
                  {fcData.source_dataset || '—'}
                </dd>
              </div>
              <div className={styles.dlRow}>
                <dt>Spatial coverage</dt>
                <dd>{fcData.spatial_coverage || '—'}</dd>
              </div>
              <div className={styles.dlRow}>
                <dt>Reference time</dt>
                <dd>{fcData.reference_time}</dd>
              </div>
              <div className={styles.dlRow}>
                <dt>Quality</dt>
                <dd>{fcData.quality}</dd>
              </div>
            </dl>

            {/* Evaluation metrics */}
            {fcData.metrics && (
              <div style={{ marginTop: 16 }}>
                <div className={styles.cardTitle} style={{ fontSize: '0.9rem' }}>
                  Forecast Evaluation (time-ordered split, no random shuffle)
                </div>
                <table className={styles.table} aria-label="Sea-ice forecast evaluation metrics">
                  <thead>
                    <tr>
                      <th>Method</th>
                      <th>MAE</th>
                      <th>RMSE</th>
                      <th>Train samples</th>
                      <th>Val samples</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Persistence (baseline)</td>
                      <td>{fcData.metrics.persistence_mae?.toFixed(5) ?? '—'}</td>
                      <td>{fcData.metrics.persistence_rmse?.toFixed(5) ?? '—'}</td>
                      <td>{fcData.metrics.n_samples_train}</td>
                      <td>{fcData.metrics.n_samples_val}</td>
                    </tr>
                    {fcData.metrics.model_mae != null && (
                      <tr>
                        <td>ML Model (HistGBR)</td>
                        <td>{fcData.metrics.model_mae?.toFixed(5) ?? '—'}</td>
                        <td>{fcData.metrics.model_rmse?.toFixed(5) ?? '—'}</td>
                        <td>{fcData.metrics.n_samples_train}</td>
                        <td>{fcData.metrics.n_samples_val}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <div style={{ marginTop: 8, fontSize: '0.8rem', color: '#8899aa' }}>
                  <strong>ML better than persistence:</strong>{' '}
                  {fcData.metrics.model_better_than_persistence === null
                    ? 'Not evaluated'
                    : fcData.metrics.model_better_than_persistence
                      ? '✓ Yes — ML used in production steps'
                      : '✗ No — persistence retained (honest disclosure)'}
                  {' · '}
                  <strong>Status:</strong> {fcData.metrics.evaluation_status}
                </div>
                {fcData.metrics.notes && (
                  <div style={{ marginTop: 4, fontSize: '0.78rem', color: '#aaa' }}>
                    {fcData.metrics.notes}
                  </div>
                )}
              </div>
            )}

            {/* Per-horizon steps */}
            {fcData.steps.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div className={styles.cardTitle} style={{ fontSize: '0.9rem' }}>
                  Forecast Steps
                </div>
                <table className={styles.table} aria-label="Sea-ice forecast steps">
                  <thead>
                    <tr>
                      <th>Horizon</th>
                      <th>Valid Time</th>
                      <th>Method</th>
                      <th>Confidence</th>
                      <th>Mean Conc.</th>
                      <th>Max Conc.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fcData.steps.map((step: SeaIceForecastResponse['steps'][number], i: number) => (
                      <tr key={i}>
                        <td>+{step.horizon_hours}h</td>
                        <td style={{ fontSize: '0.8rem' }}>
                          {new Date(step.valid_time).toUTCString().slice(0, 22)}
                        </td>
                        <td>{step.method}</td>
                        <td>{confidenceBadge(step.confidence)}</td>
                        <td>{(step.mean_concentration * 100).toFixed(1)}%</td>
                        <td>{(step.max_concentration * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div style={{ marginTop: 6, fontSize: '0.76rem', color: '#8899aa' }}>
                  Concentration = fraction of grid cells covered by sea ice (0 = open water, 1 = full cover).
                  Confidence decreases with horizon (persistence skill degrades beyond 48 h).
                </div>
              </div>
            )}

            {/* PS notice */}
            <div className={styles.noticeBox} style={{ marginTop: 12 }} role="note">
              {fcData.prototype_notice}
            </div>
          </>
        )}
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          SECTION C — Data Status (NEW)
         ═══════════════════════════════════════════════════════════════ */}
      <div className={styles.card} style={{ marginTop: '1.5rem' }}>
        <div className={styles.cardTitle}>
          Research Data Mode &amp; Source Availability
        </div>

        {dataStatus.status === 'loading' && (
          <div className={styles.statusBanner}>Checking data source availability…</div>
        )}
        {dataStatus.status === 'error' && (
          <div className={styles.errorBanner}>{dataStatus.error ?? 'Data status check failed.'}</div>
        )}

        {dsData && (
          <>
            <dl className={styles.dl}>
              <div className={styles.dlRow}>
                <dt>Active mode</dt>
                <dd>
                  <span className={styles.modeBadge} style={{ fontSize: '0.75rem', padding: '2px 8px' }}>
                    {dsData.active_mode}
                  </span>
                </dd>
              </div>
              <div className={styles.dlRow}>
                <dt>SYNTHETIC_DEMO available</dt>
                <dd>{dsData.synthetic_demo_available ? '✓ Yes (always)' : '✗ No'}</dd>
              </div>
            </dl>

            <div style={{ marginTop: 12 }}>
              <table className={styles.table} aria-label="Data source availability">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Target Dataset</th>
                    <th>Variables</th>
                    <th>Resolution</th>
                    <th>Credentials</th>
                    <th>Fallback</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(dsData.sources).map(([key, srcRaw]) => {
                    const src = srcRaw as DataStatusResponse['sources'][string]
                    return (
                    <tr key={key}>
                      <td style={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '0.8rem' }}>
                        {key.replace(/_/g, ' ')}
                      </td>
                      <td style={{ fontSize: '0.78rem', maxWidth: 180, wordBreak: 'break-word' }}>
                        {src.target_organisation}
                      </td>
                      <td style={{ fontSize: '0.78rem' }}>
                        {src.target_variables?.join(', ') ?? '—'}
                      </td>
                      <td style={{ fontSize: '0.78rem' }}>
                        {src.target_spatial_resolution_km
                          ? `${src.target_spatial_resolution_km} km`
                          : '—'}
                      </td>
                      <td>
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 6px',
                          borderRadius: 4,
                          fontSize: '0.72rem',
                          fontWeight: 600,
                          background: src.credentials_status === 'AVAILABLE' ? '#00c89630' : '#e0313130',
                          color: src.credentials_status === 'AVAILABLE' ? '#00c896' : '#e03131',
                        }}>
                          {src.credentials_status}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.76rem', color: '#8899aa' }}>
                        {src.fallback}
                      </td>
                    </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div style={{ marginTop: 8, fontSize: '0.76rem', color: '#8899aa' }}>
              To enable RESEARCH_DATA mode: set{' '}
              <code style={{ background: '#1a2332', padding: '1px 4px', borderRadius: 3 }}>
                HIMDRISHTI_DATA_MODE=RESEARCH_DATA
              </code>{' '}
              plus the appropriate credential env vars (see DEPLOYMENT.md).
              No credentials are ever exposed through this interface.
            </div>

            <div className={styles.noticeBox} style={{ marginTop: 12 }} role="note">
              {dsData.prototype_notice}
            </div>
          </>
        )}
      </div>

      <div className={styles.tag}>SIH 2026 · PS 26059</div>
    </div>
  )
}
