/**
 * EnvironmentalForecastPanel.tsx
 * SIH 2026 · PS 26188
 *
 * Environmental Forecast (Selected Route) evidence panel matching reference.png bottom-center.
 * Displays 4 compact spatial/evidence cards:
 *   1. Sea-Ice Concentration (%)
 *   2. Iceberg Probability
 *   3. Wind Speed (m/s)
 *   4. Wave Height (m)
 */

import styles from './EnvironmentalForecastPanel.module.css'

export default function EnvironmentalForecastPanel() {
  return (
    <div className={styles.container} aria-label="Environmental forecast evidence along selected corridor">
      <div className={styles.header}>
        <h3 className={styles.title}>Environmental Forecast (Selected Route)</h3>
      </div>

      <div className={styles.grid}>
        {/* 1. Sea-Ice Concentration */}
        <div className={styles.card}>
          <div className={styles.cardLabel}>Sea-Ice Concentration</div>
          <div className={styles.canvasWrapper}>
            <svg viewBox="0 0 140 64" className={styles.previewSvg} preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <linearGradient id="iceGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#0f172a" />
                  <stop offset="25%" stopColor="#1e3a8a" />
                  <stop offset="50%" stopColor="#0284c7" />
                  <stop offset="70%" stopColor="#059669" />
                  <stop offset="85%" stopColor="#eab308" />
                  <stop offset="100%" stopColor="#dc2626" />
                </linearGradient>
              </defs>
              <rect width="140" height="64" fill="url(#iceGrad)" />
              {/* Synthetic ice contours matching Antarctic shelf */}
              <path d="M 0,20 Q 40,45 80,25 T 140,55 L 140,64 L 0,64 Z" fill="rgba(255,255,255,0.4)" />
              <path d="M 30,10 Q 70,30 110,15 T 140,40" stroke="#ffffff" strokeWidth="1.2" fill="none" opacity="0.8" />
              <path d="M 0,40 Q 60,60 120,35" stroke="rgba(255,255,255,0.6)" strokeWidth="1" strokeDasharray="3 2" fill="none" />
            </svg>
          </div>
          <div className={styles.scaleRow}>
            <span>0</span>
            <span>25</span>
            <span>50</span>
            <span>75</span>
            <span>100</span>
          </div>
        </div>

        {/* 2. Iceberg Probability */}
        <div className={styles.card}>
          <div className={styles.cardLabel}>Iceberg Probability</div>
          <div className={styles.canvasWrapper}>
            <svg viewBox="0 0 140 64" className={styles.previewSvg} preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <linearGradient id="bergGrad" x1="0%" y1="100%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#0284c7" />
                  <stop offset="40%" stopColor="#38bdf8" />
                  <stop offset="70%" stopColor="#f8fafc" />
                  <stop offset="100%" stopColor="#1e293b" />
                </linearGradient>
              </defs>
              <rect width="140" height="64" fill="#0369a1" />
              {/* Drift probability clouds */}
              <ellipse cx="45" cy="32" rx="35" ry="18" fill="rgba(186, 230, 253, 0.45)" />
              <ellipse cx="95" cy="40" rx="30" ry="16" fill="rgba(224, 242, 254, 0.65)" />
              <circle cx="50" cy="32" r="3" fill="#ffffff" />
              <circle cx="95" cy="40" r="3" fill="#ffffff" />
              <path d="M 20,40 Q 60,20 100,45" stroke="#bae6fd" strokeWidth="1.2" strokeDasharray="2 2" fill="none" />
            </svg>
          </div>
          <div className={styles.scaleRow}>
            <span>0.0</span>
            <span>0.2</span>
            <span>0.4</span>
            <span>0.6</span>
            <span>0.8</span>
          </div>
        </div>

        {/* 3. Wind Speed (m/s) */}
        <div className={styles.card}>
          <div className={styles.cardLabel}>Wind Speed (m/s)</div>
          <div className={styles.canvasWrapper}>
            <svg viewBox="0 0 140 64" className={styles.previewSvg} preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <linearGradient id="windGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#0284c7" />
                  <stop offset="35%" stopColor="#0d9488" />
                  <stop offset="65%" stopColor="#10b981" />
                  <stop offset="85%" stopColor="#f59e0b" />
                  <stop offset="100%" stopColor="#ef4444" />
                </linearGradient>
              </defs>
              <rect width="140" height="64" fill="url(#windGrad)" />
              {/* Wind stream lines */}
              <path d="M 0,15 C 30,25 70,5 140,20" stroke="rgba(255,255,255,0.7)" strokeWidth="1.2" fill="none" />
              <path d="M 0,35 C 40,45 80,25 140,40" stroke="rgba(255,255,255,0.7)" strokeWidth="1.2" fill="none" />
              <path d="M 0,52 C 50,60 90,45 140,55" stroke="rgba(255,255,255,0.7)" strokeWidth="1.2" fill="none" />
              {/* Vector arrowheads */}
              <polygon points="75,8 82,13 75,18" fill="rgba(255,255,255,0.85)" />
              <polygon points="85,28 92,33 85,38" fill="rgba(255,255,255,0.85)" />
              <polygon points="95,45 102,50 95,55" fill="rgba(255,255,255,0.85)" />
            </svg>
          </div>
          <div className={styles.scaleRow}>
            <span>0</span>
            <span>5</span>
            <span>10</span>
            <span>15</span>
            <span>20</span>
          </div>
        </div>

        {/* 4. Wave Height (m) */}
        <div className={styles.card}>
          <div className={styles.cardLabel}>Wave Height (m)</div>
          <div className={styles.canvasWrapper}>
            <svg viewBox="0 0 140 64" className={styles.previewSvg} preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <linearGradient id="waveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#1e3a8a" />
                  <stop offset="30%" stopColor="#0284c7" />
                  <stop offset="60%" stopColor="#0d9488" />
                  <stop offset="80%" stopColor="#eab308" />
                  <stop offset="100%" stopColor="#dc2626" />
                </linearGradient>
              </defs>
              <rect width="140" height="64" fill="url(#waveGrad)" />
              {/* Swell wavefronts */}
              <path d="M 10,64 Q 35,20 60,64" stroke="rgba(255,255,255,0.6)" strokeWidth="1.5" fill="none" />
              <path d="M 50,64 Q 75,15 100,64" stroke="rgba(255,255,255,0.6)" strokeWidth="1.5" fill="none" />
              <path d="M 90,64 Q 115,25 140,64" stroke="rgba(255,255,255,0.6)" strokeWidth="1.5" fill="none" />
              <path d="M 0,30 Q 70,10 140,30" stroke="#fef08a" strokeWidth="1" strokeDasharray="3 2" fill="none" />
            </svg>
          </div>
          <div className={styles.scaleRow}>
            <span>0</span>
            <span>2</span>
            <span>4</span>
            <span>6</span>
            <span>8</span>
          </div>
        </div>
      </div>
    </div>
  )
}
