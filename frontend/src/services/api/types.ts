/**
 * frontend/src/services/api/types.ts
 * ------------------------------------
 * TypeScript types matching the HimDrishti backend API contracts.
 * Keep in sync with backend/schemas/responses.py
 * SIH 2026 · PS 26059
 *
 * Phase 8 additions:
 *   - OperatingMode
 *   - RiskBudget (request)
 *   - ApiRouteMetrics
 *   - RiskBudgetStatus
 *   - CounterfactualDelta, CounterfactualComparison
 *   - ForecastConfidence
 *   - WholeVoyageRisk
 *   - Extended ApiRoute + GenerateRoutesResponse
 *   - GenerateRoutesRequest (outgoing)
 */

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

export type DataMode = 'SYNTHETIC_DEMO' | 'FIXTURE' | 'LIVE'
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'
export type AlertSeverity = 'info' | 'warning' | 'critical'
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN'
export type RiskBudgetStatusValue =
  | 'WITHIN_BUDGET'
  | 'EXCEEDS_BUDGET'
  | 'NO_ROUTE_WITHIN_RISK_BUDGET'

// Phase 8: Operating modes
export type OperatingMode = 'SAFETY_FIRST' | 'BALANCED' | 'FUEL_SAVER'

// ---------------------------------------------------------------------------
// Phase 8: Request types (outgoing)
// ---------------------------------------------------------------------------

export interface RiskBudgetRequest {
  max_acceptable_risk: number        // 0.0–1.0
  uncertainty_weight?: number        // default 0.5
  risk_weight?: number | null
  fuel_weight?: number | null
  time_weight?: number | null
}

export interface GenerateRoutesRequest {
  origin: { name: string; lat: number; lon: number }
  destination: { name: string; lat: number; lon: number }
  departure_time: string             // ISO 8601 UTC
  vessel: {
    name: string
    ice_class: string
    draft_m: number
    speed_knots: number
  }
  forecast_horizon_hours: number
  operating_mode: OperatingMode
  risk_budget: RiskBudgetRequest
  extreme_risk_acknowledged: boolean
}

// ---------------------------------------------------------------------------
// Phase 8: Route metrics (whole-voyage)
// ---------------------------------------------------------------------------

export interface ApiRouteMetrics {
  max_segment_risk: number | null
  integrated_risk: number | null
  highest_risk_segment_index: number | null
  uncertainty_contribution: number | null
  distance_km: number | null
  path_cell_count: number | null
  total_distance_nm?: number | null
  estimated_duration_hours?: number | null
}

// ---------------------------------------------------------------------------
// Phase 8: Risk budget status per route
// ---------------------------------------------------------------------------

export interface RiskBudgetStatus {
  status: RiskBudgetStatusValue
  budget_limit: number
  actual_risk: number | null
  prototype_notice: string
}

// ---------------------------------------------------------------------------
// Phase 8: Counterfactual comparison
// ---------------------------------------------------------------------------

export interface CounterfactualDelta {
  route_id: string
  route_name: string
  fuel_delta_pct: number | null
  eta_delta_hours: number | null
  risk_delta_pct: number | null
  uncertainty_delta_pct: number | null
  distance_delta_km: number | null
  risk_budget_status: RiskBudgetStatusValue | null
}

export interface CounterfactualComparison {
  baseline_route_id: string
  baseline_route_name: string
  comparisons: CounterfactualDelta[]
  prototype_notice: string
}

// ---------------------------------------------------------------------------
// Phase 8: Forecast confidence
// ---------------------------------------------------------------------------

export interface ForecastConfidence {
  level: ConfidenceLevel
  score: number | null
  degradation_flags: string[]
  horizon_policy: Record<string, string>
  assessment_basis: string
}

// ---------------------------------------------------------------------------
// Phase 8: Whole-voyage risk
// ---------------------------------------------------------------------------

export interface WholeVoyageRisk {
  max_segment_risk: number | null
  integrated_risk_recommended: number | null
  risk_budget_status_recommended: string | null
  highest_risk_segment_index: number | null
  prototype_notice: string
}

// ---------------------------------------------------------------------------
// Route types
// ---------------------------------------------------------------------------

export interface ApiRoutePoint {
  lon: number
  lat: number
  /**
   * 'approach'  — origin → grid boundary, open ocean, not hazard-modeled.
   * 'pipeline'  — within the Dijkstra / UCS hazard grid, scientifically computed.
   * 'arrival'   — grid boundary → destination, not hazard-modeled.
   * Render approach/arrival segments with reduced opacity/dashed style.
   */
  segment: string
}

export interface ApiRouteCostBreakdown {
  time_hours: number
  fuel_tonnes: number
  risk_cost: number
  weighted_cost: number
}

export interface ApiRiskFactors {
  environmental: number
  navigation: number
  ice_condition: number
  iceberg_collision: number
}

export interface ApiRoute {
  route_id: string
  name: string
  risk_level: RiskLevel
  risk_category: string
  polaris_rio: number
  cost_breakdown: ApiRouteCostBreakdown
  risk_factors: ApiRiskFactors
  points: ApiRoutePoint[]
  label_coord: ApiRoutePoint | null
  color: string
  system_explanation: string
  rationale: string
  // Phase 8
  metrics: ApiRouteMetrics | null
  risk_budget_status: RiskBudgetStatus | null
  // Phase 10: path distinctness
  is_distinct: boolean
  convergence_note: string | null
  data_mode: DataMode
  prototype_notice: string
}

