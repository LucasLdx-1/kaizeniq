"""
KaizenIQ — Data Service (with session-scoped dynamic store)
============================================================
Loads the synthetic demonstration data used by all agents:

  - data/iso_processes.json : 15 fictional ISO 9001 processes ("Meridian Industries")
  - data/m365_activity.json : Simulated M365 signals (Teams, Outlook, Planner, SharePoint)

Session-scoped dynamic store
----------------------------
Beyond the 15 seeded processes, users can add NEW processes at runtime
(see POST /api/processes/analyze). Those live in an in-memory store for the
duration of the server session — no database, no persistence. On restart the
store resets to the 15 seeded processes.

Because every agent reads the process list through `get_processes()`, adding a
process to the store makes it immediately visible to the diagnostic agents, the
Agent Factory, the orchestrator, and Foundry IQ retrieval — without changing
any of those modules. One function is the single source of truth.

In production the dynamic store would be replaced by documents indexed in
Foundry IQ (Azure AI Search); the in-memory store is the session-scoped stand-in.
"""

import json
from functools import lru_cache
from typing import Any, Dict, List

from app.core.config import DATA_DIR


@lru_cache(maxsize=1)
def load_iso_data() -> Dict[str, Any]:
    """Load the full seeded ISO dataset (organization metadata + process list)."""
    path = DATA_DIR / "iso_processes.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_m365_activity() -> Dict[str, Any]:
    """Load the simulated Microsoft 365 organizational activity snapshot."""
    path = DATA_DIR / "m365_activity.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Session-scoped dynamic process store                                         #
# --------------------------------------------------------------------------- #
# Holds processes added at runtime. Reset when the server restarts.
_session_processes: List[Dict[str, Any]] = []


def get_processes() -> List[Dict[str, Any]]:
    """
    Return ALL processes: the 15 seeded ones plus any added during this session.
    This is the single source of truth every agent reads from.
    """
    return load_iso_data()["processes"] + _session_processes


def get_process_by_id(process_id: str) -> Dict[str, Any] | None:
    """Return a single process by its ID (e.g. 'PROC-004'), or None."""
    for process in get_processes():
        if process["id"] == process_id:
            return process
    return None


def add_session_process(process: Dict[str, Any]) -> None:
    """Append a user-added process to the session store."""
    _session_processes.append(process)


def get_session_processes() -> List[Dict[str, Any]]:
    """Return only the processes added during this session."""
    return list(_session_processes)


def next_process_id() -> str:
    """
    Generate the next sequential process id (PROC-016, PROC-017, ...) so
    user-added processes follow the same convention as the seeded ones.
    """
    existing = get_processes()
    max_n = 0
    for p in existing:
        try:
            n = int(p["id"].split("-")[1])
            max_n = max(max_n, n)
        except (IndexError, ValueError):
            continue
    return f"PROC-{max_n + 1:03d}"


def get_organization() -> Dict[str, Any]:
    """Return organization metadata (name, certification info, etc.)."""
    return load_iso_data()["organization"]
