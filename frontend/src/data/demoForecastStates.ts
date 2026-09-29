/**
 * demoForecastStates.ts — HimDrishti Phase 4
 * SIH 2026 · PS 26059
 *
 * Pre-computed iceberg positions and uncertainty cones for each
 * forecast time step. Derived from deterministic drift parameters.
 *
 * DEMO DATA ONLY — not real iceberg trajectory forecasts.
 * These cones are geometrically constructed for visual demonstration.
 *
 * Real values will come from the Phase 6 iceberg trajectory engine.
 */

// ── Types ─────────────────────────────────────────────────────────

/** [longitude, latitude] pair */
type Pos = [number, number]

/** GeoJSON Polygon coordinate rings: [ring] */
type PolygonRings = Pos[][]

export interface IcebergState {
  id: string
  name: string
  /** Projected position at this forecast time */
  position: Pos
  /** 90% confidence cone polygon rings */
  cone90: PolygonRings
  /** 50% confidence cone polygon rings */
  cone50: PolygonRings
}

export interface ForecastState {
  hours: number
  label: string
  icebergs: IcebergState[]
}

export type ForecastHourIndex = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7
export const FORECAST_HOURS = [0, 24, 48, 72, 96, 120, 144, 168] as const

// ── Iceberg drift parameters ───────────────────────────────────────

interface IcebergSpec {
  id: string
  name: string
  /** Initial position [lon, lat] */
  origin: Pos
  /** Compass heading of drift (degrees from north, clockwise) */
  headingDeg: number
  /** Longitude displacement per hour (adjusted for latitude) */
  lonDegPerHour: number
  /** Latitude displacement per hour (negative = southward) */
  latDegPerHour: number
}

const ICEBERG_SPECS: IcebergSpec[] = [
  {
    id: 'A', name: 'Iceberg A',
    origin: [44.5, -60.0],
    headingDeg: 82,
    lonDegPerHour: 0.070,
    latDegPerHour: -0.003,
  },
  {
    id: 'B', name: 'Iceberg B',
    origin: [63.0, -61.0],
    headingDeg: 78,
    lonDegPerHour: 0.055,
    latDegPerHour: -0.004,
  },
  {
    id: 'C', name: 'Iceberg C',
    origin: [87.0, -61.5],
    headingDeg: 90,
    lonDegPerHour: 0.050,
    latDegPerHour: 0.000,
  },
]

// ── Cone geometry helper ───────────────────────────────────────────

/**
 * Generate a sector (fan) polygon from an origin point.
 * The sector opens in the direction of the iceberg's drift.
 * Polygon follows GeoJSON convention: first/last coord identical.
 *
 * @param origin   [lon, lat] of the cone tip (current iceberg position)
 * @param headingDeg  Compass heading (degrees, 0=N, 90=E)
 * @param distanceDeg Max reach of cone in degrees (determines length)
 * @param halfSpreadDeg Half-angle of the cone spread
 * @param steps    Number of arc segments
 */
function sectorPolygon(
  origin: Pos,
  headingDeg: number,
  distanceDeg: number,
  halfSpreadDeg: number,
  steps = 14,
): PolygonRings {
  if (distanceDeg < 0.05) {
    // Degenerate case: 0h state — return tiny circle-like polygon
    const r = 0.4
    const ring: Pos[] = []
    for (let i = 0; i <= 8; i++) {
      const a = (2 * Math.PI * i) / 8
      ring.push([origin[0] + r * Math.cos(a) * 0.7, origin[1] + r * Math.sin(a)])
    }
    ring.push(ring[0])
    return [ring]
  }

  // Convert compass heading to math angle (CCW from +x axis)
  const mathAngle = ((90 - headingDeg) * Math.PI) / 180
  const halfSpread = (halfSpreadDeg * Math.PI) / 180
  // Latitude correction: east-west distances shrink at high latitudes
  const latCos = Math.max(Math.cos((Math.abs(origin[1]) * Math.PI) / 180), 0.1)

  const ring: Pos[] = [origin]

  for (let i = 0; i <= steps; i++) {
    const a = mathAngle - halfSpread + (2 * halfSpread * i) / steps
    const dLon = (distanceDeg * Math.cos(a)) / latCos
    const dLat = distanceDeg * Math.sin(a)
    ring.push([origin[0] + dLon, origin[1] + dLat])
  }

  ring.push(origin) // close polygon
  return [ring]
}

