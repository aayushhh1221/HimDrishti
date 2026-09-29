/**
 * DataProvenancePanel.tsx — HimDrishti Phase 7
 * SIH 2026 · PS 26059
 *
 * "6. Data Provenance" panel — shows data source records with sync status.
 * Phase 7: fetches from GET /api/v1/provenance, falls back to DEMO_PROVENANCE.
 * Drawer opens full provenance detail.
 * Visual design unchanged — no redesign.
 */

import { useState } from 'react'
import { Info, ChevronRight, X } from 'lucide-react'
import ProvenanceRow from './ProvenanceRow'
import {
  DEMO_PROVENANCE,
  FULL_PROVENANCE_NOTE,
  getLiveIstTimestamp,
  type ProvenanceRecord,
} from '../../data/demoProvenance'
import { useProvenance } from '../../hooks/useApi'
import type { ApiProvenanceRecord } from '../../services/api'
import styles from './DataProvenancePanel.module.css'

/** Map API provenance record to demo shape so ProvenanceRow works unchanged */
function apiRecordToDemo(r: ApiProvenanceRecord, idx: number): ProvenanceRecord {
  const statusMap: Record<string, ProvenanceRecord['status']> = {
    available: 'synced',
    stale: 'stale',
    unavailable: 'unavailable',
    invalid: 'unavailable',
  }
  return {
    id: `prov-api-${idx}`,
    category: r.dataset_name.replace(/\[SYNTHETIC DEMO\]\s*/i, '').split(' (')[0].trim(),
    source: r.source,
    dataset: r.dataset_name,
    status: statusMap[r.status] ?? 'synced',
    updatedAt: r.retrieved_at,
    updatedAtShort: r.retrieved_at.slice(0, 16).replace('T', ' ') + ' UTC',
    coverage: r.spatial_coverage,
  }
}

export default function DataProvenancePanel() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const provState = useProvenance()

  // Use API records when available, fall back to demo
  const rawRecords: ProvenanceRecord[] =
    provState.status === 'success' && provState.data
      ? provState.data.records.map(apiRecordToDemo)
      : DEMO_PROVENANCE

  // For static demo records only, show current live IST to indicate the prototype is running.
  // For API records, preserve the actual retrieved_at from the backend.
  const liveIst = getLiveIstTimestamp()
  const records: ProvenanceRecord[] = rawRecords.map((r) => {
    const isApiRecord = provState.status === 'success' && provState.data
    return isApiRecord
      ? r                          // keep real backend timestamp
      : { ...r, updatedAtShort: liveIst, updatedAt: liveIst }  // demo only
  })

  const isApiData = provState.status === 'success'
  const isLoading = provState.status === 'loading'

  const drawerNote =
    isApiData && provState.data
      ? provState.data.prototype_notice
      : FULL_PROVENANCE_NOTE

  return (
    <section className={styles.panel} aria-labelledby="prov-panel-heading">
      {/* Header */}
      <div className={styles.header}>
        <span id="prov-panel-heading" className={styles.headerTitle}>
          6. Data Provenance
          {isLoading && (
            <span style={{ fontSize: '10px', color: '#64748b', marginLeft: '6px' }}>
              Loading…
            </span>
          )}
        </span>
        <Info
          size={13}
          className={styles.infoIcon}
          aria-label={
            isApiData
              ? 'API provenance data — SYNTHETIC DEMO'
              : 'Demo provenance — data sources not being fetched live'
          }
          role="img"
        />
      </div>



      {/* Source rows */}
      <div className={styles.body} role="table" aria-label="Data source provenance records">
        {records.map((rec) => (
          <ProvenanceRow key={rec.id} record={rec} />
        ))}


      </div>

      {/* View Full Provenance link */}
      <div className={styles.footer}>
        <button
          className={styles.viewFullBtn}
          type="button"
          onClick={() => setDrawerOpen(true)}
          aria-label="View full data provenance details"
          aria-expanded={drawerOpen}
          aria-controls="prov-drawer"
        >
          View Full Provenance
          <ChevronRight size={13} aria-hidden="true" />
        </button>
      </div>

      {/* Inline provenance drawer */}
      {drawerOpen && (
        <div
          id="prov-drawer"
          className={styles.drawer}
          role="region"
          aria-label="Full provenance detail"
        >
          <div className={styles.drawerHeader}>
            <span className={styles.drawerTitle}>Full Data Provenance</span>
            <button
              className={styles.drawerClose}
              type="button"
              onClick={() => setDrawerOpen(false)}
              aria-label="Close provenance detail"
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>

          <div className={styles.drawerBody}>
            {records.map((rec) => (
              <div key={rec.id} className={styles.drawerRecord}>
                <div className={styles.drawerRecordHeader}>{rec.category}</div>
                <dl className={styles.drawerDl}>
                  <div className={styles.drawerDlRow}>
                    <dt>Source</dt><dd>{rec.source}</dd>
                  </div>
                  <div className={styles.drawerDlRow}>
                    <dt>Dataset</dt><dd>{rec.dataset}</dd>
                  </div>
                  <div className={styles.drawerDlRow}>
                    <dt>Last updated</dt><dd>{rec.updatedAt}</dd>
                  </div>
                  <div className={styles.drawerDlRow}>
                    <dt>Coverage</dt><dd>{rec.coverage}</dd>
                  </div>
                  <div className={styles.drawerDlRow}>
                    <dt>Status</dt>
                    <dd style={{ textTransform: 'capitalize' }}>{rec.status}</dd>
                  </div>
                </dl>
              </div>
            ))}

            <p className={styles.drawerNote}>{drawerNote}</p>
          </div>
        </div>
      )}
    </section>
  )
}
