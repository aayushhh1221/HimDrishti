/**
 * frontend/src/services/api/client.ts
 * --------------------------------------
 * Centralized API client for HimDrishti.
 * All fetch() calls go through here — never scattered in components.
 *
 * Features:
 *   - Single source of truth for API URLs
 *   - Structured error handling (never throws raw fetch errors to UI)
 *   - Returns ApiState<T> with status, data, error
 *   - Graceful degradation when backend is unavailable
 *
 * SIH 2026 · PS 26059
 */

import { API_BASE_URL, API_V1 } from './config'
import type {
  AlertsResponse,
  ApiState,
  DepartureWindowsResponse,
  ForecastResponse,
  GenerateRoutesResponse,
  ProvenanceResponse,
  ReplayRunResponse,
  RiskResponse,
} from './types'

// Re-export ApiState so consumers can import it directly from client.ts
export type { ApiState }

// ---------------------------------------------------------------------------
// Internal fetch helper
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Timeout constants (H1 hardening)
// ---------------------------------------------------------------------------

/** Route generation timeout: 240 s (120 s pipeline + up to 60 s Render cold start) */
const ROUTE_TIMEOUT_MS = 240_000

/** Departure-window timeout: 300 s (4 candidates × ~60 s each) */
const DEPARTURE_WINDOW_TIMEOUT_MS = 300_000

// ---------------------------------------------------------------------------
// Internal fetch helper
// ---------------------------------------------------------------------------

/**
 * Extract a human-readable error message from a FastAPI error body.
 * Handles:
 *   - Plain string detail: "some message"
 *   - Nested object: { detail: "some message" }
 *   - Validation array: [{ loc: [...], msg: "..." }]  → joined readable string
 *   Never returns [object Object].
 */
function extractErrorDetail(errBody: unknown, httpStatus: string): string {
  if (errBody == null) return httpStatus
  if (typeof errBody === 'string') return errBody

  const body = errBody as Record<string, unknown>
  const detail = body.detail

  if (detail == null) return httpStatus
  if (typeof detail === 'string') return detail

  // FastAPI validation error: array of { loc, msg, type }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((e) => {
        if (typeof e === 'string') return e
        if (typeof e === 'object' && e !== null) {
          const err = e as Record<string, unknown>
          const loc = Array.isArray(err.loc) ? `[${err.loc.join(' → ')}] ` : ''
          const msg = typeof err.msg === 'string' ? err.msg : JSON.stringify(err)
          return `${loc}${msg}`
        }
        return String(e)
      })
      .filter(Boolean)
      .join('; ')
    return messages || httpStatus
  }

  // Nested detail object (e.g. our own 500 error shape)
  if (typeof detail === 'object' && detail !== null) {
    const nested = detail as Record<string, unknown>
    if (typeof nested.detail === 'string') return nested.detail
    if (typeof nested.error === 'string') return nested.error
  }

  return httpStatus
}

async function apiFetch<T>(
  url: string,
  options?: RequestInit & { timeoutMs?: number },
): Promise<ApiState<T>> {
  const timeoutMs = options?.timeoutMs ?? ROUTE_TIMEOUT_MS
  const controller = new AbortController()
  const timerId = setTimeout(() => controller.abort(), timeoutMs)

  // Strip our custom timeoutMs key before passing to fetch
  const { timeoutMs: _ignored, ...fetchOptions } = options ?? {}

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...fetchOptions?.headers,
      },
    })

    clearTimeout(timerId)

    if (!response.ok) {
      const httpStatus = `HTTP ${response.status}`
      let errBody: unknown = null
      try { errBody = await response.json() } catch { /* body not JSON */ }
      const detail = extractErrorDetail(errBody, httpStatus)
      return { status: 'error', data: null, error: detail }
    }

    const data: T = await response.json()
    return { status: 'success', data, error: null }
  } catch (err) {
    clearTimeout(timerId)

    // Timeout (AbortController)
    if (err instanceof DOMException && err.name === 'AbortError') {
      return {
        status: 'error',
        data: null,
        error: `Request timed out after ${Math.round(timeoutMs / 1000)}s. ` +
               'The pipeline may still be running. Please try again.',
      }
    }

    if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
      // Network error — backend unreachable
      return {
        status: 'unavailable',
        data: null,
        error:
          'Backend unavailable. Showing demo data. ' +
          'Start the backend: uvicorn backend.main:app --reload --port 8000',
      }
    }
    const message = err instanceof Error ? err.message : 'Unknown error'
    return { status: 'error', data: null, error: message }
  }
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

