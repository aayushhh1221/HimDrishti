/**
 * demoRoutes.ts — HimDrishti Phase 4
 * SIH 2026 · PS 26059
 *
 * Three deterministic demo routes: Cape Town → Bharati Station.
 * Coordinates represent the Indian Ocean sector of the Southern Ocean.
 *
 * DEMO DATA — not real operational navigation recommendations.
 * POLARIS/RIO values are illustrative placeholders only.
 */

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'

export interface DemoRoute {
  id: string
  name: string
  shortLabel: string
  riskLevel: RiskLevel
  /** Human-readable ETA, e.g. "5d 14h" */
  etaLabel: string
  etaHours: number
  fuelMT: number
  polarisRIO: number
  /** Hex colour for map line and card accent */
  color: string
  /** Lighter background for card header */
  colorSoft: string
  /** Text colour for risk badge */
  badgeTextColor: string
  lineStyle: 'solid' | 'dashed'
  /** MapLibre dashArray — undefined for solid, [dash, gap] pairs for dashed */
  dashArray: number[] | undefined
  /** GeoJSON [lon, lat] coordinate pairs */
  coordinates: [number, number][]
  /** Position for the route name pill label on the map */
  labelCoord: [number, number]
  /** Whether this route follows a path distinct from other routes in the same run */
  is_distinct: boolean
  /** Set when is_distinct=false; explains why the path converged */
  convergence_note: string | null
}

export const DEMO_ROUTES: DemoRoute[] = [
  {
    id: 'recommended',
    name: 'Recommended Route',
    shortLabel: 'Recommended Route',
    riskLevel: 'LOW',
    etaLabel: '5d 14h',
    etaHours: 134,
    fuelMT: 142.6,
    polarisRIO: 18,
    color: '#00c896',       // vivid teal-green
    colorSoft: '#dcfce7',   // green-100
    badgeTextColor: '#15803d',
    lineStyle: 'solid',
    dashArray: undefined,
    // Curves NORTH of icebergs A/B — longer but avoids high-ice corridor
    coordinates: [
      [18.42, -33.93],
      [28.0,  -50.0 ],
      [36.0,  -61.5 ],
      [47.0,  -59.5 ],   // arc north of Iceberg A zone
      [58.0,  -62.5 ],   // north of Iceberg B
      [68.0,  -65.5 ],   // north of Iceberg C
      [76.19, -69.41],
    ],
    labelCoord: [55.0, -62.0],
    is_distinct: true,
    convergence_note: null,
  },
  {
    id: 'alternative1',
    name: 'Alternative Route 1',
    shortLabel: 'Alternative Route 1',
    riskLevel: 'MEDIUM',
    etaLabel: '5d 2h',
    etaHours: 122,
    fuelMT: 128.3,
    polarisRIO: 42,
    color: '#f5a623',       // vivid amber
    colorSoft: '#fef3c7',   // amber-100
    badgeTextColor: '#b45309',
    lineStyle: 'dashed',
    dashArray: [5, 4],
    // Middle path — through Iceberg A uncertainty zone, near B
    coordinates: [
      [18.42, -33.93],
      [26.0,  -48.0 ],
      [36.0,  -61.5 ],
      [50.0,  -63.5 ],   // through A cone zone
      [64.0,  -66.5 ],   // near Iceberg B
      [76.19, -69.41],
    ],
    labelCoord: [79.0, -67.0],
    is_distinct: true,
    convergence_note: null,
  },
  {
    id: 'higher-risk',
    name: 'Higher Risk Route',
    shortLabel: 'Higher Risk Route',
    riskLevel: 'HIGH',
    etaLabel: '4d 17h',
    etaHours: 113,
    fuelMT: 115.7,
    polarisRIO: 73,
    color: '#e03131',       // vivid red
    colorSoft: '#fee2e2',   // red-100
    badgeTextColor: '#b91c1c',
    lineStyle: 'dashed',
    dashArray: [6, 3],
    // Direct — through high ice-concentration corridor, near B/C cones
    coordinates: [
      [18.42, -33.93],
      [23.0,  -45.0 ],
      [36.0,  -61.5 ],
      [52.0,  -65.5 ],   // deep into ice zone
      [67.0,  -68.0 ],   // through Iceberg B/C zone
      [76.19, -69.41],
    ],
    labelCoord: [64.0, -68.5],
    is_distinct: true,
    convergence_note: null,
  },
]

/** Vessel starting position (current position, partway into voyage) */
export const VESSEL_POSITION: [number, number] = [36.0, -61.5]
