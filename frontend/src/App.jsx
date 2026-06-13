/**
 * KaizenIQ — Application shell
 * =============================
 * Sidebar navigation + page switching. The full analysis is fetched once
 * and shared with every page through props (single source of truth).
 *
 * Pages:
 *   Dashboard        — executive summary, drift map, savings, roadmap
 *   Agent Portfolio  — the 14 agents (7 implemented + 7 proposed) with
 *                      one-click "Train" that shows the Foundry-grounded prompt
 *   Non-Conformities — ISO findings ledger with clauses + remediation
 *   Processes        — process list + live Mermaid flowchart (the catalyst)
 */
import { useEffect, useState, useCallback } from 'react';
import { getAnalysis } from './api/client.js';
import Dashboard from './pages/Dashboard.jsx';
import Agents from './pages/Agents.jsx';
import NonConformities from './pages/NonConformities.jsx';
import Processes from './pages/Processes.jsx';
import AddProcess from './pages/AddProcess.jsx';
import Chat from './pages/Chat.jsx';
import Telemetry from './pages/Telemetry.jsx';
import CompanyMap from './pages/CompanyMap.jsx';

const PAGES = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'chat', label: 'Talk to Agents' },
  { id: 'add', label: 'Add Process' },
  { id: 'map', label: 'Company Map' },
  { id: 'agents', label: 'Agent Portfolio' },
  { id: 'ncs', label: 'Non-Conformities' },
  { id: 'processes', label: 'Processes' },
  { id: 'telemetry', label: 'Telemetry & Safety' },
];

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);

  // Load (and reload) the shared orchestration result.
  const refresh = useCallback(() => {
    getAnalysis().then(setAnalysis).catch((e) => setError(e.message));
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  if (error) {
    return (
      <div className="loading">
        Could not reach the KaizenIQ API.<br />
        Start the backend with <code>uvicorn main:app --reload</code> and refresh.
        <br /><br /><small>{error}</small>
      </div>
    );
  }
  if (!analysis) return <div className="loading">改 &nbsp; Running the seven agents…</div>;

  const ncCount = analysis.non_conformities.summary.total;
  const mode = analysis.foundry_iq.mode;

  return (
    <div className="shell">
      <aside className="sidebar">
        {/* Brand — the hanko seal is the signature element of the identity */}
        <div className="brand">
          <div className="seal" aria-hidden="true">改</div>
          <div>
            <h1>KaizenIQ</h1>
            <small>Continuous improvement, agentic</small>
          </div>
        </div>

        <nav className="nav" aria-label="Main">
          {PAGES.map((p) => (
            <button
              key={p.id}
              className={page === p.id ? 'active' : ''}
              onClick={() => setPage(p.id)}
            >
              {p.label}
              {p.id === 'ncs' && <span className="count">{ncCount}</span>}
            </button>
          ))}
        </nav>

        <div className="foot">
          <span className="mode-chip">
            <span className="dot" /> Foundry IQ · {mode}
          </span>
          <div>{analysis.organization.name}</div>
          <div>{analysis.organization.iso_certification}</div>
        </div>
      </aside>

      <main className="main">
        {page === 'dashboard' && <Dashboard data={analysis} />}
        {page === 'chat' && <Chat foundryMode={mode} />}
        {page === 'add' && <AddProcess onAdded={refresh} foundryMode={mode} />}
        {page === 'map' && <CompanyMap />}
        {page === 'agents' && <Agents data={analysis} />}
        {page === 'ncs' && <NonConformities data={analysis} />}
        {page === 'processes' && <Processes data={analysis} />}
        {page === 'telemetry' && <Telemetry />}
      </main>
    </div>
  );
}
