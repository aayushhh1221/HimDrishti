# Map Research: OpenFreeMap + MapLibre GL JS for HimDrishti

> **Research-only document** — no code changes were made.
> Date: 2026-09-24 · SIH 2026 · PS 26059

---

## 1. Current Implementation Audit

### 1.1 Rendering Library
- **MapLibre GL JS v4.7.1** — already installed as a production dependency (`maplibre-gl` in `package.json`).
- CSS imported globally in `main.tsx` (`maplibre-gl/dist/maplibre-gl.css`).

### 1.2 Tile Source (Current)
The map uses **OSM raster tiles** via an inline `StyleSpecification` object defined in `AntarcticMap.tsx` (lines 44–74):

```ts
const MAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    'osm-raster': {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
      maxzoom: 19,
    },
  },
  layers: [
    { id: 'ocean-background', type: 'background', paint: { 'background-color': '#0d2137' } },
    { id: 'osm-tiles', type: 'raster', source: 'osm-raster', paint: { 'raster-opacity': 0.45 } },
  ],
}
```

**Key observation:** The basemap is a dark navy `background` layer with OSM raster tiles at 45% opacity blended on top. This creates the muted, dark-ocean aesthetic specified in `design.md` §11 ("muted Antarctic map, minimal labels, no visually noisy satellite imagery").

### 1.3 Overlay Layers (all GeoJSON, dynamically added after `map.on('load')`)
| Layer ID | Type | Source | Purpose |
|---|---|---|---|
| `sea-ice-fill` / `sea-ice-outline` | fill / line | `sea-ice` (GeoJSON) | Sea ice extent polygon |
| `grid-lines-layer` | line | `grid-lines` (GeoJSON) | Latitude/longitude reference grid |
| `route-{id}-casing` / `route-{id}-layer` | line | `route-{id}` (GeoJSON) | 3 voyage routes with casings |
| `iceberg-cones-90-*` / `iceberg-cones-50-*` | fill / line | `iceberg-cones-*` (GeoJSON) | Iceberg uncertainty cones |

### 1.4 HTML Markers (above WebGL layers)
- Vessel position marker (custom SVG)
- Iceberg position dots + name labels
- Route name pills (Recommended, Alternative, Higher Risk)
- "Indian Ocean" label

### 1.5 Map Interactions
- `MapControls.tsx`: zoom in/out, layer toggle, reset view (`flyTo`), fullscreen
- `ForecastTimeline.tsx`: play/pause animation, range slider, dynamic GeoJSON update via `setData()` on iceberg cone sources
- No click-on-route selection (routes are visual only; selection happens via RouteComparisonPanel)

### 1.6 Known Issues with Current OSM Raster Setup
1. **Rate limiting risk**: `tile.openstreetmap.org` has a strict usage policy — no API key, but requires valid User-Agent, caching, and prohibits bulk downloading. Development iteration can trigger throttling.
2. **Raster tiles are visually noisy at Southern Ocean latitudes** — OSM land/label detail is irrelevant for Antarctic waters, yet the tiles still load and render at 45% opacity, adding visual clutter.
3. **256px raster tiles are blurry on HiDPI/Retina displays** — no `@2x` variant available from `tile.openstreetmap.org`.
4. **No styling control** — raster tiles are pre-rendered PNGs. You cannot filter labels, change colors, or hide land detail without the opacity hack.
5. **Performance** — raster tiles are larger payloads than vector tiles for equivalent coverage, and each zoom/pan requires new image downloads.

---

## 2. OpenFreeMap + MapLibre: What Is It?

**OpenFreeMap** is an open-source, free-to-use **vector tile hosting service** that serves OpenStreetMap-derived vector tiles in the MapLibre style specification format.

| Property | Value |
|---|---|
| Tile format | **Vector tiles** (MVT / Protobuf) |
| Schema | OpenMapTiles |
| Style URL format | `https://tiles.openfreemap.org/styles/{style_name}` |
| Available styles | `liberty`, `bright`, `positron`, `dark`, `fiord` |
| API key | **Not required** |
| Rate limits | **None stated** — no registration, no user database |
| Cost | **Free** (donation-funded) |
| License | MIT (code), ODbL (OSM data) |
| MapLibre compatible | **Yes** — designed specifically for MapLibre GL JS |
| Self-hostable | Yes (Btrfs + nginx) |

