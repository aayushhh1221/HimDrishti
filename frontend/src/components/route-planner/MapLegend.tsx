/**
 * MapLegend.tsx — Map overlay, top-right corner
 * SIH 2026 · PS 26059
 *
 * Clean institutional legend control matching reference-ui2.png.
 */

import { useState } from 'react'
import { List } from 'lucide-react'
import styles from './MapLegend.module.css'

export default function MapLegend() {
  const [open, setOpen] = useState(false)

  return (
    <div className={styles.legendContainer}>
      <button
        className={styles.legendBtn}
        type="button"
        aria-label="Toggle map legend"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <List size={13} aria-hidden="true" />
        Legend
      </button>

      {open && (
        <div
          className={styles.panel}
          role="dialog"
          aria-label="Map legend"
          aria-modal="false"
        >
          <p className={styles.panelTitle}>Legend</p>

          {/* Routes */}
          <div className={styles.item}>
            <div className={styles.swatch} style={{ background: '#16a34a' }} aria-hidden="true" />
            <span>Recommended Route</span>
          </div>
          <div className={styles.item}>
            <div
              className={`${styles.swatch} ${styles.swatchDashed}`}
              style={{ color: '#d97706', width: '28px' }}
              aria-hidden="true"
            />
            <span>Alternative Route 1</span>
          </div>
          <div className={styles.item}>
            <div
              className={`${styles.swatch} ${styles.swatchDashed}`}
              style={{ color: '#dc2626', width: '28px' }}
              aria-hidden="true"
            />
            <span>Higher Risk Route</span>
          </div>

          <hr className={styles.divider} aria-hidden="true" />

          {/* Vessel */}
          <div className={styles.item}>
            <div className={styles.swatchVessel} aria-hidden="true">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="3">
                <polygon points="3 11 22 2 13 21 11 13 3 11" />
              </svg>
            </div>
            <span>Current Vessel</span>
          </div>

          {/* Icebergs */}
          <div className={styles.item}>
            <div className={styles.swatchDot} style={{ background: '#38bdf8' }} aria-hidden="true" />
            <span>Iceberg position</span>
          </div>
          <div className={styles.item}>
            <div className={styles.swatchCone} style={{ background: 'rgba(2, 132, 199, 0.26)' }} aria-hidden="true" />
            <span>50% uncertainty cone</span>
          </div>
          <div className={styles.item}>
            <div className={styles.swatchCone} style={{ background: 'rgba(2, 132, 199, 0.12)' }} aria-hidden="true" />
            <span>90% uncertainty cone</span>
          </div>

          <hr className={styles.divider} aria-hidden="true" />

          {/* Ice */}
          <div className={styles.item}>
            <div className={styles.swatchIce} style={{ background: 'rgba(224, 242, 254, 0.6)' }} aria-hidden="true" />
            <span>Sea ice extent</span>
          </div>

          <p className={styles.footerNote}>
            SIH 2026 · PS 26059 · Research Prototype
          </p>
        </div>
      )}
    </div>
  )
}
