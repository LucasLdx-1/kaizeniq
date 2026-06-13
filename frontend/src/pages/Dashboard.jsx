/**
 * KaizenIQ — Dashboard page
 * ==========================
 * The executive view a Quality Manager opens first:
 *   1. Headline produced by the Master Orchestrator
 *   2. Stat row (drift, non-conformities, recoverable hours and cost)
 *   3. Process drift map (alignment of all 15 ISO processes)
 *   4. Top automation candidates with estimated yearly savings
 *   5. Three-phase transformation roadmap
 */
import { useMemo } from 'react';

/** Map an alignment label to its badge class. */
const alignmentBadge = {
  ALIGNED: 'aligned',
  MINOR_DRIFT: 'drift-minor',
  SIGNIFICANT_DRIFT: 'drift-significant',
  CRITICAL_DRIFT: 'drift-critical',
};

/** Human-readable alignment labels. */
const alignmentLabel = {
  ALIGNED: 'Aligned',
  MINOR_DRIFT: 'Minor drift',
  SIGNIFICANT_DRIFT: 'Significant drift',
  CRITICAL_DRIFT: 'Critical drift',
};

const usd = (n) => `$${Number(n).toLocaleString('en-US')}`;

export default function Dashboard({ data }) {
  const ex = data.executive_summary;
  const assessments = data.current_state.assessments;
  const roadmap = data.roadmap;

  // Top automation candidates, ranked by yearly cost (already sorted by API).
  const topFindings = data.repetitive_work.findings.slice(0, 5);
  const maxCost = topFindings[0]?.estimated_yearly_cost_usd || 1;

  // Sort the drift map: worst first, so attention lands where it matters.
  const sorted = useMemo(
    () => [...assessments].sort((a, b) => b.misalignment_score - a.misalignment_score),
    [assessments]
  );

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Executive diagnostic</div>
        <h2>{data.organization.name}</h2>
        <p>{ex.headline}</p>
      </div>

      {/* ---- Stat row ------------------------------------------------ */}
      <div className="stats">
        <div className="stat">
          <div className="label">Processes drifting</div>
          <div className="value red">{ex.processes_drifting}<span style={{ fontSize: 15, color: 'var(--stone)' }}>/{assessments.length}</span></div>
          <div className="hint">documentation vs. practice</div>
        </div>
        <div className="stat">
          <div className="label">Open non-conformities</div>
          <div className="value red">{ex.open_non_conformities}</div>
          <div className="hint">ISO 9001 findings</div>
        </div>
        <div className="stat">
          <div className="label">Recoverable hours / yr</div>
          <div className="value">{Math.round(ex.recoverable_hours_per_year).toLocaleString('en-US')}</div>
          <div className="hint">repetitive manual work</div>
        </div>
        <div className="stat">
          <div className="label">Estimated impact / yr</div>
          <div className="value green">{usd(roadmap.total_estimated_yearly_impact_usd)}</div>
          <div className="hint">if proposed agents deployed</div>
        </div>
      </div>

      <div className="two-col">
        {/* ---- Drift map -------------------------------------------- */}
        <section className="ledger">
          <header>
            <h3>Process drift map</h3>
            <span className="sub">documented process vs. observed M365 behavior</span>
          </header>
          <table>
            <thead>
              <tr><th>Process</th><th>Alignment</th><th>Evidence</th></tr>
            </thead>
            <tbody>
              {sorted.map((a) => (
                <tr key={a.process_id}>
                  <td>
                    <span className="mono">{a.process_id}</span><br />
                    {a.process_name}
                  </td>
                  <td>
                    <span className={`badge ${alignmentBadge[a.alignment]}`}>
                      {alignmentLabel[a.alignment]}
                    </span>
                  </td>
                  <td className="mono">{a.evidence.length} signals</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <div>
          {/* ---- Automation candidates ------------------------------ */}
          <section className="ledger">
            <header>
              <h3>Top automation candidates</h3>
              <span className="sub">estimated yearly cost of manual work</span>
            </header>
            <div className="body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {topFindings.map((f) => (
                <div key={f.pattern}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <strong>{f.pattern}</strong>
                    <span className="mono" style={{ color: 'var(--hanko)' }}>
                      {usd(f.estimated_yearly_cost_usd)}/yr
                    </span>
                  </div>
                  {/* Proportional bar — pure CSS, no chart library needed here */}
                  <div style={{ background: 'var(--slate-soft)', borderRadius: 4, height: 8, marginTop: 5 }}>
                    <div
                      style={{
                        width: `${(f.estimated_yearly_cost_usd / maxCost) * 100}%`,
                        background: 'var(--ink)',
                        height: '100%',
                        borderRadius: 4,
                      }}
                    />
                  </div>
                  <div style={{ fontSize: 11.5, color: 'var(--stone)', marginTop: 3 }}>
                    {f.hours_per_week}h/week · {f.linked_process} · {f.type === 'MEETING' ? 'recurring meeting' : 'email workflow'}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* ---- Roadmap --------------------------------------------- */}
          <section className="ledger">
            <header>
              <h3>Transformation roadmap</h3>
              <span className="sub">phased rollout proposed by the orchestrator</span>
            </header>
            <div className="body">
              {roadmap.phases.map((ph) => (
                <div className="phase" key={ph.phase}>
                  <div className="when">PHASE {ph.phase}<br />wk {ph.weeks}</div>
                  <div>
                    <h4>{ph.name}</h4>
                    <p>{ph.rationale}</p>
                    <div className="agents">
                      {ph.agents.map((a) => (
                        <span className="badge tier" key={a}>{a}</span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
