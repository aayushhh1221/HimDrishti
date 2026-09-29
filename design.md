# HimDrishti — SIH 2026 Government-Grade Design System

**Project:** HimDrishti — Antarctic Sea-Ice, Iceberg Trajectory & Navigation Decision Support  
**SIH Problem Statement:** PS 26059  
**Target:** SIH 2026 national-level screening / demo  
**Frontend:** React + TypeScript  
**Primary reference:** UX4G Design System 3.0  
**Compliance/reference:** GIGW 3.0  
**Domain/brand reference:** Ministry of Earth Sciences (MoES) + NCPOR  
**Design direction:** Government-institutional + scientific operations console, NOT a generic SaaS dashboard

---

## 1. Executive Design Decision

Do **not** copy one Indian government website literally.

Build a **hybrid Government-of-India scientific decision-support interface**:

1. **UX4G 3.0** → component behaviour, spacing, accessibility, tokens, forms, alerts, navigation patterns.
2. **GIGW 3.0** → government-style information hierarchy, ownership/context, accessibility, semantic structure, keyboard support, freshness/updated information.
3. **MoES** → institutional/scientific identity cues and restrained government visual language.
4. **NCPOR** → Antarctic/polar-science context.
5. **HimDrishti** → modern operational map/dashboard layer for the actual decision-support workflow.

The final product should feel like:

> **“A Government of India scientific mission-control application modernised for a professional ship/navigation environment.”**

It should NOT feel like:

- a startup landing page
- a crypto dashboard
- a cyber-security dashboard
- a neon AI dashboard
- a generic Tailwind admin template
- a futuristic sci-fi control room
- a fake official Government of India website

---

# 2. Important Authenticity Rule

This is an SIH prototype, not an official Government of India website.

Therefore:

- Do **not** falsely present HimDrishti as an official Government of India service.
- Do not place the State Emblem of India in a way that implies official ownership unless the team has explicit permission and the SIH presentation rules permit it.
- If government/ministry logos are used, treat them as contextual/reference branding and follow SIH and logo-use permissions.
- Add a small but visible label:

**“SIH 2026 Prototype · PS 26059”**

Recommended institutional line:

**“Designed for Antarctic navigation decision support | SIH 2026”**

The interface can look government-grade without impersonating an official government portal.

---

# 3. Visual Positioning

### Desired visual impression

**Institutional 45%**
- government/public-sector seriousness
- restrained navigation
- formal typography
- clear hierarchy
- no excessive rounded cards

**Scientific 25%**
- geospatial layers
- forecast timelines
- uncertainty visualisation
- measurable values
- provenance

**Maritime operations 20%**
- persistent map
- high legibility
- risk state
- route alternatives
- captain decision area

**Modern UI 10%**
- subtle transitions
- clean component states
- responsive layout
- polished interactions

---

# 4. Design References

## Reference A — UX4G Design System 3.0

Use as the **primary UI-system reference**.

Official:
https://www.ux4g.gov.in/

Developer documentation:
https://doc.ux4g.gov.in/

Use it for:

- design tokens
- buttons
- navigation
- badges
- alerts
- tables
- forms
- breadcrumbs
- status states
- accessibility
- responsive behaviour
- component consistency

Do not blindly copy the purple UX4G demo palette. Re-theme the components for HimDrishti.

---

## Reference B — GIGW 3.0

Use as the **government UX/compliance reference**.

Official:
https://guidelines.india.gov.in/

Important principles to implement:

- clear ownership/context
- clear page titles
- semantic heading hierarchy
- strong contrast
- keyboard accessibility
- skip-to-content support
- accessible tables
- colour must not be the only indicator
- visible updated/freshness information
- responsive behaviour
- meaningful alternative text

---

## Reference C — Ministry of Earth Sciences

Use for **institutional/scientific visual cues**, not literal cloning.

Official:
https://moes.gov.in/

Reference characteristics:

- Government of India institutional identity
- ministry name prominently presented
- restrained navigation
- formal content hierarchy
- scientific/public-sector tone
- information-first layout

---

## Reference D — NCPOR

Use for **polar-science context**.

Official:
https://www.ncpor.res.in/

Reference characteristics:

- polar/cryosphere identity
- scientific terminology
- institutional credibility
- Antarctic research context

---

## Reference E — National Portal of India

Use for broad **government information architecture**.

Official:
https://www.india.gov.in/