// ---------------------------------------------------------------------------
// Route generation response
// ---------------------------------------------------------------------------

export interface GenerateRoutesResponse {
  request_id: string
  generated_at: string
  routes: ApiRoute[]
  recommended_route_id: string | null  // null when pipeline produced no viable routes
  forecast_horizon_hours: number
  data_mode: DataMode
  data_quality_summary: Record<string, string>
  provenance_summary: Record<string, unknown>[]
  pipeline_warnings: string[]
  // Phase 8
  operating_mode: OperatingMode
  risk_budget_limit: number
  counterfactual: CounterfactualComparison | null
  forecast_confidence: ForecastConfidence | null
  whole_voyage_risk: WholeVoyageRisk | null
  run_log: Record<string, unknown>  // audit/diagnostic log
  prototype_notice: string
}

// ---------------------------------------------------------------------------
// Risk response
// ---------------------------------------------------------------------------

export interface RiskResponse {
  route_id: string
  polaris_rio: number
  polaris_status: string
  risk_level: RiskLevel
  risk_category: string
  risk_factors: ApiRiskFactors
  system_explanation: string
  data_mode: DataMode
  prototype_notice: string
}

// ---------------------------------------------------------------------------
// Forecast response
// ---------------------------------------------------------------------------

export interface ForecastDataQuality {
  sea_ice: string
  wind: string
  ocean_current: string
  icebergs: string
}

export interface ForecastResponse {
  reference_time: string
  available_horizon_hours: number
  requested_horizon_hours: number
  horizon_steps: number[]
  data_quality: ForecastDataQuality
  provenance: Record<string, unknown>[]
  data_mode: DataMode
  prototype_notice: string
}

// ---------------------------------------------------------------------------
// Provenance response
// ---------------------------------------------------------------------------

export interface ApiProvenanceRecord {
  source: string
  dataset_name: string
  retrieved_at: string
  valid_time_start: string
  valid_time_end: string
  spatial_coverage: string
  units: string
  coordinate_system: string
  status: string
  notes: string
}

export interface ProvenanceResponse {
  records: ApiProvenanceRecord[]
  data_mode: DataMode
  generated_at: string
  prototype_notice: string
}

// ---------------------------------------------------------------------------
// Alerts response
// ---------------------------------------------------------------------------

export interface ApiAlertDetail {
  label: string
  value: string
}

export interface ApiAlert {
  id: string
  severity: AlertSeverity
  title: string
  description: string
  details: ApiAlertDetail[]
  forecast_horizon: string
  data_mode: DataMode
}

export interface AlertsResponse {
  alerts: ApiAlert[]
  data_mode: DataMode
  generated_at: string
  prototype_notice: string
}

// ---------------------------------------------------------------------------
// API state wrapper
// ---------------------------------------------------------------------------

export type ApiStatus = 'idle' | 'loading' | 'success' | 'error' | 'unavailable'

export interface ApiState<T> {
  status: ApiStatus
  data: T | null
  error: string | null
}

// ---------------------------------------------------------------------------
// Phase 9: Departure Window types
// ---------------------------------------------------------------------------

export interface DepartureWindowResult {
  offset_hours: number
  departure_time: string
  route_id: string | null
  route_name: string | null
  risk: number | null
  fuel_tonnes: number | null
  eta_hours: number | null
  distance_km: number | null
  risk_budget_status: string | null
  forecast_confidence_level: string | null
  forecast_confidence_score: number | null
  data_quality: Record<string, string>
  elapsed_seconds: number
  error: string | null
}

export interface DepartureWindowDelta {
  offset_hours: number
  risk_delta_pct: number | null
  fuel_delta_pct: number | null
  eta_delta_hours: number | null
  distance_delta_km: number | null
}

export interface DepartureWindowsResponse {
  base_departure_time: string
  operating_mode: string
  risk_budget_limit: number
  results: DepartureWindowResult[]
  deltas: DepartureWindowDelta[]
  recommended_offset_hours: number | null
  recommendation_basis: string
  total_elapsed_seconds: number
  prototype_notice: string
}

// ---------------------------------------------------------------------------
// Phase 9: Historical Replay types
// ---------------------------------------------------------------------------

export interface HorizonVerificationResult {
  horizon_h: number
  sample_count: number
  mean_distance_error_km: number | null
  max_distance_error_km: number | null
  mean_lat_error_deg: number | null
  mean_lon_error_deg: number | null
  evaluation_status: string
  notes: string
}

export interface ForecastVerificationResponse {
  run_id: string
  dataset_id: string
  data_mode: string
  per_horizon: HorizonVerificationResult[]
  evaluation_status: string
  confidence_calibration_status: string
  prototype_notice: string
}

export interface DatasetContract {
  dataset_id: string
  source: string
  product: string
  start_time: string
  end_time: string
  spatial_coverage: string
  retrieved_at: string
  data_mode: string
  quality_status: string
  access_note: string
  prototype_notice: string
}

export interface ReplayRunResponse {
  run_id: string
  dataset_id: string
  data_mode: string
  elapsed_seconds: number
  evaluation_status: string
  evaluation_note: string
  dataset_contract: DatasetContract
  computation_trace: string[]
  forecast_verification: ForecastVerificationResponse
  route_risk: number | null
  route_fuel_tonnes: number | null
  route_eta_hours: number | null
  provenance: Record<string, unknown>[]
  error: string | null
  prototype_notice: string
}

