"""
KaizenIQ — API Routes
======================
REST surface consumed by the KaizenIQ portal (React frontend).

Endpoints
---------
GET  /api/health                     liveness + Foundry IQ mode
GET  /api/analysis                   full orchestration result (cached)
POST /api/analysis/refresh           force a re-run of all agents
GET  /api/processes                  ISO process list (raw)
GET  /api/processes/{id}/flowchart   Mermaid source for one process
GET  /api/agents                     14-agent portfolio
POST /api/agents/{id}/train          generate grounded system prompt (Foundry IQ)
GET  /api/non-conformities           findings list
POST /api/foundry/setup              create live Foundry IQ resources (live mode)
POST /api/foundry/query              free-form grounded Q&A against the KB
"""

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.orchestrator import orchestrator
from app.services.foundry_iq_service import foundry_iq
from app.services.mock_data_service import (
    get_process_by_id,
    get_processes,
    get_session_processes,
)
from app.services.process_intake_service import ProcessIntakeService

router = APIRouter(prefix="/api")

# Intake service reuses the same Foundry Local instance the IQ service holds,
# so a user-added process is structured by the real on-device Foundry model.
_intake = ProcessIntakeService(foundry_local=foundry_iq.foundry_local)


# --------------------------------------------------------------------------- #
# Request models                                                                #
# --------------------------------------------------------------------------- #
class NewProcess(BaseModel):
    """A process pasted by the user: name + area + steps. Foundry infers the rest."""
    name: str
    macro_process: str
    steps: List[str]


class FoundryQuery(BaseModel):
    """Free-form question routed to the Foundry IQ knowledge base."""
    question: str
    effort: str = "low"  # minimal | low | medium (Episode 3 semantics)


# --------------------------------------------------------------------------- #
# Health & status                                                               #
# --------------------------------------------------------------------------- #
@router.get("/health")
def health():
    """Liveness probe + current Foundry IQ mode for the portal header."""
    return {"status": "ok", "foundry_iq": foundry_iq.status()}


# --------------------------------------------------------------------------- #
# Orchestration                                                                 #
# --------------------------------------------------------------------------- #
@router.get("/analysis")
def get_analysis():
    """Full diagnostic + agent portfolio (cached after first run)."""
    return orchestrator.run_full_analysis()


@router.post("/analysis/refresh")
def refresh_analysis():
    """Force all seven agents to re-run."""
    return orchestrator.run_full_analysis(force=True)


# --------------------------------------------------------------------------- #
# Processes & flowcharts                                                        #
# --------------------------------------------------------------------------- #
@router.get("/processes")
def list_processes():
    """Raw ISO 9001 process list (seeded + session-added)."""
    return {"processes": get_processes()}


@router.post("/processes/analyze")
def analyze_process(body: NewProcess):
    """
    Add a NEW process from pasted text (name + area + steps).

    The local Microsoft Foundry model (Foundry Local) infers the ISO clause,
    KPIs and metadata; we generate its flowchart and fold it into the live
    analysis so the diagnostics, Agent Factory and orchestrator all see it.
    Session-scoped: resets on server restart.
    """
    if not body.steps:
        raise HTTPException(status_code=400, detail="At least one step is required")

    # 1. Structure the process via Foundry Local (or safe defaults).
    process = _intake.create_process(body.name, body.macro_process, body.steps)

    # 2. Invalidate the cached analysis so everything recomputes with the new process.
    orchestrator.invalidate()
    analysis = orchestrator.run_full_analysis()

    # 3. Return the new process, its generated flowchart, and refreshed summary.
    mermaid = analysis["flowcharts"]["flowcharts"].get(process["id"])
    return {
        "process": process,
        "flowchart": mermaid,
        "foundry_mode": foundry_iq.status()["mode"],
        "executive_summary": analysis["executive_summary"],
    }


@router.get("/processes/{process_id}/flowchart")
def process_flowchart(process_id: str):
    """Mermaid flowchart source for a single process."""
    process = get_process_by_id(process_id)
    if process is None:
        raise HTTPException(status_code=404, detail=f"Process {process_id} not found")
    analysis = orchestrator.run_full_analysis()
    mermaid = analysis["flowcharts"]["flowcharts"].get(process_id)
    return {"process_id": process_id, "name": process["name"], "mermaid": mermaid}


# --------------------------------------------------------------------------- #
# Agent portfolio                                                               #
# --------------------------------------------------------------------------- #
@router.get("/agents")
def list_agents():
    """The 14-agent portfolio produced by the Agent Factory."""
    return orchestrator.run_full_analysis()["agent_portfolio"]