Useful cues:

- simple search
- clear service/content grouping
- formal information hierarchy
- government identity
- accessible navigation

---

# 5. Final Design System

## 5.1 Colour Philosophy

The interface must be restrained.

### Base colours

```text
INK / PRIMARY
#102A43

DEEP NAVY
#0B1F33

OFF-WHITE
#F7F8FA

SURFACE
#FFFFFF

BORDER
#D9E1E8

MUTED TEXT
#52606D

SECONDARY TEXT
#334E68
```

### Operational accent

```text
TEAL
#287D7A

LIGHT TEAL
#D9F0EE
```

Use teal for:

- active route
- selected state
- operational status
- positive system state
- interactive controls

### Risk colours

Use colour sparingly.

```text
CAUTION / AMBER
#B7791F

DANGER / RED
#B42318

SAFE / GREEN
#18794E
```

Risk colour must ALWAYS be accompanied by:

- label
- icon
- number/value
- text explanation

Never communicate risk using colour alone.

---

# 6. Background & Surface Rules

Avoid:

- black background
- purple gradients
- glassmorphism
- heavy shadows
- neon cyan
- glowing borders
- excessive transparency

Preferred:

- warm/off-white application shell
- white panels
- navy text
- thin neutral borders
- very subtle shadows
- flat scientific map layers

The UI should look good when projected on a large screen during judging.

---

# 7. Typography

Primary font:

**Noto Sans**

Fallback:

```text
system-ui,
-apple-system,
BlinkMacSystemFont,
"Segoe UI",
sans-serif
```

Why:

- highly legible
- government/public-sector feel
- good multilingual support
- suitable for scientific dashboards
- readable at distance

### Type scale

```text
Display: 32px / 40px
H1:      26px / 34px
H2:      21px / 28px
H3:      17px / 24px
Body:    15px / 22px
Small:   13px / 18px
Micro:   11px / 16px
```

Do not use 7–10 different font sizes.

---

# 8. Layout System

Use a 12-column desktop grid.

```text
Max content width: 1440px
Page padding:      24px
Panel gap:         16px
Section gap:       24px
Large section:     32px
```

Primary application layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ Government / SIH Context + Freshness + User Status          │
├──────────────────────────────────────────────────────────────┤
│ HimDrishti Identity     Navigation / Current Module         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                     MAIN APPLICATION                         │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ System status / data provenance / last updated               │
└──────────────────────────────────────────────────────────────┘
```

Do not create a giant marketing hero.

The first screen should immediately show the **decision-support system**.

---

# 9. Header Design — FINAL Government-Style Top Structure

The first viewport MUST include a **Government of India-style utility/accessibility bar** inspired by current Indian government UX patterns.

The screenshot supplied by the team should be treated as the visual reference for the top utility bar:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ 🇮🇳 Government of India ↗     Skip to main content   A−  A  A+  ♿  🌐 English⌄ │
└──────────────────────────────────────────────────────────────────────────────┘
```

This is a **design reference**, not a claim that HimDrishti is an official Government of India service.

## 9.1 Government Utility Bar

Height:

```text
32–40px desktop
```

Background:

```text
Deep institutional navy / near-black navy
#100A2A  (reference direction)
```

Text:

```text
White / high-contrast
```

### Left side

Show:

```text
[Indian flag / approved contextual mark]
Government of India
[external-link icon]
```

The external-link icon must be visually small and accessible.

Do NOT use the Government of India text/logo arrangement in a way that falsely represents HimDrishti as an official government service.

### Right side

Show:

```text
Skip to main content
|
A−
A
A+
|
Accessibility icon
|
Globe icon  English  ▼
```

Required behaviour:

- **Skip to main content** → keyboard focus moves to the primary content region.
- **A−** → decreases application text size within defined limits.
- **A** → restores default text size.
- **A+** → increases application text size within defined limits.
- **Accessibility icon** → opens accessibility controls/help.
- **English ▼** → language selector; architecture must allow future Indian-language localisation.

The controls must be real UI controls, not decorative text.

## 9.2 Accessibility Bar Rules

The utility bar MUST support:

- keyboard navigation
- visible focus states
- semantic buttons/links
- accessible names
- adequate hit targets
- sufficient contrast
- no colour-only meaning
- responsive behaviour

The accessibility controls should remain usable even when text size is increased.

