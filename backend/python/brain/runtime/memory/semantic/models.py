from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class SemanticFact:
    fact_id: str
    subject: str
    predicate: str
    object_value: str
    confidence: float
    source_episode_ids: list[str]
    goal_types: list[str]
    created_at: str
    last_reinforced_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["object"] = payload.pop("object_value")
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SemanticFact":
        return cls(
            fact_id=str(payload.get("fact_id", "")),
            subject=str(payload.get("subject", "")),
            predicate=str(payload.get("predicate", "")),
            object_value=str(payload.get("object", payload.get("object_value", ""))),
            confidence=float(payload.get("confidence", 0.0) or 0.0),
            source_episode_ids=[str(item) for item in payload.get("source_episode_ids", []) if str(item).strip()],
            goal_types=[str(item) for item in payload.get("goal_types", []) if str(item).strip()],
            created_at=str(payload.get("created_at", utc_now_iso())),
            last_reinforced_at=str(payload.get("last_reinforced_at", utc_now_iso())),
            metadata=dict(payload.get("metadata", {}) or {}),
        )
