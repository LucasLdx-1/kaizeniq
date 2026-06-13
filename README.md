<div align="center">

# 改 KaizenIQ

### Continuous improvement meets agentic AI

**An AI Agent Factory that diagnoses an ISO 9001 organization through its Microsoft 365 signals, grounds every conclusion in Foundry IQ, and proposes — then trains — a portfolio of specialized agents for digital transformation.**

*Microsoft Agents League Hackathon 2026 · Reasoning Agents track (Microsoft Foundry)*

</div>

---

## The problem

ISO 9001 organizations live a double life. On paper: controlled documents, defined KPIs, audit-ready processes. In practice: stale work instructions circulating as email attachments, corrective actions aging on forgotten Planner boards, managers spending hours every week manually compiling KPI emails, and approval bottlenecks visible only in Teams chat archaeology.

The gap between *the documented organization* and *the real organization* is exactly where audits fail, money leaks, and digital transformation initiatives die. Today, finding that gap requires weeks of consultant interviews.

## The solution

KaizenIQ reads both sides — the documented ISO 9001 processes **and** the organization's Microsoft 365 activity signals — and reasons across them with a multi-agent pipeline:

1. **Diagnose** — five specialized agents map drift, repetitive work, bottlenecks and ISO non-conformities, with evidence for every finding.
2. **Visualize** — every process becomes an auto-generated flowchart: the catalyst for transformation conversations.
3. **Propose** — the **Agent Factory** converts findings into a 14-agent portfolio: 7 agents implemented in this MVP plus 7 new specialized agents, each with complete specs — objective, scope, guardrails, human-in-the-loop checkpoints, success metrics and estimated yearly impact.
4. **Train** — one click asks Foundry IQ for the organizational grounding and composes a production-ready, citation-backed system prompt for any proposed agent. New agents are born already knowing the company.

> **Diagnostic result on the demo dataset:** 15/15 processes drifting · 11 non-conformities (4 critical) · ~2,000 recoverable hours/year · **~$86,584/year** estimated impact from the proposed agents.

## Microsoft IQ integration (Foundry IQ)

