"""
KaizenIQ — Process Intake Service
==================================
Turns a user-pasted process (name + area + steps) into a fully structured
ISO 9001 process object — the same shape as the 15 seeded ones — by reasoning
with the **local Microsoft Foundry model** (Foundry Local).

Flow
----
1. User provides: name, macro_process (area), and a list of steps.
2. The Foundry model infers the likely ISO clause, plausible KPIs (with
   targets and a current value that implies a gap), and a criticality rating.
3. We assemble a process dict, assign the next PROC id, and add it to the
   session store so every agent immediately sees it.

Robustness
----------
Small local models can return malformed JSON. We:
  - prompt for strict JSON only,
  - extract the first JSON object defensively,
  - fall back to sensible defaults if parsing fails,
so the feature never crashes the demo.

If Foundry Local is unavailable, we still build a valid process using
deterministic defaults (the flowchart and analysis still work) — the model
simply enriches the result when present.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional

from app.services.mock_data_service import add_session_process, next_process_id

logger = logging.getLogger("kaizeniq.intake")


# Decision keywords reused from the FlowchartAgent so diamond detection matches.
_DECISION_KEYWORDS = ("review", "approval", "approve", "verify", "check", "evaluate", "decide")


class ProcessIntakeService:
    """Builds a structured process from pasted text, enriched by Foundry Local."""

    def __init__(self, foundry_local=None) -> None:
        # foundry_local is the FoundryLocalService instance (may be None/unavailable)
        self.foundry_local = foundry_local

    # ------------------------------------------------------------------ #
    # Public entry point                                                  #
    # ------------------------------------------------------------------ #
    def create_process(self, name: str, macro_process: str,
                        steps: List[str]) -> Dict[str, Any]:
        """
        Build and register a new process from user input.
        Returns the full process dict (already added to the session store).
        """
        steps = [s.strip() for s in steps if s.strip()]
        inferred = self._infer_with_foundry(name, macro_process, steps)

        process_id = next_process_id()
        process = {
            "id": process_id,
            "name": name,
            "macro_process": macro_process,
            "iso_clause": inferred.get("iso_clause", "Not specified"),
            "description": inferred.get(
                "description", f"User-defined process for {name}."
            ),
            "owner": inferred.get("owner", "Process Owner"),
            "responsible_team": macro_process,
            "inputs": inferred.get("inputs", []),
            "outputs": inferred.get("outputs", []),
            "steps": steps,
            "kpis": inferred.get("kpis", []),
            "criticality": inferred.get("criticality", "MEDIUM"),
            "frequency": inferred.get("frequency", "ON_DEMAND"),
            "last_updated": date.today().isoformat(),
            "updated_by": "user@kaizeniq-demo.com",
            "document_version": "1.0",
            "related_documents": [],
            "source": "user_added",  # marks it as session-added for the UI
        }

        add_session_process(process)
        logger.info("Added session process %s (%s)", process_id, name)
        return process

    # ------------------------------------------------------------------ #
    # Foundry Local inference                                             #
    # ------------------------------------------------------------------ #
    def _infer_with_foundry(self, name: str, area: str,
                            steps: List[str]) -> Dict[str, Any]:
        """Ask the local Foundry model to infer ISO metadata. Safe on failure."""
        if not (self.foundry_local and getattr(self.foundry_local, "available", False)):
            logger.info("Foundry Local unavailable — using default inference")
            return self._default_inference(name, steps)

        steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
        system_prompt = (
            "You are an ISO 9001:2015 quality management expert. Given a business "
            "process, infer its metadata. Respond with STRICT JSON only — no prose, "
            "no markdown fences. Use this exact schema:\n"
            '{"iso_clause": "<clause number and name>", '
            '"description": "<one sentence>", '
            '"owner": "<role>", '
            '"criticality": "HIGH|MEDIUM|LOW", '
            '"frequency": "DAILY|WEEKLY|MONTHLY|QUARTERLY|ON_DEMAND", '
            '"inputs": ["..."], "outputs": ["..."], '
            '"kpis": [{"name": "<kpi>", "target": "<target>", "current": "<current value implying a gap>"}]}'
        )
        user_prompt = (
            f"Process name: {name}\n"
            f"Area / department: {area}\n"
            f"Steps:\n{steps_text}\n\n"
            "Return the JSON now."
        )

        try:
            raw = self.foundry_local.synthesize(system_prompt, user_prompt, max_tokens=500)
            parsed = self._extract_json(raw)
            if parsed:
                # Ensure kpis is a list of well-formed dicts
                parsed.setdefault("kpis", [])
                return parsed
            logger.warning("Foundry returned unparseable JSON — using defaults")
        except Exception as exc:
            logger.warning("Foundry inference failed (%s) — using defaults", exc)
        return self._default_inference(name, steps)

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Defensively extract the first JSON object from model output."""
        if not text:
            return None
        # Strip markdown fences if present
        text = text.replace("```json", "").replace("```", "")
        # Find the first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _default_inference(name: str, steps: List[str]) -> Dict[str, Any]:
        """Deterministic fallback so the feature works even without the model."""
        has_decision = any(
            any(k in s.lower() for k in _DECISION_KEYWORDS) for s in steps
        )
        return {
            "iso_clause": "8.1 - Operational planning and control",
            "description": f"User-defined process: {name}.",
            "owner": "Process Owner",
            "criticality": "HIGH" if has_decision else "MEDIUM",
            "frequency": "ON_DEMAND",
            "inputs": [],
            "outputs": [],
            "kpis": [
                {"name": "Process cycle time", "target": "TBD", "current": "Not measured"}
            ],
        }
