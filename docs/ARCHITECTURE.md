# KaizenIQ — Architecture

This document explains *how* KaizenIQ reasons, for reviewers who want more depth
than the README.

## Design principles

1. **Reasoning is layered, not monolithic.** Deterministic structured analysis
   (the diagnostic agents) feeds a knowledge-grounded reasoning layer
   (Foundry IQ). Findings are therefore *explainable*: every number traces back
   to a JSON record, every narrative traces back to a citation.
2. **The demo can never fail.** `FOUNDRY_MODE=mock` replays the identical
   pipeline offline. Live mode is a configuration change, not a code change.
3. **Agents are specifications first.** The Agent Factory's output is not a
   list of names — each proposal carries scope, guardrails, HITL checkpoints
   and success metrics. "Training" composes those specs with Foundry IQ
   grounding into a deployable system prompt.

## The 7-step orchestration pipeline

| Step | Agent | Input | Output |
|---|---|---|---|
| 1 | Flowchart Generator | ISO process step lists | Mermaid graph per process (decision steps → diamonds, KPI node appended) |
| 2 | Current State Analyzer | processes + Teams/Outlook/Planner signals | alignment label per process (`ALIGNED` → `CRITICAL_DRIFT`) with evidence list |
| 3 | Repetitive Work Detector | Outlook workflow patterns + meeting metadata | automation candidates with hours/yr and $/yr (rate documented below) |
| 4 | Bottleneck Identifier | KPI gaps + conversational patterns | bottleneck signals with severity |
| 5 | Non-Conformity Detector | SharePoint staleness + Planner overdue + access anomalies | NC findings with ISO clause + remediation |
| 6 | Agent Factory | outputs of 3, 4, 5 | 14-agent portfolio (Tier 1 implemented, Tier 2 automation, Tier 3 governance) |
| 7 | Roadmap synthesis | portfolio | 3-phase rollout: governance → high-impact automation → scale & review |

The Master Orchestrator caches the result in memory; `POST /api/analysis/refresh`
forces a re-run.

### Drift scoring (step 2)

Each piece of evidence adds to a misalignment score: Teams pattern +1,
stale/duplicated document mention +2, overdue Planner board +2, each
off-target KPI +1. Thresholds: 0 = `ALIGNED`, ≤2 = `MINOR_DRIFT`,
≤5 = `SIGNIFICANT_DRIFT`, else `CRITICAL_DRIFT`. Deliberately simple and
auditable — sophistication belongs in the grounded narrative, not the
arithmetic.

### Impact economics (steps 3 & 6)

`yearly_hours = hours_per_week × 48`; `yearly_cost = yearly_hours × $35`
(blended hourly rate, a documented assumption of the synthetic dataset).
Tier-2 proposals claim 80% of the underlying waste as recoverable impact.

## Foundry IQ integration detail

Live mode follows the IQ Series cookbooks step by step:

1. **Index** — `kaizeniq-iso-index`, one document per process: `id`, `title`,
   searchable `content` (description + clause + steps + KPIs + version),
   facetable `macro_process` and `criticality`.
2. **Knowledge Source** — `kaizeniq-iso-processes` over that index.
3. **Knowledge Base** — `kaizeniq-kb`, pairing the source with a `gpt-4o-mini`
   deployment for answer synthesis.
4. **Retrieval** — `retrieve_from_knowledge_base(...)` with
   `reasoning_effort ∈ {minimal, low, medium}` (Episode 3 semantics).

The mock retriever reproduces the same contract: keyword scoring over the same
fields, top-3 selection, synthesized answer text, `[{id, title}]` citations.
This keeps the frontend and the agent-training flow byte-compatible across
modes.

### Agent training flow

```
POST /api/agents/AGENT-09/train
  └─ orchestrator.train_agent
       ├─ locate proposal in latest portfolio
       ├─ grounding query anchored on the linked process name
       │    └─ foundry_iq.query(...)  →  answer + citations
       └─ compose system prompt:
            identity · objective · ORGANIZATIONAL GROUNDING (cited) ·
            scope · guardrails · HITL · success metrics · operating rules
```

The resulting prompt is what you would paste into a Microsoft Foundry Agent
Service agent definition — which is exactly the post-hackathon roadmap.

## Security & governance posture

- Read-only by construction: no agent writes to source systems.
- Secrets only via environment variables; `.env` is git-ignored, and the repo
  ships `.env.example` instead.
- Synthetic data only; the dataset disclaimer lives in both the README and the
  data files themselves.
- Guardrails are first-class spec fields, and Tier 3 includes a Compliance
  Guardrails Agent whose job is to keep it that way as the portfolio grows.
