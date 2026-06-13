/**
 * KaizenIQ — Non-Conformities page
 * =================================
 * An auditor-style ledger of every ISO 9001 finding raised by the
 * Non-Conformity Detector: severity, threatened clause, evidence-based
 * description and a concrete remediation hint.
 *
 * CRITICAL severity uses the hanko red — the only place besides the brand
 * where the seal color appears, keeping its meaning sharp.
 */
import { useMemo, useState } from 'react';

const SEVERITY_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

export default function NonConformities({ data }) {
  const ncs = data.non_conformities;
  const [filter, setFilter] = useState('ALL');

  // Stable sort: severity first, then id.
  const rows = useMemo(() => {
    const list = [...ncs.findings].sort(
      (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || a.id.localeCompare(b.id)
    );
    return filter === 'ALL' ? list : list.filter((f) => f.severity === filter);
  }, [ncs, filter]);

  const sev = ncs.summary.by_severity;

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Audit ledger</div>
        <h2>Non-Conformities</h2>
        <p>
          {ncs.summary.total} findings detected from organizational signals — stale controlled
          documents, overdue corrective actions and information-governance anomalies, each
          mapped to the ISO 9001:2015 clause it threatens.
        </p>
      </div>

      {/* ---- Severity filter chips ---------------------------------- */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
        {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((s) => (
          <button
            key={s}
            className="btn ghost"
            style={{
              background: filter === s ? 'var(--ink)' : undefined,
              color: filter === s ? 'var(--paper)' : undefined,
            }}
            onClick={() => setFilter(s)}
          >
            {s === 'ALL' ? `All (${ncs.summary.total})` : `${s} (${sev[s] || 0})`}
          </button>
        ))}
      </div>

      <section className="ledger">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Severity</th>
              <th>Finding</th>
              <th>ISO clause</th>
              <th>Remediation</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => (
              <tr key={f.id}>
                <td className="mono">{f.id}</td>
                <td>
                  <span className={`badge ${f.severity.toLowerCase()}`}>{f.severity}</span>
                </td>
                <td>
                  <strong>{f.process_name}</strong>{' '}
                  <span className="mono" style={{ color: 'var(--stone)' }}>({f.process_id})</span>
                  <br />
                  <span style={{ color: 'var(--stone)', fontSize: 12.5 }}>{f.description}</span>
                </td>
                <td className="mono" style={{ fontSize: 11.5 }}>{f.iso_clause}</td>
                <td style={{ fontSize: 12.5, color: 'var(--stone)' }}>{f.remediation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
