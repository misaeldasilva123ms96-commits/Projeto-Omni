from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class CoordinationState:
    """Bounded shared coordination context for one chat-turn coordination (no hidden globals)."""

    coordination_id: str
    coordination_fingerprint: str
    session_id: str
    run_id: str
    plan_id: str
    memory_context_id: str
    strategy_trace_id: str
    coordination_mode: str
    control_execution_allowed: bool
    control_reason_code: str
    routing_task_type: str
    routing_risk_level: str
    routing_execution_strategy: str
    routing_verification_intensity: str
    reasoning_trace_id: str
    decomposition_subtask_count: int = 0
    decomposition_truncated: bool = False
    decomposition_trace_id: str = ""
    specialist_notes: list[str] = field(default_factory=list)

    def record_note(self, note: str) -> None:
        text = str(note or "").strip()
        if text and len(self.specialist_notes) < 48:
            self.specialist_notes.append(text[:400])

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
