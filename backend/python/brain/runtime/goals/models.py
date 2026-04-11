from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class GoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ACHIEVED = "achieved"
    FAILED = "failed"
    ABANDONED = "abandoned"


class ConstraintType(str, Enum):
    SCOPE_LIMIT = "scope_limit"
    RESOURCE_LIMIT = "resource_limit"
    SAFETY_LIMIT = "safety_limit"
    COMPATIBILITY = "compatibility"
    TIME_LIMIT = "time_limit"


class Severity(str, Enum):
    HARD = "hard"
    SOFT = "soft"


class CriterionType(str, Enum):
    STRUCTURAL = "structural"
    FUNCTIONAL = "functional"
    EVALUATIVE = "evaluative"
    COMPOSITE = "composite"


class ToleranceType(str, Enum):
    MAX_RETRIES = "max_retries"
    MAX_REPAIRS = "max_repairs"
    ERROR_RATE = "error_rate"
    PARTIAL_SUCCESS = "partial_success"


class StopConditionType(str, Enum):
    MAX_CYCLES = "max_cycles"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    EXTERNAL_SIGNAL = "external_signal"
    DEPENDENCY_FAILED = "dependency_failed"


@dataclass(slots=True)
class Constraint:
    constraint_id: str
    description: str
    constraint_type: ConstraintType
    severity: Severity
    evaluation_fn: str
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        description: str,
        constraint_type: ConstraintType,
        severity: Severity,
        evaluation_fn: str,
        active: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> "Constraint":
        return cls(
            constraint_id=f"constraint-{uuid4()}",
            description=description,
            constraint_type=constraint_type,
            severity=severity,
            evaluation_fn=evaluation_fn,
            active=active,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["constraint_type"] = self.constraint_type.value
        payload["severity"] = self.severity.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Constraint":
        return cls(
            constraint_id=str(payload.get("constraint_id", "")),
            description=str(payload.get("description", "")),
            constraint_type=ConstraintType(str(payload.get("constraint_type", ConstraintType.SCOPE_LIMIT.value))),
            severity=Severity(str(payload.get("severity", Severity.SOFT.value))),
            evaluation_fn=str(payload.get("evaluation_fn", "")),
            active=bool(payload.get("active", True)),
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(slots=True)
class SuccessCriterion:
    criterion_id: str
    description: str
    criterion_type: CriterionType
    weight: float
    required: bool
    evaluation_fn: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        description: str,
        criterion_type: CriterionType,
        weight: float,
        required: bool,
        evaluation_fn: str,
        metadata: dict[str, Any] | None = None,
    ) -> "SuccessCriterion":
        return cls(
            criterion_id=f"criterion-{uuid4()}",
            description=description,
            criterion_type=criterion_type,
            weight=max(0.0, weight),
            required=required,
            evaluation_fn=evaluation_fn,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["criterion_type"] = self.criterion_type.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SuccessCriterion":
        return cls(
            criterion_id=str(payload.get("criterion_id", "")),
            description=str(payload.get("description", "")),
            criterion_type=CriterionType(str(payload.get("criterion_type", CriterionType.EVALUATIVE.value))),
            weight=float(payload.get("weight", 1.0) or 1.0),
            required=bool(payload.get("required", False)),
            evaluation_fn=str(payload.get("evaluation_fn", "")),
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(slots=True)
class FailureTolerance:
    tolerance_id: str
    description: str
    tolerance_type: ToleranceType
    threshold: float
    current_value: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        description: str,
        tolerance_type: ToleranceType,
        threshold: float,
        current_value: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> "FailureTolerance":
        return cls(
            tolerance_id=f"tolerance-{uuid4()}",
            description=description,
            tolerance_type=tolerance_type,
            threshold=threshold,
            current_value=current_value,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tolerance_type"] = self.tolerance_type.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FailureTolerance":
        return cls(
            tolerance_id=str(payload.get("tolerance_id", "")),
            description=str(payload.get("description", "")),
            tolerance_type=ToleranceType(str(payload.get("tolerance_type", ToleranceType.MAX_RETRIES.value))),
            threshold=float(payload.get("threshold", 0.0) or 0.0),
            current_value=float(payload.get("current_value", 0.0) or 0.0),
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(slots=True)
class StopCondition:
    stop_condition_id: str
    description: str
    condition_type: StopConditionType
    trigger_fn: str
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        description: str,
        condition_type: StopConditionType,
        trigger_fn: str,
        active: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> "StopCondition":
        return cls(
            stop_condition_id=f"stop-condition-{uuid4()}",
            description=description,
            condition_type=condition_type,
            trigger_fn=trigger_fn,
            active=active,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["condition_type"] = self.condition_type.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StopCondition":
        return cls(
            stop_condition_id=str(payload.get("stop_condition_id", "")),
            description=str(payload.get("description", "")),
            condition_type=StopConditionType(str(payload.get("condition_type", StopConditionType.MAX_CYCLES.value))),
            trigger_fn=str(payload.get("trigger_fn", "")),
            active=bool(payload.get("active", True)),
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(slots=True)
class SubGoal:
    subgoal_id: str
    parent_goal_id: str
    description: str
    success_criteria: list[SuccessCriterion]
    order: int
    status: GoalStatus
    depends_on_subgoal_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        parent_goal_id: str,
        description: str,
        success_criteria: list[SuccessCriterion],
        order: int,
        status: GoalStatus = GoalStatus.ACTIVE,
        depends_on_subgoal_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "SubGoal":
        return cls(
            subgoal_id=f"subgoal-{uuid4()}",
            parent_goal_id=parent_goal_id,
            description=description,
            success_criteria=success_criteria,
            order=order,
            status=status,
            depends_on_subgoal_ids=depends_on_subgoal_ids or [],
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "subgoal_id": self.subgoal_id,
            "parent_goal_id": self.parent_goal_id,
            "description": self.description,
            "success_criteria": [criterion.as_dict() for criterion in self.success_criteria],
            "order": self.order,
            "status": self.status.value,
            "depends_on_subgoal_ids": list(self.depends_on_subgoal_ids),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SubGoal":
        return cls(
            subgoal_id=str(payload.get("subgoal_id", "")),
            parent_goal_id=str(payload.get("parent_goal_id", "")),
            description=str(payload.get("description", "")),
            success_criteria=[SuccessCriterion.from_dict(item) for item in payload.get("success_criteria", []) if isinstance(item, dict)],
            order=int(payload.get("order", 0) or 0),
            status=GoalStatus(str(payload.get("status", GoalStatus.ACTIVE.value))),
            depends_on_subgoal_ids=[str(item) for item in payload.get("depends_on_subgoal_ids", []) if str(item).strip()],
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(slots=True)
class Goal:
    goal_id: str
    description: str
    intent: str
    subgoals: list[SubGoal]
    constraints: list[Constraint]
    success_criteria: list[SuccessCriterion]
    failure_tolerances: list[FailureTolerance]
    stop_conditions: list[StopCondition]
    status: GoalStatus
    priority: int
    created_at: str
    resolved_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        description: str,
        intent: str,
        subgoals: list[SubGoal],
        constraints: list[Constraint],
        success_criteria: list[SuccessCriterion],
        failure_tolerances: list[FailureTolerance],
        stop_conditions: list[StopCondition],
        priority: int,
        status: GoalStatus = GoalStatus.ACTIVE,
        metadata: dict[str, Any] | None = None,
    ) -> "Goal":
        return cls(
            goal_id=f"goal-{uuid4()}",
            description=description,
            intent=intent,
            subgoals=subgoals,
            constraints=constraints,
            success_criteria=success_criteria,
            failure_tolerances=failure_tolerances,
            stop_conditions=stop_conditions,
            status=status,
            priority=priority,
            created_at=utc_now_iso(),
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "intent": self.intent,
            "subgoals": [subgoal.as_dict() for subgoal in self.subgoals],
            "constraints": [constraint.as_dict() for constraint in self.constraints],
            "success_criteria": [criterion.as_dict() for criterion in self.success_criteria],
            "failure_tolerances": [tolerance.as_dict() for tolerance in self.failure_tolerances],
            "stop_conditions": [condition.as_dict() for condition in self.stop_conditions],
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Goal":
        return cls(
            goal_id=str(payload.get("goal_id", "")),
            description=str(payload.get("description", "")),
            intent=str(payload.get("intent", "")),
            subgoals=[SubGoal.from_dict(item) for item in payload.get("subgoals", []) if isinstance(item, dict)],
            constraints=[Constraint.from_dict(item) for item in payload.get("constraints", []) if isinstance(item, dict)],
            success_criteria=[SuccessCriterion.from_dict(item) for item in payload.get("success_criteria", []) if isinstance(item, dict)],
            failure_tolerances=[FailureTolerance.from_dict(item) for item in payload.get("failure_tolerances", []) if isinstance(item, dict)],
            stop_conditions=[StopCondition.from_dict(item) for item in payload.get("stop_conditions", []) if isinstance(item, dict)],
            status=GoalStatus(str(payload.get("status", GoalStatus.ACTIVE.value))),
            priority=int(payload.get("priority", 3) or 3),
            created_at=str(payload.get("created_at", utc_now_iso())),
            resolved_at=str(payload.get("resolved_at")) if payload.get("resolved_at") else None,
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(slots=True, frozen=True)
class GoalContext:
    goal_id: str
    description: str
    intent: str
    active_constraints: tuple[str, ...]
    success_criteria_descriptions: tuple[str, ...]
    stop_condition_descriptions: tuple[str, ...]
    status: str
    priority: int

    @classmethod
    def from_goal(cls, goal: Goal) -> "GoalContext":
        return cls(
            goal_id=goal.goal_id,
            description=goal.description,
            intent=goal.intent,
            active_constraints=tuple(constraint.description for constraint in goal.constraints if constraint.active),
            success_criteria_descriptions=tuple(criterion.description for criterion in goal.success_criteria),
            stop_condition_descriptions=tuple(condition.description for condition in goal.stop_conditions if condition.active),
            status=goal.status.value,
            priority=goal.priority,
        )

    def to_prompt_block(self) -> str:
        constraints = "; ".join(self.active_constraints) if self.active_constraints else "No active constraints."
        criteria = "; ".join(self.success_criteria_descriptions) if self.success_criteria_descriptions else "No success criteria."
        stops = "; ".join(self.stop_condition_descriptions) if self.stop_condition_descriptions else "No stop conditions."
        return (
            f"Goal ID: {self.goal_id}\n"
            f"Goal: {self.description}\n"
            f"Intent: {self.intent}\n"
            f"Status: {self.status}\n"
            f"Priority: {self.priority}\n"
            f"Constraints: {constraints}\n"
            f"Success Criteria: {criteria}\n"
            f"Stop Conditions: {stops}"
        )


@dataclass(slots=True)
class GoalEvaluationResult:
    should_stop: bool
    should_fail: bool
    is_achieved: bool
    progress_score: float
    violated_constraints: list[str]
    triggered_stop_conditions: list[str]
    unmet_criteria: list[str]
    reasoning: str
    soft_constraint_violations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
