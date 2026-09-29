/**
 * demoVoyage.ts — HimDrishti Phase 4
 * SIH 2026 · PS 26059
 *
 * Deterministic demo voyage scenario.
 * Replace with backend API response in Phase 7.
 *
 * DEMO DATA — not an operational voyage plan.
 */

export interface VoyageScenario {
  from: string
  fromShort: string
  to: string
  toShort: string
  departure: string
  vessel: string
  iceClass: string
  draftM: number
  speedKnots: number
}

export const DEMO_VOYAGE: VoyageScenario = {
  from: 'Cape Town, South Africa',
  fromShort: 'Cape Town',
  to: 'Bharati Station, Larsemann Hills',
  toShort: 'Bharati Station',
  departure: '21 May 2026, 12:00 IST',
  vessel: 'NCPOR Charter Vessel (Ice Class 1B)',
  iceClass: '1B',
  draftM: 7.2,
  speedKnots: 12,
}

export const VESSEL_VESSELS = [
  'NCPOR Charter Vessel (Ice Class 1B)',
  'M/V Akademik Tryoshnikov (Ice Class 1A)',
  'RSV Nuyina (Ice Class PC3)',
] as const