---

## 3. Compatibility Analysis

### 3.1 MapLibre GL JS — ✅ Fully Compatible

OpenFreeMap is explicitly designed for MapLibre GL JS. The current project already uses `maplibre-gl@^4.7.1`. The switch would change **only the `style` parameter** passed to `new maplibregl.Map()`.

**Current:**
```ts
const map = new maplibregl.Map({
  container: innerContainer,
  style: MAP_STYLE,  // ← inline StyleSpecification with OSM raster source
  ...
})
```

**After switch (conceptual):**
```ts
const map = new maplibregl.Map({
  container: innerContainer,
  style: 'https://tiles.openfreemap.org/styles/dark',  // ← vector tile style URL
  ...
})
```

### 3.2 GeoJSON Overlays — ✅ Fully Compatible

All HimDrishti overlay layers (sea ice, grid lines, routes, iceberg cones) use MapLibre's `map.addSource()` and `map.addLayer()` with `type: 'geojson'`. These are **completely independent of the basemap tile source**. GeoJSON overlay layers coexist with vector tile basemaps exactly as they do with raster basemaps.

**No changes needed to any of these functions:**
- `addSeaIceLayer()` — ✅ works unchanged
- `addGridLines()` — ✅ works unchanged
- `addRoutes()` — ✅ works unchanged
- `addIcebergCones()` — ✅ works unchanged
- `updateIcebergSources()` — ✅ works unchanged

### 3.3 HTML Markers — ✅ Fully Compatible

`maplibregl.Marker` with custom HTML elements works identically regardless of basemap type. These are DOM elements positioned above the WebGL canvas.

### 3.4 MapControls — ✅ Fully Compatible

`zoomIn()`, `zoomOut()`, `flyTo()`, `getContainer()`, `resize()`, `setCenter()`, `setZoom()` — all are MapLibre Map instance methods, unrelated to tile source.

### 3.5 ForecastTimeline — ✅ Fully Compatible

The timeline controls `forecastIndex` state, which triggers `updateIcebergSources()` to call `setData()` on GeoJSON sources. No basemap dependency.

### 3.6 API Contracts — ✅ No Impact

The map component consumes frontend-only demo data (`demoRoutes.ts`, `demoForecastStates.ts`) and does not interact with the FastAPI backend. The tile source change has zero impact on `/api/v1/*` endpoints.

### 3.7 Vite Proxy — ✅ No Impact

The Vite dev server proxies `/api` to `http://localhost:8000`. Map tile requests go directly to `tile.openstreetmap.org` (current) or `tiles.openfreemap.org` (proposed) — neither passes through the proxy.

### 3.8 Build Pipeline — ✅ No Impact

`npm run build` compiles TypeScript and bundles with Vite. A tile URL string change has no TypeScript or build implications. No new dependencies needed.

### 3.9 Test Suite — ✅ No Impact

All 317 pytest tests are backend/pipeline tests using `TestClient`. No test references the tile URL. The frontend `npm run build` would still pass.

---

## 4. Potential Concerns and Mitigations

### 4.1 ⚠️ Layer Draw Order with Vector Basemap

**Concern:** The current inline `StyleSpecification` has exactly 2 layers (`ocean-background`, `osm-tiles`). All GeoJSON overlays are added after `map.on('load')` and naturally stack on top. With a vector tile style (e.g., `dark`), the basemap brings **many built-in layers** (water, land, roads, labels, etc.). Your overlays added via `addLayer()` would default to being drawn on top of *all* basemap layers, which is the desired behavior for routes and markers. However, if you ever need overlays *between* basemap layers (e.g., below labels but above water), you'd use `map.addLayer(layer, beforeId)`.

**Verdict:** For HimDrishti's current architecture, overlays on top of basemap is correct. **No issue.**

### 4.2 ⚠️ Dark Background Aesthetic

**Concern:** The current setup uses a manual `#0d2137` dark navy background with OSM tiles at 45% opacity. OpenFreeMap's `dark` style has its own dark color scheme that may not exactly match `#0d2137`.

**Mitigation:** Two approaches:
1. Use the `dark` or `fiord` style as-is (close to desired aesthetic).
2. Use a hybrid approach: keep the inline `StyleSpecification` with `#0d2137` background, but replace the `osm-raster` source with OpenFreeMap's vector tile source for better quality. This requires constructing a custom style object.

