from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskClassification(str, Enum):
    SINGLE_STEP = "single_step"
    MULTI_STEP = "multi_step"
    RESUMABLE_WORKFLOW = "resumable_workflow"
    LONG_RUNNING_WORK = "long_running_work"
    NON_PLANNABLE = "non_plannable"


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    PAUSED = "paused"


class TaskPlanStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ResumeDecisionType(str, Enum):
    RESUME_FROM_CHECKPOINT = "resume_from_checkpoint"
    RESTART_CURRENT_STEP = "restart_current_step"
    REBUILD_PLAN = "rebuild_plan"
    MANUAL_INTERVENTION_REQUIRED = "manual_intervention_required"


class PlanCheckpointStatus(str, Enum):
    VALID = "valid"
    STALE = "stale"
    INVALID = "invalid"


@dataclass(slots=True)
class TaskClassificationDecision:
    classification: TaskClassification
    reason_code: str
    summary: str
    should_plan: bool

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["classification"] = self.classification.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaskClassificationDecision":
        return cls(
            classification=TaskClassification(str(payload.get("classification", TaskClassification.NON_PLANNABLE.value))),
            reason_code=str(payload.get("reason_code", "")),
            summary=str(payload.get("summary", "")),
            should_plan=bool(payload.get("should_plan")),
        )


