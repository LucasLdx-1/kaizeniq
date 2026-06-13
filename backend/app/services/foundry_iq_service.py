"""
KaizenIQ — Foundry IQ Service
==============================
Integration layer with Microsoft Foundry IQ (the knowledge layer of Microsoft IQ).

This module follows the official patterns from the Microsoft IQ Series cookbooks
(https://github.com/microsoft/iq-series):

  Episode 1 — Create a Knowledge Source backed by an Azure AI Search index
  Episode 2 — Ingest data (here: ISO 9001 processes) into the index
  Episode 3 — Query the Knowledge Base with agentic retrieval and citations

Architecture (live mode):

    ISO process JSON ──> Azure AI Search index ──> Knowledge Source
                                                        │
                                                  Knowledge Base ── paired with
                                                        │            gpt-4o-mini
                                              Agentic Retrieval (plan ▸ subqueries
                                              ▸ rerank ▸ synthesize + citations)

Dual-mode design:
  - FOUNDRY_MODE=live : real calls to Azure AI Search / Foundry IQ
  - FOUNDRY_MODE=mock : deterministic simulated responses so the demo and the
                        frontend work end-to-end without any Azure credentials.
                        Every mock answer is grounded in the same JSON dataset
                        the live index would contain, so behavior is equivalent.

SDK note: live mode requires the preview SDK pinned by the official cookbook:
    pip install azure-search-documents==12.1.0b1 azure-identity
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.core.config import (
    AOAI_ENDPOINT,
    AOAI_GPT_DEPLOYMENT,
    KNOWLEDGE_BASE_NAME,
    KNOWLEDGE_SOURCE_NAME,
    SEARCH_ENDPOINT,
    SEARCH_INDEX_NAME,
    is_live_mode,
)
from app.services.mock_data_service import get_processes, load_m365_activity

logger = logging.getLogger("kaizeniq.foundry")


class FoundryIQService:
    """
    Thin client around Foundry IQ knowledge bases.

    Public surface used by the agents:
        setup()                      -> ensure index / source / base exist (live mode)
        query(question, effort)      -> grounded answer with citations
        status()                     -> current mode + resource names (for the UI)
    """

    def __init__(self) -> None:
        self.live = is_live_mode()
        self._search_index_client = None
        self._knowledge_client = None
        if self.live:
            self._init_live_clients()

        # Foundry Local: a real Microsoft Foundry-hosted model running on-device.
        # When FOUNDRY_MODE=local (or 'auto' and a local model is reachable),
        # answer synthesis is performed by that model instead of the
        # deterministic mock text — satisfying the "at least one Microsoft
        # Foundry hosted model" requirement without Azure quota.
        import os
        self._foundry_local = None
        self.local_enabled = False
        mode = os.getenv("FOUNDRY_MODE", "mock").lower()
        if mode in ("local", "auto") and not self.live:
            try:
                from app.services.foundry_local_service import FoundryLocalService
                model_alias = os.getenv("FOUNDRY_LOCAL_MODEL", "phi-3.5-mini")
                self._foundry_local = FoundryLocalService(model_alias=model_alias)
                self.local_enabled = self._foundry_local.available
            except Exception as exc:
                logger.warning("Foundry Local init failed (%s)", exc)

        active = "live" if self.live else ("local" if self.local_enabled else "mock")
        logger.info("FoundryIQService initialized (mode=%s)", active)

    # ------------------------------------------------------------------ #
    # Live-mode client initialization                                     #
    # ------------------------------------------------------------------ #
    def _init_live_clients(self) -> None:
        """
        Create Azure SDK clients. Uses DefaultAzureCredential, which works with
        `az login` locally (exactly as the IQ Series cookbooks recommend).
        """
        try:
            from azure.identity import DefaultAzureCredential
            from azure.search.documents.indexes import SearchIndexClient

            credential = DefaultAzureCredential()
            self._search_index_client = SearchIndexClient(
                endpoint=SEARCH_ENDPOINT, credential=credential
            )
            # The 12.1.0b1 preview SDK exposes knowledge source / knowledge base
            # operations on the SearchIndexClient — kept on one client here.
            self._knowledge_client = self._search_index_client
        except Exception as exc:  # pragma: no cover - depends on environment
            logger.warning("Live Foundry IQ unavailable, falling back to mock: %s", exc)
            self.live = False

    # ------------------------------------------------------------------ #
    # Setup: index + knowledge source + knowledge base                    #
    # ------------------------------------------------------------------ #
    def setup(self) -> Dict[str, Any]:
        """
        Idempotently create the Foundry IQ resources.

        Live mode steps (mirrors Episode 1 + 2 cookbooks):
          1. Create/refresh the Azure AI Search index with ISO process documents
          2. Register a Knowledge Source pointing at that index
          3. Register a Knowledge Base pairing the source with the AOAI deployment

        Mock mode: no-op, returns the simulated resource map.
        """
        if not self.live:
            return {
                "mode": "mock",
                "message": "Mock mode active — knowledge base simulated in-memory. "
                           "Set FOUNDRY_MODE=live and provide Azure endpoints to "
                           "use real Foundry IQ resources.",
                "knowledge_source": KNOWLEDGE_SOURCE_NAME,
                "knowledge_base": KNOWLEDGE_BASE_NAME,
                "documents_indexed": len(get_processes()),
            }

        # ---- 1. Build / update the search index with process documents ----
        documents = self._processes_as_search_documents()
        self._ensure_index_with_documents(documents)

        # ---- 2 + 3. Knowledge source and knowledge base -------------------
        # NOTE: exact model class names follow azure-search-documents 12.1.0b1.
        # If Microsoft revs the preview SDK, align these calls with the current
        # Episode 1 cookbook (foundry-iq-cookbook.ipynb) — the flow is identical.
        self._ensure_knowledge_source()
        self._ensure_knowledge_base()

        return {
            "mode": "live",
            "knowledge_source": KNOWLEDGE_SOURCE_NAME,
            "knowledge_base": KNOWLEDGE_BASE_NAME,
            "index": SEARCH_INDEX_NAME,
            "documents_indexed": len(documents),
        }

    def _processes_as_search_documents(self) -> List[Dict[str, Any]]:
        """
        Flatten each ISO process into a search-friendly document.
        One document per process keeps citations human-readable
        (e.g. "[PROC-004] Nonconformity & Corrective Action").
        """
        docs: List[Dict[str, Any]] = []
        for p in get_processes():
            kpi_text = "; ".join(
                f"{k['name']}: target {k['target']}, current {k['current']}"
                for k in p.get("kpis", [])
            )
            docs.append(
                {
                    "id": p["id"],
                    "title": p["name"],
                    "content": (
                        f"{p['description']} ISO clause: {p['iso_clause']}. "
                        f"Owner: {p['owner']} ({p['responsible_team']}). "
                        f"Steps: {' -> '.join(p['steps'])}. "
                        f"KPIs: {kpi_text}. "
                        f"Criticality: {p['criticality']}. "
                        f"Last updated: {p['last_updated']} (v{p['document_version']})."
                    ),
                    "macro_process": p["macro_process"],
                    "criticality": p["criticality"],
                }
            )
        return docs

    def _ensure_index_with_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Create the index if missing and upload all process documents."""
        from azure.search.documents import SearchClient
        from azure.search.documents.indexes.models import (
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SimpleField,
            SearchableField,
        )
        from azure.identity import DefaultAzureCredential

        index = SearchIndex(
            name=SEARCH_INDEX_NAME,
            fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="title", type=SearchFieldDataType.String),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchableField(name="macro_process", type=SearchFieldDataType.String,
                                filterable=True, facetable=True),
                SimpleField(name="criticality", type=SearchFieldDataType.String,
                            filterable=True, facetable=True),
            ],
        )
        self._search_index_client.create_or_update_index(index)

        search_client = SearchClient(
            endpoint=SEARCH_ENDPOINT,
            index_name=SEARCH_INDEX_NAME,
            credential=DefaultAzureCredential(),
        )
        search_client.upload_documents(documents)
        logger.info("Indexed %d ISO process documents", len(documents))

    def _ensure_knowledge_source(self) -> None:
        """
        Register the Knowledge Source over the index (Episode 1 pattern).
        Wrapped in try/except: portal-created resources are also valid, and the
        preview API surface may differ between SDK builds.
        """
        try:
            from azure.search.documents.indexes.models import (  # type: ignore
                SearchIndexKnowledgeSource,
                SearchIndexKnowledgeSourceParameters,
            )

            source = SearchIndexKnowledgeSource(
                name=KNOWLEDGE_SOURCE_NAME,
                description="ISO 9001 documented processes of the organization",
                search_index_parameters=SearchIndexKnowledgeSourceParameters(
                    search_index_name=SEARCH_INDEX_NAME,
                ),
            )
            self._knowledge_client.create_or_update_knowledge_source(  # type: ignore
                knowledge_source=source
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Knowledge source registration via SDK skipped (%s). "
                "Create it once in the Foundry IQ portal if needed.", exc
            )

    def _ensure_knowledge_base(self) -> None:
        """Register the Knowledge Base pairing the source with gpt-4o-mini."""
        try:
            from azure.search.documents.indexes.models import (  # type: ignore
                KnowledgeBase,
                KnowledgeSourceReference,
                AzureOpenAIModel,
            )

            kb = KnowledgeBase(
                name=KNOWLEDGE_BASE_NAME,
                knowledge_sources=[
                    KnowledgeSourceReference(name=KNOWLEDGE_SOURCE_NAME)
                ],
                answer_synthesis_model=AzureOpenAIModel(
                    azure_open_ai_parameters={
                        "resource_url": AOAI_ENDPOINT,
                        "deployment_name": AOAI_GPT_DEPLOYMENT,
                        "model_name": AOAI_GPT_DEPLOYMENT,
                    }
                ),
            )
            self._knowledge_client.create_or_update_knowledge_base(  # type: ignore
                knowledge_base=kb
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Knowledge base registration via SDK skipped (%s). "
                "Create it once in the Foundry IQ portal if needed.", exc
            )

    @property
    def foundry_local(self):
        """The FoundryLocalService instance (or None) — reused by other services."""
        return self._foundry_local

    # ------------------------------------------------------------------ #
    # Query                                                                #
    # ------------------------------------------------------------------ #
    def query(self, question: str, effort: str = "low") -> Dict[str, Any]:
        """
        Ask the knowledge base a question.

        Args:
            question: natural-language question about the organization's processes
            effort:   reasoning effort ("minimal" | "low" | "medium"),
                      matching Episode 3 of the IQ Series.

        Returns:
            {"answer": str, "citations": [...], "mode": "live"|"mock"}
        """
        if self.live:
            try:
                return self._query_live(question, effort)
            except Exception as exc:  # pragma: no cover
                logger.warning("Live query failed (%s) — answering from mock KB", exc)
        if self.local_enabled:
            try:
                return self._query_local(question)
            except Exception as exc:
                logger.warning("Foundry Local query failed (%s) — falling back to mock", exc)
        return self._query_mock(question)

    def _retrieve_top_processes(self, question: str, k: int = 3) -> List[Dict[str, Any]]:
        """Keyword retrieval over the ISO dataset (shared by mock and local)."""
        q = question.lower()
        scored: List[tuple[int, Dict[str, Any]]] = []
        for p in get_processes():
            haystack = " ".join(
                [p["name"], p["description"], p["macro_process"], p["iso_clause"]]
                + p["steps"]
            ).lower()
            score = sum(1 for word in q.split() if len(word) > 3 and word in haystack)
            if score:
                scored.append((score, p))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [p for _, p in scored[:k]]

    def chat(self, question: str) -> Dict[str, Any]:
        """
        Conversational endpoint for the 'Talk to the agents' page.

        Unlike `query` (top-k retrieval), chat gives the Foundry model an
        awareness of the ENTIRE process catalog (a compact roster of every
        process, seeded + session-added) plus the full detail of the most
        relevant ones. This lets the orchestrator answer both broad questions
        ("how many processes are drifting?", "list the quality processes") and
        specific ones ("what are the KPIs of customer onboarding?").

        Falls back to mock synthesis when Foundry Local is unavailable.
        """
        all_processes = get_processes()

        # Compact roster so the model is aware of everything.
        roster = "\n".join(
            f"- [{p['id']}] {p['name']} (area: {p['macro_process']}, "
            f"criticality: {p['criticality']})"
            for p in all_processes
        )

        # Detailed context for the most relevant processes.
        top = self._retrieve_top_processes(question, k=4) or all_processes[:4]
        details = []
        for p in top:
            kpi_summary = "; ".join(
                f"{k['name']} at {k['current']} (target {k['target']})" for k in p["kpis"]
            )
            details.append(
                f"[{p['id']}] {p['name']} — {p['description']} "
                f"ISO {p['iso_clause']}. Owner: {p['owner']}. KPIs: {kpi_summary}. "
                f"Steps: {' -> '.join(p['steps'])}."
            )
        detail_text = "\n".join(details)
        citations = [{"id": p["id"], "title": p["name"]} for p in top]

        if not self.local_enabled:
            # Mock fallback: deterministic summary.
            answer = (
                f"The organization has {len(all_processes)} documented ISO 9001 "
                f"processes. Most relevant to your question:\n" + detail_text
            )
            return {"answer": answer, "citations": citations, "mode": "mock"}

        system_prompt = (
            "You are the KaizenIQ Master Orchestrator, the lead agent of an "
            "ISO 9001 quality-management multi-agent system. You have full "
            "awareness of the organization's process catalog (provided below). "
            "Answer the user's question grounded in that catalog. Cite process "
            "ids in square brackets like [PROC-004]. Be concise, factual and "
            "helpful. If something is outside the catalog, say so plainly."
        )
        user_prompt = (
            f"FULL PROCESS CATALOG ({len(all_processes)} processes):\n{roster}\n\n"
            f"DETAILED CONTEXT (most relevant):\n{detail_text}\n\n"
            f"User question: {question}\n\nAnswer:"
        )
        answer = self._foundry_local.synthesize(  # type: ignore
            system_prompt, user_prompt, max_tokens=500
        )
        return {"answer": answer.strip(), "citations": citations, "mode": "local"}

    def _query_local(self, question: str) -> Dict[str, Any]:
        """
        Retrieval-augmented answer synthesized by a **real Microsoft Foundry
        model running locally** (Foundry Local).

        The retrieval step finds the relevant ISO processes; the Foundry model
        then writes a grounded answer constrained to that context — the same
        shape Foundry IQ produces in the cloud, but on-device. Citations come
        from the retrieved process ids (deterministic, verifiable).
        """
        top = self._retrieve_top_processes(question)
        if not top:
            return {
                "answer": "No matching processes found in the knowledge base for this question.",
                "citations": [],
                "mode": "local",
            }

        # Build grounded context for the model.
        context_blocks = []
        for p in top:
            kpi_summary = "; ".join(
                f"{k['name']} at {k['current']} (target {k['target']})" for k in p["kpis"]
            )
            context_blocks.append(
                f"[{p['id']}] {p['name']} (ISO {p['iso_clause']}). "
                f"{p['description']} KPIs: {kpi_summary}."
            )
        context = "\n".join(context_blocks)

        system_prompt = (
            "You are Foundry IQ, the knowledge layer of an ISO 9001 quality "
            "management assistant. Answer ONLY from the provided process context. "
            "Cite process ids in square brackets like [PROC-004]. Be concise and "
            "factual. If the context does not contain the answer, say so."
        )
        user_prompt = (
            f"Process context:\n{context}\n\nQuestion: {question}\n\n"
            "Grounded answer with citations:"
        )

        answer = self._foundry_local.synthesize(system_prompt, user_prompt)  # type: ignore
        citations = [{"id": p["id"], "title": p["name"]} for p in top]
        return {"answer": answer.strip(), "citations": citations, "mode": "local"}

    def _query_live(self, question: str, effort: str) -> Dict[str, Any]:
        """Real agentic-retrieval call against the knowledge base (Episode 3)."""
        # The preview SDK exposes knowledge base retrieval on the index client.
        result = self._knowledge_client.retrieve_from_knowledge_base(  # type: ignore
            knowledge_base_name=KNOWLEDGE_BASE_NAME,
            messages=[{"role": "user", "content": question}],
            reasoning_effort=effort,
        )
        answer = getattr(result, "answer", None) or str(result)
        citations = [
            {"id": ref.get("id"), "title": ref.get("title")}
            for ref in getattr(result, "references", []) or []
        ]
        return {"answer": answer, "citations": citations, "mode": "live"}

    def _query_mock(self, question: str) -> Dict[str, Any]:
        """
        Deterministic keyword retrieval over the same dataset the live index
        holds. Produces grounded answers with process-level citations so the
        full agent pipeline (and the UI) behaves identically offline.
        """
        q = question.lower()
        scored: List[tuple[int, Dict[str, Any]]] = []
        for p in get_processes():
            haystack = " ".join(
                [p["name"], p["description"], p["macro_process"], p["iso_clause"]]
                + p["steps"]
            ).lower()
            score = sum(1 for word in q.split() if len(word) > 3 and word in haystack)
            if score:
                scored.append((score, p))
        scored.sort(key=lambda t: t[0], reverse=True)
        top = [p for _, p in scored[:3]]

        if not top:
            return {
                "answer": "No matching processes found in the knowledge base for this question.",
                "citations": [],
                "mode": "mock",
            }

        lines = []
        for p in top:
            kpi_summary = "; ".join(
                f"{k['name']} at {k['current']} (target {k['target']})" for k in p["kpis"]
            )
            lines.append(
                f"[{p['id']}] {p['name']} — {p['description']} "
                f"Current KPI status: {kpi_summary}."
            )
        answer = (
            "Based on the organization's documented ISO 9001 processes:\n" + "\n".join(lines)
        )
        citations = [{"id": p["id"], "title": p["name"]} for p in top]
        return {"answer": answer, "citations": citations, "mode": "mock"}

    # ------------------------------------------------------------------ #
    # Status (used by the dashboard header)                                #
    # ------------------------------------------------------------------ #
    def status(self) -> Dict[str, Any]:
        """Expose current mode and resource names to the frontend."""
        m365 = load_m365_activity()
        mode = "live" if self.live else ("local" if self.local_enabled else "mock")
        status = {
            "mode": mode,
            "knowledge_base": KNOWLEDGE_BASE_NAME,
            "knowledge_source": KNOWLEDGE_SOURCE_NAME,
            "documents_indexed": len(get_processes()),
            "m365_snapshot_date": m365.get("snapshot_date"),
        }
        # Surface the real Foundry model when running locally.
        if self.local_enabled and self._foundry_local is not None:
            status["foundry_local_model"] = self._foundry_local.model_id
            status["foundry_local_endpoint"] = self._foundry_local.endpoint
        return status


# Module-level singleton — agents import this instance.
foundry_iq = FoundryIQService()