export async function checkHealth(): Promise<boolean> {
  try {
    const resp = await fetch(`${API_BASE_URL}/health`, { method: 'GET' })
    return resp.ok
  } catch {
    return false
  }
}

// ---------------------------------------------------------------------------
// PS 26059: Sea-ice forecast — GET /api/v1/sea-ice-forecast
// ---------------------------------------------------------------------------

/** Shape returned by /api/v1/sea-ice-forecast */
export interface SeaIceForecastResponse {
  reference_time: string
  valid_times: string[]
  horizon_hours: number[]
  method: string             // PERSISTENCE | ML
  baseline_method: string
  data_mode: string          // SYNTHETIC_DEMO | RESEARCH_DATA
  source_dataset: string
  source_organisation: string
  spatial_coverage: string
  retrieved_at: string | null
  quality: string
  active_mode: string
  prototype_notice: string
  steps: Array<{
    horizon_hours: number
    valid_time: string
    method: string
    confidence: string        // HIGH | MEDIUM | LOW | UNKNOWN
    mean_concentration: number
    max_concentration: number
    min_concentration: number
    shape: number[]
    notes: string
  }>
  metrics: {
    persistence_mae: number | null
    persistence_rmse: number | null
    model_mae: number | null
    model_rmse: number | null
    n_samples_train: number
    n_samples_val: number
    model_better_than_persistence: boolean | null
    evaluation_status: string
    notes: string
  } | null
  provenance: Array<Record<string, unknown>>
}

export async function getSeaIceForecast(
  horizonHours = 120,
  method: 'persistence' | 'ml' | 'auto' = 'auto',
): Promise<ApiState<SeaIceForecastResponse>> {
  return apiFetch<SeaIceForecastResponse>(
    `${API_V1}/sea-ice-forecast?horizon_hours=${horizonHours}&method=${method}`,
    { method: 'GET', timeoutMs: 60_000 },
  )
}

// ---------------------------------------------------------------------------
// PS 26059: Data status — GET /api/v1/data-status
// ---------------------------------------------------------------------------

export interface DataStatusResponse {
  active_mode: string
  synthetic_demo_available: boolean
  prototype_notice: string
  sources: Record<string, {
    mode: string
    target_dataset: string
    target_organisation: string
    target_variables: string[]
    target_spatial_resolution_km: number | null
    target_temporal_resolution_h: number | null
    credentials_status: string
    credentials_note: string
    fallback: string
    fallback_available: boolean
  }>
}

export async function getDataStatus(): Promise<ApiState<DataStatusResponse>> {
  return apiFetch<DataStatusResponse>(`${API_V1}/data-status`, { method: 'GET' })
}

// ---------------------------------------------------------------------------
// Route generation

// ---------------------------------------------------------------------------

export interface GenerateRoutesPayload {
  origin: { name: string; lat: number; lon: number }
  destination: { name: string; lat: number; lon: number }
  departure_time: string // ISO 8601 UTC e.g. "2026-05-21T12:00:00Z"
  vessel: {
    name: string
    ice_class: string
    draft_m: number
    speed_knots: number
  }
  forecast_horizon_hours: number
  route_preferences?: {
    risk_weight: number
    time_weight: number
    fuel_weight: number
  }
  // Phase 8
  operating_mode: 'SAFETY_FIRST' | 'BALANCED' | 'FUEL_SAVER'
  risk_budget: {
    max_acceptable_risk: number
    uncertainty_weight?: number
  }
  extreme_risk_acknowledged: boolean
}