**Verdict:** Requires visual verification but is trivially adjustable. **Low risk.**

### 4.3 ⚠️ Antarctic/Southern Ocean Coverage (Latitude Limits)

**Concern:** Web Mercator (EPSG:3857) clips at ~±85.05° latitude. The project's map viewport is centered at `[58.0, -64.0]` with zoom 3.8, showing routes between ~34°S to ~69°S.

**Verification:** Both the current OSM raster tiles AND OpenFreeMap vector tiles use Web Mercator. The HimDrishti map viewport (34°S–69°S) is **well within** the coverage limit. Routes to Bharati Station (-69.41°S) are covered. The sea ice polygon extends to -80°S, which is also within Mercator limits.

**Verdict:** **No issue.** Neither current nor proposed has a polar limitation for HimDrishti's viewport.

### 4.4 ⚠️ External Network Dependency

**Concern:** Both current and proposed setups require internet access to fetch tiles. OpenFreeMap has no SLA guarantees.

**Mitigation:** For a prototype/demo, this is acceptable. For production, self-hosting OpenFreeMap or using PMTiles would eliminate the dependency. The current OSM setup has the same limitation.

**Verdict:** **Equal risk to current setup.** Actually slightly better because OpenFreeMap has no rate limiting.

### 4.5 ⚠️ Vector Tile Detail at Low Zoom

**Concern:** At zoom 3.8, vector tiles from OpenFreeMap provide coarse geographic detail. However, this is actually a *feature* for HimDrishti — `design.md` §11 specifically requires "muted Antarctic map, minimal labels."

**Verdict:** **Net positive.** Vector tiles at low zoom naturally show less detail, matching the design spec.

### 4.6 ⚠️ Font/Label Consistency

**Concern:** OpenFreeMap styles use Noto Sans for labels (same font HimDrishti uses). Map labels will visually integrate with the app's typography.

**Verdict:** **Net positive.**

---

## 5. What Would Change (Minimal Scope)

If this migration were approved, the changes would be limited to **one constant** in one file:

| File | What Changes |
|---|---|
| `AntarcticMap.tsx` lines 44–74 | Replace inline `MAP_STYLE` raster definition with OpenFreeMap style URL (or custom inline style using OFM vector source) |
| `AntarcticMap.tsx` line 551 | Update attribution text |

**Nothing else changes.** No new dependencies. No new packages. No API changes. No routing changes. No scientific code changes.

---

## 6. What Would NOT Change

- `maplibre-gl` package version — already compatible
- All GeoJSON overlay logic (sea ice, grid, routes, icebergs)
- All HTML markers (vessel, icebergs, labels)
- MapControls, MapLegend, ForecastTimeline components
- RoutePlannerContext, RouteComparisonPanel
- VoyageScenarioPanel
- Backend API endpoints and contracts
- Test suite (317 tests)
- Build pipeline
- Deployment configuration

---

## 7. Recommendation

**Yes, OpenFreeMap + MapLibre is an excellent approach for HimDrishti.** The assessment is:

| Criterion | Current (OSM Raster) | Proposed (OpenFreeMap Vector) |
|---|---|---|
| Visual quality | ⚠️ Blurry at HiDPI, noisy labels | ✅ Crisp at any DPI, clean labels |
| Style control | ❌ None (pre-rendered PNGs) | ✅ Full control (colors, labels, filtering) |
| Dark theme | ⚠️ Hack (45% opacity blend) | ✅ Native `dark` style available |
| Performance | ⚠️ Larger payloads per tile | ✅ Smaller vector payloads |
| Rate limiting | ⚠️ Strict OSM usage policy | ✅ No limits, no API key |
| Cost | Free | Free |
| MapLibre compat | ✅ | ✅ |
| GeoJSON overlays | ✅ No impact | ✅ No impact |
| API/backend | ✅ No impact | ✅ No impact |
| Tests | ✅ No impact | ✅ No impact |
| Breaking risk | — | **Extremely low** |

### Summary

The switch is **safe, beneficial, and minimally invasive**. It changes one constant (the tile source) and improves visual quality, performance, and reliability. All existing overlays, markers, interactions, API contracts, routes, and scientific code remain completely untouched.

---

> **Note:** This document is research and verification only. No code was modified.
