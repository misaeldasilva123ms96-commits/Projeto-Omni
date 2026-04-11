from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class WorkingMemoryEvent:
    event_id: str
    event_type: str
    description: str
    outcome: str
    progress_score: float
    evidence_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkingMemoryEvent":
        return cls(
            event_id=str(payload.get("event_id", "")),
            event_type=str(payload.get("event_type", "")),
            description=str(payload.get("description", "")),
            outcome=str(payload.get("outcome", "")),
            progress_score=float(payload.get("progress_score", 0.0) or 0.0),
            evidence_ids=[str(item) for item in payload.get("evidence_ids", []) if str(item).strip()],
            metadata=dict(payload.get("metadata", {}) or {}),
            timestamp=str(payload.get("timestamp", utc_now_iso())),
        )


@dataclass(slots=True)
class WorkingMemoryState:
    session_id: str | None = None
    goal_id: str | None = None
    active_plan_id: str | None = None
    recent_events: list[WorkingMemoryEvent] = field(default_factory=list)
    active_constraints: list[str] = field(default_factory=list)
    current_progress: float = 0.0
    opened_at: str | None = None
    closed_at: str | None = None
    ttl_seconds: int = 3600
    status: str = "idle"

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["recent_events"] = [event.as_dict() for event in self.recent_events]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkingMemoryState":
        return cls(
            session_id=str(payload.get("session_id")) if payload.get("session_id") else None,
            goal_id=str(payload.get("goal_id")) if payload.get("goal_id") else None,
            active_plan_id=str(payload.get("active_plan_id")) if payload.get("active_plan_id") else None,
            recent_events=[
                WorkingMemoryEvent.from_dict(item)
                for item in payload.get("recent_events", [])
                if isinstance(item, dict)
            ],
            active_constraints=[str(item) for item in payload.get("active_constraints", []) if str(item).strip()],
            current_progress=float(payload.get("current_progress", 0.0) or 0.0),
            opened_at=str(payload.get("opened_at")) if payload.get("opened_at") else None,
            closed_at=str(payload.get("closed_at")) if payload.get("closed_at") else None,
            ttl_seconds=int(payload.get("ttl_seconds", 3600) or 3600),
            status=str(payload.get("status", "idle")),
        )
