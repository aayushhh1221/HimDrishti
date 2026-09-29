# HimDrishti — Map Implementation Rules

## Authority Order
1. Existing validated HimDrishti repository
2. `map.md`
3. `design.md`
4. Approved reference UI/screenshots
5. Astra 6 implementation plan

## Mandatory Preservation
Do not change:
- backend APIs
- scientific routing
- iceberg drift calculations
- POLARIS/RIO
- risk calculations
- route metrics
- provenance/audit logic
- Captain/Master decision logic

Do not modify `ai/*.py` for a visual map task.

## Map Stack
- MapLibre GL JS
- OpenFreeMap vector basemap
- existing HimDrishti GeoJSON/HTML overlays

Keep Web Mercator for this scope.

## Primary Scenario
Default:
**Cape Town, South Africa → Bharati / Larsemann Hills**

Do not make India → Antarctica the primary route.

## Visual Priority
1. Routes
2. Sea-ice/hazard field
3. Iceberg markers
4. Uncertainty cones
5. Vessel
6. Forecast state
7. Relevant geography

Avoid unnecessary city/road/POI clutter.

## Scope
Prefer the smallest safe set of changes. Focus on existing map components and, only if needed, a local style JSON.

Do not modify unrelated pages.

## Never Do
- no new AI/LLM/RAG/RL
- no new backend service
- no fake map data
- no fake route geometry
- no fake progress
- no invented polar projection
- no whole-project refactor
- no unnecessary dependency upgrades
- no removal of fallback behavior

## Completion
Only one commit after all checks pass.

Required:
```text
pytest tests/ -v --tb=short -q
npm run build
```

Also manually verify desktop and narrow/mobile map behavior.
Hard stop after the map task.
