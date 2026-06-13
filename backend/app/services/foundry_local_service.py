"""
KaizenIQ — Foundry Local Service
=================================
Connects KaizenIQ to a **Microsoft Foundry-hosted model running locally** via
Foundry Local (https://learn.microsoft.com/azure/foundry-local).

Why this exists
---------------
The Agents League minimum integration requires "at least one Microsoft Foundry
hosted model." Azure OpenAI quota is unavailable on the student subscription,
so instead of a cloud-hosted model we use Foundry Local: the same curated
Foundry model catalog (Phi, Qwen, Mistral, ...), running on-device, exposed
through an OpenAI-compatible REST endpoint. No Azure subscription required.

Connection strategy
--------------------
Foundry Local runs a local OpenAI-compatible server on a random port. We
discover that endpoint, in order of preference:

  1. FOUNDRY_LOCAL_ENDPOINT env var (explicit override) — most reliable
  2. `foundry service status` CLI output (parse the running URL)
  3. foundry_local_sdk, if the installed version exposes a service URL

Then we drive inference with the standard `openai` client pointed at that
endpoint — exactly the pattern Microsoft documents. This avoids coupling to a
specific SDK version's in-process API, which changes between releases.

If nothing is reachable, `available` stays False and the caller falls back to
mock mode, so the demo never breaks.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger("kaizeniq.foundry_local")

DEFAULT_MODEL_ALIAS = "phi-3.5-mini"


class FoundryLocalService:
    """Thin wrapper over a locally running Foundry model (OpenAI-compatible)."""

    def __init__(self, model_alias: str = DEFAULT_MODEL_ALIAS) -> None:
        self.model_alias = model_alias
        self.available = False
        self.endpoint: Optional[str] = None
        self.model_id: Optional[str] = None
        self._client = None
        self._connect()

    # ------------------------------------------------------------------ #
    # Connection                                                          #
    # ------------------------------------------------------------------ #
    def _connect(self) -> None:
        endpoint = self._discover_endpoint()
        if not endpoint:
            logger.warning(
                "Foundry Local endpoint not found. Is the service running? "
                "Try: foundry model run %s", self.model_alias
            )
            return

        # Normalize to the /v1 base the OpenAI client expects.
        base = endpoint.rstrip("/")
        if not base.endswith("/v1"):
            base = base + "/v1"
        self.endpoint = base

        try:
            from openai import OpenAI

            self._client = OpenAI(base_url=self.endpoint, api_key="not-needed")
            # Ask the local server which model id it serves.
            models = self._client.models.list()
            if models.data:
                # Prefer a model whose id matches our alias; else take the first.
                match = next(
                    (m.id for m in models.data if self.model_alias in m.id.lower()),
                    models.data[0].id,
                )
                self.model_id = match
            else:
                self.model_id = self.model_alias
            self.available = True
            logger.warning(  # warning level so it shows in default uvicorn logs
                "Foundry Local CONNECTED (model=%s, endpoint=%s)",
                self.model_id, self.endpoint,
            )
        except Exception as exc:
            logger.warning(
                "Foundry Local endpoint found (%s) but client failed: %s: %s",
                self.endpoint, type(exc).__name__, exc,
            )
            self.available = False

    def _discover_endpoint(self) -> Optional[str]:
        """Find the running Foundry Local endpoint URL."""
        # 1. Explicit override
        env = os.getenv("FOUNDRY_LOCAL_ENDPOINT")
        if env:
            logger.warning("Using FOUNDRY_LOCAL_ENDPOINT=%s", env)
            return env

        # 2. Parse `foundry service status`
        url = self._endpoint_from_cli()
        if url:
            return url

        # 3. Try the SDK (best-effort; API varies by version)
        url = self._endpoint_from_sdk()
        if url:
            return url

        return None

    @staticmethod
    def _endpoint_from_cli() -> Optional[str]:
        """Run `foundry service status` and extract the http URL."""
        try:
            out = subprocess.run(
                ["foundry", "service", "status"],
                capture_output=True, text=True, timeout=15, shell=True,
            )
            text = (out.stdout or "") + (out.stderr or "")
            m = re.search(r"https?://127\.0\.0\.1:\d+", text)
            if m:
                logger.warning("Foundry Local endpoint from CLI: %s", m.group(0))
                return m.group(0)
            logger.warning("Could not parse endpoint from `foundry service status`")
        except Exception as exc:
            logger.warning("`foundry service status` failed: %s", exc)
        return None

    def _endpoint_from_sdk(self) -> Optional[str]:
        """Best-effort endpoint discovery via foundry_local_sdk (version-tolerant)."""
        try:
            from foundry_local_sdk import Configuration, FoundryLocalManager  # type: ignore

            config = Configuration(app_name="kaizeniq")
            FoundryLocalManager.initialize(config)
            manager = FoundryLocalManager.instance
            # Different versions expose the URL differently; try common spots.
            for attr in ("endpoint", "url"):
                val = getattr(manager, attr, None)
                if isinstance(val, str) and val.startswith("http"):
                    return val
            urls = getattr(manager, "urls", None)
            if urls:
                return urls[0]
        except Exception as exc:
            logger.warning("SDK endpoint discovery skipped: %s", exc)
        return None

    # ------------------------------------------------------------------ #
    # Inference                                                           #
    # ------------------------------------------------------------------ #
    def synthesize(self, system_prompt: str, user_prompt: str,
                   max_tokens: int = 400) -> str:
        """Run a chat completion on the local Foundry model (with telemetry)."""
        if not self.available or self._client is None:
            raise RuntimeError("Foundry Local is not available")

        from app.services.telemetry_service import telemetry

        with telemetry.timer(
            "foundry_model_call",
            detail=f"chat completion ({self.model_id})",
            metadata={"model": self.model_id, "max_tokens": max_tokens},
        ):
            response = self._client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.2,
            )
        return response.choices[0].message.content or ""

    # ------------------------------------------------------------------ #
    # Status                                                              #
    # ------------------------------------------------------------------ #
    def status(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "endpoint": self.endpoint,
            "model_id": self.model_id,
            "model_alias": self.model_alias,
        }