@router.post("/agents/{agent_id}/train")
def train_agent(agent_id: str):
    """
    Generate the grounded system prompt for a proposed agent.
    This is the 'factory trains the newcomer' step — grounding comes from
    Foundry IQ so the new agent is born knowing the organization.
    """
    result = orchestrator.train_agent(agent_id.upper())
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# --------------------------------------------------------------------------- #
# Non-conformities                                                              #
# --------------------------------------------------------------------------- #
@router.get("/non-conformities")
def list_non_conformities():
    """ISO 9001 non-conformity findings with clauses and remediation hints."""
    return orchestrator.run_full_analysis()["non_conformities"]


# --------------------------------------------------------------------------- #
# Foundry IQ direct access                                                      #
# --------------------------------------------------------------------------- #
@router.post("/foundry/setup")
def foundry_setup():
    """Create / verify Foundry IQ resources (index, source, base)."""
    return foundry_iq.setup()


@router.post("/foundry/query")
def foundry_query(body: FoundryQuery):
    """Grounded Q&A against the organization's knowledge base."""
    return foundry_iq.query(body.question, body.effort)


# --------------------------------------------------------------------------- #
# Chat with the agents                                                          #
# --------------------------------------------------------------------------- #
class ChatMessage(BaseModel):
    """A question for the Master Orchestrator (aware of all processes)."""
    message: str


@router.post("/chat")
def chat(body: ChatMessage):
    """
    Talk to the Master Orchestrator. It answers grounded in the FULL process
    catalog (seeded + session-added) using the local Foundry model, with
    citations. Recorded in telemetry.
    """
    from app.services.telemetry_service import telemetry
    with telemetry.timer("chat_message", detail=body.message[:60]):
        result = foundry_iq.chat(body.message)
    return result


# --------------------------------------------------------------------------- #
# Telemetry & observability                                                     #
# --------------------------------------------------------------------------- #
@router.get("/telemetry")
def get_telemetry():
    """
    Runtime observability: recent events, call counts and average latencies
    across agents and Foundry model calls. Supports the Reliability & Safety
    and observability criteria.
    """
    from app.services.telemetry_service import telemetry
    snap = telemetry.snapshot()
    status = foundry_iq.status()

    # Collect the guardrails declared across the agent portfolio (safety view).
    portfolio = orchestrator.run_full_analysis()["agent_portfolio"]
    guardrails = []
    seen = set()
    for agent in portfolio["proposals"]:
        for g in agent.get("guardrails", []):
            if g not in seen:
                seen.add(g)
                guardrails.append(g)

    return {
        "foundry_mode": status["mode"],
        "foundry_model": status.get("foundry_local_model"),
        "processes_tracked": len(get_processes()),
        "agents_total": portfolio["summary"]["total_proposed"],
        "telemetry": snap,
        "active_guardrails": guardrails,
    }


# --------------------------------------------------------------------------- #
# Company-wide process map (incremental)                                        #
# --------------------------------------------------------------------------- #
@router.get("/company-map")
def company_map():
    """
    A Mermaid map of the WHOLE organization: every process grouped by its
    macro-process. Incremental — processes added via /processes/analyze appear
    here automatically (they flow through the same dynamic store).
    """
    processes = get_processes()

    # Group by macro_process.
    groups: dict = {}
    for p in processes:
        groups.setdefault(p["macro_process"], []).append(p)

    # Build a Mermaid graph: Organization -> Macro-process -> Processes.
    lines = ["graph LR", '    ORG["🏭 Meridian Industries<br/>ISO 9001:2015"]']
    g_idx = 0
    for macro, procs in groups.items():
        g_id = f"G{g_idx}"
        safe_macro = macro.replace('"', "'")
        lines.append(f'    {g_id}["{safe_macro}"]')
        lines.append(f"    ORG --> {g_id}")
        for i, p in enumerate(procs):
            p_node = f"{g_id}P{i}"
            # Highlight session-added processes and critical ones.
            label = f"{p['id']}<br/>{p['name']}".replace('"', "'")
            lines.append(f'    {p_node}["{label}"]')
            lines.append(f"    {g_id} --> {p_node}")
            if p.get("source") == "user_added":
                lines.append(f"    style {p_node} fill:#edf5f1,stroke:#1e5945,stroke-width:2px")
            elif p.get("criticality") == "HIGH":
                lines.append(f"    style {p_node} fill:#fdf1ef,stroke:#c0392b")
        g_idx += 1

    lines.append('    style ORG fill:#1c1917,color:#faf9f6')
    mermaid = "\n".join(lines)

    return {
        "mermaid": mermaid,
        "total_processes": len(processes),
        "macro_processes": list(groups.keys()),
        "user_added": [p["id"] for p in processes if p.get("source") == "user_added"],
    }
