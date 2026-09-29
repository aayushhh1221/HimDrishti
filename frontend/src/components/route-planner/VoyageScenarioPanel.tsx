/**
 * VoyageScenarioPanel — Left Panel (Voyage Configuration)
 * SIH 2026 · PS 26188
 *
 * Matches reference.png Left Column layout & styling.
 * Preserves all scientific routing parameters, departure window pipeline,
 * and extreme risk acknowledgement gates.
 */

import { useState } from 'react'
import {
  MapPin,
  Calendar,
  Clock,
  Ship,
  Shield,
  Scale,
  Leaf,
  ChevronDown,
  ChevronUp,
  Info,
  Play,
  Loader2,
  AlertTriangle,
} from 'lucide-react'
import { DEMO_VOYAGE, VESSEL_VESSELS } from '../../data/demoVoyage'
import { useVoyageSession } from '../../contexts/VoyageSessionContext'
import { runDepartureWindows } from '../../services/api/client'
import type { DepartureWindowsResponse } from '../../services/api/types'
import styles from './VoyageScenarioPanel.module.css'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const CAPE_TOWN = { name: 'Cape Town, South Africa', lat: -33.93, lon: 18.42 }
const BHARATI   = { name: 'Bharati Station, Larsemann Hills', lat: -69.41, lon: 76.19 }

const ICE_CLASS_MAP: Record<string, string> = {
  'NCPOR Charter Vessel (Ice Class 1B)':        'NON_ICE_STRENGTHENED',
  'M/V Akademik Tryoshnikov (Ice Class 1A)':    'IA_SUPER_1A',
  'RSV Nuyina (Ice Class PC3)':                  'PC3_PC5',
}

type OperatingMode = 'SAFETY_FIRST' | 'BALANCED' | 'FUEL_SAVER'

const EXTREME_RISK_THRESHOLD = 0.70

function toUTCISOString(value: string): string {
  const d = new Date(value)
  if (isNaN(d.getTime())) {
    const hasOffset = /[Z+\-]\d*$/.test(value.trim())
    return hasOffset ? value : value + 'Z'
  }
  return d.toISOString()
}

