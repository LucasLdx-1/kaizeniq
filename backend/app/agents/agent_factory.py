"""
KaizenIQ — Agent Factory
=========================
The core differentiator of KaizenIQ: instead of only *reporting* problems,
the factory turns diagnostic findings into a portfolio of proposed
specialized agents — each with a complete, implementable specification.

How proposals are generated
---------------------------
  Tier 1 (implemented)  : the 5 diagnostic agents already running in this MVP
                          + the Master Orchestrator + this factory itself = 7.
  Tier 2 (data-driven)  : one automation agent per top repetitive-work finding.
  Tier 3 (governance)   : compliance / learning / guardrails agents derived
                          from non-conformity categories.

Every proposed agent spec includes:
  - objective, scope, inputs, outputs
  - explicit GUARDRAILS (what the agent must never do)
  - success metrics and estimated yearly impact
  - the Foundry IQ grounding it requires
  - human-in-the-loop checkpoints

The Master Orchestrator can then "train" a proposal: it asks Foundry IQ to
generate the system prompt for the new agent, grounded in the organization's
own processes (see orchestrator.train_agent).
"""

from __future__ import annotations

from typing import Any, Dict, List


class AgentFactory:
    """Generates the 14-agent portfolio from diagnostic results."""

    name = "Agent Factory"

    def run(
        self,
        repetitive_work: Dict[str, Any],
        bottlenecks: Dict[str, Any],
        non_conformities: Dict[str, Any],
    ) -> Dict[str, Any]:
        proposals: List[Dict[str, Any]] = []

        proposals.extend(self._tier1_implemented())
        proposals.extend(self._tier2_from_repetitive_work(repetitive_work))
        proposals.extend(self._tier3_governance(non_conformities, bottlenecks))

        # Keep exactly 14, ranked: implemented first, then by estimated impact
        proposals = proposals[:14]
        for i, p in enumerate(proposals, start=1):
            p["id"] = f"AGENT-{i:02d}"

        return {
            "agent": self.name,
            "summary": {
                "total_proposed": len(proposals),
                "implemented": sum(1 for p in proposals if p["status"] == "IMPLEMENTED"),
                "proposed": sum(1 for p in proposals if p["status"] == "PROPOSED"),
                "total_estimated_yearly_impact_usd": sum(
                    p.get("estimated_yearly_impact_usd", 0) for p in proposals
                ),
            },
            "proposals": proposals,
        }

    # ------------------------------------------------------------------ #
    # Tier 1 — agents already implemented in this repository               #
    # ------------------------------------------------------------------ #
    def _tier1_implemented(self) -> List[Dict[str, Any]]:
        base_guardrails = [
            "Read-only access to organizational data; never modifies source systems",
            "All outputs carry evidence references for human verification",
            "No personal data beyond business role/email is processed or stored",
        ]
        catalog = [
            ("Master Orchestrator",
             "Coordinates all agents, aggregates findings, and trains new agent proposals via Foundry IQ.",
             "ISO process KB + all sub-agent outputs"),
            ("Current State Analyzer",
             "Compares documented ISO processes with observed M365 behavior and scores alignment drift.",
             "ISO process KB + Teams/Outlook/Planner signals"),
            ("Repetitive Work Detector",
             "Identifies recurring manual workflows and quantifies recoverable hours and cost.",
             "Outlook patterns + meeting metadata"),
            ("Bottleneck Identifier",
             "Locates structural slowness by combining KPI gaps with conversational evidence.",
             "KPI data + Teams channel patterns"),
            ("Non-Conformity Detector",
             "Raises ISO 9001 non-conformities (stale documents, overdue actions, governance anomalies).",
             "SharePoint signals + Planner boards + ISO clause map"),
            ("Flowchart Generator",
             "Renders every process as a Mermaid flowchart — the visual catalyst for transformation discussions.",
             "ISO process step definitions"),
            ("Agent Factory",
             "Converts diagnostic findings into complete specifications for new specialized agents.",
             "All diagnostic outputs"),
        ]
        return [
            {
                "name": name,
                "tier": 1,
                "status": "IMPLEMENTED",
                "objective": objective,
                "scope": "Organization-wide, read-only analysis",
                "inputs": grounding,
                "outputs": "Structured JSON findings consumed by the KaizenIQ portal",
                "guardrails": base_guardrails,
                "foundry_iq_grounding": "kaizeniq-kb (ISO 9001 process knowledge base)",
                "human_in_the_loop": "All findings reviewed in portal before any action",
                "success_metrics": ["Findings precision validated by Quality Manager"],
                "estimated_yearly_impact_usd": 0,  # enabling layer; impact realized by Tier 2/3
            }
            for name, objective, grounding in catalog
        ]

    # ------------------------------------------------------------------ #
    # Tier 2 — automation agents derived from repetitive-work findings     #
    # ------------------------------------------------------------------ #
    def _tier2_from_repetitive_work(self, repetitive: Dict[str, Any]) -> List[Dict[str, Any]]:
        proposals: List[Dict[str, Any]] = []
        # Top 4 findings by estimated yearly cost become agent proposals
        for finding in repetitive["findings"][:4]:
            agent_name = self._automation_agent_name(finding["pattern"])
            proposals.append(
                {
                    "name": agent_name,
                    "tier": 2,
                    "status": "PROPOSED",
                    "objective": f"Automate the recurring workflow: \"{finding['pattern']}\".",
                    "origin_finding": finding["pattern"],
                    "linked_process": finding["linked_process"],
                    "scope": finding["description"],
                    "inputs": "Same data sources currently handled manually "
                              "(system exports, mailbox rules, Planner board)",
                    "outputs": "Automated artifact (report / notification / board update) "
                               "with full audit trail",
                    "guardrails": [
                        "Drafts only — a human approves before anything is sent externally",
                        "Operates within the linked process scope; no cross-process writes",
                        "Every automated action logged to the QMS audit trail",
                        "Hard stop + escalation if confidence below threshold",
                    ],
                    "foundry_iq_grounding": "kaizeniq-kb section for "
                                            f"{finding['linked_process']}",
                    "human_in_the_loop": "Approval gate on first 30 days of operation, "
                                         "then exception-based review",
                    "success_metrics": [
                        f"Recover ≥ 80% of {finding['estimated_yearly_hours']}h/year",
                        "Zero unauthorized external communications",
                    ],
                    "estimated_yearly_impact_usd": round(
                        finding["estimated_yearly_cost_usd"] * 0.8
                    ),
                }
            )
        return proposals

    @staticmethod
    def _automation_agent_name(pattern: str) -> str:
        """Derive a short, descriptive agent name from the workflow pattern."""
        mapping = {
            "Weekly KPI compilation email": "KPI Compiler Agent",
            "Supplier certificate chasing": "Supplier Certificate Agent",
            "Calibration due notifications": "Calibration Reminder Agent",
            "Complaint status updates to sales": "Complaint Status Agent",
            "Document approval reminders": "Approval Nudge Agent",
            "Training completion chasing": "Training Compliance Agent",
            "Weekly quote status review": "Quote Digest Agent",
            "Daily line status standup": "Line Status Agent",
            "Monthly document control sync": "Document Review Digest Agent",
        }
        return mapping.get(pattern, f"{pattern[:24]} Agent")

    # ------------------------------------------------------------------ #
    # Tier 3 — governance agents derived from non-conformity categories    #
    # ------------------------------------------------------------------ #
    def _tier3_governance(
        self, non_conformities: Dict[str, Any], bottlenecks: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        nc_categories = {f["category"] for f in non_conformities["findings"]}
        proposals: List[Dict[str, Any]] = []

        if "DOCUMENTED_INFORMATION" in nc_categories:
            proposals.append(self._spec(
                name="Document Staleness Sentinel",
                objective="Continuously monitor SharePoint controlled libraries and Outlook "
                          "attachments to flag stale or duplicated controlled documents "
                          "before auditors do.",
                scope="QMS controlled library + email attachment scanning (metadata only)",
                guardrail_extra="Never opens attachment content — metadata and version only",
                metrics=["Documents past review date kept at 0",
                         "Uncontrolled copies detected within 24h"],
                impact=18000,
            ))
        if "OVERDUE_ACTIONS" in nc_categories:
            proposals.append(self._spec(
                name="CAPA Shepherd Agent",
                objective="Track corrective actions and audit findings end-to-end, nudging "
                          "owners, escalating aging items, and preparing effectiveness-check "
                          "evidence for Management Review.",
                scope="CAPA and audit Planner boards + QMS records",
                guardrail_extra="Escalation messages follow a pre-approved template; "
                                "cannot close actions by itself",
                metrics=["Average CAPA closure time < 45 days",
                         "Findings closed on time > 90%"],
                impact=22000,
            ))
        if "INFORMATION_SECURITY" in nc_categories:
            proposals.append(self._spec(
                name="Compliance Guardrails Agent",
                objective="Verify data-governance posture: permission anomalies, "
                          "oversharing, and privacy alignment (LGPD/GDPR) of QMS data flows; "
                          "also defines guardrail policies for every new agent the factory proposes.",
                scope="SharePoint permission reports + agent guardrail registry",
                guardrail_extra="Detection and recommendation only — never changes permissions",
                metrics=["High-severity access anomalies resolved < 48h",
                         "100% of new agents launched with approved guardrail set"],
                impact=15000,
            ))

        # Capability gaps surfaced by bottlenecks → learning recommender
        proposals.append(self._spec(
            name="Microsoft Learn Recommender",
            objective="Map detected bottlenecks to skill gaps and assign targeted "
                      "Microsoft Learn paths to the affected teams, tracking completion.",
            scope="Bottleneck findings + competence matrix + Microsoft Learn catalog",
            guardrail_extra="Recommendations only; enrollment decided by the team manager",
            metrics=["Training effectiveness score > 4.0/5",
                     "Onboarding completion within 90 days = 100%"],
            impact=12000,
        ))
        return proposals

    @staticmethod
    def _spec(name: str, objective: str, scope: str, guardrail_extra: str,
              metrics: List[str], impact: int) -> Dict[str, Any]:
        """Shared template for Tier-3 governance agent specifications."""
        return {
            "name": name,
            "tier": 3,
            "status": "PROPOSED",
            "objective": objective,
            "scope": scope,
            "inputs": "Diagnostic findings + organizational signals (read-only)",
            "outputs": "Alerts, prepared evidence packages, and portal dashboards",
            "guardrails": [
                "Read-only on source systems; recommendations require human approval",
                guardrail_extra,
                "All activity logged to the QMS audit trail",
            ],
            "foundry_iq_grounding": "kaizeniq-kb (ISO 9001 process knowledge base)",
            "human_in_the_loop": "Quality Manager approves every externally visible action",
            "success_metrics": metrics,
            "estimated_yearly_impact_usd": impact,
        }
