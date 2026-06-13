"""
KaizenIQ — Telemetry Service
=============================
Lightweight, in-memory observability for the agent system. Records every
significant event (agent runs, Foundry model calls, process additions) with
timing, so the portal can show how the multi-agent system behaves at runtime.

This directly supports the hackathon's "Reliability & Safety" and
"Evaluations / telemetry / observability" criteria: judges can see that the
system is instrumented, that calls are traced, and which execution mode
(local Foundry model vs. mock) served each request.

Session-scoped: resets on server restart. No external dependencies.
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional


class TelemetryService:
    """Thread-safe, capped, in-memory event log with simple aggregates."""

    def __init__(self, max_events: int = 200) -> None:
        self._events: deque = deque(maxlen=max_events)
        self._lock = Lock()
        self._counters: Dict[str, int] = {}
        self._latencies: Dict[str, List[float]] = {}

    # ------------------------------------------------------------------ #
    # Recording                                                           #
    # ------------------------------------------------------------------ #
    def record(self, event_type: str, detail: str = "",
               duration_ms: Optional[float] = None,
               metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a single telemetry event."""
        with self._lock:
            self._events.appendleft({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": event_type,
                "detail": detail,
                "duration_ms": round(duration_ms, 1) if duration_ms is not None else None,
                "metadata": metadata or {},
            })
            self._counters[event_type] = self._counters.get(event_type, 0) + 1
            if duration_ms is not None:
                self._latencies.setdefault(event_type, []).append(duration_ms)

    def timer(self, event_type: str, detail: str = "",
              metadata: Optional[Dict[str, Any]] = None):
        """Context manager that records an event with its duration."""
        return _Timer(self, event_type, detail, metadata)

    # ------------------------------------------------------------------ #
    # Reporting                                                           #
    # ------------------------------------------------------------------ #
    def snapshot(self) -> Dict[str, Any]:
        """Return recent events plus aggregate stats for the dashboard."""
        with self._lock:
            events = list(self._events)
            counters = dict(self._counters)
            avg_latency = {
                k: round(sum(v) / len(v), 1)
                for k, v in self._latencies.items() if v
            }
            total_calls = sum(counters.values())
        return {
            "total_events": total_calls,
            "counters": counters,
            "avg_latency_ms": avg_latency,
            "recent_events": events[:40],
        }

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._counters.clear()
            self._latencies.clear()


class _Timer:
    """Internal context manager for timing a block and recording it."""

    def __init__(self, telemetry: TelemetryService, event_type: str,
                 detail: str, metadata: Optional[Dict[str, Any]]) -> None:
        self.telemetry = telemetry
        self.event_type = event_type
        self.detail = detail
        self.metadata = metadata
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        duration_ms = (time.perf_counter() - self._start) * 1000
        detail = self.detail
        if exc_type is not None:
            detail = f"{detail} [error: {exc_type.__name__}]"
        self.telemetry.record(self.event_type, detail, duration_ms, self.metadata)
        return False  # never suppress exceptions


# Module-level singleton shared across the app.
telemetry = TelemetryService()
