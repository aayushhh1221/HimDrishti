# HimDrishti — Phase 1 Project Audit

**Date:** 2026-08-30  
**Auditor:** Antigravity (Claude Sonnet 4.6 Thinking)  
**SIH Problem Statement:** PS 26059  
**Audit scope:** Complete repository inspection before any Phase 2 work begins

---

## Audit Confirmation

> I have read `design.md` completely (1,772 lines, 38,499 bytes).
> I have inspected `reference-ui.png` (1,758,662 bytes — full-resolution annotated screenshot of the target UI).
> No project files were modified, created, or deleted during this audit.

---

## A. Current Repository Structure

```
d:\HimDrishti\
├── design.md            (38,499 bytes — 1,772 lines — visual + UX source of truth)
└── reference-ui.png     (1,758,662 bytes — high-resolution target UI reference screenshot)
```

**Total files:** 2  
**Total directories:** 1 (root only — docs/ created by this audit)  
**Git repository:** NOT initialised  
**Hidden files/dirs:** None found  
**Node modules:** None  
**Python environment:** None  

The repository is a **clean slate** — it contains only the design specification and the visual reference image. There is no source code of any kind.

---

## B. Existing Frontend

| Property | Status |
|---|---|
| Framework | NONE |
| Entry point | NONE |
| Components | NONE |
| Styling approach | NONE |
| Routing | NONE |
| package.json | NONE |
| node_modules | NONE |
| React | NOT installed |
| TypeScript | NOT installed |
| Vite | NOT installed |

**Verdict:** No frontend exists. Zero frontend files are present.

---

## C. Existing Backend

| Property | Status |
|---|---|
| Framework | NONE |
| Entry point | NONE |
| API endpoints | NONE |
| requirements.txt | NONE |
| pyproject.toml | NONE |
| FastAPI | NOT installed |
| Uvicorn | NOT installed |

**Verdict:** No backend exists. Zero backend files are present.

---

## D. Existing Scientific Engine

### D.1 Iceberg Drift Module
- `ai/iceberg_drift.py` — DOES NOT EXIST

### D.2 POLARIS Risk Module
- `ai/polaris_risk.py` — DOES NOT EXIST

### D.3 Route Search Module
- `ai/route_search.py` — DOES NOT EXIST

### D.4 Demo Runner
- `demo/demo_run.py` — DOES NOT EXIST

**Verdict:** No scientific engine exists. The entire `ai/` and `demo/` directories are absent. There are no Python files of any kind.

---

## E. Existing Tests

| Test type | Status |
|---|---|
| Unit tests | NONE |
| Integration tests | NONE |
| End-to-end tests | NONE |
| Test runner config | NONE |
| pytest | NOT installed |
| vitest / jest | NOT installed |

**Demo run result:** Cannot run — demo does not exist.
**Test run result:** Cannot run — no tests exist.

---

## F. Missing Pieces Required by design.md

### F.1 Project Foundation
| Item | Status |
|---|---|
| Git repository | MISSING |
| .gitignore | MISSING |
| README.md | MISSING |

### F.2 Frontend Infrastructure (design.md section 1, 34, 41)
| Item | Status |
|---|---|
| React + TypeScript + Vite project | MISSING |
| package.json | MISSING |
| vite.config.ts | MISSING |
| tsconfig.json | MISSING |
| index.html | MISSING |
| src/main.tsx | MISSING |
| src/App.tsx | MISSING |

### F.3 Design System (design.md section 33)
| Item | Required path | Status |
|---|---|---|
| Design tokens | frontend/src/design-system/tokens.ts | MISSING |
| Typography tokens | frontend/src/design-system/typography.ts | MISSING |
| Accessibility utilities | frontend/src/design-system/accessibility.ts | MISSING |
| Global CSS | frontend/src/index.css | MISSING |
| Noto Sans font integration | design.md section 7 | MISSING |

### F.4 Government Components (design.md sections 9, 34)
| Component | Status |
|---|---|
| GovernmentUtilityBar | MISSING |
| InstitutionalHeader | MISSING |
| PrototypeBadge | MISSING |

### F.5 Navigation Components (design.md sections 9.4, 34)
| Component | Status |
|---|---|
| MainNavigation | MISSING |
| Breadcrumbs | MISSING |

### F.6 Map Components (design.md sections 11, 12, 34)
| Component | Status |
|---|---|
| HazardMap | MISSING |
| IceLayer | MISSING |
| IcebergCone | MISSING |
| VesselMarker | MISSING |
| RouteLayer | MISSING |

### F.7 Route Components (design.md sections 13, 14, 15, 34)
| Component | Status |
|---|---|
| RouteSummary | MISSING |
| RoutePreferenceSlider | MISSING |
| RouteAlternatives | MISSING |
| CaptainDecisionPanel | MISSING |

### F.8 Risk Components (design.md sections 17, 34)
| Component | Status |
|---|---|
| PolarisRIO | MISSING |
| RiskBadge | MISSING |
| RiskBreakdown | MISSING |