KaizenIQ uses **Foundry IQ** as its knowledge layer, following the official [IQ Series cookbooks](https://github.com/microsoft/iq-series):

| IQ Series pattern | KaizenIQ implementation |
|---|---|
| Knowledge Source over an Azure AI Search index | `kaizeniq-iso-processes` — one document per ISO process |
| Knowledge Base paired with an Azure OpenAI deployment | `kaizeniq-kb` + `gpt-4o-mini` for answer synthesis |
| Agentic retrieval with reasoning effort + citations | Every agent-training call and free-form Q&A returns grounded answers with `[PROC-xxx]` citations |
| SDK pin from the cookbook | `azure-search-documents==12.1.0b1` |

**Dual-mode design:** `FOUNDRY_MODE=live` uses real Azure resources (deployable via the [IQ Series Deploy to Azure button](https://aka.ms/iq-series/deploytoazure)); `FOUNDRY_MODE=mock` runs the identical pipeline fully offline against the same dataset — so the demo never depends on network or quota. The mock retriever mirrors live behavior: keyword retrieval, top-k selection, synthesized answer, citations.

### Foundry Local — a real Microsoft Foundry model, on-device

Because Azure OpenAI quota is unavailable on student subscriptions (a known Agents League limitation that Microsoft has publicly acknowledged), KaizenIQ also runs with **`FOUNDRY_MODE=local`**: a genuine Microsoft Foundry-hosted model (e.g. `phi-3.5-mini`) running **on-device** via [Foundry Local](https://learn.microsoft.com/azure/foundry-local), exposed through its OpenAI-compatible endpoint. This satisfies the minimum "at least one Microsoft Foundry hosted model" requirement with **no Azure subscription required**, and is fully reproducible by any judge.

In `local` mode the model performs real answer synthesis for: the **agent training** prompts, the **"Talk to the Agents"** chat, the free-form Q&A, and the **process intake** (inferring ISO clause and KPIs for user-added processes). Setup:

```bash
winget install Microsoft.FoundryLocal
foundry model run phi-3.5-mini
# then set FOUNDRY_MODE=local in backend/.env
```

### Beyond diagnosis — interactive, incremental, observable

- **Talk to the Agents** — chat with the Master Orchestrator; it answers grounded in the full process catalog (seeded + session-added) with `[PROC-xxx]` citations, synthesized by the local Foundry model.
- **Add Process** — paste a process (name + area + steps); Foundry Local infers its ISO clause, KPIs and criticality, generates its flowchart, and folds it into the live analysis. Session-scoped (resets on restart).
- **Company Map** — a Mermaid map of the whole organization grouped by macro-process; incremental (added processes appear automatically).
- **Telemetry & Safety** — live observability: agent/model call counts, latencies, an activity trace, and the consolidated guardrails enforced across the portfolio.

The simulated Microsoft 365 signals (Teams, Outlook, Planner, SharePoint) represent the organizational context that **Work IQ** surfaces in production; the data contract is isolated in one service so swapping mock JSON for real Work IQ calls is a single-file change.

## Architecture

```
                        ┌──────────────────────────────────────────┐
                        │            KaizenIQ Portal (React)        │
                        │  Dashboard · Agents · NCs · Flowcharts    │
                        └────────────────────┬─────────────────────┘
                                             │ REST
                        ┌────────────────────▼─────────────────────┐
                        │           FastAPI backend                 │
                        │  ┌─────────────────────────────────────┐ │
                        │  │        Master Orchestrator          │ │
                        │  │  7-step reasoning pipeline + cache  │ │
                        │  └──┬──────────────────────────────┬───┘ │
                        │     │                              │     │
                        │  ┌──▼───────────────┐   ┌──────────▼───┐ │
                        │  │ Diagnostic agents │   │ Agent Factory│ │
                        │  │ CurrentState      │   │ 14-agent     │ │
                        │  │ RepetitiveWork    │──▶│ portfolio +  │ │
                        │  │ Bottleneck        │   │ train_agent()│ │
                        │  │ NonConformity     │   └──────┬───────┘ │
                        │  │ Flowchart         │          │         │
                        │  └──┬───────────────┘           │         │
                        └─────┼───────────────────────────┼─────────┘
                              │ grounding queries          │ grounded prompts
                        ┌─────▼───────────────────────────▼─────────┐
                        │              Foundry IQ                    │
                        │  Knowledge Source ─▶ Knowledge Base        │
                        │  (Azure AI Search)   (+ gpt-4o-mini)       │
                        │        ▲    agentic retrieval + citations  │
                        └────────┼───────────────────────────────────┘
                                 │ indexed
                  ┌──────────────┴──────────────┐
                  │ ISO 9001 processes (15)      │   ┌─ M365 signals ─────────┐
                  │ data/iso_processes.json      │   │ Teams · Outlook ·       │
                  └─────────────────────────────┘   │ Planner · SharePoint    │
                                                    │ data/m365_activity.json │
                                                    │ (Work IQ in production) │
                                                    └─────────────────────────┘
```

## Quick start

**Prerequisites:** Python 3.11+, Node 18+.

```bash
# 1. Backend (runs in mock mode out of the box — no Azure needed)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Interactive docs: http://localhost:8000/docs

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev
# Portal: http://localhost:5173
```

### Live mode (real Foundry IQ)

1. Deploy the IQ Series infrastructure: <https://aka.ms/iq-series/deploytoazure> (Azure AI Search + Azure OpenAI).
2. Copy `.env.example` to `backend/.env` and fill in the endpoints from the deployment outputs.
3. Set `FOUNDRY_MODE=live`, then `POST /api/foundry/setup` once to create the index, knowledge source and knowledge base.

## API surface

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/analysis` | Full diagnostic + agent portfolio (cached) |
| POST | `/api/analysis/refresh` | Re-run all seven agents |
| POST | `/api/processes/analyze` | Add a process from pasted text — Foundry Local infers ISO clause, KPIs, draws the flowchart, folds it into the live analysis |
| GET | `/api/processes/{id}/flowchart` | Mermaid source for one process |
| GET | `/api/company-map` | Mermaid map of the whole organization (incremental) |
| GET | `/api/agents` | The 14-agent portfolio |
| POST | `/api/agents/{id}/train` | Generate a Foundry-grounded system prompt |
| POST | `/api/chat` | Talk to the Master Orchestrator (grounded in all processes, with citations) |
| GET | `/api/telemetry` | Runtime observability: calls, latencies, guardrails |
| GET | `/api/non-conformities` | ISO findings with clauses + remediation |
| POST | `/api/foundry/query` | Free-form grounded Q&A against the KB |
| POST | `/api/foundry/setup` | Create live Foundry IQ resources |

## Project structure

```
kaizeniq/
├── backend/
│   ├── main.py                          # FastAPI bootstrap
│   └── app/
│       ├── core/config.py               # env config, dual-mode flag
│       ├── services/
│       │   ├── foundry_iq_service.py    # Foundry IQ client (cookbook patterns)
│       │   └── mock_data_service.py     # demo data loaders
│       ├── agents/
│       │   ├── diagnostic_agents.py     # 5 diagnostic sub-agents
│       │   ├── agent_factory.py         # 14-agent portfolio generator
│       │   └── orchestrator.py          # pipeline + train_agent()
│       └── api/routes.py                # REST surface
├── frontend/                            # React + Vite portal
│   └── src/pages/                       # Dashboard · Agents · NCs · Processes
├── data/
│   ├── iso_processes.json               # 15 synthetic ISO 9001 processes
│   └── m365_activity.json               # synthetic M365 signals
└── docs/ARCHITECTURE.md
```

## Responsible AI & data disclaimer

- **All data in this repository is synthetic.** "Meridian Industries Ltd.", its employees, processes, emails and metrics are fictional, generated for this hackathon. No real organizational or personal data is used.
- Every agent operates **read-only** with explicit guardrails; proposed automation agents require human approval gates by specification.
- The Compliance Guardrails Agent pattern bakes governance into the factory itself: no agent ships without an approved guardrail set.

## Roadmap beyond the hackathon

- Replace mock M365 signals with live **Work IQ** retrieval (REST/MCP).
- Instantiate trained agents directly in **Microsoft Foundry Agent Service** using the generated system prompts.
- Expose the knowledge base's **MCP endpoint** so trained agents share one grounded brain.
- **Fabric IQ** integration for KPI time-series instead of point-in-time snapshots.

---

<div align="center">

Built by **Lucas** ([@LucasLdx-1](https://github.com/LucasLdx-1)) for the Microsoft Agents League Hackathon 2026.

改善 — *change for the better.*

</div>
