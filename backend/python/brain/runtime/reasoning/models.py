from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from brain.runtime.language.oil_schema import OILRequest, OILResult


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ReasoningTrace:
    trace_id: str
    session_id: str | None
    run_id: str | None
    mode: str
    interpreted_intent: str
    interpretation_summary: str
    plan_summary: str
    validation_result: str
    handoff_decision: str
    governance: dict[str, Any] = field(default_factory=dict)
    observability: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "mode": self.mode,
            "interpreted_intent": self.interpreted_intent,
            "interpretation_summary": self.interpretation_summary,
            "plan_summary": self.plan_summary,
            "validation_result": self.validation_result,
            "handoff_decision": self.handoff_decision,
            "governance": dict(self.governance),
            "observability": dict(self.observability),
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class ReasoningOutcome:
    mode: str
    normalized_input: str
    oil_request: OILRequest
    oil_result: OILResult
    execution_handoff: dict[str, Any]
    trace: ReasoningTrace
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "normalized_input": self.normalized_input,
            "confidence": self.confidence,
            "oil_request": self.oil_request.serialize(),
            "oil_result": self.oil_result.serialize(),
            "execution_handoff": dict(self.execution_handoff),
            "trace": self.trace.as_dict(),
        }
