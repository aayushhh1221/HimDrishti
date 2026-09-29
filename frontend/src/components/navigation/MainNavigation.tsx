/**
 * MainNavigation
 * SIH 2026 · PS 26188
 *
 * Primary application navigation bar matching reference.png Row 3.
 * Dark navy (#0b1f33 or #091e36), height ~44px.
 * Features 8 mission navigation items + Mission Mode segmented pill selector.
 */

import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  SlidersHorizontal,
  BarChart2,
  ShieldCheck,
  Database,
  PlayCircle,
  ClipboardList,
  FileText,
  Info,
} from 'lucide-react'
import styles from './MainNavigation.module.css'

interface NavItem {
  to: string
  label: string
  icon: React.ReactNode
  ariaLabel: string
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/route-planner',
    label: 'Route Planner',
    icon: <SlidersHorizontal size={14} strokeWidth={2.2} />,
    ariaLabel: 'Route Planner — mission workspace',
  },
  {
    to: '/forecast-explorer',
    label: 'Forecast Explorer',
    icon: <BarChart2 size={14} strokeWidth={2.2} />,
    ariaLabel: 'Forecast Explorer',
  },
  {
    to: '/risk-compliance',
    label: 'Risk & Compliance',
    icon: <ShieldCheck size={14} strokeWidth={2.2} />,
    ariaLabel: 'Risk and Compliance',
  },
  {
    to: '/data-provenance',
    label: 'Data Provenance',
    icon: <Database size={14} strokeWidth={2.2} />,
    ariaLabel: 'Data Provenance',
  },
  {
    to: '/mission-replay',
    label: 'Mission Replay',
    icon: <PlayCircle size={14} strokeWidth={2.2} />,
    ariaLabel: 'Mission Replay and Verification',
  },
  {
    to: '/audit-log',
    label: 'Audit Log',
    icon: <ClipboardList size={14} strokeWidth={2.2} />,
    ariaLabel: 'Decision Audit Log',
  },
  {
    to: '/reports',
    label: 'Reports',
    icon: <FileText size={14} strokeWidth={2.2} />,
    ariaLabel: 'Mission Reports & Dossiers',
  },
  {
    to: '/about',
    label: 'About',
    icon: <Info size={14} strokeWidth={2.2} />,
    ariaLabel: 'About HimDrishti',
  },
]

export default function MainNavigation() {
  const [missionMode, setMissionMode] = useState<'Research' | 'Operational'>('Operational')

  return (
    <nav className={styles.nav} aria-label="Primary navigation">
      <div className={styles.navInner}>
        {/* Navigation items */}
        <ul className={styles.navList} role="list">
          {NAV_ITEMS.map((item) => (
            <li key={item.to} className={styles.navItem} role="listitem">
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`
                }
                aria-label={item.ariaLabel}
              >
                {({ isActive }) => (
                  <>
                    <span className={styles.navIcon} aria-hidden="true">
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                    {isActive && <span className="sr-only"> (current page)</span>}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>

        {/* Right side: Mission Mode segmented toggle */}
        <div className={styles.missionModeContainer}>
          <div className={styles.missionModeLabel}>
            <span>Mission Mode</span>
            <Info size={12} className={styles.infoIcon} aria-hidden="true" />
          </div>
          <div className={styles.segmentedToggle} role="radiogroup" aria-label="Mission Mode selector">
            <button
              type="button"
              role="radio"
              aria-checked={missionMode === 'Research'}
              className={`${styles.toggleBtn} ${missionMode === 'Research' ? styles.toggleBtnActive : ''}`}
              onClick={() => setMissionMode('Research')}
            >
              Research
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={missionMode === 'Operational'}
              className={`${styles.toggleBtn} ${missionMode === 'Operational' ? styles.toggleBtnActive : ''}`}
              onClick={() => setMissionMode('Operational')}
            >
              Operational
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}
