"""
KaizenIQ — Master Orchestrator
===============================
The central reasoning coordinator. Runs the full diagnostic pipeline,
feeds findings into the Agent Factory, and can "train" any proposed agent
by generating its grounded system prompt through Foundry IQ.

Pipeline (multi-step reasoning, matching the hackathon rubric):

  Step 1  Flowcharts          — visualize every documented process (catalyst)
  Step 2  Current State       — documented vs. observed alignment
  Step 3  Repetitive Work     — automation candidates with $ impact
  Step 4  Bottlenecks         — where the organization is slow and why
  Step 5  Non-Conformities    — ISO 9001 findings with clauses + remediation
  Step 6  Agent Factory       — 14-agent portfolio with full specifications
  Step 7  Roadmap synthesis   — phased transformation plan

Results are cached in-memory so the portal loads instantly after the first run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.agents.agent_factory import AgentFactory
from app.agents.diagnostic_agents import (
    BottleneckAgent,
    CurrentStateAgent,
    FlowchartAgent,
    NonConformityAgent,
    RepetitiveWorkAgent,
)
from app.services.foundry_iq_service import foundry_iq
from app.services.mock_data_service import get_organization

logger = logging.getLogger("kaizeniq.orchestrator")


class MasterOrchestrator:
    """Coordinates the seven implemented agents and exposes their results."""

    def __init__(self) -> None:
        self.flowchart_agent = FlowchartAgent()
        self.current_state_agent = CurrentStateAgent()
        self.repetitive_work_agent = RepetitiveWorkAgent()
        self.bottleneck_agent = BottleneckAgent()
        self.non_conformity_agent = NonConformityAgent()
        self.agent_factory = AgentFactory()
        self._last_result: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------ #
    # Full pipeline                                                        #
    # ------------------------------------------------------------------ #
    def invalidate(self) -> None:
        """Clear the cached analysis so the next call recomputes from scratch.

        Called when the process set changes (e.g. a user adds a new process),
        so the diagnostics, Agent Factory and roadmap all reflect it.
        """
        self._last_result = None

    def run_full_analysis(self, force: bool = False) -> Dict[str, Any]:
        """Execute all steps. Cached after first run unless force=True."""
        if self._last_result and not force:
            return self._last_result

        from app.services.telemetry_service import telemetry

        logger.info("Orchestration started")
        started = datetime.now(timezone.utc)
        telemetry.record("orchestration_started", "Master Orchestrator pipeline")

        # Step 1 — visual catalyst
        with telemetry.timer("agent_run", "Flowchart Generator"):
            flowcharts = self.flowchart_agent.run()

        # Steps 2–5 — diagnostics
        with telemetry.timer("agent_run", "Current State Analyzer"):
            current_state = self.current_state_agent.run()
        with telemetry.timer("agent_run", "Repetitive Work Detector"):
            repetitive_work = self.repetitive_work_agent.run()
        with telemetry.timer("agent_run", "Bottleneck Identifier"):
            bottlenecks = self.bottleneck_agent.run()
        with telemetry.timer("agent_run", "Non-Conformity Detector"):
            non_conformities = self.non_conformity_agent.run()

        # Step 6 — the differentiator
        with telemetry.timer("agent_run", "Agent Factory"):
            agent_portfolio = self.agent_factory.run(
                repetitive_work=repetitive_work,
                bottlenecks=bottlenecks,
                non_conformities=non_conformities,
            )

        # Step 7 — roadmap synthesis
        roadmap = self._build_roadmap(agent_portfolio)

        result = {
            "organization": get_organization(),
            "foundry_iq": foundry_iq.status(),
            "generated_at": started.isoformat(),
            "executive_summary": self._executive_summary(
                current_state, repetitive_work, non_conformities, agent_portfolio
            ),
            "flowcharts": flowcharts,
            "current_state": current_state,
            "repetitive_work": repetitive_work,
            "bottlenecks": bottlenecks,
            "non_conformities": non_conformities,
            "agent_portfolio": agent_portfolio,
            "roadmap": roadmap,
        }
        self._last_result = result
        telemetry.record("orchestration_complete",
                         f"{len(agent_portfolio['proposals'])} agents, "
                         f"{non_conformities['summary']['total']} non-conformities")
        logger.info("Orchestration complete")
        return result

    # ------------------------------------------------------------------ #
    # Roadmap synthesis                                                    #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_roadmap(agent_portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase the proposed agents into a realistic rollout:
          Phase 1 (weeks 1–2)  : governance foundations (Tier-3 sentinels)
          Phase 2 (weeks 3–6)  : top-2 automation agents (highest $ impact)
          Phase 3 (weeks 7–10) : remaining automation agents + review cycle
        """
        proposed = [p for p in agent_portfolio["proposals"] if p["status"] == "PROPOSED"]
        tier3 = [p for p in proposed if p["tier"] == 3]
        tier2 = sorted(
            (p for p in proposed if p["tier"] == 2),
            key=lambda p: p["estimated_yearly_impact_usd"],
            reverse=True,
        )
        phases = [
            {
                "phase": 1,
                "name": "Governance foundations",
                "weeks": "1–2",
                "agents": [p["name"] for p in tier3],
                "rationale": "Guardrails, document hygiene and CAPA discipline must be in "
                             "place before automation agents act on organizational data.",
            },
            {
                "phase": 2,
                "name": "High-impact automation",
                "weeks": "3–6",
                "agents": [p["name"] for p in tier2[:2]],
                "rationale": "Largest recoverable cost first; builds momentum and trust.",
            },
            {
                "phase": 3,
                "name": "Scale & review",
                "weeks": "7–10",
                "agents": [p["name"] for p in tier2[2:]],
                "rationale": "Remaining automations plus effectiveness review of phases 1–2 "
                             "in the next Management Review.",
            },
        ]
        return {
            "phases": phases,
            "total_estimated_yearly_impact_usd":
                agent_portfolio["summary"]["total_estimated_yearly_impact_usd"],
        }

    # ------------------------------------------------------------------ #
    # Executive summary                                                    #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _executive_summary(current_state, repetitive, ncs, portfolio) -> Dict[str, Any]:
        return {
            "headline": (
                f"{current_state['summary']['drifting']} of "
                f"{current_state['summary']['total_processes']} processes show drift between "
                f"documentation and practice; {ncs['summary']['total']} non-conformities "
                f"detected; {portfolio['summary']['proposed']} new agents proposed with "
                f"~${portfolio['summary']['total_estimated_yearly_impact_usd']:,}/year "
                f"estimated impact."
            ),
            "processes_aligned": current_state["summary"]["aligned"],
            "processes_drifting": current_state["summary"]["drifting"],
            "recoverable_hours_per_year":
                repetitive["summary"]["total_recoverable_hours_per_year"],
            "recoverable_cost_usd_per_year":
                repetitive["summary"]["total_recoverable_cost_usd_per_year"],
            "open_non_conformities": ncs["summary"]["total"],
            "agents_proposed": portfolio["summary"]["proposed"],
        }

    # ------------------------------------------------------------------ #
    # Agent "training" — the factory's second act                          #
    # ------------------------------------------------------------------ #
    def train_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Generate the grounded system prompt for a proposed agent.

        Flow:
          1. Find the proposal in the latest portfolio
          2. Query Foundry IQ for the linked process context (grounding)
          3. Compose a production-ready system prompt embedding objective,
             guardrails, grounding citations and escalation rules

        This is what makes the factory more than a report generator: every
        proposal ships ready to be instantiated as a Foundry agent.
        """
        analysis = self.run_full_analysis()
        proposal = next(
            (p for p in analysis["agent_portfolio"]["proposals"] if p["id"] == agent_id),
            None,
        )
        if proposal is None:
            return {"error": f"Agent {agent_id} not found"}

        # Grounding query — pulls the relevant process knowledge from Foundry IQ.
        # When the proposal is linked to a specific process, anchor the query on
        # that process name so citations land on the right knowledge.
        linked = proposal.get("linked_process")
        anchor = ""
        if linked:
            from app.services.mock_data_service import get_process_by_id
            linked_proc = get_process_by_id(linked)
            if linked_proc:
                anchor = f"{linked_proc['name']} ({linked}). "
        grounding_question = (
            f"{anchor}Summarize the process, KPIs and current issues relevant to: "
            f"{proposal['objective']}"
        )
        grounding = foundry_iq.query(grounding_question, effort="low")

        system_prompt = self._compose_system_prompt(proposal, grounding)
        return {
            "agent_id": agent_id,
            "agent_name": proposal["name"],
            "grounding_citations": grounding["citations"],
            "foundry_mode": grounding["mode"],
            "system_prompt": system_prompt,
        }

    @staticmethod
    def _compose_system_prompt(proposal: Dict[str, Any], grounding: Dict[str, Any]) -> str:
        guardrails = "\n".join(f"  - {g}" for g in proposal["guardrails"])
        metrics = "\n".join(f"  - {m}" for m in proposal["success_metrics"])
        return f"""You are {proposal['name']}, a specialized agent operating inside an
ISO 9001:2015 certified organization.

OBJECTIVE
{proposal['objective']}

ORGANIZATIONAL GROUNDING (retrieved via Foundry IQ — cite these sources):
{grounding['answer']}

SCOPE
{proposal['scope']}

GUARDRAILS (non-negotiable):
{guardrails}

HUMAN IN THE LOOP
{proposal['human_in_the_loop']}

SUCCESS METRICS
{metrics}

OPERATING RULES
1. Ground every statement in the knowledge base; cite process IDs (e.g. PROC-004).
2. When confidence is low or data is missing, stop and escalate to the Quality Manager.
3. Log every action with timestamp, evidence and rationale to the QMS audit trail.
4. Never act outside the linked process scope.
"""


# Module-level singleton consumed by the API layer.
orchestrator = MasterOrchestrator()
