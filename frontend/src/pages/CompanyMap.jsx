/**
 * KaizenIQ — Company Map page
 * ============================
 * A single Mermaid map of the WHOLE organization: every ISO 9001 process
 * grouped under its macro-process, branching from the company root.
 *
 * Incremental: processes added on the "Add Process" page flow through the same
 * dynamic store, so they appear here automatically (highlighted in green).
 * Critical processes are highlighted in the hanko red.
 */
import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { getCompanyMap } from '../api/client.js';

mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  flowchart: { curve: 'basis', nodeSpacing: 30, rankSpacing: 55 },
  fontFamily: 'Zen Kaku Gothic New, sans-serif',
});

let seq = 0;

export default function CompanyMap() {
  const [info, setInfo] = useState(null);
  const [svg, setSvg] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getCompanyMap();
        if (cancelled) return;
        setInfo(data);
        const { svg } = await mermaid.render(`company-map-${++seq}`, data.mermaid);
        if (!cancelled) setSvg(svg);
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Systemic view</div>
        <h2>Company Process Map</h2>
        <p>
          Every documented process across the organization, grouped by
          macro-process. Processes you add appear here automatically
          (<span style={{ color: 'var(--pine)' }}>green</span>); critical
          processes are marked in <span style={{ color: 'var(--hanko)' }}>red</span>.
        </p>
      </div>

      {info && (
        <div className="stats">
          <div className="stat">
            <div className="label">Total processes</div>
            <div className="value">{info.total_processes}</div>
          </div>
          <div className="stat">
            <div className="label">Macro-processes</div>
            <div className="value">{info.macro_processes.length}</div>
          </div>
          <div className="stat">
            <div className="label">Added this session</div>
            <div className="value green">{info.user_added.length}</div>
            <div className="hint">{info.user_added.join(', ') || 'none yet'}</div>
          </div>
        </div>
      )}

      <div className="flowchart-box">
        {error && <p style={{ color: 'var(--hanko)' }}>Could not render map: {error}</p>}
        {!svg && !error && <p style={{ color: 'var(--stone)' }}>改 &nbsp;Rendering company map…</p>}
        {svg && <div dangerouslySetInnerHTML={{ __html: svg }} />}
      </div>
    </>
  );
}