// ── Build forecast state for a given time index ────────────────────

export function buildForecastState(index: ForecastHourIndex): ForecastState {
  const hours = FORECAST_HOURS[index]

  const icebergs: IcebergState[] = ICEBERG_SPECS.map((spec) => {
    // Project iceberg position at this forecast time
    const position: Pos = [
      spec.origin[0] + spec.lonDegPerHour * hours,
      spec.origin[1] + spec.latDegPerHour * hours,
    ]

    // Cone parameters grow with forecast horizon
    const distance = Math.max(0.05, hours * 0.055)
    const spread50 = 8 + (hours / 120) * 14    // 8° → 22° half-spread
    const spread90 = 16 + (hours / 120) * 22   // 16° → 38° half-spread
    const dist50 = distance * 0.80
    const dist90 = distance * 1.10

    return {
      id: spec.id,
      name: spec.name,
      position,
      cone90: sectorPolygon(spec.origin, spec.headingDeg, dist90, spread90),
      cone50: sectorPolygon(spec.origin, spec.headingDeg, dist50, spread50),
    }
  })

  return {
    hours,
    label: hours === 0 ? 'Current' : `+${hours}h`,
    icebergs,
  }
}

/** All pre-computed forecast states (called once at module load) */
export const FORECAST_STATES: ForecastState[] = (
  [0, 1, 2, 3, 4, 5, 6, 7] as ForecastHourIndex[]
).map(buildForecastState)

// ── Sea ice GeoJSON polygon ────────────────────────────────────────

/**
 * Simplified Antarctic sea ice extent polygon.
 * Covers the Indian Ocean sector (20°E → 120°E).
 * Ice edge variation is illustrative — not NSIDC data.
 * DEMO DATA ONLY.
 */
export const SEA_ICE_POLYGON = {
  type: 'FeatureCollection' as const,
  features: [
    {
      type: 'Feature' as const,
      properties: { type: 'sea-ice' },
      geometry: {
        type: 'Polygon' as const,
        coordinates: [[
          // Ice edge (irregular realistic-looking boundary)
          [10,  -61.5], [20, -63.0], [30, -65.5], [40, -67.5],
          [50,  -64.5], [60, -63.0], [70, -64.5], [80, -62.5],
          [90,  -64.0], [100, -66.5], [110, -65.0], [120, -63.5],
          [130, -64.0], [140, -65.5], [150, -64.0], [160, -63.5],
          [170, -64.5], [180, -64.0],
          // Cover Antarctica to south pole limit (Web Mercator boundary)
          [180, -80.0], [10, -80.0],
          // Close back to start
          [10, -61.5],
        ]],
      },
    },
  ],
}

// ── Geographic grid lines ──────────────────────────────────────────

const buildGridLines = () => {
  const features: object[] = []

  // Latitude lines: 60°S and 70°S
  for (const lat of [-60, -70]) {
    features.push({
      type: 'Feature',
      properties: { type: 'lat-line', label: `${Math.abs(lat)}°S` },
      geometry: {
        type: 'LineString',
        coordinates: Array.from({ length: 37 }, (_, i) => [10 + i * 5, lat]),
      },
    })
  }

  // Longitude lines: 40°E, 60°E, 80°E, 100°E
  for (const lon of [40, 60, 80, 100]) {
    features.push({
      type: 'Feature',
      properties: { type: 'lon-line', label: `${lon}°E` },
      geometry: {
        type: 'LineString',
        coordinates: [
          [lon, -50],
          [lon, -80],
        ],
      },
    })
  }

  return { type: 'FeatureCollection', features }
}

export const GRID_LINES = buildGridLines()
