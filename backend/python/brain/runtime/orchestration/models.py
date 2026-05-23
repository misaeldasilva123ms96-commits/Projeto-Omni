from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrchestrationRoute(str, Enum):
    DIRECT_EXECUTION = "direct_execution"
    REPAIR_ATTEMPT = "repair_attempt"
    RETRY_EXECUTION = "retry_execution"
    PLAN_REBUILD = "plan_rebuild"
    ANALYSIS_STEP = "analysis_step"
    TOOL_DELEGATION = "tool_delegation"
    PAUSE_PLAN = "pause_plan"
    ESCALATE_FAILURE = "escalate_failure"
    COMPLETE_PLAN = "complete_plan"


@dataclass(slots=True)
class OrchestrationContext:
    context_id: str
    session_id: str | None
    task_id: str | None
    run_id: str | None
    plan_id: str | None
    plan_status: str
    current_step_id: str | None
    current_step_status: str
    continuation_decision_type: str
    checkpoint_id: str | None
    checkpoint_status: str
    goal_id: str | None
    goal_context: dict[str, Any] | None
    operational_summary: dict[str, Any]
    action: dict[str, Any]
    recent_execution_receipt_ids: list[str] = field(default_factory=list)
    recent_repair_receipt_ids: list[str] = field(default_factory=list)
    learning_signals: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        session_id: str | None,
        task_id: str | None,
        run_id: str | None,
        plan_id: str | None,
        plan_status: str,
        current_step_id: str | None,
        current_step_status: str,
        continuation_decision_type: str,
        checkpoint_id: str | None,
        checkpoint_status: str,
        goal_id: str | None,
        goal_context: dict[str, Any] | None,
        operational_summary: dict[str, Any],
        action: dict[str, Any],
        recent_execution_receipt_ids: list[str] | None = None,
        recent_repair_receipt_ids: list[str] | None = None,
        learning_signals: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "OrchestrationContext":
        return cls(
            context_id=f"orchestration-context-{uuid4()}",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            plan_id=plan_id,
            plan_status=plan_status,
            current_step_id=current_step_id,
            current_step_status=current_step_status,
            continuation_decision_type=continuation_decision_type,
            checkpoint_id=checkpoint_id,
            checkpoint_status=checkpoint_status,
            goal_id=goal_id,
            goal_context=goal_context,
            operational_summary=operational_summary,
            action=action,
            recent_execution_receipt_ids=recent_execution_receipt_ids or [],
            recent_repair_receipt_ids=recent_repair_receipt_ids or [],
            learning_signals=learning_signals or [],
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CapabilityDescriptor:
    capability_id: str
    subsystem: str
    supported_action_types: list[str]
    priority_level: int
    confidence_score: float
    failure_risk: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OrchestrationPolicy:
    allow_tool_delegation: bool = True
    allow_analysis_routing: bool = True
    allow_learning_hints: bool = True
    max_learning_weight: float = 0.25

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OrchestrationDecision:
    decision_id: str
    context_id: str
    plan_id: str | None
    task_id: str | None
    step_id: str | None
    selected_capability_id: str
    route: OrchestrationRoute
    reason_code: str
    reason_summary: str
    confidence_score: float
    timestamp: str
    linked_execution_receipt_ids: list[str] = field(default_factory=list)
    linked_repair_receipt_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        context_id: str,
        plan_id: str | None,
        task_id: str | None,
        step_id: str | None,
        selected_capability_id: str,
        route: OrchestrationRoute,
        reason_code: str,
        reason_summary: str,
        confidence_score: float,
        linked_execution_receipt_ids: list[str] | None = None,
        linked_repair_receipt_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "OrchestrationDecision":
        return cls(
            decision_id=f"orchestration-decision-{uuid4()}",
            context_id=context_id,
            plan_id=plan_id,
            task_id=task_id,
            step_id=step_id,
            selected_capability_id=selected_capability_id,
            route=route,
            reason_code=reason_code,
            reason_summary=reason_summary,
            confidence_score=confidence_score,
            timestamp=utc_now_iso(),
            linked_execution_receipt_ids=linked_execution_receipt_ids or [],
            linked_repair_receipt_ids=linked_repair_receipt_ids or [],
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["route"] = self.route.value
        return payload


@dataclass(slots=True)
class ConflictResolution:
    resolution_id: str
    selected_route: OrchestrationRoute
    reason_code: str
    reason_summary: str
    conflicts: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        selected_route: OrchestrationRoute,
        reason_code: str,
        reason_summary: str,
        conflicts: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ConflictResolution":
        return cls(
            resolution_id=f"orchestration-resolution-{uuid4()}",
            selected_route=selected_route,
            reason_code=reason_code,
            reason_summary=reason_summary,
            conflicts=conflicts or [],
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["selected_route"] = self.selected_route.value
        return payload


@dataclass(slots=True)
class OrchestrationResult:
    result_id: str
    context_id: str
    decision_id: str
    route: OrchestrationRoute
    synthesized_summary: str
    artifact_references: dict[str, Any]
    primary_result: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        context_id: str,
        decision_id: str,
        route: OrchestrationRoute,
        synthesized_summary: str,
        artifact_references: dict[str, Any],
        primary_result: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> "OrchestrationResult":
        return cls(
            result_id=f"orchestration-result-{uuid4()}",
            context_id=context_id,
            decision_id=decision_id,
            route=route,
            synthesized_summary=synthesized_summary,
            artifact_references=artifact_references,
            primary_result=primary_result,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["route"] = self.route.value
        return payload
