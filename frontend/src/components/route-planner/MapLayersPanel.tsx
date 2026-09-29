/**
 * MapLayersPanel.tsx
 * SIH 2026 · PS 26188
 *
 * Floating Map Layers control matching reference.png top-right panel.
 * Genuine toggles driving MapLibre layer visibility.
 */

import { useState } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import styles from './MapLayersPanel.module.css'

export interface MapLayersState {
  recommendedRoute: boolean
  alternativeRoutes: boolean
  higherRiskRoute: boolean
  seaIce: boolean
  icebergEnsemble: boolean
  riskZones: boolean
  windCurrent: boolean
  historicalTracks: boolean
}

interface MapLayersPanelProps {
  layers: MapLayersState
  onToggleLayer: (key: keyof MapLayersState) => void
}

export default function MapLayersPanel({ layers, onToggleLayer }: MapLayersPanelProps) {
  const [open, setOpen] = useState(true)

  return (
    <div className={styles.panel} aria-label="Map layers control">
      <button
        type="button"
        className={styles.header}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span className={styles.title}>Map Layers</span>
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {open && (
        <div className={styles.body}>
          {/* Recommended Route */}
          <label className={styles.layerRow}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={layers.recommendedRoute}
              onChange={() => onToggleLayer('recommendedRoute')}
            />
            <span className={styles.routeIconGreen} aria-hidden="true" />
            <span className={styles.layerLabel}>Recommended Route</span>
          </label>

          {/* Alternative Routes */}
          <label className={styles.layerRow}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={layers.alternativeRoutes}
              onChange={() => onToggleLayer('alternativeRoutes')}
            />
            <span className={styles.routeIconAmber} aria-hidden="true" />
            <span className={styles.layerLabel}>Alternative Routes</span>
          </label>

          {/* Higher Risk Route */}
          <label className={styles.layerRow}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={layers.higherRiskRoute}
              onChange={() => onToggleLayer('higherRiskRoute')}
            />
            <span className={styles.routeIconRed} aria-hidden="true" />
            <span className={styles.layerLabel}>Higher Risk Route</span>
          </label>

          {/* Sea-Ice Concentration */}
          <label className={styles.layerRow}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={layers.seaIce}
              onChange={() => onToggleLayer('seaIce')}
            />
            <span className={styles.iconGradient} aria-hidden="true" />
            <span className={styles.layerLabel}>Sea-Ice Concentration</span>
          </label>

          {/* Iceberg Ensemble */}
          <label className={styles.layerRow}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={layers.icebergEnsemble}
              onChange={() => onToggleLayer('icebergEnsemble')}
            />
            <span className={styles.iconBerg} aria-hidden="true" />
            <span className={styles.layerLabel}>Iceberg Ensemble</span>
          </label>

          {/* Risk Zones */}
          <label className={styles.layerRow}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={layers.riskZones}
              onChange={() => onToggleLayer('riskZones')}
            />
            <span className={styles.iconRiskZone} aria-hidden="true" />
            <span className={styles.layerLabel}>Risk Zones</span>
          </label>

          {/* Wind & Current */}
          <label className={styles.layerRow}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={layers.windCurrent}
              onChange={() => onToggleLayer('windCurrent')}
            />
            <span className={styles.iconArrow} aria-hidden="true">&rarr;</span>
            <span className={styles.layerLabel}>Wind &amp; Current</span>
          </label>

          {/* Historical Tracks */}
          <label className={styles.layerRow}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={layers.historicalTracks}
              onChange={() => onToggleLayer('historicalTracks')}
            />
            <span className={styles.iconTrack} aria-hidden="true" />
            <span className={styles.layerLabel}>Historical Tracks</span>
          </label>
        </div>
      )}
    </div>
  )
}
