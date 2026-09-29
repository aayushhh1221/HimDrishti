/**
 * InstitutionalHeader
 * SIH 2026 · PS 26059
 *
 * White institutional header matching reference.png.
 * Three-column layout: MoES identity | HimDrishti | NCPOR identity.
 */

import governmentEmblem from '../../assets/logos/government-emblem.png'
import himdrishtiLogo   from '../../assets/logos/himdrishti-logo.png'
import ncporLogo        from '../../assets/logos/ncpor-logo.png'
import styles from './InstitutionalHeader.module.css'

export default function InstitutionalHeader() {
  return (
    <header className={styles.header} role="banner" aria-label="HimDrishti institutional header">

      {/* ── LEFT: Ministry of Earth Sciences identity ─────── */}
      <div className={styles.leftZone}>
        <img
          src={governmentEmblem}
          alt="Government of India emblem"
          className={styles.governmentEmblem}
          draggable={false}
        />

        <div className={styles.ministryText}>
          <span className={styles.ministryName}>Ministry of Earth Sciences</span>
          <span className={styles.ministrySubtext}>Government of India</span>
        </div>
      </div>

      {/* Vertical divider */}
      <div className={styles.divider} aria-hidden="true" />

      {/* ── CENTER: HimDrishti identity ───────────────────── */}
      <div className={styles.centerZone}>
        <img
          src={himdrishtiLogo}
          alt="HimDrishti logo"
          className={styles.himDrishtiLogo}
          draggable={false}
        />

        <div className={styles.himDrishtiIdentity}>
          <div className={styles.wordmarkRow}>
            <h1 className={styles.wordmark}>HimDrishti</h1>
          </div>
          <p className={styles.subtitle}>
            AI-Enabled Antarctic Sea-Ice, Iceberg Trajectory &amp; Navigation Decision Support System
          </p>
          <p className={styles.sihTag}>
            SIH 2026 &bull; PS 26059 &nbsp;|&nbsp; National Centre for Polar and Ocean Research
          </p>
        </div>
      </div>

      {/* ── RIGHT: NCPOR identity ─────────────────────────── */}
      <div className={styles.rightZone} aria-label="Partner institution">
        <div className={styles.ncporRow}>
          <img
            src={ncporLogo}
            alt="National Centre for Polar and Ocean Research logo"
            className={styles.ncporLogo}
            draggable={false}
          />
          <div className={styles.ncporText}>
            <span className={styles.ncporName}>
              National Centre for Polar and Ocean Research (NCPOR)
            </span>
            <span className={styles.ncporSubtext}>
              Ministry of Earth Sciences, Government of India
            </span>
          </div>
        </div>
      </div>

    </header>
  )
}