export async function generateRoutes(
  payload: GenerateRoutesPayload,
): Promise<ApiState<GenerateRoutesResponse>> {
  return apiFetch<GenerateRoutesResponse>(`${API_V1}/routes/generate`, {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: ROUTE_TIMEOUT_MS,  // H1: 120 s explicit timeout
  })
}

// ---------------------------------------------------------------------------
// Risk
// ---------------------------------------------------------------------------

export async function getRisk(routeId: string): Promise<ApiState<RiskResponse>> {
  return apiFetch<RiskResponse>(`${API_V1}/risk/${encodeURIComponent(routeId)}`)
}

// ---------------------------------------------------------------------------
// Forecast
// ---------------------------------------------------------------------------

export async function getForecast(
  horizonHours: number = 48,
): Promise<ApiState<ForecastResponse>> {
  return apiFetch<ForecastResponse>(
    `${API_V1}/forecast?horizon_hours=${horizonHours}`,
  )
}

// ---------------------------------------------------------------------------
// Provenance
// ---------------------------------------------------------------------------

export async function getProvenance(): Promise<ApiState<ProvenanceResponse>> {
  return apiFetch<ProvenanceResponse>(`${API_V1}/provenance`)
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export async function getAlerts(): Promise<ApiState<AlertsResponse>> {
  return apiFetch<AlertsResponse>(`${API_V1}/alerts`)
}

// ---------------------------------------------------------------------------
// Phase 9: Departure Window planning
// ---------------------------------------------------------------------------

export interface DepartureWindowsPayload {
  origin: { name: string; lat: number; lon: number }
  destination: { name: string; lat: number; lon: number }
  base_departure_time: string   // ISO 8601 UTC
  vessel: {
    name: string
    ice_class: string
    draft_m: number
    speed_knots: number
  }
  forecast_horizon_hours: number
  operating_mode: 'SAFETY_FIRST' | 'BALANCED' | 'FUEL_SAVER'
  risk_budget: {
    max_acceptable_risk: number
    uncertainty_weight?: number
  }
  extreme_risk_acknowledged: boolean
  candidate_offsets_hours: number[]   // [0, 6, 12, 24]
}

export async function runDepartureWindows(
  payload: DepartureWindowsPayload,
): Promise<ApiState<DepartureWindowsResponse>> {
  return apiFetch<DepartureWindowsResponse>(`${API_V1}/planning/departure-windows`, {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: DEPARTURE_WINDOW_TIMEOUT_MS,  // H1: 300 s — 4 candidates × ~60 s
  })
}

// ---------------------------------------------------------------------------
// Phase 9: Historical Replay
// ---------------------------------------------------------------------------

export interface ReplayRunPayload {
  dataset_id: string
  start_time: string    // ISO 8601 UTC
  end_time: string      // ISO 8601 UTC
  seed: number
  config?: Record<string, string>
  forecast_horizon_hours?: number
}

export async function runReplay(
  payload: ReplayRunPayload,
): Promise<ApiState<ReplayRunResponse>> {
  return apiFetch<ReplayRunResponse>(`${API_V1}/replay/run`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

// ---------------------------------------------------------------------------
// Phase 10: Voyage Dossier / Report Export
// ---------------------------------------------------------------------------

export interface ReportVoyageConfig {
  origin_name: string
  destination_name: string
  departure_time: string
  vessel_name: string
  operating_mode: string
  max_acceptable_risk: number
}

export interface ReportRouteSnapshot {
  route_id: string
  name: string
  total_distance_nm: number | null
  estimated_duration_hours: number | null
  polaris_rio: number | null
  risk_level: string | null
  data_mode: string
  is_distinct: boolean
  convergence_note: string | null
  prototype_notice: string
}

export interface ReportCaptainDecision {
  state: string
  route_id: string
  route_name: string
  timestamp: string
  remarks: string
}

export interface ReportAuditEvent {
  id: string
  timestamp: string
  role: string
  action: string
  detail: string
  sessionId: string
}

export interface ReportExportPayload {
  session_id: string
  voyage_config: ReportVoyageConfig
  selected_route: ReportRouteSnapshot
  captain_decision: ReportCaptainDecision | null
  audit_events: ReportAuditEvent[]
  export_format: 'pdf'  // backend always attempts PDF, falls back to JSON
  sea_ice_forecast?: Record<string, unknown> | null
}

export interface DossierDocument {
  dossier_type: string
  generated_at_utc: string
  session_id: string
  prototype_disclaimer: string
  voyage_configuration: Record<string, unknown>
  selected_route: Record<string, unknown>
  captain_decision: Record<string, unknown>
  audit_log: Array<Record<string, unknown>>
  audit_event_count: number
  _pdf_fallback_reason?: string
}

/**
 * exportReport — legacy JSON-only path (kept for compatibility).
 * Prefer exportReportPDF for the live download flow.
 */
export async function exportReport(
  payload: ReportExportPayload,
): Promise<ApiState<DossierDocument>> {
  return apiFetch<DossierDocument>(`${API_V1}/reports/export`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export interface PdfExportResult {
  blob: Blob
  filename: string
  isPdf: boolean
}

/**
 * exportReportPDF — calls POST /api/v1/reports/export and downloads the
 * server response as a binary blob.
 *
 * - If the server returns application/pdf: saves as .pdf
 * - If the server returns application/json (fallback): saves as .json
 * - If the network fails: throws an Error
 *
 * The caller is responsible for creating an <a> element and triggering
 * the download. window.print() is NOT used.
 */
export async function exportReportPDF(
  payload: Omit<ReportExportPayload, 'export_format'>,
): Promise<PdfExportResult> {
  const response = await fetch(`${API_V1}/reports/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, export_format: 'pdf' }),
  })

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText)
    throw new Error(`Export failed (HTTP ${response.status}): ${text.slice(0, 200)}`)
  }

  const contentType = response.headers.get('Content-Type') ?? ''
  const disposition  = response.headers.get('Content-Disposition') ?? ''
  const isPdf = contentType.includes('application/pdf')

  // Extract filename from Content-Disposition header, or synthesise one
  let filename = isPdf
    ? `himdrishti_dossier_${payload.session_id.slice(0, 8)}.pdf`
    : `himdrishti_dossier_${payload.session_id.slice(0, 8)}.json`
  const match = disposition.match(/filename="?([^"]+)"?/)
  if (match?.[1]) filename = match[1]

  const blob = await response.blob()
  return { blob, filename, isPdf }
}

/**
 * exportReportEnvironmental — calls POST /api/v1/reports/export/environmental
 * and downloads the server response as a binary blob.
 * Only passes pipeline-available fields — never fabricated observations.
 */
export async function exportReportEnvironmental(
  payload: Omit<ReportExportPayload, 'export_format'> & {
    forecast_horizon_hours?: number
    forecast_horizon_steps?: number[]
    forecast_data_mode?: string
    forecast_prototype_notice?: string
    provenance_records?: Array<Record<string, unknown>>
    alert_records?: Array<Record<string, unknown>>
  },
): Promise<PdfExportResult> {
  const response = await fetch(`${API_V1}/reports/export/environmental`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, export_format: 'pdf' }),
  })

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText)
    throw new Error(`Environmental export failed (HTTP ${response.status}): ${text.slice(0, 200)}`)
  }

  const contentType = response.headers.get('Content-Type') ?? ''
  const disposition  = response.headers.get('Content-Disposition') ?? ''
  const isPdf = contentType.includes('application/pdf')

  let filename = isPdf
    ? `himdrishti_env_summary_${payload.session_id.slice(0, 8)}.pdf`
    : `himdrishti_env_summary_${payload.session_id.slice(0, 8)}.json`
  const match = disposition.match(/filename="?([^"]+)"?/)
  if (match?.[1]) filename = match[1]

  const blob = await response.blob()
  return { blob, filename, isPdf }
}
