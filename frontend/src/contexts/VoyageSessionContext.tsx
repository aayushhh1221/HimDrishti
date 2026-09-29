/**
 * frontend/src/contexts/VoyageSessionContext.tsx
 * -----------------------------------------------
 * Single source of truth for the entire HimDrishti voyage session.
 *
 * Extends RoutePlannerContext with:
 *   - voyageConfig: snapshot of the last GenerateRoutesRequest
 *   - captainDecision: ACCEPT / MODIFY / REJECT (human-in-the-loop)
 *   - auditEvents: append-only chronological session log
 *   - lastReplay: most recent replay run result
 *
 * All pages read from this context.
 * No page should import from demoRisk / demoAlerts / demoProvenance
 * once a route has been generated.
 *
 * SIH 2026 · PS 26059
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from 'react'
import { useRoutes } from '../hooks/useApi'
import type {
  ApiRoute,
  ApiState,
  DataMode,
  GenerateRoutesResponse,
  GenerateRoutesRequest,
  ReplayRunResponse,
} from '../services/api'
import type { GenerateRoutesPayload } from '../services/api/client'

// ---------------------------------------------------------------------------
// Audit event
// ---------------------------------------------------------------------------

export type AuditRole = 'SYSTEM' | 'OPERATOR' | 'CAPTAIN' | 'PIPELINE'

export interface AuditEvent {
  id: string
  timestamp: string          // ISO 8601 UTC
  role: AuditRole
  action: string
  detail: string
  sessionId: string
}

// ---------------------------------------------------------------------------
// Captain decision
// ---------------------------------------------------------------------------

export type CaptainDecisionState = 'pending' | 'accepted' | 'modified' | 'rejected'

export interface CaptainDecision {
  state: CaptainDecisionState
  routeId: string
  routeName: string
  timestamp: string
  remarks: string
}

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------

interface VoyageSessionContextValue {
  // ── Route generation ─────────────────────────────────────────────
  routeState: ApiState<GenerateRoutesResponse>
  generateRoutes: (payload: GenerateRoutesPayload) => Promise<void>
  selectedRouteId: string
  setSelectedRouteId: (id: string) => void
  activeRoute: ApiRoute | null
  dataMode: DataMode

  // ── Voyage config snapshot ────────────────────────────────────────
  voyageConfig: GenerateRoutesRequest | null

  // ── Captain decision ─────────────────────────────────────────────
  captainDecision: CaptainDecision | null
  setCaptainDecision: (decision: CaptainDecision) => void
  clearCaptainDecision: () => void

  // ── Audit log ────────────────────────────────────────────────────
  auditEvents: AuditEvent[]
  pushAuditEvent: (role: AuditRole, action: string, detail: string) => void

  // ── Replay ───────────────────────────────────────────────────────
  lastReplay: ReplayRunResponse | null
  setLastReplay: (r: ReplayRunResponse) => void

  // ── Session ID ───────────────────────────────────────────────────
  sessionId: string
}

const VoyageSessionContext = createContext<VoyageSessionContextValue | null>(null)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeId(): string {
  return Math.random().toString(36).slice(2, 10)
}

function utcNow(): string {
  return new Date().toISOString()
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function VoyageSessionProvider({ children }: { children: ReactNode }) {
  const { state: routeState, generate } = useRoutes()
  const [selectedRouteId, setSelectedRouteIdState] = useState('recommended')
  const [voyageConfig, setVoyageConfig] = useState<GenerateRoutesRequest | null>(null)
  const [captainDecision, setCaptainDecisionState] = useState<CaptainDecision | null>(null)
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [lastReplay, setLastReplayState] = useState<ReplayRunResponse | null>(null)
  const sessionIdRef = useRef<string>(makeId())

  // ── Audit event appender ────────────────────────────────────────
  const pushAuditEvent = useCallback(
    (role: AuditRole, action: string, detail: string) => {
      const ev: AuditEvent = {
        id: makeId(),
        timestamp: utcNow(),
        role,
        action,
        detail,
        sessionId: sessionIdRef.current,
      }
      setAuditEvents((prev) => [...prev, ev])
    },
    [],
  )

  // ── Route generation ────────────────────────────────────────────
  const generateRoutes = useCallback(
    async (payload: GenerateRoutesPayload) => {
      pushAuditEvent('SYSTEM', 'ROUTE_GENERATION_STARTED', `Mode: ${payload.operating_mode ?? 'BALANCED'}`)
      // Capture voyage config snapshot
      setVoyageConfig(payload as unknown as GenerateRoutesRequest)
      // Clear previous captain decision when new generation starts
      setCaptainDecisionState(null)

      const result = await generate(payload)

      if (result.status === 'success' && result.data?.recommended_route_id) {
        setSelectedRouteIdState(result.data.recommended_route_id)
        pushAuditEvent(
          'PIPELINE',
          'ROUTE_GENERATION_COMPLETE',
          `request_id=${result.data.request_id} routes=${result.data.routes.length} mode=${result.data.data_mode}`,
        )
      } else if (result.status === 'error') {
        pushAuditEvent('SYSTEM', 'ROUTE_GENERATION_FAILED', result.error ?? 'Unknown error')
      }
    },
    [generate, pushAuditEvent],
  )

  // ── Route selection ─────────────────────────────────────────────
  const setSelectedRouteId = useCallback(
    (id: string) => {
      setSelectedRouteIdState(id)
      const route = routeState.data?.routes.find((r) => r.route_id === id)
      if (route) {
        pushAuditEvent('OPERATOR', 'ROUTE_SELECTED', `route_id=${id} name="${route.name}"`)
      }
    },
    [routeState.data, pushAuditEvent],
  )

  // ── Captain decision ────────────────────────────────────────────
  const setCaptainDecision = useCallback(
    (decision: CaptainDecision) => {
      setCaptainDecisionState(decision)
      pushAuditEvent(
        'CAPTAIN',
        `CAPTAIN_DECISION_${decision.state.toUpperCase()}`,
        `route_id=${decision.routeId} route="${decision.routeName}" remarks="${decision.remarks}"`,
      )
    },
    [pushAuditEvent],
  )

  const clearCaptainDecision = useCallback(() => {
    setCaptainDecisionState(null)
  }, [])

  // ── Replay ──────────────────────────────────────────────────────
  const setLastReplay = useCallback(
    (r: ReplayRunResponse) => {
      setLastReplayState(r)
      pushAuditEvent(
        'SYSTEM',
        'REPLAY_COMPLETE',
        `run_id=${r.run_id} status=${r.evaluation_status} elapsed=${r.elapsed_seconds.toFixed(1)}s`,
      )
    },
    [pushAuditEvent],
  )

  // ── Derived ─────────────────────────────────────────────────────
  const activeRoute =
    routeState.data?.routes.find((r) => r.route_id === selectedRouteId) ?? null
  const dataMode: DataMode = routeState.data?.data_mode ?? 'SYNTHETIC_DEMO'

  return (
    <VoyageSessionContext.Provider
      value={{
        routeState,
        generateRoutes,
        selectedRouteId,
        setSelectedRouteId,
        activeRoute,
        dataMode,
        voyageConfig,
        captainDecision,
        setCaptainDecision,
        clearCaptainDecision,
        auditEvents,
        pushAuditEvent,
        lastReplay,
        setLastReplay,
        sessionId: sessionIdRef.current,
      }}
    >
      {children}
    </VoyageSessionContext.Provider>
  )
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useVoyageSession(): VoyageSessionContextValue {
  const ctx = useContext(VoyageSessionContext)
  if (!ctx) {
    throw new Error('useVoyageSession must be used inside <VoyageSessionProvider>')
  }
  return ctx
}

/**
 * Back-compat alias — components that previously used useRoutePlanner()
 * can be migrated incrementally by importing this alias.
 */
export const useRoutePlanner = useVoyageSession
