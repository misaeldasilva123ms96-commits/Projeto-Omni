from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from brain.runtime.planning.models import utc_now_iso


@dataclass(slots=True)
class ExecutionPlanStep:
    """Single auditable step in a Phase-33 execution plan (distinct from operational TaskPlan steps)."""

    step_id: str
    step_type: str
    summary: str
    description: str
    depends_on: list[str]
    requires_validation: bool
    validation_checkpoint_id: str | None
    fallback_edge_id: str | None
    capability_hints: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "summary": self.summary,
            "description": self.description,
            "depends_on": list(self.depends_on),
            "requires_validation": self.requires_validation,
            "validation_checkpoint_id": self.validation_checkpoint_id,
            "fallback_edge_id": self.fallback_edge_id,
            "capability_hints": list(self.capability_hints),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class PlanCheckpointBinding:
    """Validation checkpoint anchored after a concrete plan step."""

    checkpoint_id: str
    label: str
    after_step_id: str
    validation_kind: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "label": self.label,
            "after_step_id": self.after_step_id,
            "validation_kind": self.validation_kind,
        }


@dataclass(slots=True)
class PlanFallbackEdge:
    """Bounded fallback path between steps (metadata for execution / audit)."""

    fallback_id: str
    trigger_step_id: str
    target_step_id: str | None
    notes: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "fallback_id": self.fallback_id,
            "trigger_step_id": self.trigger_step_id,
            "target_step_id": self.target_step_id,
            "notes": self.notes,
        }


@dataclass(slots=True)
class ExecutionPlan:
    """Structured execution plan produced downstream of reasoning (Phase 33)."""

    plan_id: str
    session_id: str | None
    run_id: str | None
    task_id: str
    reasoning_trace_id: str | None
    title: str
    objective: str
    execution_ready: bool
    planning_summary: str
    steps: list[ExecutionPlanStep]
    checkpoints: list[PlanCheckpointBinding]
    fallbacks: list[PlanFallbackEdge]
    linked_reasoning: dict[str, Any]
    metadata: dict[str, Any]
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "reasoning_trace_id": self.reasoning_trace_id,
            "title": self.title,
            "objective": self.objective,
            "execution_ready": self.execution_ready,
            "planning_summary": self.planning_summary,
            "steps": [s.as_dict() for s in self.steps],
            "checkpoints": [c.as_dict() for c in self.checkpoints],
            "fallbacks": [f.as_dict() for f in self.fallbacks],
            "linked_reasoning": dict(self.linked_reasoning),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class PlanningTrace:
    """Concise observability for planning intelligence (Phase 33)."""

    trace_id: str
    plan_id: str
    session_id: str | None
    run_id: str | None
    reasoning_trace_id: str | None
    step_count: int
    dependency_edge_count: int
    checkpoint_count: int
    fallback_count: int
    execution_ready: bool
    fallback_branch_defined: bool
    degraded: bool
    error: str
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "plan_id": self.plan_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "reasoning_trace_id": self.reasoning_trace_id,
            "step_count": self.step_count,
            "dependency_edge_count": self.dependency_edge_count,
            "checkpoint_count": self.checkpoint_count,
            "fallback_count": self.fallback_count,
            "execution_ready": self.execution_ready,
            "fallback_branch_defined": self.fallback_branch_defined,
            "degraded": self.degraded,
            "error": self.error,
            "created_at": self.created_at,
        }

    @classmethod
    def from_plan(
        cls,
        plan: ExecutionPlan,
        *,
        trace_id: str,
        degraded: bool,
        error: str,
    ) -> PlanningTrace:
        dep_edges = sum(len(s.depends_on) for s in plan.steps)
        return cls(
            trace_id=trace_id,
            plan_id=plan.plan_id,
            session_id=plan.session_id,
            run_id=plan.run_id,
            reasoning_trace_id=plan.reasoning_trace_id,
            step_count=len(plan.steps),
            dependency_edge_count=dep_edges,
            checkpoint_count=len(plan.checkpoints),
            fallback_count=len(plan.fallbacks),
            execution_ready=plan.execution_ready,
            fallback_branch_defined=len(plan.fallbacks) > 0,
            degraded=degraded,
            error=str(error or ""),
            created_at=utc_now_iso(),
        )