### F.9 Provenance Components (design.md sections 18, 19, 30, 34)
| Component | Status |
|---|---|
| DataFreshness | MISSING |
| SourceStatusTable | MISSING |
| ContradictionAlert | MISSING |

### F.10 Common Components (design.md sections 21, 22, 23, 29, 34)
| Component | Status |
|---|---|
| Button | MISSING |
| Badge | MISSING |
| Alert | MISSING |
| DataTable | MISSING |
| Skeleton | MISSING |

### F.11 Pages (design.md sections 34, 35)
| Page | Priority | Status |
|---|---|---|
| Home.tsx | P0 | MISSING |
| RoutePlanner.tsx | P0 | MISSING |
| ForecastExplorer.tsx | P1 | MISSING |
| RiskCompliance.tsx | P1 | MISSING |
| Provenance.tsx | P1 | MISSING |
| AuditLog.tsx | P2 | MISSING |

### F.12 Backend (Python + FastAPI)
| Item | Status |
|---|---|
| backend/main.py (FastAPI entry) | MISSING |
| backend/requirements.txt | MISSING |
| Route computation API endpoint | MISSING |
| Iceberg drift API endpoint | MISSING |
| POLARIS risk API endpoint | MISSING |
| Data provenance API endpoint | MISSING |
| CORS configuration | MISSING |

### F.13 Scientific Engine
| Module | Status |
|---|---|
| ai/iceberg_drift.py | MISSING |
| ai/polaris_risk.py | MISSING |
| ai/route_search.py | MISSING |
| demo/demo_run.py | MISSING |

### F.14 Tests
| Test suite | Status |
|---|---|
| Frontend unit tests | MISSING |
| Backend unit tests | MISSING |
| Scientific module tests | MISSING |
| Integration tests | MISSING |

---

## G. Recommended Implementation Order

### Stage 0 — Project Scaffolding (blocks everything else)
1. Initialise git repository
2. Create .gitignore
3. Scaffold React + TypeScript + Vite frontend (frontend/)
4. Scaffold Python + FastAPI backend (backend/)
5. Create README.md

### Stage 1 — Design System (blocks all components)
6. Install Noto Sans via fontsource npm package (self-hosted)
7. Create tokens.ts with all colour, spacing, radius, typography tokens from design.md section 33
8. Create typography.ts
9. Create accessibility.ts (skip-to-content, font-size control, reduced-motion)
10. Create index.css with CSS custom properties from design tokens

### Stage 2 — P0 Government Shell (visual priority, blocks all pages)
11. GovernmentUtilityBar — navy bar, flag, A-/A/A+ controls, accessibility icon, language selector
12. InstitutionalHeader — MoES logo, HimDrishti wordmark, NCPOR logo, SIH prototype badge
13. PrototypeBadge — "SIH 2026 Prototype · PS 26059"
14. MainNavigation — Route Planner / Forecast Explorer / Risk & Compliance / Data Provenance / Audit Log / About
15. Status row — Voyage, Vessel, Ice Class, Data freshness, System status

### Stage 3 — P0 Map (visual centrepiece)
16. HazardMap — MapLibre GL JS base, Antarctic projection, muted base layer
17. IceLayer — sea-ice concentration heat layer
18. IcebergCone — position + trajectory + 50%/90% uncertainty cone
19. VesselMarker — vessel icon with heading
20. RouteLayer — solid teal (recommended), dashed navy/amber (alternative), red overlay (unsafe)
21. Forecast time slider (play/pause, 0-120h)

### Stage 4 — P0 Right Panel
22. RouteSummary — ETA, Fuel, POLARIS RIO, Risk level
23. RouteAlternatives — 3-route comparison cards (Recommended / Alternative 1 / Higher Risk)
24. RoutePreferenceSlider — LOW RISK to FAST with live updates

### Stage 5 — P0 Bottom Row
25. PolarisRIO — gauge, RIO value, risk category, sub-scores
26. CaptainDecisionPanel — Accept / Modify / Reject, decision authority label
27. DataFreshness — per-source freshness badges
28. Alert component — Key Alerts (iceberg proximity, ice zone, forecast confidence)

### Stage 6 — Scientific Engine (Python)
29. ai/iceberg_drift.py — physics-based + ML-correction drift model
30. ai/polaris_risk.py — POLARIS RIO calculation per route segment
31. ai/route_search.py — multi-objective route optimisation (time/fuel/risk)
32. demo/demo_run.py — standalone demo that exercises all three modules

### Stage 7 — Backend API
33. FastAPI application with CORS
34. /api/routes — route generation endpoint
35. /api/icebergs — iceberg state + forecast endpoint
36. /api/risk — POLARIS assessment endpoint
37. /api/provenance — data source status endpoint

