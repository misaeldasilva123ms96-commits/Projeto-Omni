from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from typing import Any


def new_turn_id() -> str:
    return f"turn-{int(time.time() * 1000):x}"


def new_experience_id(session_id: str, turn_id: str) -> str:
    h = hashlib.sha256(f"{session_id}|{turn_id}".encode("utf-8")).hexdigest()[:24]
    return f"exp-{h}"


@dataclass(slots=True)
class ExperienceRecord:
    experience_id: str
    session_id: str
    turn_id: str
    timestamp: str
    user_input: str
    normalized_intent: str
    provider_selected: str
    model_selected: str
    tools_selected: list[str]
    strategy_selected: str
    latency_ms: int
    cost_estimate: float | None
    fallback_used: bool
    error_class: str
    response_quality_score: float | None
    feedback_class: str
    feedback_source: str
    success_outcome: bool
    agent_trace_summary: str
    learning_signals_summary: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tools_selected"] = list(self.tools_selected)
        d["metadata"] = dict(self.metadata)
        return d
