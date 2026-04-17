from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class MemorySignal:
    memory_type: str
    signal_id: str
    summary: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "memory_type": self.memory_type,
            "signal_id": self.signal_id,
            "summary": self.summary,
            "score": self.score,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class UnifiedMemoryContext:
    context_id: str
    session_id: str
    run_id: str | None
    query: str
    sources_used: list[str]
    selected_signals: list[MemorySignal]
    selected_count: int
    total_candidates: int
    context_summary: str
    short_term: list[dict[str, Any]] = field(default_factory=list)
    long_term: list[dict[str, Any]] = field(default_factory=list)
    semantic: list[dict[str, Any]] = field(default_factory=list)
    operational: list[dict[str, Any]] = field(default_factory=list)
    scoring: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "query": self.query,
            "sources_used": list(self.sources_used),
            "selected_signals": [item.as_dict() for item in self.selected_signals],
            "selected_count": self.selected_count,
            "total_candidates": self.total_candidates,
            "context_summary": self.context_summary,
            "short_term": [dict(item) for item in self.short_term],
            "long_term": [dict(item) for item in self.long_term],
            "semantic": [dict(item) for item in self.semantic],
            "operational": [dict(item) for item in self.operational],
            "scoring": dict(self.scoring),
            "created_at": self.created_at,
        }
