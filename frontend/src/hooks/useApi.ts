/**
 * frontend/src/hooks/useApi.ts
 * ------------------------------
 * React hooks wrapping the API client for each endpoint.
 *
 * Strategy:
 *   - useRoutes(): generates routes and returns ApiState<GenerateRoutesResponse>
 *   - useAlerts(): fetches alerts on mount, returns ApiState<AlertsResponse>
 *   - useProvenance(): fetches provenance on mount
 *   - useForecast(horizonHours): fetches forecast metadata
 *
 * Each hook:
 *   - Starts in 'idle' state (no fetch on mount by default for routes)
 *   - Shows 'loading' while fetching
 *   - Falls back to demo data (status:'unavailable') if backend unreachable
 *   - Never crashes the UI
 *
 * SIH 2026 · PS 26059
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  generateRoutes,
  getAlerts,
  getForecast,
  getProvenance,
  runReplay,
  type GenerateRoutesPayload,
  type ReplayRunPayload,
} from '../services/api'
import type {
  AlertsResponse,
  ApiState,
  ForecastResponse,
  GenerateRoutesResponse,
  ProvenanceResponse,
  ReplayRunResponse,
} from '../services/api'

// ---------------------------------------------------------------------------
// useRoutes — triggered explicitly by the user pressing "Generate Routes"
// ---------------------------------------------------------------------------

export function useRoutes() {
  const [state, setState] = useState<ApiState<GenerateRoutesResponse>>({
    status: 'idle',
    data: null,
    error: null,
  })

  const generate = useCallback(async (payload: GenerateRoutesPayload) => {
    setState({ status: 'loading', data: null, error: null })
    const result = await generateRoutes(payload)
    setState(result)
    return result
  }, [])

  const reset = useCallback(() => {
    setState({ status: 'idle', data: null, error: null })
  }, [])

  return { state, generate, reset }
}

// ---------------------------------------------------------------------------
// useAlerts — fetches on mount
// ---------------------------------------------------------------------------

export function useAlerts() {
  const [state, setState] = useState<ApiState<AlertsResponse>>({
    status: 'loading',
    data: null,
    error: null,
  })
  const hasFetched = useRef(false)

  useEffect(() => {
    if (hasFetched.current) return
    hasFetched.current = true
    getAlerts().then(setState)
  }, [])

  return state
}

// ---------------------------------------------------------------------------
// useProvenance — fetches on mount
// ---------------------------------------------------------------------------

export function useProvenance() {
  const [state, setState] = useState<ApiState<ProvenanceResponse>>({
    status: 'loading',
    data: null,
    error: null,
  })
  const hasFetched = useRef(false)

  useEffect(() => {
    if (hasFetched.current) return
    hasFetched.current = true
    getProvenance().then(setState)
  }, [])

  return state
}

// ---------------------------------------------------------------------------
// useForecast — re-fetches when horizonHours changes
// ---------------------------------------------------------------------------

export function useForecast(horizonHours: number) {
  const [state, setState] = useState<ApiState<ForecastResponse>>({
    status: 'loading',
    data: null,
    error: null,
  })

  useEffect(() => {
    setState({ status: 'loading', data: null, error: null })
    getForecast(horizonHours).then(setState)
  }, [horizonHours])

  return state
}

// ---------------------------------------------------------------------------
// useReplay — triggered explicitly by user pressing "Run Replay"
// Phase 11: surfaces the Phase 9 replay endpoint to the UI
// ---------------------------------------------------------------------------

export function useReplay() {
  const [state, setState] = useState<ApiState<ReplayRunResponse>>({
    status: 'idle',
    data: null,
    error: null,
  })

  const execute = useCallback(async (payload: ReplayRunPayload) => {
    setState({ status: 'loading', data: null, error: null })
    const result = await runReplay(payload)
    setState(result)
    return result
  }, [])

  const reset = useCallback(() => {
    setState({ status: 'idle', data: null, error: null })
  }, [])

  return { state, execute, reset }
}
