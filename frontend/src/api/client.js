/**
 * KaizenIQ — API client
 * =====================
 * Thin fetch wrapper. All calls use relative /api paths: in development the
 * Vite proxy forwards them to the FastAPI backend (see vite.config.js).
 */

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json();
}

/** Full diagnostic + agent portfolio (cached server-side). */
export const getAnalysis = () => request('/api/analysis');

/** Mermaid source for one process flowchart. */
export const getFlowchart = (id) => request(`/api/processes/${id}/flowchart`);

/** Generate the grounded system prompt for a proposed agent. */
export const trainAgent = (id) =>
  request(`/api/agents/${id}/train`, { method: 'POST' });

/** Free-form grounded Q&A against the Foundry IQ knowledge base. */
export const queryFoundry = (question) =>
  request('/api/foundry/query', {
    method: 'POST',
    body: JSON.stringify({ question, effort: 'low' }),
  });

/** Add a new process (name + area + steps); Foundry Local infers the rest. */
export const analyzeProcess = (name, macro_process, steps) =>
  request('/api/processes/analyze', {
    method: 'POST',
    body: JSON.stringify({ name, macro_process, steps }),
  });

/** Talk to the Master Orchestrator (grounded in all processes). */
export const sendChat = (message) =>
  request('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });

/** Runtime telemetry + safety snapshot. */
export const getTelemetry = () => request('/api/telemetry');

/** Company-wide process map (Mermaid). */
export const getCompanyMap = () => request('/api/company-map');