### Stage 8 — P1 Pages
38. ForecastExplorer — timeline map, layer toggles, Physics / Physics+ML switch
39. RiskCompliance — POLARIS table, vessel ice class selector, regulatory references
40. Provenance — data source table, freshness badges, contradiction alerts, confidence score

### Stage 9 — P2 Pages + Common Components
41. AuditLog — decision timeline, role-based read-only view
42. Common: Badge, DataTable, Skeleton, ContradictionAlert, SourceStatusTable
43. Responsive layout (tablet/mobile stacking)
44. Dark mode (optional)

### Stage 10 — Tests
45. Vitest unit tests for frontend components
46. pytest unit tests for ai/ modules
47. Integration tests for backend API endpoints

---

## H. Conflicts Between Existing Code and design.md

Since there is no existing code, there are no code conflicts. The following are structural tensions within the specification:

### H.1 Layout path naming (Medium severity)
design.md section 34 specifies components under `frontend/src/` implying the Vite project root should be `frontend/`, not the repository root. Must be locked before scaffolding. Recommendation: use `frontend/` as the Vite project root, `backend/` as the FastAPI root.

### H.2 Map library not specified (Medium severity)
design.md section 11 describes a detailed map with Antarctic projection, sea-ice heat layers, iceberg cones, and route lines but does not name the mapping library. Options: Leaflet + react-leaflet, MapLibre GL JS, Deck.gl. Recommendation: MapLibre GL JS for Antarctic projections and scientific overlays.

### H.3 POLARIS RIO gauge not described in text (Low severity)
design.md section 17 describes a POLARIS RIO table but the reference-ui.png shows a colour-arc gauge (value 18/100, "LOW RISK") with 4 sub-scores that is not described in the text specification. The reference image must be treated as authoritative for gauge design.

### H.4 Font loading strategy not specified (Low severity)
design.md section 7 specifies Noto Sans but does not state whether to use Google Fonts CDN or self-hosted. Ship-based navigation console should not require internet. Recommendation: self-host via fontsource npm package.

### H.5 Backend language confirmed only by AI module filenames (Low severity)
design.md states "React + TypeScript" for frontend. The Python `.py` extension of the four scientific modules implies Python + FastAPI for the backend, but design.md does not explicitly state the backend language. The audit prompt specifies FastAPI, confirming Python.

### H.6 Reference UI shows satellite imagery vs design.md text preference (Low severity)
The reference-ui.png shows an Antarctic satellite imagery basemap. design.md section 11 says "no visually noisy satellite imagery by default." Mild conflict. Resolution: use reference-ui.png as visual authority; satellite imagery is acceptable for SIH demo.

---

## Summary Report

### 1. What Was Inspected
| Item | Result |
|---|---|
| design.md | Read completely (1,772 lines) |
| reference-ui.png | Inspected (full annotated UI screenshot) |
| Repository file tree | Complete — only 2 files exist |
| Hidden files/directories | Checked — none |
| Git history | Checked — not a git repo |
| ai/iceberg_drift.py | Checked — does not exist |
| ai/polaris_risk.py | Checked — does not exist |
| ai/route_search.py | Checked — does not exist |
| demo/demo_run.py | Checked — does not exist |
| React/Vite frontend | Checked — does not exist |
| Python/FastAPI backend | Checked — does not exist |
| Tests | Checked — do not exist |

### 2. Current Project Structure
Only two files. The project is a blank canvas with a complete design specification and reference UI.

### 3. Existing Technologies
None installed. No runtime, no package manager locks, no virtual environments.

### 4. Existing Scientific Modules
None. All four required scientific Python files are absent.

### 5. Existing Tests
None. No test files, no test runners, no test configuration.

### 6. Demo Result
Cannot run. demo/demo_run.py does not exist. Nothing to execute.

### 7. Missing Pieces (Summary)
- Git repository
- React + TypeScript + Vite frontend (complete — 30+ components, 6 pages)
- Python + FastAPI backend (complete — 4+ endpoints)
- All 4 scientific Python modules
- Design token system
- All tests

### 8. Problems Found
| Problem | Severity | Notes |
|---|---|---|
| No git repository | Medium | Cannot track changes, no rollback |
| No .gitignore | Low | Will pollute repo on first install |
| Map library undecided | Medium | Must be chosen before map components |
| Font strategy undecided | Low | Self-host recommended for ship context |
| Layout root path ambiguity | Medium | Must be locked before scaffolding |
| Reference UI shows satellite imagery vs design.md muted map preference | Low | Use reference-ui.png as authority |
| No Python virtual environment | Low | Needed before backend/AI work |

### 9. Files Changed or Created During This Audit
| Action | File |
|---|---|
| Created | d:\HimDrishti\docs\PROJECT_AUDIT.md |
| Not modified | d:\HimDrishti\design.md |
| Not modified | d:\HimDrishti\reference-ui.png |

No source code was written, modified, or deleted.

---

**Audit complete. Phase 1 finished. Awaiting user approval to proceed to Phase 2.**
