/**
 * ForecastTimeline — Bottom overlay on the map
 * SIH 2026 · PS 26188
 *
 * Interactive play/pause + scrubber for 0h → 168h forecast progression.
 * Drives iceberg position and cone updates in AntarcticMap via parent state.
 * Matches reference.png timeline bar.
 */

import { useEffect, useRef, useCallback } from 'react'
import { Play, Pause, ChevronDown } from 'lucide-react'
import { FORECAST_HOURS } from '../../data/demoForecastStates'
import type { ForecastHourIndex } from '../../data/demoForecastStates'
import styles from './ForecastTimeline.module.css'

interface ForecastTimelineProps {
  forecastIndex: ForecastHourIndex
  isPlaying: boolean
  onForecastChange: (index: ForecastHourIndex) => void
  onPlayingChange: (playing: boolean) => void
}

const PLAY_INTERVAL_MS = 1000

// Ticks derived directly from FORECAST_HOURS as the single source of truth
const TIMELINE_TICKS = FORECAST_HOURS.map((h) => `${h}h`)

export default function ForecastTimeline({
  forecastIndex,
  isPlaying,
  onForecastChange,
  onPlayingChange,
}: ForecastTimelineProps) {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const forecastIndexRef = useRef<ForecastHourIndex>(forecastIndex)
  forecastIndexRef.current = forecastIndex

  // Fill percentage for slider background gradient (mapped to 0-5 index which corresponds to 0h-120h/168h)
  const fillPct = (forecastIndex / (FORECAST_HOURS.length - 1)) * 100

  const advance = useCallback(() => {
    const next = (forecastIndexRef.current + 1) as ForecastHourIndex
    if (next >= FORECAST_HOURS.length) {
      onPlayingChange(false)
      if (intervalRef.current) clearInterval(intervalRef.current)
      return
    }
    onForecastChange(next)
  }, [onForecastChange, onPlayingChange])

  // Play/pause animation
  useEffect(() => {
    if (!isPlaying) {
      if (intervalRef.current) clearInterval(intervalRef.current)
      return
    }

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
      onForecastChange((FORECAST_HOURS.length - 1) as ForecastHourIndex)
      onPlayingChange(false)
      return
    }

    if (forecastIndex >= FORECAST_HOURS.length - 1) {
      onForecastChange(0)
    }

    intervalRef.current = setInterval(advance, PLAY_INTERVAL_MS)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isPlaying]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (forecastIndex >= FORECAST_HOURS.length - 1 && isPlaying) {
      onPlayingChange(false)
    }
  }, [forecastIndex, isPlaying, onPlayingChange])

  function handlePlay() {
    onPlayingChange(!isPlaying)
  }

  function handleSlider(e: React.ChangeEvent<HTMLInputElement>) {
    onPlayingChange(false)
    onForecastChange(Number(e.target.value) as ForecastHourIndex)
  }

  const currentHour = FORECAST_HOURS[forecastIndex] ?? 48

  return (
    <div className={styles.timeline} role="region" aria-label="Forecast simulation timeline">
      {/* Play/pause circular button */}
      <button
        className={styles.playBtn}
        type="button"
        aria-label={isPlaying ? 'Pause forecast timeline' : 'Play forecast timeline'}
        onClick={handlePlay}
      >
        {isPlaying ? (
          <Pause size={14} fill="#ffffff" />
        ) : (
          <Play size={14} fill="#ffffff" style={{ marginLeft: '2px' }} />
        )}
      </button>

      {/* Scrubber Area */}
      <div className={styles.scrubberArea}>
        <div className={styles.titleRow}>
          <span className={styles.timelineTitle}>Forecast Timeline (hours)</span>
        </div>

        {/* Ticks */}
        <div className={styles.ticks} aria-hidden="true">
          {TIMELINE_TICKS.map((t, idx) => {
            const isMatch = idx === forecastIndex
            return (
              <span
                key={t}
                className={`${styles.tick} ${isMatch ? styles.tickActive : ''}`}
                onClick={() => {
                  onPlayingChange(false)
                  onForecastChange(idx as ForecastHourIndex)
                }}
              >
                {t}
              </span>
            )
          })}
        </div>

        {/* Slider */}
        <div className={styles.sliderWrapper}>
          <input
            type="range"
            min={0}
            max={FORECAST_HOURS.length - 1}
            step={1}
            value={forecastIndex}
            onChange={handleSlider}
            className={styles.slider}
            style={{ '--fill': `${fillPct}%` } as React.CSSProperties}
            aria-label={`Forecast hour: +${currentHour}h`}
            aria-valuemin={0}
            aria-valuemax={168}
            aria-valuenow={currentHour}
          />
        </div>
      </div>

      {/* Right side accessories */}
      <div className={styles.accessories}>
        <div className={styles.timeBadge}>
          Forecast Time: +{currentHour}h
        </div>

        <div className={styles.resolutionPill}>
          <span>100 NM</span>
          <ChevronDown size={11} />
        </div>
      </div>
    </div>
  )
}