@dataclass(slots=True)
class PlanStep:
    step_id: str
    title: str
    description: str
    step_type: str
    dependency_step_ids: list[str]
    status: PlanStepStatus
    retry_count: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    failure_summary: str = ""
    expected_outcome: str = ""
    produced_artifacts_summary: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanStep":
        return cls(
            step_id=str(payload.get("step_id", "")),
            title=str(payload.get("title", "")),
            description=str(payload.get("description", "")),
            step_type=str(payload.get("step_type", "")),
            dependency_step_ids=[str(item) for item in payload.get("dependency_step_ids", []) if str(item).strip()],
            status=PlanStepStatus(str(payload.get("status", PlanStepStatus.PENDING.value))),
            retry_count=int(payload.get("retry_count", 0) or 0),
            started_at=str(payload.get("started_at")) if payload.get("started_at") else None,
            completed_at=str(payload.get("completed_at")) if payload.get("completed_at") else None,
            failure_summary=str(payload.get("failure_summary", "")),
            expected_outcome=str(payload.get("expected_outcome", "")),
            produced_artifacts_summary=[str(item) for item in payload.get("produced_artifacts_summary", []) if str(item).strip()],
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(slots=True)
class PlanCheckpoint:
    checkpoint_id: str
    plan_id: str
    timestamp: str
    step_id: str | None
    snapshot_summary: str
    resumable_state_payload: dict[str, Any]
    last_outcome_summary: str
    status: PlanCheckpointStatus = PlanCheckpointStatus.VALID

    @classmethod
    def build(
        cls,
        *,
        plan_id: str,
        step_id: str | None,
        snapshot_summary: str,
        resumable_state_payload: dict[str, Any],
        last_outcome_summary: str,
        status: PlanCheckpointStatus = PlanCheckpointStatus.VALID,
    ) -> "PlanCheckpoint":
        return cls(
            checkpoint_id=f"checkpoint-{uuid4()}",
            plan_id=plan_id,
            timestamp=utc_now_iso(),
            step_id=step_id,
            snapshot_summary=snapshot_summary,
            resumable_state_payload=resumable_state_payload,
            last_outcome_summary=last_outcome_summary,
            status=status,
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanCheckpoint":
        return cls(
            checkpoint_id=str(payload.get("checkpoint_id", "")),
            plan_id=str(payload.get("plan_id", "")),
            timestamp=str(payload.get("timestamp", "")),
            step_id=str(payload.get("step_id")) if payload.get("step_id") else None,
            snapshot_summary=str(payload.get("snapshot_summary", "")),
            resumable_state_payload=dict(payload.get("resumable_state_payload", {}) or {}),
            last_outcome_summary=str(payload.get("last_outcome_summary", "")),
            status=PlanCheckpointStatus(str(payload.get("status", PlanCheckpointStatus.VALID.value))),
        )


@dataclass(slots=True)
class TaskPlan:
    plan_id: str
    task_id: str
    title: str
    objective: str
    creation_timestamp: str
    updated_at: str
    status: TaskPlanStatus
    classification: TaskClassification
    current_step_id: str | None
    total_step_count: int
    completed_step_count: int
    failed_step_count: int
    checkpoint_pointer: str | None
    session_id: str | None
    run_id: str | None
    linked_execution_receipt_ids: list[str] = field(default_factory=list)
    linked_repair_receipt_ids: list[str] = field(default_factory=list)
    steps: list[PlanStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        task_id: str,
        title: str,
        objective: str,
        classification: TaskClassification,
        steps: list[PlanStep],
        session_id: str | None,
        run_id: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> "TaskPlan":
        now = utc_now_iso()
        first_step = next((step.step_id for step in steps if step.status == PlanStepStatus.PENDING), None)
        return cls(
            plan_id=f"plan-{uuid4()}",
            task_id=task_id,
            title=title,
            objective=objective,
            creation_timestamp=now,
            updated_at=now,
            status=TaskPlanStatus.CREATED,
            classification=classification,
            current_step_id=first_step,
            total_step_count=len(steps),
            completed_step_count=0,
            failed_step_count=0,
            checkpoint_pointer=None,
            session_id=session_id,
            run_id=run_id,
            steps=steps,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "title": self.title,
            "objective": self.objective,
            "creation_timestamp": self.creation_timestamp,
            "updated_at": self.updated_at,
            "status": self.status.value,
            "classification": self.classification.value,
            "current_step_id": self.current_step_id,
            "total_step_count": self.total_step_count,
            "completed_step_count": self.completed_step_count,
            "failed_step_count": self.failed_step_count,
            "checkpoint_pointer": self.checkpoint_pointer,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "linked_execution_receipt_ids": list(self.linked_execution_receipt_ids),
            "linked_repair_receipt_ids": list(self.linked_repair_receipt_ids),
            "steps": [item.as_dict() for item in self.steps],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaskPlan":
        return cls(
            plan_id=str(payload.get("plan_id", "")),
            task_id=str(payload.get("task_id", "")),
            title=str(payload.get("title", "")),
            objective=str(payload.get("objective", "")),
            creation_timestamp=str(payload.get("creation_timestamp", "")),
            updated_at=str(payload.get("updated_at", payload.get("creation_timestamp", ""))),
            status=TaskPlanStatus(str(payload.get("status", TaskPlanStatus.CREATED.value))),
            classification=TaskClassification(str(payload.get("classification", TaskClassification.NON_PLANNABLE.value))),
            current_step_id=str(payload.get("current_step_id")) if payload.get("current_step_id") else None,
            total_step_count=int(payload.get("total_step_count", 0) or 0),
            completed_step_count=int(payload.get("completed_step_count", 0) or 0),
            failed_step_count=int(payload.get("failed_step_count", 0) or 0),
            checkpoint_pointer=str(payload.get("checkpoint_pointer")) if payload.get("checkpoint_pointer") else None,
            session_id=str(payload.get("session_id")) if payload.get("session_id") else None,
            run_id=str(payload.get("run_id")) if payload.get("run_id") else None,
            linked_execution_receipt_ids=[str(item) for item in payload.get("linked_execution_receipt_ids", []) if str(item).strip()],
            linked_repair_receipt_ids=[str(item) for item in payload.get("linked_repair_receipt_ids", []) if str(item).strip()],
            steps=[PlanStep.from_dict(item) for item in payload.get("steps", []) if isinstance(item, dict)],
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(slots=True)
class ResumeDecision:
    decision: ResumeDecisionType
    reason_code: str
    summary: str
    plan_id: str | None = None
    checkpoint_id: str | None = None
    step_id: str | None = None
    resumable_state_payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return payload


@dataclass(slots=True)
class OperationalSummary:
    plan_id: str
    task_id: str
    current_objective: str
    plan_status: str
    completed_steps: list[str]
    current_step: str | None
    last_failure: str
    next_recommended_action: str
    resumability_state: str
    linked_execution_receipt_ids: list[str] = field(default_factory=list)
    linked_repair_receipt_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OperationalSummary":
        return cls(
            plan_id=str(payload.get("plan_id", "")),
            task_id=str(payload.get("task_id", "")),
            current_objective=str(payload.get("current_objective", "")),
            plan_status=str(payload.get("plan_status", "")),
            completed_steps=[str(item) for item in payload.get("completed_steps", []) if str(item).strip()],
            current_step=str(payload.get("current_step")) if payload.get("current_step") else None,
            last_failure=str(payload.get("last_failure", "")),
            next_recommended_action=str(payload.get("next_recommended_action", "")),
            resumability_state=str(payload.get("resumability_state", "")),
            linked_execution_receipt_ids=[str(item) for item in payload.get("linked_execution_receipt_ids", []) if str(item).strip()],
            linked_repair_receipt_ids=[str(item) for item in payload.get("linked_repair_receipt_ids", []) if str(item).strip()],
            metadata=dict(payload.get("metadata", {}) or {}),
        )
