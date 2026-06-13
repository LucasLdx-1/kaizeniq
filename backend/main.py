"""
KaizenIQ — API Entry Point
===========================
FastAPI application bootstrap.

Run locally:
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import API_TITLE, API_VERSION, CORS_ORIGINS

logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=(
        "KaizenIQ — Continuous improvement meets agentic AI. "
        "Diagnoses an ISO 9001 organization through Microsoft 365 signals, "
        "grounds reasoning in Foundry IQ, and proposes a portfolio of "
        "specialized agents for digital transformation."
    ),
)

# CORS: allow the local React dev server (Vite) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    """Friendly root pointing humans to the interactive docs."""
    return {"app": API_TITLE, "version": API_VERSION, "docs": "/docs"}
