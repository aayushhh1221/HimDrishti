/**
 * ApplicationShell
 * SIH 2026 · PS 26188
 *
 * Full application chrome following reference.png:
 *   1. GovernmentUtilityBar
 *   2. InstitutionalHeader
 *   3. MainNavigation
 *   4. VoyageStatusStrip (bound to VoyageSessionContext)
 *   5. <main> (page content via React Router)
 *   6. Institutional Footer
 *
 * VoyageSessionProvider wraps all page content — single source of truth.
 */

import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

import GovernmentUtilityBar from '../government/GovernmentUtilityBar'
import InstitutionalHeader from '../government/InstitutionalHeader'
import MainNavigation from '../navigation/MainNavigation'
import VoyageStatusStrip from '../government/VoyageStatusStrip'

import RoutePlanner from '../../pages/RoutePlanner'
import ForecastExplorer from '../../pages/ForecastExplorer'
import RiskCompliance from '../../pages/RiskCompliance'
import Provenance from '../../pages/Provenance'
import MissionReplay from '../../pages/MissionReplay'
import AuditLog from '../../pages/AuditLog'
import Reports from '../../pages/Reports'
import About from '../../pages/About'
import { VoyageSessionProvider } from '../../contexts/VoyageSessionContext'

import type { FontSizeLevel } from '../../design-system/accessibility'
import { applyFontSize } from '../../design-system/accessibility'

import styles from './ApplicationShell.module.css'

const FONT_SIZE_STORAGE_KEY = 'himdrishti_font_size'

function getSavedFontSize(): FontSizeLevel {
  try {
    const saved = localStorage.getItem(FONT_SIZE_STORAGE_KEY)
    if (saved === 'small' || saved === 'normal' || saved === 'large') return saved
  } catch { /* storage not available */ }
  return 'normal'
}

export default function ApplicationShell() {
  const [fontSizeLevel, setFontSizeLevel] = useState<FontSizeLevel>(getSavedFontSize)

  useEffect(() => {
    applyFontSize(fontSizeLevel)
    try {
      localStorage.setItem(FONT_SIZE_STORAGE_KEY, fontSizeLevel)
    } catch { /* storage not available */ }
  }, [fontSizeLevel])

  return (
    <VoyageSessionProvider>
      <div className={styles.shell}>

        {/* ── 1. Government utility bar ───────────────────────── */}
        <GovernmentUtilityBar
          fontSizeLevel={fontSizeLevel}
          onFontSizeChange={setFontSizeLevel}
        />

        {/* ── 2. Institutional branding header ────────────────── */}
        <InstitutionalHeader />

        {/* ── 3. Primary navigation ───────────────────────────── */}
        <MainNavigation />

        {/* ── 4. Voyage status / KPI strip (Row 4) ────────────── */}
        <VoyageStatusStrip />

        {/* ── 5. Main content area ────────────────────────────── */}
        <main
          id="main-content"
          className={styles.mainContent}
          aria-label="HimDrishti main workspace"
          tabIndex={-1}
        >
          <Routes>
            <Route path="/" element={<Navigate to="/route-planner" replace />} />
            <Route path="/route-planner" element={<RoutePlanner />} />
            <Route path="/forecast-explorer" element={<ForecastExplorer />} />
            <Route path="/risk-compliance" element={<RiskCompliance />} />
            <Route path="/data-provenance" element={<Provenance />} />
            <Route path="/mission-replay" element={<MissionReplay />} />
            <Route path="/audit-log" element={<AuditLog />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/about" element={<About />} />
            <Route path="*" element={<Navigate to="/route-planner" replace />} />
          </Routes>
        </main>

        {/* ── 6. Institutional Footer ──── */}
        <footer className={styles.footer} role="contentinfo">
          <div className={styles.footerContainer}>
            {/* LEFT */}
            <div className={styles.footerLeft}>
              <a href="/about" className={styles.footerLink}>Terms of Use</a>
              <a href="/about" className={styles.footerLink}>Privacy Policy</a>
              <a href="/about" className={styles.footerLink}>Accessibility Statement</a>
              <a href="/about" className={styles.footerLink}>Contact Us</a>
            </div>

            {/* CENTER */}
            <div className={styles.footerCenter}>
              &copy; 2026 Ministry of Earth Sciences, Government of India
            </div>

            {/* RIGHT */}
            <div className={styles.footerRight}>
              This is a SIH 2026 Prototype. Not for Operational Use.
            </div>
          </div>
        </footer>

      </div>
    </VoyageSessionProvider>
  )
}
