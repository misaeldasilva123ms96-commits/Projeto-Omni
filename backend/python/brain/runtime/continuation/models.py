from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContinuationDecisionType(str, Enum):
    CONTINUE_EXECUTION = "continue_execution"
    RETRY_STEP = "retry_step"
    PAUSE_PLAN = "pause_plan"
    REBUILD_PLAN = "rebuild_plan"
    ESCALATE_FAILURE = "escalate_failure"
    COMPLETE_PLAN = "complete_plan"


class PlanHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALLED = "stalled"
    BLOCKED = "blocked"
    COMPLETED = "completed"


@dataclass(slots=True)
class ContinuationPolicy:
    max_retries_per_step: int = 2
    allow_replan: bool = True
    allow_auto_pause: bool = True
    allow_auto_escalate: bool = True
    max_replans_per_plan: int = 1

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlanEvaluation:
    evaluation_id: str
    plan_id: str
    current_step_id: str | None
    plan_health: PlanHealth
    progress_ratio: float
    failed_step_count: int
    blocked_step_count: int
    retry_pressure: float
    repair_outcome_summary: str
    resumability_state: str
    dependency_health: str
    recent_receipt_summary: dict[str, Any]
    recommendation_hints: list[str]
    timestamp: str

    @classmethod
    def build(
        cls,
        *,
        plan_id: str,
        current_step_id: str | None,
        plan_health: PlanHealth,
        progress_ratio: float,
        failed_step_count: int,
        blocked_step_count: int,
        retry_pressure: float,
        repair_outcome_summary: str,
        resumability_state: str,
        dependency_health: str,
        recent_receipt_summary: dict[str, Any],
        recommendation_hints: list[str],
    ) -> "PlanEvaluation":
        return cls(
            evaluation_id=f"continuation-evaluation-{uuid4()}",
            plan_id=plan_id,
            current_step_id=current_step_id,
            plan_health=plan_health,
            progress_ratio=progress_ratio,
            failed_step_count=failed_step_count,
            blocked_step_count=blocked_step_count,
            retry_pressure=retry_pressure,
            repair_outcome_summary=repair_outcome_summary,
            resumability_state=resumability_state,
            dependency_health=dependency_health,
            recent_receipt_summary=recent_receipt_summary,
            recommendation_hints=recommendation_hints,
            timestamp=utc_now_iso(),
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["plan_health"] = self.plan_health.value
        return payload


@dataclass(slots=True)
class ContinuationDecision:
    decision_id: str
    plan_id: str
    task_id: str
    step_id: str | None
    decision_type: ContinuationDecisionType
    reason_code: str
    reason_summary: str
    confidence_score: float
    recommended_action: str
    timestamp: str
    linked_execution_receipt_ids: list[str] = field(default_factory=list)
    linked_repair_receipt_ids: list[str] = field(default_factory=list)
    linked_checkpoint_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        plan_id: str,
        task_id: str,
        step_id: str | None,
        decision_type: ContinuationDecisionType,
        reason_code: str,
        reason_summary: str,
        confidence_score: float,
        recommended_action: str,
        linked_execution_receipt_ids: list[str] | None = None,
        linked_repair_receipt_ids: list[str] | None = None,
        linked_checkpoint_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ContinuationDecision":
        return cls(
            decision_id=f"continuation-decision-{uuid4()}",
            plan_id=plan_id,
            task_id=task_id,
            step_id=step_id,
            decision_type=decision_type,
            reason_code=reason_code,
            reason_summary=reason_summary,
            confidence_score=confidence_score,
            recommended_action=recommended_action,
            timestamp=utc_now_iso(),
            linked_execution_receipt_ids=linked_execution_receipt_ids or [],
            linked_repair_receipt_ids=linked_repair_receipt_ids or [],
            linked_checkpoint_id=linked_checkpoint_id,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision_type"] = self.decision_type.value
        return payload
