/**
 * VoyageStatusStrip.tsx
 * SIH 2026 · PS 26059 / PS 26188
 *
 * Compact Voyage Status / KPI strip immediately below main navigation.
 * Bound to real application state via VoyageSessionContext.
 *
 * Five left-aligned items:
 * 1. Selected Route: route name + distance nm (from API) or "Cape Town → Bharati"
 * 2. Departure: Live browser/system time in IST (auto-updating)
 * 3. Vessel: from voyageConfig.vessel.name or "NCPOR Charter Vessel"
 * 4. Operating Mode: Balanced / selected mode (from routeState)
 * 5. Region: Southern Ocean (60°S–90°S)
 */

import { useState, useEffect } from 'react'
import {
  Navigation,
  Calendar,
  Ship,
  Compass,
  Globe,
} from 'lucide-react'
import { useVoyageSession } from '../../contexts/VoyageSessionContext'
import styles from './VoyageStatusStrip.module.css'

function getLiveISTString(): string {
  const now = new Date()
  const day = new Intl.DateTimeFormat('en-GB', { day: '2-digit', timeZone: 'Asia/Kolkata' }).format(now)
  const month = new Intl.DateTimeFormat('en-GB', { month: 'short', timeZone: 'Asia/Kolkata' }).format(now)
  const year = new Intl.DateTimeFormat('en-GB', { year: 'numeric', timeZone: 'Asia/Kolkata' }).format(now)
  const time = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' }).format(now)
  return `${day} ${month} ${year}, ${time} IST`
}

export default function VoyageStatusStrip() {
  // Single destructure — no duplicate hook calls
  const { routeState, activeRoute, voyageConfig } = useVoyageSession()
  const [liveTime, setLiveTime] = useState(getLiveISTString)

  useEffect(() => {
    const timer = setInterval(() => {
      setLiveTime(getLiveISTString())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Operating mode from route state or default to Balanced
  const operatingMode = routeState.data?.operating_mode
    ? routeState.data.operating_mode === 'SAFETY_FIRST'
      ? 'Safety-First'
      : routeState.data.operating_mode === 'FUEL_SAVER'
        ? 'Fuel-Saver'
        : 'Balanced'
    : 'Balanced'

  // Live KPI values from session state
  const vesselName   = (voyageConfig as any)?.vessel?.name ?? 'NCPOR Charter Vessel'
  const routeLabel   = activeRoute?.name ?? 'Recommended Route'
  const distanceNm   = activeRoute?.metrics?.total_distance_nm
  const durationHrs  = activeRoute?.metrics?.estimated_duration_hours

  // "Fast Route · 3,720 nm" when data present, else "Cape Town → Bharati Station"
  const routeKpi = distanceNm != null
    ? `${routeLabel} · ${distanceNm.toFixed(0)} nm`
    : 'Cape Town → Bharati Station'

  // "13.3 hrs transit" when data present, else blank (used as sub-label)
  const transitLabel = durationHrs != null ? `${durationHrs.toFixed(1)} hrs transit` : null

  return (
    <section
      className={styles.strip}
      aria-label="Voyage status and mission overview"
    >
      <div className={styles.inner}>
        {/* 1. Selected Route */}
        <div className={styles.kpiItem}>
          <div className={styles.iconBoxBlue} aria-hidden="true">
            <Navigation size={14} className={styles.iconBlue} />
          </div>
          <div className={styles.textBox}>
            <span className={styles.kpiLabel}>Selected Route</span>
            <span className={styles.kpiValue} title={transitLabel ?? undefined}>
              {routeKpi}
            </span>
          </div>
        </div>

        <div className={styles.divider} aria-hidden="true" />

        {/* 2. Departure (Live Current IST Time) */}
        <div className={styles.kpiItem}>
          <div className={styles.iconBoxBlue} aria-hidden="true">
            <Calendar size={14} className={styles.iconBlue} />
          </div>
          <div className={styles.textBox}>
            <span className={styles.kpiLabel}>Departure</span>
            <span className={styles.kpiValue}>{liveTime}</span>
          </div>
        </div>

        <div className={styles.divider} aria-hidden="true" />

        {/* 3. Vessel */}
        <div className={styles.kpiItem}>
          <div className={styles.iconBoxBlue} aria-hidden="true">
            <Ship size={14} className={styles.iconBlue} />
          </div>
          <div className={styles.textBox}>
            <span className={styles.kpiLabel}>Vessel</span>
            <span className={styles.kpiValue}>
              {vesselName}
            </span>
          </div>
        </div>

        <div className={styles.divider} aria-hidden="true" />

        {/* 4. Operating Mode */}
        <div className={styles.kpiItem}>
          <div className={styles.iconBoxBlue} aria-hidden="true">
            <Compass size={14} className={styles.iconBlue} />
          </div>
          <div className={styles.textBox}>
            <span className={styles.kpiLabel}>Operating Mode</span>
            <span className={styles.kpiValue}>{operatingMode}</span>
          </div>
        </div>

        <div className={styles.divider} aria-hidden="true" />

        {/* 5. Region */}
        <div className={styles.kpiItem}>
          <div className={styles.iconBoxBlue} aria-hidden="true">
            <Globe size={14} className={styles.iconBlue} />
          </div>
          <div className={styles.textBox}>
            <span className={styles.kpiLabel}>Region</span>
            <span className={styles.kpiValue}>
              Southern Ocean (60°S&ndash;90°S)
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}