This follows the spirit of GIGW 3.0, which explicitly addresses accessibility, usability and user-centric government web/app experiences, and UX4G 3.0, which documents WCAG 2.1 AA-oriented accessible components.

## 9.3 Prototype / Institutional Identity Header

Immediately below the utility bar:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ [HimDrishti]  HimDrishti                                                     │
│               Antarctic Navigation Decision Support                           │
│               SIH 2026 · PS 26059 · Prototype                                 │
│                                                                              │
│ Route Planner   Forecast Explorer   Risk & Compliance   Provenance           │
└──────────────────────────────────────────────────────────────────────────────┘
```

Recommended height:

```text
64–76px
```

Do not make this look like a marketing hero.

The identity should feel like a serious scientific/public-sector application.

## 9.4 Primary Navigation

Use restrained navigation:

```text
Route Planner | Forecast Explorer | Risk & Compliance | Provenance | Audit Log
```

Active item:

- strong text contrast
- subtle teal indicator
- thin bottom border or underline
- no giant pill

Avoid:

- oversized SaaS sidebar
- floating navigation
- neon active states
- excessive rounded navigation pills

## 9.5 Current-System Status Row

Immediately below navigation, show a compact operational strip:

```text
Voyage: Antarctic Resupply
Vessel: Demo Vessel
Ice Class: Configurable
Data: Fresh · 12 min ago
System: Operational
```

This row can collapse into a compact status bar on smaller screens.

## 9.6 Why This Header Exists

The header should communicate, within seconds:

1. Indian public-sector context
2. SIH 2026 prototype context
3. HimDrishti identity
4. current operational module
5. accessibility
6. data freshness
7. navigation between scientific modules

Do not fill the header with decorative branding.

## 9.7 Mobile Header

On mobile:

```text
Government utility bar
        ↓
HimDrishti identity
        ↓
Current module + menu
        ↓
Data freshness
```

The accessibility controls remain available through the accessible menu.

## 9.8 Official Government UX References

Use these as reference material, not as pages to clone:

- UX4G Design System 3.0 — official Government of India design-system initiative.
- UX4G developer documentation — components, tokens, accessibility and implementation guidance.
- GIGW 3.0 — Government of India website/app quality, accessibility, usability and security guidance.
- Ministry of Earth Sciences — institutional/scientific context.
- NCPOR — Antarctic/polar-science context.

Current official references:

https://www.ux4g.gov.in/
https://doc.ux4g.gov.in/
https://guidelines.india.gov.in/gigw3/
https://moes.gov.in/
https://www.ncpor.res.in/

UX4G 3.0 currently describes itself as the official component library/pattern repository for Government of India initiatives and documents reusable components, design tokens and WCAG 2.1 AA accessibility. GIGW 3.0 is the Government of India's guideline framework for government websites and apps, covering quality, accessibility, cybersecurity and lifecycle management.

# 10. First Page — Route Planner

This is the **hero page** and the most important screen.

The first screen must communicate the entire product in approximately 5 seconds.

## Screen hierarchy

```text
┌──────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
├──────────────────────────────────────────────────────────────┤
│ Voyage: Antarctic Resupply  |  ETA  |  Ice Class | Status   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                    MAP / HAZARD FIELD                        │
│                                                              │
│        iceberg uncertainty cones                             │
│        sea-ice concentration                                 │
│        recommended route                                     │
│        alternative route                                     │
│                                                              │
│                                  ┌─────────────────────────┐ │
│                                  │ ROUTE RECOMMENDATION    │ │
│                                  │                         │ │
│                                  │ Time                    │ │
│                                  │ Fuel                    │ │
│                                  │ Risk / RIO              │ │
│                                  │                         │ │
│                                  │ Why this route?         │ │
│                                  └─────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│ Risk ◄───────────────●──────────────────► Time/Fuel          │
├──────────────────────────────────────────────────────────────┤
│ Fastest | Balanced | Cautious                                │
└──────────────────────────────────────────────────────────────┘
```

---

# 11. Map — The Visual Centrepiece

The map must occupy approximately:

**60–70% of the main workspace.**

Do not make the map a small card.

Map layers:

### Base

- muted Antarctic map
- minimal labels
- no visually noisy satellite imagery by default

### Sea ice

Use a restrained ice-concentration heat layer.

### Icebergs

Show:

- current position
- forecast trajectory
- uncertainty cone
- confidence state

### Vessel

Use a clear vessel icon.

### Routes

Recommended route:

**solid teal line**

Alternative route:

**dashed navy/amber line**

Unsafe/high-risk area:

**transparent red/amber overlay**

---

# 12. Uncertainty Cone

This is a major differentiation feature.

Never show only:

```text
Iceberg → single future point
```

Show:

```text
              . . . . .
          .               .
       .                     .
     .        forecast         .
    .          cone             .
     .                         .
       .                     .
          .               .
              •
         current position
