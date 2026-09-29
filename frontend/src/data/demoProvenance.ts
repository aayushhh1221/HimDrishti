/**
 * demoProvenance.ts — HimDrishti Phase 5
 * SIH 2026 · PS 26059
 *
 * Deterministic demo data provenance records.
 * DEMO DATA ONLY — these sources are NOT being fetched live.
 * Real provenance integration is planned for Phase 8.
 */

export type ProvenanceStatus = 'synced' | 'stale' | 'unavailable'

export interface ProvenanceRecord {
  id: string
  /** Display category name */
  category: string
  /** Primary data source name */
  source: string
  /** Dataset / product identifier */
  dataset: string
  status: ProvenanceStatus
  /** Human-readable timestamp */
  updatedAt: string
  /** Coverage region */
  coverage: string
  /** Short version for the compact panel row */
  updatedAtShort: string
}

export function getLiveIstTimestamp(): string {
  const d = new Date()
  const day = d.getDate()
  const month = d.toLocaleString('en-US', { month: 'short', timeZone: 'Asia/Kolkata' })
  const time = d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Kolkata',
  })
  return `${day} ${month}, ${time} IST`
}

export const DEMO_PROVENANCE: ProvenanceRecord[] = [
  {
    id: 'prov-sea-ice',
    category: 'Sea Ice Data',
    source: 'Sentinel-1 SAR',
    dataset: 'GRD IW — Sea Ice Extent',
    status: 'synced',
    updatedAt: 'Live',
    updatedAtShort: '',
    coverage: 'Southern Ocean 30°S–90°S',
  },
  {
    id: 'prov-iceberg',
    category: 'Iceberg Data',
    source: 'Sentinel-1 SAR + MODIS',
    dataset: 'NSIDC Iceberg Tracking (demo)',
    status: 'synced',
    updatedAt: 'Live',
    updatedAtShort: '',
    coverage: 'Indian Ocean sector 20°E–120°E',
  },
  {
    id: 'prov-atmosphere',
    category: 'Ocean & Atmosphere',
    source: 'ECMWF IFS',
    dataset: 'ERA5 / Open IFS — 0.25° grid',
    status: 'synced',
    updatedAt: 'Live',
    updatedAtShort: '',
    coverage: 'Global — 120h forecast horizon',
  },
  {
    id: 'prov-ocean-currents',
    category: 'Ocean Currents',
    source: 'Mercator Ocean',
    dataset: 'NEMO Ocean Physics — 0.25° grid',
    status: 'synced',
    updatedAt: 'Live',
    updatedAtShort: '',
    coverage: 'Southern Ocean circumpolar',
  },
]

export const FULL_PROVENANCE_NOTE =
  'All data shown is deterministic demo data for SIH 2026 prototype purposes. ' +
  'Sentinel-1, MODIS, and ECMWF IFS are NOT being queried live. ' +
  'Real data integration is planned for Phase 8 (operational backend).'
