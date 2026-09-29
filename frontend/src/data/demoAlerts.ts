/**
 * demoAlerts.ts — HimDrishti Phase 5
 * SIH 2026 · PS 26059
 *
 * Deterministic demo alert data for the Key Alerts panel.
 * DEMO DATA ONLY — not real operational threat assessment.
 * Real alert engine is planned for Phase 8.
 */

export type AlertSeverity = 'info' | 'warning' | 'critical'

export interface AlertDetail {
  label: string
  value: string
}

export interface DemoAlert {
  id: string
  severity: AlertSeverity
  /** Icon identifier — maps to Lucide icon name */
  icon: 'triangle-alert' | 'info' | 'ice' | 'shield-alert'
  title: string
  description: string
  /** Expanded detail rows shown when user clicks the alert */
  details: AlertDetail[]
}

export const DEMO_ALERTS: DemoAlert[] = [
  {
    id: 'alert-iceberg-a',
    severity: 'warning',
    icon: 'triangle-alert',
    title: 'Iceberg A within 25 NM in 48h',
    description: 'Uncertainty cone moving south-east.',
    details: [
      { label: 'Forecast horizon', value: '+48h' },
      { label: 'Confidence', value: 'Medium' },
      { label: 'Distance', value: '25 NM' },
      { label: 'Drift direction', value: 'South-East (~118°)' },
      { label: 'Source', value: 'Demo forecast data' },
    ],
  },
  {
    id: 'alert-ice-zone',
    severity: 'warning',
    icon: 'shield-alert',
    title: 'High Ice Concentration Zone',
    description: 'Expected near 66°S, 80°E in 72h.',
    details: [
      { label: 'Forecast horizon', value: '+72h' },
      { label: 'Location', value: '66°S, 80°E' },
      { label: 'Concentration', value: '≥70%' },
      { label: 'Confidence', value: 'Medium–High' },
      { label: 'Source', value: 'Demo sea-ice forecast' },
    ],
  },
  {
    id: 'alert-confidence',
    severity: 'info',
    icon: 'info',
    title: 'Forecast Confidence: Medium',
    description: 'Due to sparse satellite coverage.',
    details: [
      { label: 'Overall confidence', value: 'Medium' },
      { label: 'Coverage gap', value: '66°S–72°S, 60°E–90°E' },
      { label: 'Last SAR pass', value: '21 May 2026, 09:45 IST' },
      { label: 'Next expected pass', value: '22 May 2026, 08:30 IST' },
      { label: 'Source', value: 'Sentinel-1 SAR (demo)' },
    ],
  },
]
