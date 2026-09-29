/**
 * MapControls — Overlaid on left side of the map
 * SIH 2026 · PS 26188
 * Matches reference.png map navigation toolbar.
 */

import type { RefObject } from 'react'
import * as maplibregl from 'maplibre-gl'
import { Plus, Minus, Layers, Maximize2, Compass, Home } from 'lucide-react'
import { VOYAGE_BOUNDS, VOYAGE_FIT_PADDING } from './AntarcticMap'
import styles from './MapControls.module.css'

interface MapControlsProps {
  mapRef: RefObject<maplibregl.Map | null>
  onToggleLayers?: () => void
}

export default function MapControls({ mapRef, onToggleLayers }: MapControlsProps) {
  const map = () => mapRef.current

  return (
    <div className={styles.controls} role="toolbar" aria-label="Map navigation controls">
      {/* Compass / North indicator */}
      <div className={styles.group}>
        <button
          className={styles.controlBtn}
          type="button"
          aria-label="Reset North orientation"
          title="Reset North"
          onClick={() => map()?.resetNorthPitch({ duration: 500 })}
        >
          <Compass size={16} strokeWidth={2} style={{ color: '#dc2626' }} />
        </button>
      </div>

      <div className={styles.separator} aria-hidden="true" />

      {/* Zoom controls */}
      <div className={styles.group}>
        <button
          className={styles.controlBtn}
          type="button"
          aria-label="Zoom in"
          title="Zoom in"
          onClick={() => map()?.zoomIn()}
        >
          <Plus size={15} strokeWidth={2.5} />
        </button>
        <button
          className={styles.controlBtn}
          type="button"
          aria-label="Zoom out"
          title="Zoom out"
          onClick={() => map()?.zoomOut()}
        >
          <Minus size={15} strokeWidth={2.5} />
        </button>
      </div>

      <div className={styles.separator} aria-hidden="true" />

      {/* Layers, Fit bounds & Home */}
      <div className={styles.group}>
        <button
          className={styles.controlBtn}
          type="button"
          aria-label="Toggle map layers panel"
          title="Toggle Layers"
          onClick={onToggleLayers}
        >
          <Layers size={14} strokeWidth={2} />
        </button>
        <button
          className={styles.controlBtn}
          type="button"
          aria-label="Fit route bounds"
          title="Fit view to voyage"
          onClick={() => {
            map()?.fitBounds(VOYAGE_BOUNDS, { padding: VOYAGE_FIT_PADDING, duration: 800 })
          }}
        >
          <Maximize2 size={14} strokeWidth={2} />
        </button>
        <button
          className={styles.controlBtn}
          type="button"
          aria-label="Reset map to default home view"
          title="Home view"
          onClick={() => {
            map()?.fitBounds(VOYAGE_BOUNDS, { padding: VOYAGE_FIT_PADDING, duration: 800 })
          }}
        >
          <Home size={14} strokeWidth={2} />
        </button>
      </div>
    </div>
  )
}
