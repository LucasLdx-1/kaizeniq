<div align="center">

# 改 KaizenIQ

### Continuous improvement meets agentic AI

**An AI Agent Factory grounded in ISO 9001 process knowledge. KaizenIQ uses an organization's mapped processes so that AI agents can understand the whole company, and from that understanding, proposes the specialized agents that will drive its digital transformation, monitoring, and continuous improvement.**

*Microsoft Agents League Hackathon 2026 · Reasoning Agents track (Microsoft Foundry)*

</div>

---

## The idea

Most agents are asked to reason about a business they know nothing about. KaizenIQ starts from a different premise: ISO 9001 certified organizations already have their processes documented, with owners, KPIs, and clauses. That documented knowledge is exactly what an agent needs to truly understand a company.

KaizenIQ ingests those process flows as its knowledge base and grounds every agent in them. From that understanding, it does two things: it diagnoses where the organization can improve, and it proposes a portfolio of specialized agents to drive digital transformation, continuous monitoring, and improvement. ISO 9001 is not the goal here. It is the structured, trustworthy source of organizational knowledge that makes grounded agentic reasoning possible.

## How it works

A Master Orchestrator runs a seven-step reasoning pipeline over the process knowledge:

1. **Understand** — read every documented process and build a complete picture of the organization.
2. **Diagnose** — specialized agents identify drift, repetitive manual work, bottlenecks and ISO non-conformities, each backed by evidence and mapped to the clause it threatens.
3. **Visualize** — every process becomes an auto-generated flowchart, and the whole organization becomes a single process map.
4. **Propose** — the **Agent Factory** converts that understanding into a portfolio of specialized agents for transformation and monitoring, each with a complete spec: objective, scope, guardrails, human-in-the-loop checkpoints, success metrics and estimated impact.
5. **Train** — one click pulls organizational grounding from the Foundry model and composes a production-ready, citation-backed system prompt, so a new agent is born already knowing the company.

You can grow the knowledge live: paste a new process and the Foundry model infers its ISO clause and KPIs, draws its flowchart, and folds it into the company-wide map and the orchestrator's knowledge. The **Talk to the Agents** chat lets you ask the orchestrator anything about the organization, grounded in the full process catalog with citations.

> **Diagnostic result on the demo dataset:** 15/15 processes analyzed · 11 non-conformities (4 critical) · ~2,000 recoverable hours/year · **~$86,584/year** estimated impact from the proposed agents.

## Microsoft IQ integration (Foundry IQ)

KaizenIQ uses **Foundry IQ** as its knowledge layer, following the official [IQ Series cookbooks](https://github.com/microsoft/iq-series):

| IQ Series pattern | KaizenIQ implementation |
|---|---|
| Knowledge Source over an Azure AI Search index | `kaizeniq-iso-processes` — one document per ISO process |
| Knowledge Base paired with a model deployment | `kaizeniq-kb` for grounded answer synthesis |
| Agentic retrieval with reasoning effort + citations | Every agent-training call and chat returns grounded answers with `[PROC-xxx]` citations |
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
              ┌──────────────────────────────────────────────────────┐
              │                 KaizenIQ Portal (React)               │
              │  Dashboard · Talk to Agents · Add Process · Company    │
              │  Map · Agent Portfolio · Non-Conformities · Telemetry  │
              └────────────────────────┬─────────────────────────────┘
                                       │ REST
              ┌────────────────────────▼─────────────────────────────┐
              │                   FastAPI backend                     │
              │  ┌─────────────────────────────────────────────────┐ │
              │  │              Master Orchestrator                │ │
              │  │     7-step reasoning pipeline + chat + train    │ │
              │  └──┬───────────────────────────────────────┬──────┘ │
              │     │                                       │        │
              │  ┌──▼───────────────┐          ┌────────────▼──────┐ │
              │  │ Diagnostic agents │          │   Agent Factory   │ │
              │  │ CurrentState      │  ───────▶│  agent portfolio  │ │
              │  │ RepetitiveWork    │          │  + train_agent()  │ │
              │  │ Bottleneck        │          └────────┬──────────┘ │
              │  │ NonConformity     │                   │            │
              │  │ Flowchart         │   + Telemetry     │            │
              │  └──┬───────────────┘     instrumentation│            │
              └─────┼─────────────────────────────────────┼──────────┘
                    │ grounding / chat queries             │ grounded prompts
              ┌─────▼─────────────────────────────────────▼──────────┐
              │         Foundry IQ knowledge layer                    │
              │  Knowledge Source ─▶ Knowledge Base ─▶ synthesis      │
              │  retrieval + citations [PROC-xxx]                     │
              │                                                       │
              │  Synthesis model (dual-mode):                         │
              │   • FOUNDRY_MODE=local → Foundry Local (phi-3.5-mini, │
              │     on-device, OpenAI-compatible) ← used in this demo │
              │   • FOUNDRY_MODE=live  → Azure AI Search + AOAI       │
              │   • FOUNDRY_MODE=mock  → deterministic offline        │
              └────────┬──────────────────────────────────────────────┘
                       │ knowledge
        ┌──────────────┴──────────────┐
        │ ISO 9001 processes           │   ┌─ M365 signals (synthetic) ─┐
        │ (15 seeded + session-added)  │   │ Teams · Outlook · Planner · │
        │ data/iso_processes.json      │   │ SharePoint                  │
        │ dynamic in-memory store      │   │ stands in for Work IQ       │
        └─────────────────────────────┘   └─────────────────────────────┘
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

## Roadmap — completing the vision

The ISO process knowledge is the foundation. The natural next step is to enrich it with the other two Microsoft IQ layers:

- **Work IQ** — bring in real organizational context from Microsoft 365 work signals (collaboration patterns, where a task sits in the flow of work), instead of the synthetic signals used here.
- **Fabric IQ** — add a semantic layer modeling the relationships between processes, roles, risks, and outcomes, so agents reason over business meaning, not just documents.
- Instantiate trained agents directly in **Microsoft Foundry Agent Service** using the generated system prompts.
- Expose the knowledge base's **MCP endpoint** so trained agents share one grounded brain.

**A note on honesty:** Work IQ and Fabric IQ are not in this submission because integrating them requires paid Azure access that wasn't feasible for this hackathon. To demonstrate the intended Work IQ context layer, KaizenIQ uses synthetic Microsoft 365 signals (Teams, Outlook, Planner, SharePoint) that stand in for what Work IQ would provide in production — the data contract is isolated in one service, so swapping the mock JSON for real Work IQ calls is a single-file change. Likewise, the Foundry model runs on-device via Foundry Local because Azure OpenAI quota is unavailable on student subscriptions (a limitation Microsoft has publicly acknowledged for this hackathon).

---

<div align="center">

Built by **Lucas** ([@LucasLdx-1](https://github.com/LucasLdx-1)) for the Microsoft Agents League Hackathon 2026.

改善 — *change for the better.*

</div>
