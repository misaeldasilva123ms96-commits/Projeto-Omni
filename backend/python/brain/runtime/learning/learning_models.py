from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from .models import utc_now_iso


def new_controlled_learning_record_id() -> str:
    return f"clr-{uuid4().hex[:16]}"


def new_improvement_signal_id() -> str:
    return f"cis-{uuid4().hex[:16]}"


@dataclass(slots=True)
class DecisionEvaluation:
    decision_correct: bool | None
    decision_issue: str = ""
    notes: str = ""
    expected_execution: bool = False
    expected_tool: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutionOutcome:
    execution_path: str
    runtime_mode: str
    success: bool
    fallback_triggered: bool = False
    compatibility_execution_active: bool = False
    failure_class: str = ""
    provider_actual: str = ""
    provider_failed: bool = False
    tool_used: str = ""
    tool_succeeded: bool | None = None
    tool_failed: bool | None = None
    tool_denied: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ImprovementSignal:
    signal_id: str
    type: str
    pattern: str
    suggestion: str
    confidence: float
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    advisory: bool = True
    timestamp: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = max(0.0, min(1.0, float(self.confidence)))
        return payload


@dataclass(slots=True)
class LearningRecord:
    record_id: str
    timestamp: str
    input_preview: str
    input_hash: str
    selected_strategy: str
    selected_tool: str
    execution_path: str
    runtime_mode: str
    success: bool
    failure_class: str
    decision_evaluation: DecisionEvaluation
    execution_outcome: ExecutionOutcome
    provider_actual: str = ""
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "input_preview": self.input_preview,
            "input_hash": self.input_hash,
            "selected_strategy": self.selected_strategy,
            "selected_tool": self.selected_tool,
            "execution_path": self.execution_path,
            "runtime_mode": self.runtime_mode,
            "success": self.success,
            "failure_class": self.failure_class,
            "decision_evaluation": self.decision_evaluation.as_dict(),
            "execution_outcome": self.execution_outcome.as_dict(),
            "provider_actual": self.provider_actual,
            "notes": self.notes,
            "metadata": dict(self.metadata),
        }
