/**
 * OperationalStatusRow
 * SIH 2026 · PS 26059
 *
 * Compact operational strip immediately below navigation.
 * Shows data freshness, forecast cycle, sync status, region.
 * Design reference: design.md §9.5, reference-ui.png status row.
 *
 * All values are MOCK data for Phase 3 visual development.
 * Replace with backend values in Phase 7+ (API integration).
 */

import { Clock, RefreshCw, CheckCircle, Globe, Calendar, ChevronDown, Info } from 'lucide-react'
import styles from './OperationalStatusRow.module.css'

/**
 * Mock operational status data.
 * These values will be replaced by API data in Phase 7.
 */
const MOCK_STATUS = {
  dataUpdated: '21 May 2026, 10:30 IST',
  nextForecastCycle: '+3h 00m',
  dataSourcesStatus: 'All Synced' as const,
  region: 'Southern Ocean (60°S–90°S)',
}

export default function OperationalStatusRow() {
  function handleViewFreshness() {
    // Phase 7: open data provenance panel or navigate to /data-provenance
    console.info('[HimDrishti] View Data Freshness — Phase 7 implementation')
  }

  return (
    <div
      className={styles.row}
      role="complementary"
      aria-label="Operational system status"
    >
      <div className={styles.items}>

        {/* ── Data Updated ─────────────────────────────────── */}
        <div className={styles.item}>
          <Info size={13} className={styles.itemIcon} aria-hidden="true" />
          <div className={styles.itemContent}>
            <span className={styles.itemLabel}>Data Updated</span>
            <span className={styles.datePill}>
              {MOCK_STATUS.dataUpdated}
            </span>
          </div>
        </div>

        {/* ── Next Forecast Cycle ──────────────────────────── */}
        <div className={styles.item}>
          <Clock size={13} className={styles.itemIcon} aria-hidden="true" />
          <div className={styles.itemContent}>
            <span className={styles.itemLabel}>Next Forecast Cycle</span>
            <span className={styles.itemValue}>{MOCK_STATUS.nextForecastCycle}</span>
          </div>
        </div>

        {/* ── Data Sources ─────────────────────────────────── */}
        <div className={styles.item}>
          <RefreshCw size={13} className={styles.itemIcon} aria-hidden="true" />
          <div className={styles.itemContent}>
            <span className={styles.itemLabel}>Data Sources</span>
            <span className={styles.syncedValue}>
              <CheckCircle size={12} aria-hidden="true" />
              {MOCK_STATUS.dataSourcesStatus}
            </span>
          </div>
        </div>

        {/* ── Region ───────────────────────────────────────── */}
        <div className={styles.item}>
          <Globe size={13} className={styles.itemIcon} aria-hidden="true" />
          <div className={styles.itemContent}>
            <span className={styles.itemLabel}>Region</span>
            <span className={styles.itemValue}>{MOCK_STATUS.region}</span>
          </div>
        </div>

      </div>

      {/* ── Right: View Data Freshness ───────────────────── */}
      <div className={styles.actions}>
        <button
          className={styles.freshnessBtn}
          type="button"
          aria-label="View Data Freshness details"
          onClick={handleViewFreshness}
        >
          <Calendar size={13} aria-hidden="true" />
          View Data Freshness
          <ChevronDown size={12} aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