```

The cone should visually widen with forecast horizon.

Add a small legend:

```text
● Current position
→ Expected drift
◌ 50% confidence region
◌ 90% confidence region
```

---

# 13. Risk / Time / Fuel Slider

This is the **killer interaction**.

Label:

**Route Preference**

```text
More Time / Lower Risk
        ◄────────────●────────────►
                              Less Time / Higher Risk
```

Better UI:

```text
Risk tolerance

LOW RISK                                      FAST
●───────────────────────────────○──────────────●
```

As the slider moves:

1. route changes
2. ETA changes
3. fuel changes
4. RIO changes
5. explanation changes

The change must be visibly obvious.

Use a 150–300ms transition.

Do NOT animate the entire dashboard.

---

# 14. Route Recommendation Panel

Use a solid white panel.

Title:

**System Recommendation**

Then:

```text
BALANCED ROUTE

ETA
8h 42m

Fuel
18.6 t

POLARIS RIO
3.2

Risk level
LOW–MODERATE
```

Then:

**Why this route?**

Use deterministic explanation data:

```text
Avoids high-concentration ice corridor
between 04:00–08:00 UTC.

Maintains vessel ice-class constraint.

Reduces expected risk by 21%
versus fastest route.
```

Never let an LLM invent numerical values.

---

# 15. Captain Decision Panel

This MUST be visually separate from the system recommendation.

Heading:

**Captain Decision**

Actions:

```text
[ Accept Route ]

[ Compare Alternatives ]

[ Override ]

[ Review Risk ]
```

Add:

```text
Decision authority:
Captain / Ice Pilot
```

The UI should communicate:

> The system recommends. The captain decides.

This is directly aligned with the solution blueprint.

---

# 16. Forecast Explorer

Purpose:

Inspect forecasts independently of routing.

Layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ Forecast Explorer                                            │
├──────────────────────────────────────────────────────────────┤
│ Time: 12h ───────●────────────────────────────── 72h         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                    FORECAST MAP                              │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ Layers                                                       │
│ ☑ Sea Ice Concentration                                      │
│ ☑ Iceberg Tracks                                             │
│ ☑ Uncertainty Cone                                           │
│ ☐ Physics Only                                               │
│ ☐ Physics + ML Correction                                    │
└──────────────────────────────────────────────────────────────┘
```

---

# 17. Risk & Compliance

This page should feel like a scientific/regulatory inspection screen.

Header:

**Risk & Compliance**

Show:

```text
POLARIS / RIO Assessment

Route Segment     RIO     Category     Status
A → B             2.8     Low          ✓
B → C             3.7     Moderate     !
C → D             5.1     High         !
```

Every value should have:

- source
- timestamp
- calculation explanation

Include:

**Vessel Ice Class**

```text
[ Select Vessel Ice Class ]
```

Include:

**Regulatory Reference**

```text
POLARIS
Polar Code
Operational Limitation Assessment
```

---

# 18. Data & Provenance

This page is important for government/scientific credibility.

Title:

**Data & Provenance**

Show:

```text
SOURCE                    UPDATED        STATUS

Sea Ice / AMSR2           10:30 UTC      Fresh
Sentinel-1 SAR            09:45 UTC      Fresh
Ocean Currents            10:10 UTC      Fresh
Wind Forecast             10:15 UTC      Fresh
Iceberg Track             08:50 UTC      Aging
```

Use badges:

```text
FRESH
AGING
STALE
CONFLICT
```

Also show:

```text
Confidence: 82%

Why?
• Ensemble spread: low
• Satellite age: 42 min
• Source agreement: high
```

This supports the blueprint's reliability layer.

---

# 19. Contradiction Warning

If two sources disagree:

```text
⚠ Data Conflict

AMSR2-derived ice concentration and
recent SAR-derived ice edge differ
beyond the configured threshold.

Affected area:
12.4 km × 18.2 km

Action:
Human review recommended.
```

Do not hide uncertainty.

