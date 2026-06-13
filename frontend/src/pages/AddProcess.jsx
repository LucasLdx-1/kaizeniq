/**
 * KaizenIQ — Add Process page
 * ============================
 * Lets the user introduce a NEW process at runtime by pasting its name, area
 * and steps. The local Microsoft Foundry model (Foundry Local) infers the ISO
 * clause, KPIs and metadata; the backend generates the flowchart and folds the
 * process into the live analysis (diagnostics, Agent Factory, orchestrator).
 *
 * Session-scoped: the process exists until the backend restarts. This is the
 * on-device stand-in for indexing a document in Foundry IQ.
 *
 * After a successful add, the parent refreshes the shared analysis so every
 * other page immediately reflects the new process.
 */
import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { analyzeProcess } from '../api/client.js';

mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  flowchart: { curve: 'basis' },
  fontFamily: 'Zen Kaku Gothic New, sans-serif',
});

let seq = 0;

export default function AddProcess({ onAdded, foundryMode }) {
  const [name, setName] = useState('');
  const [area, setArea] = useState('');
  const [stepsText, setStepsText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null); // { process, flowchart }
  const [svg, setSvg] = useState('');

  // Render the generated flowchart whenever a result arrives.
  useEffect(() => {
    if (!result?.flowchart) return;
    let cancelled = false;
    (async () => {
      try {
        const { svg } = await mermaid.render(`add-flow-${++seq}`, result.flowchart);
        if (!cancelled) setSvg(svg);
      } catch {
        if (!cancelled) setSvg('');
      }
    })();
    return () => { cancelled = true; };
  }, [result]);

  async function handleAnalyze() {
    setError(null);
    const steps = stepsText
      .split('\n')
      .map((s) => s.replace(/^\s*\d+[.)]\s*/, '').trim()) // strip "1." / "1)" prefixes
      .filter(Boolean);

    if (!name.trim() || !area.trim() || steps.length === 0) {
      setError('Please provide a name, an area, and at least one step.');
      return;
    }

    setBusy(true);
    setSvg('');
    try {
      const res = await analyzeProcess(name.trim(), area.trim(), steps);
      setResult(res);
      onAdded?.(); // tell the app to refresh the shared analysis
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setName(''); setArea(''); setStepsText('');
    setResult(null); setSvg(''); setError(null);
  }

  const p = result?.process;

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Foundry-powered intake</div>
        <h2>Add a Process</h2>
        <p>
          Paste a process and the local Microsoft Foundry model infers its ISO
          clause, KPIs and criticality, draws its flowchart, and folds it into
          the live analysis — diagnostics, Agent Factory and the orchestrator all
          start accounting for it immediately.
          {foundryMode !== 'local' && (
            <><br /><strong style={{ color: 'var(--amber)' }}>
              Note: Foundry Local is not active ({foundryMode} mode) — metadata
              uses safe defaults. Start Foundry Local for model-inferred fields.
            </strong></>
          )}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 22, alignItems: 'start' }}>
        {/* ---- Input form ------------------------------------------- */}
        <section className="ledger">
          <header><h3>New process</h3></header>
          <div className="body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <label style={{ fontSize: 13 }}>
              Process name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Customer Onboarding"
                style={inputStyle}
              />
            </label>
            <label style={{ fontSize: 13 }}>
              Area / department
              <input
                value={area}
                onChange={(e) => setArea(e.target.value)}
                placeholder="e.g. Customer Success"
                style={inputStyle}
              />
            </label>
            <label style={{ fontSize: 13 }}>
              Steps (one per line)
              <textarea
                value={stepsText}
                onChange={(e) => setStepsText(e.target.value)}
                placeholder={"Receive signed contract\nCreate customer account\nSchedule kickoff meeting\nReview onboarding checklist\nApprove go-live"}
                rows={8}
                style={{ ...inputStyle, fontFamily: 'var(--font-mono)', fontSize: 12.5, resize: 'vertical' }}
              />
            </label>
            {error && <div style={{ color: 'var(--hanko)', fontSize: 12.5 }}>{error}</div>}
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn" onClick={handleAnalyze} disabled={busy}>
                {busy ? 'Analyzing with Foundry…' : 'Analyze with Foundry'}
              </button>
              {result && (
                <button className="btn ghost" onClick={reset}>Add another</button>
              )}
            </div>
          </div>
        </section>

        {/* ---- Result ------------------------------------------------ */}
        <div>
          {!result && (
            <section className="ledger">
              <header><h3>Result</h3></header>
              <div className="body" style={{ color: 'var(--stone)', fontSize: 13 }}>
                The structured process and its generated flowchart will appear here.
              </div>
            </section>
          )}

          {p && (
            <>
              <section className="ledger">
                <header>
                  <h3>{p.id} — {p.name}</h3>
                  <span className="sub">inferred by Foundry ({result.foundry_mode} mode)</span>
                </header>
                <div className="body" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: 12.5 }}>
                  <div><strong>ISO clause</strong><br /><span style={{ color: 'var(--stone)' }}>{p.iso_clause}</span></div>
                  <div><strong>Criticality</strong><br />
                    <span className={`badge ${p.criticality === 'HIGH' ? 'high' : 'medium'}`}>{p.criticality}</span>
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <strong>KPIs inferred</strong>
                    <ul className="evidence" style={{ marginTop: 4 }}>
                      {p.kpis.map((k, i) => (
                        <li key={i}>{k.name}: target {k.target}, current {k.current}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </section>

              <div className="flowchart-box">
                {svg
                  ? <div dangerouslySetInnerHTML={{ __html: svg }} />
                  : <p style={{ color: 'var(--stone)' }}>Rendering flowchart…</p>}
              </div>

              <p style={{ fontSize: 12.5, color: 'var(--pine)', marginTop: 10 }}>
                ✓ Added to the live analysis. Open Dashboard, Agent Portfolio or
                Non-Conformities — they now account for {p.id}.
              </p>
            </>
          )}
        </div>
      </div>
    </>
  );
}

const inputStyle = {
  width: '100%',
  marginTop: 4,
  padding: '8px 10px',
  border: '1px solid var(--line)',
  borderRadius: 'var(--radius)',
  fontFamily: 'var(--font-ui)',
  fontSize: 13,
  background: 'var(--surface)',
  color: 'var(--ink)',
};
