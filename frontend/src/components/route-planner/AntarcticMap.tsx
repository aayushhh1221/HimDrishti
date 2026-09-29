/**
 * AntarcticMap.tsx — HimDrishti Phase 4 / Hard Redesign
 * SIH 2026 · PS 26059 / PS 26188
 *
 * Interactive Antarctic navigation decision-support map matching reference-ui2.png:
 * - Map section title: "Antarctic Map & Routing Overview"
 * - Clean vector basemap via OpenFreeMap (frontend/public/maps/himdrishti.json)
 * - Synchronized route rendering (Recommended Route, Alternative 1, Higher Risk)
 * - HTML markers for Cape Town (red pin), Bharati Station (green pin), Vessel, Icebergs
 * - Floating MapControls (left), floating MapLegend (top-right)
 * - Scale bar (bottom-left)
 * - ForecastTimeline (below map)
 */

import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { FeatureCollection } from 'geojson'
import { Maximize2 } from 'lucide-react'

import MapControls from './MapControls'
import MapLegend from './MapLegend'
import ForecastTimeline from './ForecastTimeline'

import {
  FORECAST_STATES,
  SEA_ICE_POLYGON,
  GRID_LINES,
} from '../../data/demoForecastStates'
import type { ForecastHourIndex, ForecastState } from '../../data/demoForecastStates'
import { DEMO_ROUTES, VESSEL_POSITION } from '../../data/demoRoutes'
import { useVoyageSession } from '../../contexts/VoyageSessionContext'
import styles from './AntarcticMap.module.css'

// ── Map Configuration ──────────────────────────────────────────────
export const MAP_CENTER: [number, number] = [48.0, -52.0]
export const MAP_ZOOM = 2.45
export const HIMDRISHTI_STYLE = '/maps/himdrishti.json'

// Voyage bounds & padding framing Cape Town -> Southern Ocean -> Hazard -> Bharati
export const VOYAGE_BOUNDS: [[number, number], [number, number]] = [
  [10.0, -73.0],
  [82.0, -28.0],
]
export const VOYAGE_FIT_PADDING = { top: 60, bottom: 45, left: 40, right: 40 }

// Distinct high-risk polygon zone near Antarctic shelf (62°S–68°S, 50°E–75°E)
const RISK_ZONE_POLYGON: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Prydz Bay High-Ice Approach Zone' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [48.0, -62.0],
            [72.0, -63.5],
            [78.0, -68.0],
            [70.0, -69.0],
            [52.0, -66.5],
            [48.0, -62.0],
          ],
        ],
      },
    },
  ],
}

// Historical tracks proxy
const HISTORICAL_TRACKS: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { season: '2024-25 NCPOR Expedition' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [18.42, -33.93],
          [30.0, -48.0],
          [42.0, -58.0],
          [56.0, -63.0],
          [68.0, -66.0],
          [76.19, -69.41],
        ],
      },
    },
  ],
}

// Surface ocean current and 10m wind stream vectors proxy
const CURRENT_WIND_VECTORS: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { type: 'current', speed: '1.2 kt' },
      geometry: {
        type: 'LineString',
        coordinates: [[30, -52], [36, -53], [42, -55]],
      },
    },
    {
      type: 'Feature',
      properties: { type: 'current', speed: '1.4 kt' },
      geometry: {
        type: 'LineString',
        coordinates: [[50, -58], [56, -60], [62, -61]],
      },
    },
    {
      type: 'Feature',
      properties: { type: 'wind', speed: '18 kt' },
      geometry: {
        type: 'LineString',
        coordinates: [[35, -45], [42, -47], [48, -48]],
      },
    },
    {
      type: 'Feature',
      properties: { type: 'wind', speed: '24 kt' },
      geometry: {
        type: 'LineString',
        coordinates: [[55, -50], [62, -52], [70, -53]],
      },
    },
  ],
}

interface AntarcticMapProps {
  forecastIndex: ForecastHourIndex
  selectedRouteId: string
  onForecastChange: (index: ForecastHourIndex) => void
  onRouteSelect: (routeId: string) => void
}