Government/scientific systems gain credibility by clearly exposing limitations.

---

# 20. Audit Log

Page:

**Decision Audit Log**

Timeline:

```text
10:42  Route computed
10:43  Captain reviewed route
10:44  Risk preference changed
10:44  Alternative route generated
10:45  Route accepted
```

Each event should show:

- timestamp
- user role
- action
- input snapshot
- route version
- risk value

Read-only for auditor role.

---

# 21. Cards

Avoid making everything a card.

Use cards only for:

- key metrics
- warnings
- route summary
- system status
- decision controls

Avoid:

```text
Card inside card inside card
```

Prefer:

```text
section
 ├── heading
 ├── data
 └── actions
```

---

# 22. Tables

Tables should be professional and dense.

Rules:

- sticky header
- clear column labels
- right-align numerical values
- units visible
- row hover
- status badge
- no excessive rounded corners
- no zebra stripes unless needed
- sortable only where useful

Example:

```text
Segment | Distance | Time | Fuel | RIO | Status
-------------------------------------------------
A-B     | 82 km    | 2h   | 4.2t | 2.8 | Safe
B-C     | 95 km    | 2.5h | 5.1t | 3.7 | Caution
C-D     | 74 km    | 1.9h | 3.8t | 5.1 | Review
```

---

# 23. Buttons

Primary:

```text
Accept Route
```

Secondary:

```text
Compare
Review
View Details
```

Destructive/critical:

```text
Override Route
```

Avoid:

```text
Launch AI
Predict Now
Magic Route
Optimize Everything
```

The language must feel professional and operational.

---

# 24. Icons

Use simple line icons.

Recommended:

- Lucide
- Material Symbols
- another accessible SVG icon library

Avoid:

- emoji as UI icons
- 3D icons
- cartoon illustrations
- glossy icon packs

Every icon needs accessible text when it communicates meaning.

---

# 25. Motion

Motion exists only to communicate state.

Allowed:

- route redraw
- slider transition
- loading skeleton
- panel expansion
- map layer transition
- status update

Avoid:

- page entrance animation
- floating cards
- parallax
- glowing effects
- animated gradients
- excessive hover effects

Animation duration:

```text
150–250ms
```

---

# 26. Accessibility

Target:

**WCAG 2.1 AA**

Implement:

- keyboard navigation
- visible focus state
- sufficient contrast
- semantic headings
- aria labels where needed
- accessible tables
- skip-to-content
- non-colour risk indicators
- screen-reader-friendly status updates
- reduced-motion support

Every risk status must be readable without colour.

Example:

Bad:

```text
red dot
```

Good:

```text
● HIGH RISK
```

---

# 27. Responsive Design

Desktop is the primary SIH demo target.

Still support:

### Desktop

1440 × 900

Primary judge/demo layout.

### Laptop

1280 × 720

### Tablet

1024 × 768

### Mobile

Do not try to preserve the desktop map layout.

On mobile:

```text
Header
↓
Voyage status
↓
Map
↓
Route summary
↓
Slider
↓
Decision controls
↓
Details
```

---

# 28. Dark Mode

Dark mode should NOT be the default.

Default:

**Light institutional mode**

Optional dark mode:

- deep navy background
- dark surfaces
- muted teal
- controlled amber/red

Dark mode must preserve contrast.

---

# 29. Empty / Loading / Error States

Every page must have all three.

## Loading

Use skeletons.

Example:

```text
Computing route…
Analysing hazard field…
```

Do not show a generic full-screen spinner.

## Error

Example:

```text
Hazard data temporarily unavailable.

Showing last known good forecast:
10:30 UTC

[ View Provenance ]
```

## Empty

Example:

```text
No voyage selected.

Select a voyage to begin route planning.
```

---

# 30. Data Freshness Indicator

Always visible.

Example:

```text
DATA
Fresh · 12 min ago
```

When stale:

```text
DATA
Stale · 2h 14m ago
```

This should be in the header.

This is a major credibility feature.

---

# 31. Homepage / Entry Screen

Do NOT create a flashy marketing homepage.

Use a concise launch/overview screen:

```text
HIMDRISHTI

Antarctic Sea-Ice, Iceberg Trajectory &
Navigation Decision Support

SIH 2026 · PS 26059

[ Open Route Planner ]

-------------------------------------

SYSTEM STATUS

Sea Ice       Fresh
Icebergs      Fresh
Ocean Data    Fresh
Forecast      Ready

-------------------------------------

Decision Support
Forecasting → Hazard Field → Risk → Route → Captain Decision
```

