from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Episode:
    episode_id: str
    goal_id: str
    subgoal_id: str | None
    session_id: str
    description: str
    event_type: str
    outcome: str
    progress_at_start: float
    progress_at_end: float
    constraints_active: list[str]
    evidence_ids: list[str]
    duration_seconds: float
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Episode":
        return cls(
            episode_id=str(payload.get("episode_id", "")),
            goal_id=str(payload.get("goal_id", "")),
            subgoal_id=str(payload.get("subgoal_id")) if payload.get("subgoal_id") else None,
            session_id=str(payload.get("session_id", "")),
            description=str(payload.get("description", "")),
            event_type=str(payload.get("event_type", "")),
            outcome=str(payload.get("outcome", "")),
            progress_at_start=float(payload.get("progress_at_start", 0.0) or 0.0),
            progress_at_end=float(payload.get("progress_at_end", 0.0) or 0.0),
            constraints_active=[str(item) for item in payload.get("constraints_active", []) if str(item).strip()],
            evidence_ids=[str(item) for item in payload.get("evidence_ids", []) if str(item).strip()],
            duration_seconds=float(payload.get("duration_seconds", 0.0) or 0.0),
            created_at=str(payload.get("created_at", utc_now_iso())),
            metadata=dict(payload.get("metadata", {}) or {}),
        )