export default function AntarcticMap({
  forecastIndex,
  selectedRouteId,
  onForecastChange,
  onRouteSelect,
}: AntarcticMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  // Track route label markers for cleanup on re-render
  const routeMarkersRef = useRef<maplibregl.Marker[]>([])

  const [mapLoaded, setMapLoaded] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)

  const { routeState } = useVoyageSession()

  // Sync route selection visual emphasis (dominant selected route)
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return

    const routes = ['recommended', 'alternative1', 'higher-risk']
    routes.forEach((id) => {
      const isSelected = selectedRouteId === id
      try {
        if (map.getLayer(`route-${id}-layer`)) {
          map.setPaintProperty(`route-${id}-layer`, 'line-opacity', isSelected ? 1.0 : 0.65)
          map.setPaintProperty(`route-${id}-layer`, 'line-width', isSelected ? 5.5 : 3.5)
        }
        if (map.getLayer(`route-${id}-casing`)) {
          map.setPaintProperty(`route-${id}-casing`, 'line-opacity', isSelected ? 0.9 : 0.45)
          map.setPaintProperty(`route-${id}-casing`, 'line-width', isSelected ? 9.5 : 6.0)
        }
      } catch {
        // layer not yet available
      }
    })
  }, [selectedRouteId, mapLoaded])

  // ── Phase 10: Update map sources when backend route generation completes ──
  // This replaces stale DEMO_ROUTES geometry with the actual pipeline output.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapLoaded) return
    if (routeState.status !== 'success' || !routeState.data) return

    const apiRoutes = routeState.data.routes

    // Route specs that match the map source IDs
    const routeSpecs = [
      { id: 'recommended', color: '#16a34a', casingColor: '#dcfce7', dashArray: undefined as number[] | undefined },
      { id: 'alternative1', color: '#d97706', casingColor: '#fef3c7', dashArray: [5, 4] as number[] },
      { id: 'higher-risk', color: '#dc2626', casingColor: '#fee2e2', dashArray: [6, 3] as number[] },
    ]

    // Remove all existing route label markers before recreating
    routeMarkersRef.current.forEach((m) => m.remove())
    routeMarkersRef.current = []

    routeSpecs.forEach((spec) => {
      const source = map.getSource(`route-${spec.id}`) as maplibregl.GeoJSONSource | undefined
      if (!source) return

      const apiRoute = apiRoutes.find((r) => r.route_id === spec.id)

      // If no route or not distinct or empty points: clear the source line
      if (!apiRoute || !apiRoute.is_distinct || apiRoute.points.length === 0) {
        source.setData({ type: 'FeatureCollection', features: [] })
        return
      }

      // Build separate features for approach/arrival (dimmed) and pipeline (full)
      const approachCoords = apiRoute.points
        .filter((p) => p.segment === 'approach' || p.segment === 'arrival')
        .map((p) => [p.lon, p.lat])
      const pipelineCoords = apiRoute.points
        .filter((p) => p.segment === 'pipeline')
        .map((p) => [p.lon, p.lat])

      // Full route for the source (all segments)
      const allCoords = apiRoute.points.map((p) => [p.lon, p.lat])
      source.setData({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            properties: { id: spec.id, segment: 'full' },
            geometry: { type: 'LineString', coordinates: allCoords },
          },
        ],
      })

      // Style pipeline segment (solid, full opacity)
      // We can't do per-point styling with a single LineString source easily,
      // so we visually differentiate by updating paint: approach opacity is lower.
      // The source already contains the full path; the distinct approach/pipeline
      // visual difference is achieved by an additional dashed overlay source.
      const approachSourceId = `route-${spec.id}-approach`
      if (approachCoords.length > 0) {
        const existingApproach = map.getSource(approachSourceId) as maplibregl.GeoJSONSource | undefined
        const approachGeoJSON = {
          type: 'FeatureCollection' as const,
          features: approachCoords.length > 1 ? [{
            type: 'Feature' as const,
            properties: {},
            geometry: { type: 'LineString' as const, coordinates: approachCoords },
          }] : [],
        }
        if (existingApproach) {
          existingApproach.setData(approachGeoJSON)
        } else {
          map.addSource(approachSourceId, { type: 'geojson', data: approachGeoJSON })
          // Dashed dim overlay for approach/arrival
          map.addLayer({
            id: `route-${spec.id}-approach-layer`,
            type: 'line',
            source: approachSourceId,
            paint: {
              'line-color': spec.color,
              'line-width': 2.0,
              'line-opacity': 0.35,
              'line-dasharray': [4, 4],
            },
          })
        }
      }

      // Add label marker at pipeline midpoint
      if (pipelineCoords.length > 0) {
        const midCoord = pipelineCoords[Math.floor(pipelineCoords.length / 2)]
        const pill = document.createElement('div')
        pill.className = styles.routeLabelPill
        pill.style.borderColor = spec.color
        pill.style.backgroundColor = spec.color
        pill.style.color = '#ffffff'
        pill.textContent = apiRoute.name
        pill.onclick = () => onRouteSelect(spec.id)
        const marker = new maplibregl.Marker({ element: pill, anchor: 'bottom' })
          .setLngLat(midCoord as [number, number])
          .addTo(map)
        routeMarkersRef.current.push(marker)
      }
    })
  }, [routeState, mapLoaded, onRouteSelect])

  // Build iceberg uncertainty cone GeoJSON
  function buildIcebergGeoJSON(state: ForecastState) {
    const cones90: FeatureCollection = { type: 'FeatureCollection', features: [] }
    const cones50: FeatureCollection = { type: 'FeatureCollection', features: [] }

    for (const ib of state.icebergs) {
      if (!ib.cone90 || !ib.cone50) continue

      cones90.features.push({
        type: 'Feature',
        properties: { iceberg: ib.name },
        geometry: { type: 'Polygon', coordinates: ib.cone90 },
      })

      cones50.features.push({
        type: 'Feature',
        properties: { iceberg: ib.name },
        geometry: { type: 'Polygon', coordinates: ib.cone50 },
      })
    }
    return { cones90, cones50 }
  }

  // Initialize MapLibre
  useEffect(() => {
    if (!containerRef.current) return

    const innerContainer = document.createElement('div')
    innerContainer.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;'
    innerContainer.setAttribute('role', 'presentation')
    containerRef.current.appendChild(innerContainer)

    const map = new maplibregl.Map({
      container: innerContainer,
      style: HIMDRISHTI_STYLE,
      center: MAP_CENTER,
      zoom: MAP_ZOOM,
      minZoom: 2,
      maxZoom: 10,
      attributionControl: false,
    })

    mapRef.current = map
    let destroyed = false

    const onLoad = () => {
      if (destroyed) return
      if ((map as any)._himdrishtiInitialized) return
      ;(map as any)._himdrishtiInitialized = true

      map.resize()
      map.fitBounds(VOYAGE_BOUNDS, { padding: VOYAGE_FIT_PADDING, duration: 0 })

      // 1. Sea-Ice Layer
      map.addSource('sea-ice', { type: 'geojson', data: SEA_ICE_POLYGON as any })
      map.addLayer({
        id: 'sea-ice-fill',
        type: 'fill',
        source: 'sea-ice',
        paint: { 'fill-color': '#e0f2fe', 'fill-opacity': 0.22 },
      })
      map.addLayer({
        id: 'sea-ice-outline',
        type: 'line',
        source: 'sea-ice',
        paint: { 'line-color': '#bae6fd', 'line-width': 1.5, 'line-opacity': 0.6 },
      })

      // 2. Risk Zones Layer
      map.addSource('risk-zones', { type: 'geojson', data: RISK_ZONE_POLYGON as any })
      map.addLayer({
        id: 'risk-zones-fill',
        type: 'fill',
        source: 'risk-zones',
        paint: { 'fill-color': '#ef4444', 'fill-opacity': 0.12 },
      })
      map.addLayer({
        id: 'risk-zones-outline',
        type: 'line',
        source: 'risk-zones',
        paint: {
          'line-color': '#ef4444',
          'line-width': 1.2,
          'line-dasharray': [4, 3],
          'line-opacity': 0.7,
        },
      })

      // 3. Grid lines
      map.addSource('grid-lines', { type: 'geojson', data: GRID_LINES as any })
      map.addLayer({
        id: 'grid-lines-layer',
        type: 'line',
        source: 'grid-lines',
        paint: {
          'line-color': 'rgba(255,255,255,0.18)',
          'line-width': 0.8,
          'line-dasharray': [3, 3],
        },
      })

      // 4. Historical Tracks
      map.addSource('historical-tracks', { type: 'geojson', data: HISTORICAL_TRACKS as any })
      map.addLayer({
        id: 'historical-tracks-layer',
        type: 'line',
        source: 'historical-tracks',
        layout: { visibility: 'none' },
        paint: {
          'line-color': '#94a3b8',
          'line-width': 2.0,
          'line-dasharray': [4, 4],
          'line-opacity': 0.75,
        },
      })

      // 5. Current & Wind Vectors
      map.addSource('current-wind', { type: 'geojson', data: CURRENT_WIND_VECTORS as any })
      map.addLayer({
        id: 'current-wind-layer',
        type: 'line',
        source: 'current-wind',
        paint: {
          'line-color': '#38bdf8',
          'line-width': 1.6,
          'line-dasharray': [6, 3],
          'line-opacity': 0.75,
        },
      })

      // 6. Routes with casings
      const apiRoutes = routeState.data?.routes
      const routeSpecs = [
        {
          id: 'recommended',
          color: '#16a34a',
          casingColor: '#dcfce7',
          defaultCoords: DEMO_ROUTES[0].coordinates,
          dashArray: undefined as number[] | undefined,
          label: 'Recommended Route',
          labelColor: '#16a34a',
          labelFraction: 0.58,
          anchor: 'bottom' as maplibregl.PositionAnchor,
        },
        {
          id: 'alternative1',
          color: '#d97706',
          casingColor: '#fef3c7',
          defaultCoords: DEMO_ROUTES[1].coordinates,
          dashArray: [5, 4],
          label: 'Alternative Route 1',
          labelColor: '#d97706',
          labelFraction: 0.32,
          anchor: 'top' as maplibregl.PositionAnchor,
        },
        {
          id: 'higher-risk',
          color: '#dc2626',
          casingColor: '#fee2e2',
          defaultCoords: DEMO_ROUTES[2].coordinates,
          dashArray: [6, 3],
          label: 'Higher Risk Route',
          labelColor: '#dc2626',
          labelFraction: 0.52,
          anchor: 'bottom' as maplibregl.PositionAnchor,
        },
      ]

      routeSpecs.forEach((spec) => {
        const matchingApiRoute = apiRoutes?.find((r) => r.route_id === spec.id)
        const coords = matchingApiRoute
          ? matchingApiRoute.points.map((p) => [p.lon, p.lat])
          : spec.defaultCoords

        const geojson: FeatureCollection = {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              properties: { id: spec.id, label: spec.label },
              geometry: { type: 'LineString', coordinates: coords },
            },
          ],
        }

        map.addSource(`route-${spec.id}`, { type: 'geojson', data: geojson })

        // Casing layer for contrast
        map.addLayer({
          id: `route-${spec.id}-casing`,
          type: 'line',
          source: `route-${spec.id}`,
          paint: {
            'line-color': spec.casingColor,
            'line-width': selectedRouteId === spec.id ? 9.5 : 6.0,
            'line-opacity': selectedRouteId === spec.id ? 0.9 : 0.45,
          },
        })

        // Core polyline layer
        const paintProps: any = {
          'line-color': spec.color,
          'line-width': selectedRouteId === spec.id ? 5.5 : 3.5,
          'line-opacity': selectedRouteId === spec.id ? 1.0 : 0.65,
        }
        if (spec.dashArray) {
          paintProps['line-dasharray'] = spec.dashArray
        }

        map.addLayer({
          id: `route-${spec.id}-layer`,
          type: 'line',
          source: `route-${spec.id}`,
          paint: paintProps,
        })

        // Route pill label with staggered non-overlapping position & anchor
        const midIdx = Math.max(0, Math.min(coords.length - 1, Math.floor(coords.length * spec.labelFraction)))
        const midPoint = coords[midIdx]
        if (midPoint) {
          const pill = document.createElement('div')
          pill.className = styles.routeLabelPill
          pill.style.borderColor = spec.color
          pill.style.color = '#ffffff'
          pill.style.backgroundColor = spec.color
          pill.textContent = spec.label
          pill.onclick = () => onRouteSelect(spec.id)
          new maplibregl.Marker({ element: pill, anchor: spec.anchor })
            .setLngLat(midPoint as [number, number])
            .addTo(map)
        }
      })

      // 7. Iceberg Uncertainty Cones
      const { cones90, cones50 } = buildIcebergGeoJSON(FORECAST_STATES[forecastIndex])
      map.addSource('iceberg-cones-90', { type: 'geojson', data: cones90 })
      map.addLayer({
        id: 'iceberg-cones-90-fill',
        type: 'fill',
        source: 'iceberg-cones-90',
        paint: { 'fill-color': '#0284c7', 'fill-opacity': 0.12 },
      })
      map.addLayer({
        id: 'iceberg-cones-90-outline',
        type: 'line',
        source: 'iceberg-cones-90',
        paint: {
          'line-color': '#38bdf8',
          'line-width': 1.0,
          'line-opacity': 0.6,
          'line-dasharray': [3, 2],
        },
      })

      map.addSource('iceberg-cones-50', { type: 'geojson', data: cones50 })
      map.addLayer({
        id: 'iceberg-cones-50-fill',
        type: 'fill',
        source: 'iceberg-cones-50',
        paint: { 'fill-color': '#0284c7', 'fill-opacity': 0.26 },
      })
      map.addLayer({
        id: 'iceberg-cones-50-outline',
        type: 'line',
        source: 'iceberg-cones-50',
        paint: {
          'line-color': '#bae6fd',
          'line-width': 1.2,
          'line-opacity': 0.8,
        },
      })

      // ── HTML Markers ──────────────────────────────────────────────
      // Origin: Cape Town (Red Pin)
      const ctEl = document.createElement('div')
      ctEl.innerHTML = `
        <div style="display:flex;align-items:center;gap:4px;cursor:pointer;">
          <div style="width:14px;height:14px;background:#ef4444;border:2px solid #ffffff;border-radius:50%;box-shadow:0 0 6px rgba(239,68,68,0.8);"></div>
          <div style="background:#0f172a;color:#ffffff;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;white-space:nowrap;box-shadow:0 2px 4px rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.2);">
            Cape Town (South Africa)
          </div>
        </div>
      `
      new maplibregl.Marker({ element: ctEl, anchor: 'left' })
        .setLngLat([18.42, -33.93])
        .addTo(map)

      // Destination: Bharati Station (Green Pin)
      const bhEl = document.createElement('div')
      bhEl.innerHTML = `
        <div style="display:flex;align-items:center;gap:4px;cursor:pointer;">
          <div style="width:14px;height:14px;background:#22c55e;border:2px solid #ffffff;border-radius:50%;box-shadow:0 0 6px rgba(34,197,94,0.8);"></div>
          <div style="background:#0f172a;color:#ffffff;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;white-space:nowrap;box-shadow:0 2px 4px rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.2);">
            Bharati Station (Larsemann Hills)
          </div>
        </div>
      `
      new maplibregl.Marker({ element: bhEl, anchor: 'left' })
        .setLngLat([76.19, -69.41])
        .addTo(map)

      // Vessel Marker
      const vesselEl = document.createElement('div')
      vesselEl.innerHTML = `
        <div style="width:28px;height:28px;border-radius:50%;background:#0f2b48;border:2px solid #ffffff;display:flex;align-items:center;justify-content:center;box-shadow:0 0 8px rgba(0,0,0,0.5);">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.5"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
        </div>
      `
      new maplibregl.Marker({ element: vesselEl, anchor: 'center' })
        .setLngLat(VESSEL_POSITION)
        .addTo(map)

      // Iceberg markers
      for (const ib of FORECAST_STATES[0].icebergs) {
        const ibEl = document.createElement('div')
        ibEl.innerHTML = `
          <div style="width:8px;height:8px;border-radius:50%;background:#38bdf8;border:1.5px solid #ffffff;box-shadow:0 0 4px #38bdf8;"></div>
        `
        new maplibregl.Marker({ element: ibEl, anchor: 'center' })
          .setLngLat(ib.position)
          .addTo(map)

        const ibLabel = document.createElement('div')
        ibLabel.textContent = ib.name
        ibLabel.style.cssText = `color:#bae6fd;font-size:9.5px;font-weight:600;text-shadow:0 1px 2px #000;pointer-events:none;`
        new maplibregl.Marker({ element: ibLabel, anchor: 'bottom-left' })
          .setLngLat([ib.position[0] + 0.6, ib.position[1] + 0.3])
          .addTo(map)
      }

      // Geographic Oceanic labels
      const makeGeoLabel = (text: string, size = '11px', weight = '700') => {
        const el = document.createElement('div')
        el.style.cssText = `color:rgba(255,255,255,0.45);font-size:${size};font-weight:${weight};letter-spacing:2px;text-transform:uppercase;font-style:italic;pointer-events:none;`
        el.textContent = text
        return el
      }

      new maplibregl.Marker({ element: makeGeoLabel('AFRICA', '13px', '800'), anchor: 'center' }).setLngLat([25.0, -31.0]).addTo(map)
      new maplibregl.Marker({ element: makeGeoLabel('Indian Ocean', '14px', '700'), anchor: 'center' }).setLngLat([56.0, -48.0]).addTo(map)
      new maplibregl.Marker({ element: makeGeoLabel('Southern Ocean', '13px', '700'), anchor: 'center' }).setLngLat([32.0, -56.0]).addTo(map)
      new maplibregl.Marker({ element: makeGeoLabel('Kerguelen Islands', '9.5px', '600'), anchor: 'center' }).setLngLat([70.0, -49.0]).addTo(map)
      new maplibregl.Marker({ element: makeGeoLabel('Prince Edward Islands', '9px', '600'), anchor: 'center' }).setLngLat([38.0, -46.5]).addTo(map)
      new maplibregl.Marker({ element: makeGeoLabel('ANTARCTICA', '18px', '900'), anchor: 'center' }).setLngLat([50.0, -71.5]).addTo(map)

      setMapLoaded(true)
    }

    if (map.isStyleLoaded()) {
      setTimeout(onLoad, 0)
    } else {
      map.once('load', onLoad)
    }

    return () => {
      destroyed = true
      map.remove()
      mapRef.current = null
      setMapLoaded(false)
      innerContainer.remove()
    }
  }, []) // initialize once with OpenFreeMap vector style

  // Update iceberg cones on forecast hour scrub
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return
    const { cones90, cones50 } = buildIcebergGeoJSON(FORECAST_STATES[forecastIndex])
    ;(mapRef.current.getSource('iceberg-cones-90') as maplibregl.GeoJSONSource)?.setData(cones90)
    ;(mapRef.current.getSource('iceberg-cones-50') as maplibregl.GeoJSONSource)?.setData(cones50)
  }, [forecastIndex, mapLoaded])

  return (
    <div className={styles.centerContainer}>
      {/* ── Map Section Title Bar (No Sub-Tabs) ───────────── */}
      <div className={styles.mapHeaderBar}>
        <h2 className={styles.mapSectionTitle}>Antarctic Map &amp; Routing Overview</h2>

        {/* Right side: Fullscreen */}
        <div className={styles.mapActions}>
          <button
            type="button"
            className={styles.fullscreenBtn}
            title="Toggle fullscreen"
            aria-label="Toggle fullscreen map"
            onClick={() => {
              if (document.fullscreenElement) {
                document.exitFullscreen()
              } else {
                containerRef.current?.requestFullscreen?.()
              }
            }}
          >
            <Maximize2 size={13} />
          </button>
        </div>
      </div>

      {/* ── Map Canvas Wrapper ────────────────────────────── */}
      <div className={styles.mapCanvasWrapper} ref={containerRef}>
        {!mapLoaded && (
          <div className={styles.loadingOverlay} aria-busy="true">
            <div className={styles.spinner} />
            <span>Loading Antarctic Navigation Model…</span>
          </div>
        )}

        {/* Overlaid Navigation Toolbar (left) */}
        {mapLoaded && (
          <MapControls
            mapRef={mapRef}
            onToggleLayers={() => {}}
          />
        )}

        {/* Small Legend Control (top-right) */}
        {mapLoaded && <MapLegend />}

        {/* Scale Bar (bottom-left) */}
        <div className={styles.scaleBar}>
          <div className={styles.scaleTicks}>
            <span>0</span>
            <span>500</span>
            <span>1,000</span>
            <span>1,500</span>
            <span>2,000 km</span>
          </div>
          <div className={styles.scaleLine} />
        </div>
      </div>

      {/* ── Forecast Timeline (hours) ─────────────────────── */}
      <div className={styles.timelineContainer}>
        <ForecastTimeline
          forecastIndex={forecastIndex}
          isPlaying={isPlaying}
          onForecastChange={onForecastChange}
          onPlayingChange={setIsPlaying}
        />
      </div>
    </div>
  )
}
