"""
KaizenIQ — Application Configuration
=====================================
Central configuration loaded from environment variables (.env file).

The application runs in two modes:
  - FOUNDRY_MODE=live : Uses real Azure AI Search + Foundry IQ resources
                        (deployed via https://aka.ms/iq-series/deploytoazure)
  - FOUNDRY_MODE=mock : Runs fully offline with simulated Foundry IQ responses.
                        Guarantees the demo always works, even without Azure.

Author: Lucas Alves do Nascimento (@LucasLdx-1)
Project: KaizenIQ — Agents League Hackathon 2026 (Reasoning Agents track)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the backend root directory
load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PROJECT_ROOT = BASE_DIR.parent                            # repo root
DATA_DIR = PROJECT_ROOT / "data"                          # mock data folder

# ---------------------------------------------------------------------------
# Execution mode
# ---------------------------------------------------------------------------
# "live" -> real Azure Foundry IQ calls | "mock" -> simulated responses
FOUNDRY_MODE: str = os.getenv("FOUNDRY_MODE", "mock").lower()

# ---------------------------------------------------------------------------
# Azure AI Search (Foundry IQ knowledge layer)
# Values come from the IQ Series "Deploy to Azure" outputs tab.
# See: https://github.com/microsoft/iq-series
# ---------------------------------------------------------------------------
SEARCH_ENDPOINT: str = os.getenv("SEARCH_ENDPOINT", "")
SEARCH_API_KEY: str = os.getenv("SEARCH_API_KEY", "")          # optional if using RBAC
KNOWLEDGE_SOURCE_NAME: str = os.getenv("KNOWLEDGE_SOURCE_NAME", "kaizeniq-iso-processes")
KNOWLEDGE_BASE_NAME: str = os.getenv("KNOWLEDGE_BASE_NAME", "kaizeniq-kb")
SEARCH_INDEX_NAME: str = os.getenv("SEARCH_INDEX_NAME", "kaizeniq-iso-index")

# ---------------------------------------------------------------------------
# Azure OpenAI (LLM used by the knowledge base for answer synthesis)
# ---------------------------------------------------------------------------
AOAI_ENDPOINT: str = os.getenv("AOAI_ENDPOINT", "")
AOAI_GPT_DEPLOYMENT: str = os.getenv("AOAI_GPT_DEPLOYMENT", "gpt-4o-mini")
AOAI_EMBEDDING_DEPLOYMENT: str = os.getenv("AOAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")

# ---------------------------------------------------------------------------
# Microsoft Foundry project (Agent Service integration)
# ---------------------------------------------------------------------------
FOUNDRY_PROJECT_ENDPOINT: str = os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
FOUNDRY_MODEL_DEPLOYMENT_NAME: str = os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# API settings
# ---------------------------------------------------------------------------
API_TITLE = "KaizenIQ API"
API_VERSION = "0.1.0"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")


def is_live_mode() -> bool:
    """Return True when real Azure Foundry IQ resources should be used."""
    return FOUNDRY_MODE == "live" and bool(SEARCH_ENDPOINT)
