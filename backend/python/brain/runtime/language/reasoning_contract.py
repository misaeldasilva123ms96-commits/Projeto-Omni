from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from brain.runtime.language.input_interpreter import interpret_input
from brain.runtime.language.oil_schema import OILRequest, OILResult
from brain.runtime.language.types import OILTrace, OIL_VERSION


def normalize_input_to_oil_request(
    text: str,
    *,
    session_id: str | None,
    run_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> OILRequest:
    normalized_metadata = dict(metadata or {})
    normalized_metadata["source_component"] = str(normalized_metadata.get("source_component", "runtime.orchestrator")).strip()
    if run_id:
        normalized_metadata["run_id"] = str(run_id).strip()
    request = interpret_input(
        text,
        session_id=session_id,
        metadata=normalized_metadata,
    )
    request.extensions["normalized_input"] = str(text or "").strip()
    return request


@dataclass(slots=True)
class ReasoningHandoffContract:
    """Structured handoff emitted by the reasoning layer."""

    proceed: bool
    mode: str
    intent: str
    task_type: str
    execution_strategy: str
    suggested_capabilities: list[str]
    reasoning_summary: str
    governance: dict[str, Any]
    observability: dict[str, Any]
    plan_steps: list[str]
    validation: dict[str, Any]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "proceed": self.proceed,
            "mode": self.mode,
            "intent": self.intent,
            "task_type": self.task_type,
            "execution_strategy": self.execution_strategy,
            "suggested_capabilities": list(self.suggested_capabilities),
            "reasoning_summary": self.reasoning_summary,
            "governance": dict(self.governance),
            "observability": dict(self.observability),
            "plan_steps": list(self.plan_steps),
            "validation": dict(self.validation),
            "metadata": dict(self.metadata),
        }


def build_reasoning_oil_result(
    *,
    handoff: ReasoningHandoffContract,
    confidence: float,
    mode: str,
) -> OILResult:
    status = "ready" if handoff.proceed else "blocked"
    trace = OILTrace(
        planner="reasoning_engine",
        specialists=["interpret", "plan", "reason", "validate", "handoff_to_execution"],
        memory_used=False,
        extensions={"reasoning_mode": mode},
    )
    return OILResult(
        oil_version=OIL_VERSION,
        result_type="reasoning_handoff",
        status=status,
        data=handoff.as_dict(),
        confidence=max(0.0, min(1.0, float(confidence))),
        trace=trace,
        extensions={"reasoning_mode": mode},
    )
