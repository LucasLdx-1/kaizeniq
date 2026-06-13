/**
 * KaizenIQ — Agent Portfolio page
 * ================================
 * The product's differentiator on screen: the 14-agent portfolio produced
 * by the Agent Factory (7 implemented, 7 proposed).
 *
 * Each PROPOSED card has a "Train with Foundry IQ" action that calls
 * POST /api/agents/{id}/train and opens a modal with the generated,
 * organization-grounded system prompt — the moment the factory "gives birth"
 * to a new agent that already knows the company.
 */
import { useState } from 'react';
import { trainAgent } from '../api/client.js';

const usd = (n) => `$${Number(n).toLocaleString('en-US')}`;

export default function Agents({ data }) {
  const portfolio = data.agent_portfolio;
  const [training, setTraining] = useState(null);   // agent id while loading
  const [trained, setTrained] = useState(null);     // train result for modal

  /** Call the backend to compose the grounded system prompt. */
  async function handleTrain(agent) {
    setTraining(agent.id);
    try {
      const result = await trainAgent(agent.id);
      setTrained(result);
    } catch (e) {
      alert(`Training failed: ${e.message}`);
    } finally {
      setTraining(null);
    }
  }

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Agent Factory output</div>
        <h2>Agent Portfolio</h2>
        <p>
          {portfolio.summary.implemented} agents implemented in this MVP,{' '}
          {portfolio.summary.proposed} proposed from diagnostic findings — total
          estimated impact {usd(portfolio.summary.total_estimated_yearly_impact_usd)}/year.
          Every proposal ships with scope, guardrails and human-in-the-loop checkpoints.
        </p>
      </div>

      <div className="agent-grid">
        {portfolio.proposals.map((a) => (
          <article
            key={a.id}
            className={`agent-card ${a.status === 'IMPLEMENTED' ? 'implemented' : 'proposed'}`}
          >
            <div className="meta">
              <span className="mono" style={{ color: 'var(--stone)', fontSize: 11 }}>{a.id}</span>
              <span className={`badge ${a.status === 'IMPLEMENTED' ? 'implemented' : 'proposed'}`}>
                {a.status}
              </span>
              <span className="badge tier">Tier {a.tier}</span>
            </div>

            <h4>{a.name}</h4>
            <p className="objective">{a.objective}</p>

            {/* Guardrails preview — first two rules, the full set lives in the prompt */}
            <ul className="evidence">
              {a.guardrails.slice(0, 2).map((g, i) => (
                <li key={i}>{g}</li>
              ))}
            </ul>

            <div className="meta">
              {a.estimated_yearly_impact_usd > 0 && (
                <span className="impact">{usd(a.estimated_yearly_impact_usd)}/yr</span>
              )}
              {a.status === 'PROPOSED' && (
                <button
                  className="btn"
                  onClick={() => handleTrain(a)}
                  disabled={training === a.id}
                  style={{ marginLeft: a.estimated_yearly_impact_usd > 0 ? 0 : 'auto' }}
                >
                  {training === a.id ? 'Grounding…' : 'Train with Foundry IQ'}
                </button>
              )}
            </div>
          </article>
        ))}
      </div>

      {/* ---- Train result modal ------------------------------------- */}
      {trained && (
        <div className="overlay" onClick={() => setTrained(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <header>
              <h3>
                <span className="seal" style={{ display: 'inline-grid', width: 26, height: 26, fontSize: 14, marginRight: 8, verticalAlign: 'middle' }}>改</span>
                {trained.agent_name} — grounded system prompt
              </h3>
              <button className="btn ghost" onClick={() => setTrained(null)}>Close</button>
            </header>
            <div className="prompt">{trained.system_prompt}</div>
            <footer>
              Grounding via Foundry IQ ({trained.foundry_mode} mode) · citations:{' '}
              {trained.grounding_citations.length
                ? trained.grounding_citations.map((c) => `[${c.id}] ${c.title}`).join(' · ')
                : 'none'}
            </footer>
          </div>
        </div>
      )}
    </>
  );
}
