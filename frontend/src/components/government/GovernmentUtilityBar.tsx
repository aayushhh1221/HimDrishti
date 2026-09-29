/**
 * GovernmentUtilityBar
 * SIH 2026 · PS 26188
 *
 * Top accessibility/government-context bar matching reference.png Row 1.
 */

import { useRef, useState } from 'react'
import {
  ExternalLink,
  Type,
  Globe,
  ChevronDown,
  Accessibility,
  X,
  CheckCircle,
  Sun,
} from 'lucide-react'
import type { FontSizeLevel } from '../../design-system/accessibility'
import styles from './GovernmentUtilityBar.module.css'

interface GovernmentUtilityBarProps {
  fontSizeLevel: FontSizeLevel
  onFontSizeChange: (level: FontSizeLevel) => void
}

const FONT_LABELS: Record<FontSizeLevel, string> = {
  small: 'A−',
  normal: 'A',
  large: 'A+',
}

export default function GovernmentUtilityBar({
  fontSizeLevel,
  onFontSizeChange,
}: GovernmentUtilityBarProps) {
  const [showA11yPanel, setShowA11yPanel] = useState(false)
  const [showLangDropdown, setShowLangDropdown] = useState(false)
  const barRef = useRef<HTMLDivElement>(null)

  function handleSkipToContent(e: React.MouseEvent | React.KeyboardEvent) {
    if ('key' in e && e.key !== 'Enter' && e.key !== ' ') return
    e.preventDefault()
    const main = document.getElementById('main-content')
    if (main) {
      main.setAttribute('tabindex', '-1')
      main.focus()
      main.addEventListener('blur', () => main.removeAttribute('tabindex'), { once: true })
    }
  }

  return (
    <div ref={barRef} className={styles.bar} role="navigation" aria-label="Government context and accessibility controls">
      {/* Skip to content — visible on keyboard focus */}
      <a
        href="#main-content"
        className={styles.skipLink}
        onClick={handleSkipToContent}
        onKeyDown={handleSkipToContent}
      >
        Skip to main content
      </a>

      {/* ── Left: Government context ─────────────────────────── */}
      <div className={styles.left}>
        <div className={styles.flagIcon} aria-hidden="true">
          <div className={styles.flagTop} />
          <div className={styles.flagMiddle}>
            <div className={styles.flagAshoka} />
          </div>
          <div className={styles.flagBottom} />
        </div>

        <span className={styles.govText}>Government of India</span>

        <button
          className={styles.extLinkBtn}
          aria-label="Government of India portal (opens in new tab)"
          title="Government of India portal"
          type="button"
          onClick={() => window.open('https://www.india.gov.in/', '_blank', 'noopener')}
        >
          <ExternalLink size={11} strokeWidth={2} />
        </button>
      </div>

      {/* ── Right: Accessibility & Utility Controls ───────────── */}
      <div className={styles.right}>
        <button
          className={styles.skipBtn}
          type="button"
          aria-label="Skip to main content"
          onClick={() => {
            const main = document.getElementById('main-content')
            if (main) { main.setAttribute('tabindex', '-1'); main.focus() }
          }}
        >
          Skip to main content
        </button>

        <div className={styles.separator} aria-hidden="true" />

        {/* Font size controls */}
        <div className={styles.fontControls} role="group" aria-label="Text size controls">
          {(['small', 'normal', 'large'] as FontSizeLevel[]).map((level) => (
            <button
              key={level}
              className={`${styles.fontBtn} ${fontSizeLevel === level ? styles.fontBtnActive : ''}`}
              type="button"
              onClick={() => onFontSizeChange(level)}
              aria-label={
                level === 'small' ? 'Decrease text size' :
                level === 'normal' ? 'Default text size' :
                'Increase text size'
              }
              aria-pressed={fontSizeLevel === level}
            >
              {FONT_LABELS[level]}
            </button>
          ))}
        </div>

        <div className={styles.separator} aria-hidden="true" />

        {/* Theme toggle icon button */}
        <button
          className={styles.iconBtn}
          type="button"
          aria-label="Light mode active"
          title="Light theme"
        >
          <Sun size={13} strokeWidth={2} />
        </button>

        <div className={styles.separator} aria-hidden="true" />

        {/* Accessibility panel toggle */}
        <div style={{ position: 'relative' }}>
          <button
            className={styles.iconBtn}
            type="button"
            aria-label="Accessibility options"
            aria-expanded={showA11yPanel}
            aria-haspopup="dialog"
            onClick={() => { setShowA11yPanel(v => !v); setShowLangDropdown(false) }}
          >
            <Accessibility size={13} strokeWidth={2} />
          </button>

          {showA11yPanel && (
            <div
              className={styles.a11yPanel}
              role="dialog"
              aria-label="Accessibility options"
              aria-modal="false"
            >
              <button
                className={styles.a11yClose}
                type="button"
                aria-label="Close accessibility panel"
                onClick={() => setShowA11yPanel(false)}
              >
                <X size={14} />
              </button>
              <p className={styles.a11yPanelTitle}>Accessibility</p>
              <div className={styles.a11yItem}>
                <Type size={13} />
                Text size: currently {fontSizeLevel}
              </div>
              <div className={styles.a11yItem}>
                <CheckCircle size={13} color="#18794e" />
                Keyboard navigation enabled
              </div>
              <div className={styles.a11yItem}>
                <CheckCircle size={13} color="#18794e" />
                WCAG 2.1 AA contrast verified
              </div>
              <div className={styles.a11yItem} style={{ marginTop: '8px', fontSize: '11px', color: '#52606d' }}>
                SIH 2026 Prototype &middot; PS 26188
              </div>
            </div>
          )}
        </div>

        <div className={styles.separator} aria-hidden="true" />

        {/* Language selector */}
        <div style={{ position: 'relative' }}>
          <button
            className={styles.iconBtn}
            type="button"
            aria-label="Select language (English)"
            aria-expanded={showLangDropdown}
            aria-haspopup="listbox"
            onClick={() => { setShowLangDropdown(v => !v); setShowA11yPanel(false) }}
          >
            <Globe size={13} strokeWidth={2} />
            <span className={styles.langText}>English</span>
            <ChevronDown size={10} strokeWidth={2.5} />
          </button>

          {showLangDropdown && (
            <div className={styles.langDropdown} role="listbox" aria-label="Language selection">
              <button
                className={`${styles.langOption} ${styles.langOptionActive}`}
                role="option"
                aria-selected="true"
                type="button"
                onClick={() => setShowLangDropdown(false)}
              >
                English
              </button>
              <button
                className={styles.langOption}
                role="option"
                aria-selected="false"
                type="button"
                title="Hindi localisation"
                onClick={() => setShowLangDropdown(false)}
                style={{ color: '#52606d' }}
              >
                हिन्दी (coming soon)
              </button>
            </div>
          )}
        </div>

        <div className={styles.separator} aria-hidden="true" />

        {/* System operational status badge */}
        <div className={styles.statusPill} role="status" aria-label="All systems operational">
          <span className={styles.statusDotGreen} aria-hidden="true" />
          <span className={styles.statusText}>All systems operational</span>
        </div>
      </div>
    </div>
  )
}
