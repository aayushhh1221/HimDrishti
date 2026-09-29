/**
 * About — Phase 11 / Phase 12
 * SIH 2026 · PS 26059
 *
 * Project information, prototype scope, limitations, tech stack, disclaimer.
 * Phase 12: migrated to shared-page.module.css.
 */

import styles from './shared-page.module.css'

export default function About() {
  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>About HimDrishti</h1>
      <p className={styles.sub}>
        AI-Assisted Polar Route Optimisation System for NCPOR Antarctic expeditions.
        Smart India Hackathon 2026 · PS 26188.
      </p>

      <div className={styles.card}>
        <div className={styles.cardTitle}>Project Overview</div>
        <p className={styles.para}>
          HimDrishti is a prototype decision-support system that assists NCPOR navigators
          in planning Antarctic supply voyages. It integrates a POLARIS/RIO-based ice risk
          model, an iceberg ensemble drift forecast, and a risk-budgeted route optimiser
          (POLARIS + Dijkstra). All outputs are computed deterministically from declared
          data sources.
        </p>
        <p className={styles.para}>
          The system does <strong>not</strong> navigate autonomously. All routing
          recommendations require confirmation by the Master, Captain, or Ice Pilot before
          operational use.
        </p>
      </div>

      <div className={styles.card}>
        <div className={styles.cardTitle}>Prototype Scope</div>
        <ul className={styles.list}>
          <li>Route planning: Cape Town → Bharati Station (Larsemann Hills), Prydz Bay</li>
          <li>Ice risk modelling: POLARIS/RIO prototype (ice class PC3–PC5)</li>
          <li>Data mode: SYNTHETIC_DEMO (fixture data, not live operational data)</li>
          <li>Forecast: synthetic iceberg ensemble drift (6-member, 5-day horizon)</li>
          <li>Route optimiser: risk-budgeted Dijkstra on polar grid</li>
          <li>Historical replay: synthetic offline fallback (Phase 9)</li>
          <li>Departure-window analysis: genuine pipeline reruns per candidate offset</li>
        </ul>
      </div>

      <div className={styles.card}>
        <div className={styles.cardTitle}>What This Prototype Does NOT Do</div>
        <ul className={styles.list}>
          <li>Does not use live satellite data, live AIS, or live sea-ice products</li>
          <li>Does not provide certified or operationally validated routing</li>
          <li>Does not use AI/LLM/RL for safety-critical decisions</li>
          <li>Does not guarantee safe passage or eliminate navigational risk</li>
          <li>POLARIS RIV values are illustrative — authoritative values require IMO MSC.1/Circ.1519</li>
        </ul>
      </div>

      <div className={styles.card}>
        <div className={styles.cardTitle}>Technology Stack</div>
        <dl className={styles.dl}>
          <div className={styles.dlRow}><dt>Backend</dt><dd>Python 3.11 / FastAPI / Pydantic v2</dd></div>
          <div className={styles.dlRow}><dt>Scientific core</dt><dd>NumPy, SciPy, NetworkX (Dijkstra)</dd></div>
          <div className={styles.dlRow}><dt>Frontend</dt><dd>React 18 / TypeScript / Vite / CSS Modules</dd></div>
          <div className={styles.dlRow}><dt>Map</dt><dd>MapLibre / Leaflet (polar stereographic navigation)</dd></div>
          <div className={styles.dlRow}><dt>Tests</dt><dd>pytest (261 tests across 5 suites)</dd></div>
          <div className={styles.dlRow}><dt>Data</dt><dd>Synthetic fixture (SYNTHETIC_DEMO)</dd></div>
        </dl>
      </div>

      <div className={styles.card}>
        <div className={styles.cardTitle}>Limitations and Disclaimers</div>
        <p className={styles.para}>
          This is a <strong>prototype</strong> built for SIH 2026. It has not been
          validated for operational polar navigation. Scientific outputs are illustrative
          and based on synthetic demonstration data. No data presented should be relied
          upon for actual voyage planning without independent expert verification.
        </p>
        <p className={styles.para}>
          The system is intended to demonstrate the feasibility of decision-support
          tooling for polar route planning and to inform future development of a
          scientifically validated operational system.
        </p>
      </div>

      <div className={styles.noticeBox} role="note">
        <strong>SIH 2026 Prototype · PS 26188</strong><br />
        Not for Operational Use. Final navigation authority rests with the
        Master / Captain / Ice Pilot at all times.
        © 2026 Ministry of Earth Sciences, Government of India.
      </div>

      <div className={styles.tag}>SIH 2026 · PS 26188</div>
    </div>
  )
}
