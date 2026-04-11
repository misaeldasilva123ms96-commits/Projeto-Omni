from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ProceduralPattern:
    pattern_id: str
    name: str
    description: str
    applicable_goal_types: list[str]
    applicable_constraint_types: list[str]
    recommended_route: str
    success_rate: float
    sample_size: int
    last_updated: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProceduralPattern":
        return cls(
            pattern_id=str(payload.get("pattern_id", "")),
            name=str(payload.get("name", "")),
            description=str(payload.get("description", "")),
            applicable_goal_types=[str(item) for item in payload.get("applicable_goal_types", []) if str(item).strip()],
            applicable_constraint_types=[str(item) for item in payload.get("applicable_constraint_types", []) if str(item).strip()],
            recommended_route=str(payload.get("recommended_route", "")),
            success_rate=float(payload.get("success_rate", 0.0) or 0.0),
            sample_size=int(payload.get("sample_size", 0) or 0),
            last_updated=str(payload.get("last_updated", utc_now_iso())),
            metadata=dict(payload.get("metadata", {}) or {}),
        )