export default function VoyageScenarioPanel() {
  const { generateRoutes, routeState } = useVoyageSession()

  const [planningTab, setPlanningTab] = useState<'Standard' | 'Bulk'>('Standard')
  // From/To are fixed to Cape Town → Bharati Station in this prototype.
  // The pipeline only supports this route; displaying them as read-only strings.
  const from = DEMO_VOYAGE.from
  const to   = DEMO_VOYAGE.to
  const [departureDate, setDepartureDate] = useState('2026-05-21')
  const [departureTime, setDepartureTime] = useState('12:00')
  const [vessel, setVessel]           = useState(DEMO_VOYAGE.vessel)
  const [draft, setDraft]             = useState(String(DEMO_VOYAGE.draftM))
  const [speed, setSpeed]             = useState(String(DEMO_VOYAGE.speedKnots))

  // Operating Mode
  const [operatingMode, setOperatingMode] = useState<OperatingMode>('BALANCED')
  const [maxRisk, setMaxRisk]             = useState<number>(0.30)
  const [maxDays, setMaxDays]             = useState<number>(15)
  const [extremeRiskAcknowledged, setExtremeRiskAcknowledged] = useState(false)

  // Accordion Sections (default open per reference.png)
  const [advancedOpen, setAdvancedOpen]       = useState(true)
  const [constraintsOpen, setConstraintsOpen] = useState(true)

  // Constraints toggles
  const [preferLowIce, setPreferLowIce]       = useState(true)
  const [avoidRiskZones, setAvoidRiskZones]   = useState(true)
  const [icebergEnsemble, setIcebergEnsemble] = useState(true)

  // Departure-window state
  const [dwWindowStart, setDwWindowStart]     = useState('2026-05-21')
  const [dwWindowEnd, setDwWindowEnd]         = useState('2026-05-30')
  const [dwLoading, setDwLoading]             = useState(false)
  const [dwError, setDwError]                 = useState<string | null>(null)
  const [dwResult, setDwResult]               = useState<DepartureWindowsResponse | null>(null)
  const [dwCurrentOffset, setDwCurrentOffset] = useState<number | null>(null)

  const isLoading   = routeState.status === 'loading'
  const requiresAcknowledgement = maxRisk > EXTREME_RISK_THRESHOLD
  const canGenerate = !isLoading && (!requiresAcknowledgement || extremeRiskAcknowledged)

  function handleModeChange(mode: OperatingMode) {
    setOperatingMode(mode)
    setMaxRisk(mode === 'SAFETY_FIRST' ? 0.25 : mode === 'FUEL_SAVER' ? 0.40 : 0.30)
    setExtremeRiskAcknowledged(false)
  }

  async function handleGenerate() {
    if (!canGenerate) return
    const combinedDeparture = `${departureDate}T${departureTime}:00`
    const deptUTC = toUTCISOString(combinedDeparture)

    await generateRoutes({
      origin: CAPE_TOWN,
      destination: BHARATI,
      departure_time: deptUTC,
      vessel: {
        name: vessel,
        ice_class: ICE_CLASS_MAP[vessel] ?? '1B',
        draft_m: parseFloat(draft) || DEMO_VOYAGE.draftM,
        speed_knots: parseFloat(speed) || DEMO_VOYAGE.speedKnots,
      },
      forecast_horizon_hours: 120,
      operating_mode: operatingMode,
      risk_budget: {
        max_acceptable_risk: maxRisk,
        uncertainty_weight: 0.5,
      },
      extreme_risk_acknowledged: extremeRiskAcknowledged,
    })
  }

  async function handleDepartureWindow(offsetHours: number) {
    const combinedDeparture = `${departureDate}T${departureTime}:00`
    const deptUTC = toUTCISOString(combinedDeparture)
    setDwLoading(true)
    setDwError(null)
    setDwCurrentOffset(offsetHours)

    try {
      const state = await runDepartureWindows({
        origin: CAPE_TOWN,
        destination: BHARATI,
        base_departure_time: deptUTC,
        vessel: {
          name: vessel,
          ice_class: ICE_CLASS_MAP[vessel] ?? '1B',
          draft_m: parseFloat(draft) || DEMO_VOYAGE.draftM,
          speed_knots: parseFloat(speed) || DEMO_VOYAGE.speedKnots,
        },
        forecast_horizon_hours: 120,
        operating_mode: operatingMode,
        risk_budget: { max_acceptable_risk: maxRisk, uncertainty_weight: 0.5 },
        extreme_risk_acknowledged: extremeRiskAcknowledged,
        candidate_offsets_hours: [0, 6, 12, 24],
      })
      if (state.status === 'success' && state.data) {
        setDwResult(state.data)
        setDwError(null)
      } else {
        setDwError(state.error ?? 'Departure-window comparison failed.')
        setDwResult(null)
      }
    } catch (err) {
      setDwError(err instanceof Error ? err.message : 'Unknown error')
      setDwResult(null)
    } finally {
      setDwLoading(false)
      setDwCurrentOffset(null)
    }
  }

  return (
    <div className={styles.panel} aria-label="Voyage configuration panel">
      {/* ── Header ─────────────────────────────────── */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <MapPin size={15} className={styles.headerPin} aria-hidden="true" />
          <h2 className={styles.headerTitle}>Voyage Configuration</h2>
        </div>
      </div>

      {/* ── Mode selector: Standard | Bulk Planning ── */}
      <div className={styles.modeTabs} role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={planningTab === 'Standard'}
          className={`${styles.tabBtn} ${planningTab === 'Standard' ? styles.tabBtnActive : ''}`}
          onClick={() => setPlanningTab('Standard')}
        >
          Standard
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={planningTab === 'Bulk'}
          className={`${styles.tabBtn} ${planningTab === 'Bulk' ? styles.tabBtnActive : ''}`}
          onClick={() => setPlanningTab('Bulk')}
          title="Bulk Planning is not yet implemented in this prototype"
        >
          Bulk Planning
          <span style={{ fontSize: '9px', marginLeft: '4px', opacity: 0.65 }}>(Coming Soon)</span>
        </button>
      </div>

      {/* ── Form Body ──────────────────────────────── */}
      <div className={styles.body}>

        {/* From */}
        <div className={styles.formGroup}>
          <label className={styles.label} htmlFor="voyage-from">
            From
            <span
              title="Only Cape Town is supported in this prototype"
              style={{ fontSize: '9px', marginLeft: '5px', opacity: 0.55, fontWeight: 400 }}
            >
              [fixed route]
            </span>
          </label>
          <div className={styles.inputWrapper}>
            <MapPin size={13} className={styles.inputIcon} aria-hidden="true" />
            <input
              id="voyage-from"
              className={styles.input}
              type="text"
              value={from}
              readOnly
              aria-label="Departure port — fixed to Cape Town in this prototype"
              style={{ cursor: 'default', opacity: 0.8 }}
            />
          </div>
        </div>

        {/* To */}
        <div className={styles.formGroup}>
          <label className={styles.label} htmlFor="voyage-to">
            To
            <span
              title="Only Bharati Station is supported in this prototype"
              style={{ fontSize: '9px', marginLeft: '5px', opacity: 0.55, fontWeight: 400 }}
            >
              [fixed route]
            </span>
          </label>
          <div className={styles.inputWrapper}>
            <MapPin size={13} className={styles.inputIcon} aria-hidden="true" />
            <input
              id="voyage-to"
              className={styles.input}
              type="text"
              value={to}
              readOnly
              aria-label="Destination station — fixed to Bharati Station in this prototype"
              style={{ cursor: 'default', opacity: 0.8 }}
            />
          </div>
        </div>

        {/* Departure Date & Time (Side-by-side) */}
        <div className={styles.formGroup}>
          <label className={styles.label}>Departure Date &amp; Time</label>
          <div className={styles.splitRow}>
            <div className={styles.inputWrapper}>
              <Calendar size={13} className={styles.inputIcon} aria-hidden="true" />
              <input
                id="voyage-dept-date"
                className={styles.input}
                type="date"
                value={departureDate}
                onChange={(e) => setDepartureDate(e.target.value)}
                aria-label="Departure date"
              />
            </div>
            <div className={styles.inputWrapper}>
              <Clock size={13} className={styles.inputIcon} aria-hidden="true" />
              <input
                id="voyage-dept-time"
                className={styles.input}
                type="time"
                value={departureTime}
                onChange={(e) => setDepartureTime(e.target.value)}
                aria-label="Departure time"
              />
            </div>
          </div>
        </div>

        {/* Vessel */}
        <div className={styles.formGroup}>
          <label className={styles.label} htmlFor="voyage-vessel">Vessel</label>
          <div className={styles.inputWrapper}>
            <Ship size={13} className={styles.inputIcon} aria-hidden="true" />
            <select
              id="voyage-vessel"
              className={styles.select}
              value={vessel}
              onChange={(e) => setVessel(e.target.value)}
              aria-label="Select research vessel"
            >
              {VESSEL_VESSELS.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
            <ChevronDown size={13} className={styles.chevronIcon} aria-hidden="true" />
          </div>
        </div>

        {/* Draft (m) & Speed (knots) (Side-by-side) */}
        <div className={styles.splitRow}>
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="voyage-draft">
              Draft (m)
              <span
                title="Vessel draft is recorded but does not affect Dijkstra / UCS route search in this prototype"
                style={{ fontSize: '9px', marginLeft: '5px', opacity: 0.55, fontWeight: 400 }}
              >
                [UI only]
              </span>
            </label>
            <div className={styles.inputWrapper}>
              <input
                id="voyage-draft"
                className={styles.input}
                type="number"
                step="0.1"
                min="3"
                max="15"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                aria-label="Vessel draft in metres"
              />
            </div>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="voyage-speed">Speed (knots)</label>
            <div className={styles.inputWrapper}>
              <input
                id="voyage-speed"
                className={styles.input}
                type="number"
                step="0.5"
                min="5"
                max="25"
                value={speed}
                onChange={(e) => setSpeed(e.target.value)}
                aria-label="Vessel speed in knots"
              />
            </div>
          </div>
        </div>

        {/* Operating Mode (3 Cards) */}
        <div className={styles.formGroup}>
          <label className={styles.label}>Operating Mode</label>
          <div className={styles.operatingModesGrid} role="radiogroup" aria-label="Operating Mode">
            {/* Safety-First */}
            <button
              type="button"
              role="radio"
              aria-checked={operatingMode === 'SAFETY_FIRST'}
              className={`${styles.modeCard} ${operatingMode === 'SAFETY_FIRST' ? styles.modeCardActive : ''}`}
              onClick={() => handleModeChange('SAFETY_FIRST')}
            >
              <Shield size={14} className={styles.modeIcon} />
              <div className={styles.modeName}>Safety-First</div>
              <div className={styles.modeDesc}>Lowest risk</div>
            </button>

            {/* Balanced */}
            <button
              type="button"
              role="radio"
              aria-checked={operatingMode === 'BALANCED'}
              className={`${styles.modeCard} ${operatingMode === 'BALANCED' ? styles.modeCardActive : ''}`}
              onClick={() => handleModeChange('BALANCED')}
            >
              <Scale size={14} className={styles.modeIcon} />
              <div className={styles.modeName}>Balanced</div>
              <div className={styles.modeDesc}>Optimal trade-off</div>
            </button>

            {/* Fuel-Saver */}
            <button
              type="button"
              role="radio"
              aria-checked={operatingMode === 'FUEL_SAVER'}
              className={`${styles.modeCard} ${operatingMode === 'FUEL_SAVER' ? styles.modeCardActive : ''}`}
              onClick={() => handleModeChange('FUEL_SAVER')}
            >
              <Leaf size={14} className={styles.modeIcon} />
              <div className={styles.modeName}>Fuel-Saver</div>
              <div className={styles.modeDesc}>Lower fuel cost</div>
            </button>
          </div>
        </div>

        {/* ── Advanced Options Accordion ────────────── */}
        <div className={styles.accordionGroup}>
          <button
            type="button"
            className={styles.accordionHeader}
            onClick={() => setAdvancedOpen(!advancedOpen)}
            aria-expanded={advancedOpen}
          >
            <div className={styles.accordionTitle}>
              <Clock size={13} className={styles.accordionIcon} />
              <span>Advanced Options</span>
            </div>
            {advancedOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>

          {advancedOpen && (
            <div className={styles.accordionBody}>
              {/* Departure Window (Sandbox) */}
              <div className={styles.subFormGroup}>
                <div className={styles.subLabelRow}>
                  <label className={styles.subLabel}>Departure Window (Sandbox)</label>
                  <span title="Evaluate voyage scenarios across candidate departure dates">
                    <Info size={11} className={styles.subInfoIcon} />
                  </span>
                </div>
                <div className={styles.splitRow}>
                  <div className={styles.inputWrapper}>
                    <Calendar size={11} className={styles.inputIcon} />
                    <input
                      type="date"
                      className={styles.inputSmall}
                      value={dwWindowStart}
                      onChange={(e) => setDwWindowStart(e.target.value)}
                    />
                  </div>
                  <span style={{ fontSize: '11px', color: '#94a3b8', alignSelf: 'center' }}>&rarr;</span>
                  <div className={styles.inputWrapper}>
                    <Calendar size={11} className={styles.inputIcon} />
                    <input
                      type="date"
                      className={styles.inputSmall}
                      value={dwWindowEnd}
                      onChange={(e) => setDwWindowEnd(e.target.value)}
                    />
                  </div>
                </div>

                {/* Candidate execution buttons */}
                <div style={{ display: 'flex', gap: '4px', marginTop: '6px' }}>
                  {[0, 6, 12, 24].map((offset) => {
                    const isRunning = dwLoading && dwCurrentOffset === offset
                    const label = offset === 0 ? 'Current' : `+${offset}h`
                    return (
                      <button
                        key={offset}
                        type="button"
                        className={styles.candidateBtn}
                        disabled={dwLoading}
                        onClick={() => handleDepartureWindow(offset)}
                        title={`Run candidate window starting ${label}`}
                      >
                        {isRunning ? <Loader2 size={10} style={{ animation: 'spin 1s linear infinite' }} /> : null}
                        {label}
                      </button>
                    )
                  })}
                </div>

                {dwLoading && (
                  <div style={{ fontSize: '10px', color: '#0284c7', marginTop: '4px' }}>
                    Running departure window simulation…
                  </div>
                )}
                {dwError && (
                  <div style={{ fontSize: '10px', color: '#ef4444', marginTop: '4px' }}>
                    {dwError}
                  </div>
                )}
                {dwResult && (
                  <div style={{ fontSize: '10px', color: '#16a34a', marginTop: '4px', background: '#f0fdf4', padding: '3px 6px', borderRadius: '3px', border: '1px solid #bbf7d0' }}>
                    Recommended: {dwResult.recommended_offset_hours !== null && dwResult.recommended_offset_hours > 0 ? `+${dwResult.recommended_offset_hours}h` : 'Current'} &bull; {dwResult.recommendation_basis || 'Optimal window'}
                  </div>
                )}
              </div>

              {/* Risk Budget (POLARIS) */}
              <div className={styles.subFormGroup}>
                <div className={styles.sliderLabelRow}>
                  <label className={styles.subLabel}>Risk Budget (POLARIS)</label>
                  <span className={styles.valueBadge}>{Math.round(maxRisk * 100)}</span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="0.85"
                  step="0.05"
                  className={styles.rangeSlider}
                  value={maxRisk}
                  onChange={(e) => setMaxRisk(parseFloat(e.target.value))}
                />
              </div>

              {/* Max Voyage Time */}
              <div className={styles.subFormGroup}>
                <div className={styles.sliderLabelRow}>
                  <label className={styles.subLabel}>
                    Max Voyage Time
                    <span
                      title="Max voyage time is not enforced by the pipeline search in this prototype"
                      style={{ fontSize: '9px', marginLeft: '5px', opacity: 0.55, fontWeight: 400 }}
                    >
                      [UI only]
                    </span>
                  </label>
                  <span className={styles.valueBadge}>{maxDays} days</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="30"
                  step="1"
                  className={styles.rangeSlider}
                  value={maxDays}
                  onChange={(e) => setMaxDays(parseInt(e.target.value, 10))}
                />
              </div>
            </div>
          )}
        </div>

        {/* ── Navigation Constraints Accordion ─────── */}
        <div className={styles.accordionGroup}>
          <button
            type="button"
            className={styles.accordionHeader}
            onClick={() => setConstraintsOpen(!constraintsOpen)}
            aria-expanded={constraintsOpen}
          >
            <div className={styles.accordionTitle}>
              <Shield size={13} className={styles.accordionIcon} />
              <span>Navigation Constraints</span>
            </div>
            {constraintsOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>

          {constraintsOpen && (
            <div className={styles.accordionBody}>
              <label className={styles.toggleRow}>
                <span className={styles.toggleLabel}>
                  Prefer lower ice concentration
                  <span style={{ fontSize: '9px', marginLeft: '4px', opacity: 0.55 }}>[UI only]</span>
                </span>
                <input
                  type="checkbox"
                  className={styles.toggleCheckbox}
                  checked={preferLowIce}
                  onChange={(e) => setPreferLowIce(e.target.checked)}
                />
                <span className={styles.toggleSwitch} />
              </label>

              <label className={styles.toggleRow}>
                <span className={styles.toggleLabel}>
                  Avoid high-risk zones
                  <span style={{ fontSize: '9px', marginLeft: '4px', opacity: 0.55 }}>[UI only]</span>
                </span>
                <input
                  type="checkbox"
                  className={styles.toggleCheckbox}
                  checked={avoidRiskZones}
                  onChange={(e) => setAvoidRiskZones(e.target.checked)}
                />
                <span className={styles.toggleSwitch} />
              </label>

              <label className={styles.toggleRow}>
                <span className={styles.toggleLabel}>Consider iceberg drift ensemble</span>
                <input
                  type="checkbox"
                  className={styles.toggleCheckbox}
                  checked={icebergEnsemble}
                  onChange={(e) => setIcebergEnsemble(e.target.checked)}
                />
                <span className={styles.toggleSwitch} />
              </label>
            </div>
          )}
        </div>

        {/* Extreme Risk Warning & Gate */}
        {requiresAcknowledgement && (
          <div className={styles.riskAlertBox}>
            <AlertTriangle size={14} className={styles.riskAlertIcon} />
            <div className={styles.riskAlertText}>
              Elevated risk threshold ({Math.round(maxRisk * 100)}/100).
              Requires operator acknowledgement before route generation.
            </div>
            <label className={styles.ackRow}>
              <input
                type="checkbox"
                checked={extremeRiskAcknowledged}
                onChange={(e) => setExtremeRiskAcknowledged(e.target.checked)}
              />
              <span>Acknowledge elevated risk</span>
            </label>
          </div>
        )}

        {/* ── Primary Action Button ────────────────── */}
        <button
          type="button"
          className={styles.generateBtn}
          onClick={handleGenerate}
          disabled={!canGenerate}
          aria-label={isLoading ? 'Generating routes…' : 'Generate routes'}
        >
          {isLoading ? (
            <>
              <Loader2 size={15} className={styles.spin} />
              <span>Generating Routes…</span>
            </>
          ) : (
            <>
              <Play size={13} fill="#ffffff" />
              <span>Generate Routes</span>
              <span className={styles.arrowIcon}>&rarr;</span>
            </>
          )}
        </button>

      </div>
    </div>
  )
}