Optional small scientific visual:

- restrained Antarctic map
- vessel route
- iceberg uncertainty cone

---

# 32. Government-Style Footer

Footer should clearly identify prototype status.

Example:

```text
HimDrishti
Antarctic Navigation Decision Support

SIH 2026 · Problem Statement 26059
Prototype / Demonstration System

Designed for academic/hackathon demonstration.
Not an operational navigation authority.

Data sources and methodology:
NSIDC · Sentinel-1 · Copernicus Marine · NIC / iceberg datasets

Accessibility · Data Provenance · System Status
```

Do not claim certification or official government ownership.

---

# 33. Design Tokens File

Create:

```text
frontend/src/design-system/tokens.ts
```

Suggested structure:

```ts
export const colors = {
  ink: "#102A43",
  navy: "#0B1F33",
  background: "#F7F8FA",
  surface: "#FFFFFF",
  border: "#D9E1E8",
  mutedText: "#52606D",
  text: "#243B53",

  teal: "#287D7A",
  tealSoft: "#D9F0EE",

  success: "#18794E",
  warning: "#B7791F",
  danger: "#B42318",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 4,
  md: 6,
  lg: 8,
} as const;

export const typography = {
  display: 32,
  h1: 26,
  h2: 21,
  h3: 17,
  body: 15,
  small: 13,
  micro: 11,
} as const;
```

Keep the radius modest.

---

# 34. Component Architecture

Create:

```text
frontend/src/
├── design-system/
│   ├── tokens.ts
│   ├── typography.ts
│   └── accessibility.ts
│
├── components/
│   ├── government/
│   │   ├── GovernmentUtilityBar.tsx
│   │   ├── InstitutionalHeader.tsx
│   │   └── PrototypeBadge.tsx
│   │
│   ├── navigation/
│   │   ├── MainNavigation.tsx
│   │   └── Breadcrumbs.tsx
│   │
│   ├── map/
│   │   ├── HazardMap.tsx
│   │   ├── IceLayer.tsx
│   │   ├── IcebergCone.tsx
│   │   ├── VesselMarker.tsx
│   │   └── RouteLayer.tsx
│   │
│   ├── route/
│   │   ├── RouteSummary.tsx
│   │   ├── RoutePreferenceSlider.tsx
│   │   ├── RouteAlternatives.tsx
│   │   └── CaptainDecisionPanel.tsx
│   │
│   ├── risk/
│   │   ├── PolarisRIO.tsx
│   │   ├── RiskBadge.tsx
│   │   └── RiskBreakdown.tsx
│   │
│   ├── provenance/
│   │   ├── DataFreshness.tsx
│   │   ├── SourceStatusTable.tsx
│   │   └── ContradictionAlert.tsx
│   │
│   └── common/
│       ├── Button.tsx
│       ├── Badge.tsx
│       ├── Alert.tsx
│       ├── DataTable.tsx
│       └── Skeleton.tsx
│
└── pages/
    ├── Home.tsx
    ├── RoutePlanner.tsx
    ├── ForecastExplorer.tsx
    ├── RiskCompliance.tsx
    ├── Provenance.tsx
    └── AuditLog.tsx
```

---

# 35. Page Priority

Build in this order:

## P0 — Must look excellent

1. Route Planner
2. Header
3. Map
4. Route preference slider
5. Route recommendation
6. Captain decision panel
7. Data freshness

## P1

8. Forecast Explorer
9. Risk & Compliance
10. Provenance

## P2

11. Audit Log
12. Settings
13. User management

Do not spend the first development cycle on settings.

---

# 36. SIH Judge First-Impression Strategy

When the page opens, the judge should immediately see:

```text
1. Government/institutional seriousness
2. Antarctic scientific problem
3. Live map
4. Moving hazard
5. Route recommendation
6. Risk score
7. Time/fuel/risk trade-off
8. Human decision authority
```

The first interaction should be:

**Move the risk slider.**

Expected visual effect:

```text
Slider moves
      ↓
Route changes
      ↓
ETA changes
      ↓
Fuel changes
      ↓
RIO changes
      ↓
Explanation changes
```

This is the demo's visual “wow” moment.

---

# 37. What NOT To Build

Never use:

