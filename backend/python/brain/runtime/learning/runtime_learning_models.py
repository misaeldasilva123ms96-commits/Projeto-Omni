from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from brain.runtime.learning.models import utc_now_iso


class SignalPolarity(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class RuntimeLearningStage(str, Enum):
    REASONING = "reasoning"
    MEMORY_INTELLIGENCE = "memory_intelligence"
    PLANNING = "planning"
    EXECUTION = "execution"
    RUNTIME = "runtime"


class OutcomeClass(str, Enum):
    SUCCESS = "success"
    DEGRADED = "degraded"
    FAILURE = "failure"


@dataclass(slots=True)
class RuntimeFeedbackSignal:
    """Phase 34 — bounded evidence signal derived from a chat turn (distinct from pattern LearningSignal)."""

    signal_id: str
    signal_type: str
    source_stage: RuntimeLearningStage
    polarity: SignalPolarity
    summary: str
    weight: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "source_stage": self.source_stage.value,
            "polarity": self.polarity.value,
            "summary": self.summary[:500],
            "weight": max(0.0, min(1.0, float(self.weight))),
            "evidence": dict(self.evidence),
        }


@dataclass(slots=True)
class ExecutionOutcomeAssessment:
    outcome_class: OutcomeClass
    execution_path: str
    response_was_safe_fallback: bool
    runtime_fallback_reason: str
    evaluation_overall: float | None
    evaluation_flag_count: int
    duration_ms: int
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome_class": self.outcome_class.value,
            "execution_path": self.execution_path,
            "response_was_safe_fallback": self.response_was_safe_fallback,
            "runtime_fallback_reason": self.runtime_fallback_reason,
            "evaluation_overall": self.evaluation_overall,
            "evaluation_flag_count": self.evaluation_flag_count,
            "duration_ms": self.duration_ms,
            "notes": list(self.notes)[:12],
        }


@dataclass(slots=True)
class RuntimeLearningSummary:
    """Aggregate view for observability and session payloads."""

    headline: str
    positive_signals: int
    negative_signals: int
    mixed_signals: int
    neutral_signals: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline[:400],
            "positive_signals": self.positive_signals,
            "negative_signals": self.negative_signals,
            "mixed_signals": self.mixed_signals,
            "neutral_signals": self.neutral_signals,
        }


@dataclass(slots=True)
class RuntimeLearningRecord:
    record_id: str
    session_id: str | None
    run_id: str | None
    reasoning_trace_id: str | None
    planning_trace_id: str | None
    plan_id: str | None
    assessment: ExecutionOutcomeAssessment
    signals: list[RuntimeFeedbackSignal]
    summary: RuntimeLearningSummary
    persisted: bool
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "reasoning_trace_id": self.reasoning_trace_id,
            "planning_trace_id": self.planning_trace_id,
            "plan_id": self.plan_id,
            "assessment": self.assessment.as_dict(),
            "signals": [s.as_dict() for s in self.signals[:24]],
            "summary": self.summary.as_dict(),
            "persisted": self.persisted,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class RuntimeLearningTrace:
    """Structured audit / observability for Phase 34."""

    trace_id: str
    learning_record_id: str
    session_id: str | None
    run_id: str | None
    signal_count: int
    positive_count: int
    negative_count: int
    mixed_count: int
    neutral_count: int
    outcome_class: str
    execution_degraded: bool
    persisted: bool
    assessment_summary: str
    degraded_assessment: bool
    error: str
    created_at: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "learning_record_id": self.learning_record_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "signal_count": self.signal_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "mixed_count": self.mixed_count,
            "neutral_count": self.neutral_count,
            "outcome_class": self.outcome_class,
            "execution_degraded": self.execution_degraded,
            "persisted": self.persisted,
            "assessment_summary": self.assessment_summary[:500],
            "degraded_assessment": self.degraded_assessment,
            "error": self.error[:500],
            "created_at": self.created_at,
        }

    @classmethod
    def from_record(
        cls,
        record: RuntimeLearningRecord,
        *,
        trace_id: str,
        degraded_assessment: bool,
        error: str,
    ) -> RuntimeLearningTrace:
        pos = neg = mix = neu = 0
        for s in record.signals:
            if s.polarity == SignalPolarity.POSITIVE:
                pos += 1
            elif s.polarity == SignalPolarity.NEGATIVE:
                neg += 1
            elif s.polarity == SignalPolarity.MIXED:
                mix += 1
            else:
                neu += 1
        degraded = (
            record.assessment.outcome_class == OutcomeClass.DEGRADED
            or record.assessment.response_was_safe_fallback
            or bool(record.assessment.runtime_fallback_reason)
        )
        return cls(
            trace_id=trace_id,
            learning_record_id=record.record_id,
            session_id=record.session_id,
            run_id=record.run_id,
            signal_count=len(record.signals),
            positive_count=pos,
            negative_count=neg,
            mixed_count=mix,
            neutral_count=neu,
            outcome_class=record.assessment.outcome_class.value,
            execution_degraded=degraded,
            persisted=record.persisted,
            assessment_summary=record.summary.headline,
            degraded_assessment=degraded_assessment,
            error=str(error or ""),
        )


def new_learning_record_id() -> str:
    return f"lr34-{uuid4().hex[:16]}"


def new_learning_trace_id(record_id: str) -> str:
    return f"ltr34-{uuid4().hex[:10]}-{record_id[-8:]}"
