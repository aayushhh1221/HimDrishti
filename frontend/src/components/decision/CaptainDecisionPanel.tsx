/**
 * CaptainDecisionPanel.tsx — HimDrishti Phase 8
 * SIH 2026 · PS 26059 / PS 26188
 *
 * "4. Captain Decision" panel.
 * Implements Accept / Modify / Reject state machine matching reference-ui2.png.
 *
 * Typography & layout matching reference-ui2.png:
 * - Heading: "4. Captain Decision" with (i) icon
 * - System recommendation note
 * - Master authority wording
 * - Primary wide "Accept Recommended Route" button
 * - Secondary side-by-side "Modify Route" and "Reject" buttons
 */

import { useState, useEffect, useRef } from 'react'
import { Info, Check, Pencil, X, RotateCcw } from 'lucide-react'
import { useVoyageSession } from '../../contexts/VoyageSessionContext'
import type { ApiRoute } from '../../services/api'
import styles from './CaptainDecisionPanel.module.css'

type LocalState = 'pending' | 'accepted' | 'modifying' | 'rejected'

interface CaptainDecisionPanelProps {
  selectedRouteId: string
  activeRoute: ApiRoute | null
}

export default function CaptainDecisionPanel({
  selectedRouteId,
  activeRoute,
}: CaptainDecisionPanelProps) {
  const [localState, setLocalState] = useState<LocalState>('pending')
  const [remarks, setRemarks]       = useState('')
  const { setCaptainDecision, captainDecision } = useVoyageSession()

  // Derive display values from activeRoute (API) — no demoRisk fallback
  const routeName  = activeRoute?.name ?? 'Recommended Route'
  const explanation = activeRoute?.system_explanation ??
    'Generate routes to view the system explanation for the selected route.'

  const prevRouteIdRef = useRef<string | null>(null)
  const prevRouteRef   = useRef<ApiRoute | null>(null)

  useEffect(() => {
    const routeIdChanged = prevRouteIdRef.current !== null &&
                           prevRouteIdRef.current !== selectedRouteId
    const activeRouteReplaced = prevRouteRef.current !== null &&
                                prevRouteRef.current !== activeRoute

    if (routeIdChanged || activeRouteReplaced) {
      setLocalState('pending')
    }

    prevRouteIdRef.current = selectedRouteId
    prevRouteRef.current   = activeRoute
  }, [selectedRouteId, activeRoute])

  function handleAccept() {
    setLocalState('accepted')
    setCaptainDecision({
      state: 'accepted',
      routeId: selectedRouteId,
      routeName,
      timestamp: new Date().toISOString(),
      remarks: '',
    })
  }
  function handleModify() {
    setRemarks('')
    setLocalState('modifying')
  }
  function confirmModify() {
    setCaptainDecision({
      state: 'modified',
      routeId: selectedRouteId,
      routeName,
      timestamp: new Date().toISOString(),
      remarks: remarks.trim() || 'Modification requested — adjust parameters and regenerate.',
    })
  }
  function handleReject() {
    setRemarks('')
    setLocalState('rejected')
  }
  function confirmReject() {
    setCaptainDecision({
      state: 'rejected',
      routeId: selectedRouteId,
      routeName,
      timestamp: new Date().toISOString(),
      remarks: remarks.trim() || 'Rejected by Master.',
    })
  }
  function handleReset() { setLocalState('pending'); setRemarks('') }

  // Sync local display state if session decision was cleared externally
  useEffect(() => {
    if (!captainDecision) setLocalState('pending')
  }, [captainDecision])


  return (
    <section
      className={styles.panel}
      aria-labelledby="captain-panel-heading"
    >
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerTitleGroup}>
          <span id="captain-panel-heading" className={styles.headerTitle}>
            4. Captain Decision
          </span>
          <Info
            size={13}
            className={styles.infoIcon}
            aria-label="Final navigation decision rests with the Master/Captain"
            role="img"
          />
        </div>
      </div>

      {/* Body */}
      <div className={styles.body}>

        {/* ── PENDING state ──────────────────── */}
        {localState === 'pending' && (
          <>
            <div className={styles.notesGroup}>
              <p className={styles.systemNote}>
                {explanation}
              </p>
              <p className={styles.authorityNote}>
                The <strong>final decision</strong> rests with the Master.
              </p>
            </div>

            <div className={styles.actions}>
              {/* Accept — primary green */}
              <button
                className={styles.btnAccept}
                type="button"
                onClick={handleAccept}
                aria-label={`Accept ${routeName}`}
              >
                <Check size={15} aria-hidden="true" />
                Accept Recommended Route
              </button>

              {/* Modify — secondary full width */}
              <button
                className={styles.btnModify}
                type="button"
                onClick={handleModify}
                aria-label="Modify route parameters"
              >
                <Pencil size={13} aria-hidden="true" />
                Modify Route
              </button>

              {/* Reject — danger outline full width */}
              <button
                className={styles.btnReject}
                type="button"
                onClick={handleReject}
                aria-label="Reject this route"
              >
                <X size={13} aria-hidden="true" />
                Reject
              </button>
            </div>
          </>
        )}

        {/* ── ACCEPTED state ─────────────────── */}
        {localState === 'accepted' && (
          <div className={styles.stateBlock} role="status" aria-live="polite">
            <div className={styles.stateIcon} data-variant="accepted">
              <Check size={16} aria-hidden="true" />
            </div>
            <p className={styles.stateTitle}>Route Decision Recorded</p>
            <p className={styles.stateDesc}>
              <strong>{routeName}</strong> accepted by Master as recommended under current forecast.
              Modeled risk values are from the SYNTHETIC_DEMO pipeline &mdash; not an operational guarantee.
              Final navigation authority rests with the Master/Captain/Ice Pilot.
            </p>
            <button
              className={styles.btnReset}
              type="button"
              onClick={handleReset}
              aria-label="Return to decision options"
            >
              <RotateCcw size={12} aria-hidden="true" />
              Change Decision
            </button>
          </div>
        )}

        {/* ── MODIFYING state ────────────────── */}
        {localState === 'modifying' && (
          <div className={styles.stateBlock} role="status" aria-live="polite">
            <div className={styles.stateIcon} data-variant="modifying">
              <Pencil size={14} aria-hidden="true" />
            </div>
            <p className={styles.stateTitle}>Route Modification</p>
            <p className={styles.stateDesc}>
              Adjust parameters in the Voyage Scenario panel and regenerate routes.
              Interactive waypoint editing is not yet implemented in this prototype.
            </p>
            <textarea
              placeholder="Modification remarks (optional)…"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              rows={2}
              className={styles.remarksInput}
              aria-label="Modification remarks"
            />
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                className={styles.btnAccept}
                type="button"
                onClick={confirmModify}
                aria-label="Confirm modification request"
                style={{ flex: 1, fontSize: '12px' }}
              >
                <Check size={13} aria-hidden="true" /> Confirm Modification
              </button>
              <button
                className={styles.btnReset}
                type="button"
                onClick={handleReset}
                aria-label="Return to decision options"
              >
                <RotateCcw size={12} aria-hidden="true" />
              </button>
            </div>
          </div>
        )}

        {/* ── REJECTED state ─────────────────── */}
        {localState === 'rejected' && (
          <div className={styles.stateBlock} role="status" aria-live="polite">
            <div className={styles.stateIcon} data-variant="rejected">
              <X size={14} aria-hidden="true" />
            </div>
            <p className={styles.stateTitle}>Route Rejected</p>
            <p className={styles.stateDesc}>
              <strong>{routeName}</strong> rejected by Master.
              Please select an alternative route from the Route Comparison panel.
            </p>
            <textarea
              placeholder="Rejection reason (optional)…"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              rows={2}
              className={styles.remarksInput}
              aria-label="Rejection reason"
            />
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                className={styles.btnReject}
                type="button"
                onClick={confirmReject}
                aria-label="Confirm rejection"
                style={{ flex: 1, fontSize: '12px' }}
              >
                <X size={13} aria-hidden="true" /> Confirm Rejection
              </button>
              <button
                className={styles.btnReset}
                type="button"
                onClick={handleReset}
                aria-label="Return to decision options"
              >
                <RotateCcw size={12} aria-hidden="true" />
              </button>
            </div>
          </div>
        )}

      </div>

      {/* Footer strip matching reference footer.png */}
      <div className={styles.authorityFooter}>
        Decision authority: Captain / Ice Pilot &middot; Demo &mdash; no data sent
      </div>
    </section>
  )
}
