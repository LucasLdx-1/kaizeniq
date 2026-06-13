"""
KaizenIQ — Diagnostic Agents
=============================
Five specialized sub-agents that analyze the organization by cross-referencing
documented ISO 9001 processes with simulated Microsoft 365 signals.

Each agent is intentionally small, deterministic, and explainable:
the *reasoning* layer (interpretation, prioritization, recommendation text)
is delegated to Foundry IQ; these agents do the structured analysis that
feeds it.

Agents in this module:
  1. CurrentStateAgent     — documented process vs. observed M365 behavior
  2. RepetitiveWorkAgent   — recurring manual workflows (automation candidates)
  3. BottleneckAgent       — slow decisions / KPI gaps / meeting overload
  4. NonConformityAgent    — ISO non-conformities (stale docs, overdue actions)
  5. FlowchartAgent        — Mermaid flowcharts of each process (the "catalyst")
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List

from app.services.mock_data_service import get_processes, load_m365_activity


# --------------------------------------------------------------------------- #
# 1. Current State Agent                                                       #
# --------------------------------------------------------------------------- #
class CurrentStateAgent:
    """
    Compares "what the ISO documentation says" with "what M365 signals show".

    Output per process: an alignment assessment with the concrete evidence
    (chat patterns, document mentions, planner status) supporting it.
    """

    name = "Current State Analyzer"

    def run(self) -> Dict[str, Any]:
        processes = get_processes()
        m365 = load_m365_activity()

        # Index M365 evidence by linked process for fast lookup
        channel_by_proc = {
            c["linked_process"]: c for c in m365["teams_activity"]["channels"]
        }
        doc_mentions_by_proc: Dict[str, List[Dict]] = {}
        for m in m365["outlook_patterns"]["document_mentions"]:
            doc_mentions_by_proc.setdefault(m["linked_process"], []).append(m)
        overdue_by_proc = {
            o["linked_process"]: o for o in m365["planner_tasks"]["overdue_by_process"]
        }

        assessments: List[Dict[str, Any]] = []
        for p in processes:
            evidence: List[str] = []
            misalignment_score = 0  # 0 = fully aligned, higher = worse

            channel = channel_by_proc.get(p["id"])
            if channel:
                for pattern in channel["notable_patterns"]:
                    evidence.append(f"Teams: {pattern}")
                    misalignment_score += 1

            for mention in doc_mentions_by_proc.get(p["id"], []):
                evidence.append(f"Outlook: {mention['note']} ({mention['document']})")
                misalignment_score += 2  # stale/duplicated docs weigh more

            overdue = overdue_by_proc.get(p["id"])
            if overdue:
                evidence.append(
                    f"Planner: {overdue['overdue']} overdue tasks on board "
                    f"'{overdue['board']}' (oldest {overdue['oldest_overdue_days']} days)"
                )
                misalignment_score += 2

            # KPI gap contributes to misalignment
            kpis_off = [k for k in p["kpis"] if not self._kpi_on_target(k)]
            if kpis_off:
                evidence.append(
                    "KPIs off target: " + "; ".join(k["name"] for k in kpis_off)
                )
                misalignment_score += len(kpis_off)

            alignment = (
                "ALIGNED" if misalignment_score == 0
                else "MINOR_DRIFT" if misalignment_score <= 2
                else "SIGNIFICANT_DRIFT" if misalignment_score <= 5
                else "CRITICAL_DRIFT"
            )

            assessments.append(
                {
                    "process_id": p["id"],
                    "process_name": p["name"],
                    "alignment": alignment,
                    "misalignment_score": misalignment_score,
                    "evidence": evidence,
                }
            )

        summary = {
            "total_processes": len(assessments),
            "aligned": sum(1 for a in assessments if a["alignment"] == "ALIGNED"),
            "drifting": sum(1 for a in assessments if "DRIFT" in a["alignment"]),
            "critical": sum(1 for a in assessments if a["alignment"] == "CRITICAL_DRIFT"),
        }
        return {"agent": self.name, "summary": summary, "assessments": assessments}

    @staticmethod
    def _kpi_on_target(kpi: Dict[str, str]) -> bool:
        """
        Naive comparison good enough for the synthetic dataset:
        if the 'current' string differs from a clearly better-or-equal reading
        of the target, we flag it. The dataset was authored so that string
        inequality == off-target.
        """
        return kpi["current"] == kpi["target"]


# --------------------------------------------------------------------------- #
# 2. Repetitive Work Agent                                                     #
# --------------------------------------------------------------------------- #
class RepetitiveWorkAgent:
    """
    Surfaces recurring manual workflows found in Outlook patterns and meetings.
    Each finding is an *automation candidate* and the primary input for the
    Agent Factory (one candidate ≈ one proposed specialized agent).
    """

    name = "Repetitive Work Detector"

    # Simple economics for impact estimation (synthetic, documented in README)
    HOURLY_COST_USD = 35

    def run(self) -> Dict[str, Any]:
        m365 = load_m365_activity()
        findings: List[Dict[str, Any]] = []

        for wf in m365["outlook_patterns"]["repetitive_email_workflows"]:
            yearly_hours = wf["estimated_hours_per_week"] * 48
            findings.append(
                {
                    "type": "EMAIL_WORKFLOW",
                    "pattern": wf["pattern"],
                    "linked_process": wf["linked_process"],
                    "frequency": wf["frequency"],
                    "description": wf["description"],
                    "hours_per_week": wf["estimated_hours_per_week"],
                    "estimated_yearly_hours": round(yearly_hours, 1),
                    "estimated_yearly_cost_usd": round(yearly_hours * self.HOURLY_COST_USD),
                    "automation_potential": "HIGH",
                }
            )

        for mtg in m365["teams_activity"]["meetings"]["meetings_flagged_could_be_async"]:
            yearly_hours = (mtg["duration_min"] / 60) * mtg["attendees"] * 48
            findings.append(
                {
                    "type": "MEETING",
                    "pattern": mtg["title"],
                    "linked_process": mtg["linked_process"],
                    "frequency": "Recurring",
                    "description": mtg["reason"],
                    "hours_per_week": round(mtg["duration_min"] / 60 * mtg["attendees"], 1),
                    "estimated_yearly_hours": round(yearly_hours, 1),
                    "estimated_yearly_cost_usd": round(yearly_hours * self.HOURLY_COST_USD),
                    "automation_potential": "MEDIUM",
                }
            )

        findings.sort(key=lambda f: f["estimated_yearly_cost_usd"], reverse=True)
        total_cost = sum(f["estimated_yearly_cost_usd"] for f in findings)
        total_hours = sum(f["estimated_yearly_hours"] for f in findings)

        return {
            "agent": self.name,
            "summary": {
                "automation_candidates": len(findings),
                "total_recoverable_hours_per_year": round(total_hours, 1),
                "total_recoverable_cost_usd_per_year": total_cost,
            },
            "findings": findings,
        }


# --------------------------------------------------------------------------- #
# 3. Bottleneck Agent                                                          #
# --------------------------------------------------------------------------- #
class BottleneckAgent:
    """
    Identifies where the organization is structurally slow by combining
    KPI gaps with the conversational evidence in Teams channels.
    """

    name = "Bottleneck Identifier"

    def run(self) -> Dict[str, Any]:
        processes = {p["id"]: p for p in get_processes()}
        m365 = load_m365_activity()
        bottlenecks: List[Dict[str, Any]] = []

        # KPI-derived bottlenecks: every off-target KPI on a HIGH-criticality
        # process is treated as a bottleneck signal.
        for p in processes.values():
            for kpi in p["kpis"]:
                if kpi["current"] != kpi["target"]:
                    bottlenecks.append(
                        {
                            "process_id": p["id"],
                            "process_name": p["name"],
                            "signal": "KPI_GAP",
                            "detail": f"{kpi['name']}: current {kpi['current']} vs target {kpi['target']}",
                            "severity": "HIGH" if p["criticality"] == "HIGH" else "MEDIUM",
                        }
                    )

        # Conversation-derived bottlenecks: approval waits, manual consolidation
        for ch in m365["teams_activity"]["channels"]:
            for pattern in ch["notable_patterns"]:
                if any(k in pattern.lower() for k in ["wait", "manual", "escalation", "delay"]):
                    bottlenecks.append(
                        {
                            "process_id": ch["linked_process"],
                            "process_name": processes[ch["linked_process"]]["name"],
                            "signal": "CONVERSATION_PATTERN",
                            "detail": pattern,
                            "severity": "MEDIUM",
                        }
                    )

        high = [b for b in bottlenecks if b["severity"] == "HIGH"]
        return {
            "agent": self.name,
            "summary": {"total": len(bottlenecks), "high_severity": len(high)},
            "bottlenecks": bottlenecks,
        }


# --------------------------------------------------------------------------- #
# 4. Non-Conformity Agent                                                      #
# --------------------------------------------------------------------------- #
class NonConformityAgent:
    """
    Detects ISO 9001 non-conformities from organizational signals:

      NC-DOC  : controlled documents stale or duplicated in the wild
      NC-ACT  : overdue corrective/audit actions (clause 10.2 / 9.2)
      NC-SEC  : data-governance anomalies on SharePoint (clause 7.5.3)

    Each finding includes the ISO clause it threatens and a remediation hint —
    the same structure an internal auditor would produce.
    """

    name = "Non-Conformity Detector"

    def run(self) -> Dict[str, Any]:
        m365 = load_m365_activity()
        processes = {p["id"]: p for p in get_processes()}
        findings: List[Dict[str, Any]] = []
        counter = 0

        def new_id() -> str:
            nonlocal counter
            counter += 1
            return f"NC-{counter:03d}"

        # --- Stale controlled documents (clause 7.5) ---
        for doc in m365["sharepoint_signals"]["stale_document_alerts"]:
            severity = "CRITICAL" if doc["days_since_update"] > 900 else "HIGH"
            findings.append(
                {
                    "id": new_id(),
                    "category": "DOCUMENTED_INFORMATION",
                    "iso_clause": "7.5 - Documented information",
                    "process_id": doc["linked_process"],
                    "process_name": processes[doc["linked_process"]]["name"],
                    "severity": severity,
                    "description": (
                        f"Controlled document {doc['document_id']} not updated for "
                        f"{doc['days_since_update']} days. Risk: {doc['risk']}"
                    ),
                    "remediation": (
                        f"Trigger document review for {doc['document_id']} via the "
                        f"Document Control process (PROC-006) and notify the owner."
                    ),
                    "status": "OPEN",
                }
            )

        # --- Overdue actions (clauses 10.2 / 9.2 / 6.1) ---
        for board in m365["planner_tasks"]["overdue_by_process"]:
            severity = "CRITICAL" if board["oldest_overdue_days"] > 90 else "HIGH"
            findings.append(
                {
                    "id": new_id(),
                    "category": "OVERDUE_ACTIONS",
                    "iso_clause": processes[board["linked_process"]]["iso_clause"],
                    "process_id": board["linked_process"],
                    "process_name": processes[board["linked_process"]]["name"],
                    "severity": severity,
                    "description": (
                        f"{board['overdue']} overdue actions on board '{board['board']}' "
                        f"(oldest: {board['oldest_overdue_days']} days). {board['note']}."
                    ),
                    "remediation": (
                        "Escalate to process owner; re-baseline deadlines with documented "
                        "justification; report aging actions in next Management Review."
                    ),
                    "status": "OPEN",
                }
            )

        # --- Data governance anomalies (clause 7.5.3 — control of documented info)
        for anomaly in m365["sharepoint_signals"]["access_anomalies"]:
            findings.append(
                {
                    "id": new_id(),
                    "category": "INFORMATION_SECURITY",
                    "iso_clause": "7.5.3 - Control of documented information",
                    "process_id": anomaly["linked_process"],
                    "process_name": processes[anomaly["linked_process"]]["name"],
                    "severity": anomaly["severity"],
                    "description": f"{anomaly['event']}: {anomaly['detail']}",
                    "remediation": (
                        "Restore correct permissions, remove uncontrolled copies, and "
                        "communicate the single-source-of-truth location to the team."
                    ),
                    "status": "OPEN",
                }
            )

        by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in findings:
            by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1

        return {
            "agent": self.name,
            "summary": {"total": len(findings), "by_severity": by_severity},
            "findings": findings,
        }


# --------------------------------------------------------------------------- #
# 5. Flowchart Agent                                                           #
# --------------------------------------------------------------------------- #
class FlowchartAgent:
    """
    Generates a Mermaid flowchart for every process — the visual *catalyst*
    of the transformation: each node a step, decision-like steps rendered as
    diamonds, and the process KPIs annotated at the end.
    """

    name = "Flowchart Generator"

    DECISION_KEYWORDS = ("review", "approval", "approve", "verify", "check", "evaluate")

    def run(self) -> Dict[str, Any]:
        charts = {p["id"]: self.generate(p) for p in get_processes()}
        return {"agent": self.name, "summary": {"flowcharts": len(charts)}, "flowcharts": charts}

    def generate(self, process: Dict[str, Any]) -> str:
        """Build a top-down Mermaid graph from the process step list."""
        lines = ["graph TD"]
        steps = process["steps"]
        node_ids: List[str] = []

        for i, step in enumerate(steps):
            node_id = f"S{i}"
            node_ids.append(node_id)
            label = step.replace('"', "'")
            if any(k in step.lower() for k in self.DECISION_KEYWORDS):
                lines.append(f'    {node_id}{{"{label}"}}')  # diamond for decisions
            else:
                lines.append(f'    {node_id}["{label}"]')

        for a, b in zip(node_ids, node_ids[1:]):
            lines.append(f"    {a} --> {b}")

        # KPI annotation node
        kpi_label = "<br/>".join(
            f"{k['name']}: {k['current']} (target {k['target']})" for k in process["kpis"]
        ).replace('"', "'")
        lines.append(f'    KPI["📊 KPIs<br/>{kpi_label}"]')
        lines.append(f"    {node_ids[-1]} --> KPI")
        lines.append("    style KPI fill:#fff7ed,stroke:#c2410c")
        return "\n".join(lines)