- neon blue/purple cyberpunk theme
- black + cyan AI dashboard
- giant “AI POWERED” text
- animated particle backgrounds
- glassmorphism everywhere
- excessive rounded cards
- giant gradient hero
- generic admin sidebar
- random charts without decision relevance
- fake live data
- fake accuracy percentages
- fake government certification
- autonomous “AI captain”
- chatbot as the main interface

---

# 38. Design Principle for AI

AI must be visible through **useful intelligence**, not decoration.

Show:

- forecast correction
- uncertainty
- route optimisation
- risk explanation
- data contradiction
- provenance

Do NOT show:

```text
AI Confidence: 97%
```

unless it is backed by an actual defined metric.

Prefer:

```text
Forecast confidence: 82%

Based on:
• ensemble spread
• data freshness
• source agreement
```

---

# 39. Scientific Credibility

Numbers must have units.

Bad:

```text
Fuel: 18.6
Risk: 3.2
Distance: 82
```

Good:

```text
Fuel: 18.6 t
POLARIS RIO: 3.2
Distance: 82 km
ETA: 8h 42m
```

Always show the time reference for forecast data.

---

# 40. Final Visual Identity

### Brand

**HimDrishti**

Subtitle:

**Antarctic Navigation Decision Support**

Optional Hindi/Indian identity can be introduced later, but English should remain the primary operational language for the bridge-console prototype.

### Visual signature

```text
Warm off-white
+
Deep navy
+
Desaturated teal
+
Small controlled amber/red
+
Noto Sans
+
Thin borders
+
Large map
+
Dense scientific data
+
Minimal motion
```

---

# 41. Antigravity / Claude Implementation Prompt

Use the following prompt after placing this file in the project root.

```text
Read design.md completely before modifying the frontend.

You are implementing the HimDrishti SIH 2026 frontend.

IMPORTANT:
The interface must look like a modern Indian government scientific decision-support application, not a startup SaaS dashboard.

Use design.md as the visual source of truth.

Reference hierarchy:
1. UX4G Design System 3.0 for component behaviour and accessibility.
2. GIGW 3.0 for government-grade UX principles.
3. Ministry of Earth Sciences and NCPOR for institutional/scientific visual cues.
4. HimDrishti design.md for the final project-specific implementation.

Do not clone any government website.
Do not create fake Government of India ownership.
Do not use the State Emblem in a way that implies official ownership.
Show “SIH 2026 · PS 26059” and “Prototype / Demonstration System”.

Build the Route Planner first.

The first viewport must immediately show:
- institutional header
- HimDrishti identity
- SIH 2026 / PS 26059 context
- data freshness
- Antarctic map
- sea-ice hazard field
- iceberg uncertainty cone
- vessel marker
- recommended route
- alternative route
- system recommendation
- captain decision panel
- risk/time/fuel slider

The risk slider must visibly change:
- route geometry
- ETA
- fuel
- POLARIS RIO
- explanation

Use realistic but clearly labelled demo data where backend data is unavailable.

Do not fake scientific accuracy.

Implement:
- responsive layout
- keyboard navigation
- WCAG 2.1 AA-oriented contrast
- visible focus states
- accessible labels
- non-colour-only risk states
- loading/error/empty states
- data freshness states

Use React + TypeScript.

Create reusable components instead of putting everything in one page.

Before finishing:
1. Run the frontend.
2. Inspect the first viewport visually.
3. Remove startup/SaaS styling.
4. Verify the government/scientific/institutional tone.
5. Verify that the slider interaction is obvious.
6. Verify that the captain decision panel is visually separate from the system recommendation.
7. Verify that no number is presented without units/context.
8. Verify that the application does not falsely claim to be an official government service.

Do not redesign the architecture or backend unless required for the frontend.
Do not add unnecessary dependencies.
```

---

# 42. Final Design Decision

**Best foundation:** UX4G Design System 3.0  
**Best government-compliance reference:** GIGW 3.0  
**Best ministry-specific visual reference:** Ministry of Earth Sciences  
**Best domain-specific reference:** NCPOR  
**Best information-architecture reference:** India.gov.in  
**Best final combination for HimDrishti:** UX4G + GIGW + MoES/NCPOR cues + custom scientific navigation-console UX.

The goal is not to make the page look “old government”.

The goal is to make it look like:

> **A credible Government of India scientific system that has been professionally modernised for Antarctic maritime decision support.**
