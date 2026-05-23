from __future__ import annotations

from typing import Any

from brain.runtime.goals import Goal
from brain.runtime.memory import MemoryFacade
from brain.runtime.planning import TaskPlan

from .models import SimulationContext


class SimulationContextBuilder:
    def __init__(self, *, memory_facade: MemoryFacade | None = None) -> None:
        self.memory_facade = memory_facade

    def build(
        self,
        *,
        plan: TaskPlan | None,
        goal: Goal | None,
        result: dict[str, Any] | None,
        session_id: str | None = None,
    ) -> SimulationContext:
        working = self.memory_facade.working.snapshot() if self.memory_facade is not None else None
        plan_steps = list(getattr(plan, "steps", []) or [])
        current_progress = 0.0
        if working is not None:
            current_progress = working.current_progress
        elif plan is not None:
            current_progress = float(getattr(plan, "completed_step_count", 0) or 0) / max(float(getattr(plan, "total_step_count", 1) or 1), 1.0)
        goal_type = self._goal_type(goal=goal, plan=plan, result=result)
        current_step = next((step for step in plan_steps if step.step_id == getattr(plan, "current_step_id", None)), None)
        repair_count = int(bool(isinstance(result, dict) and result.get("repair_receipt")))
        hard_constraint_active = bool(goal is not None and any(constraint.active and constraint.severity.value == "hard" for constraint in goal.constraints))
        active_constraints = (
            list(working.active_constraints)
            if working is not None and working.active_constraints
            else [constraint.description for constraint in goal.constraints if constraint.active]
            if goal is not None
            else []
        )
        last_outcome = ""
        if isinstance(result, dict):
            error_payload = result.get("error_payload", {}) if isinstance(result.get("error_payload"), dict) else {}
            last_outcome = str(error_payload.get("kind", "")).strip() or ("success" if result.get("ok") else "failure")
        return SimulationContext(
            goal_id=goal.goal_id if goal is not None else getattr(plan, "goal_id", None),
            goal_description=goal.description if goal is not None else str(getattr(plan, "objective", "")),
            goal_type=goal_type,
            current_progress=max(0.0, min(1.0, current_progress)),
            last_action={
                "step_id": getattr(plan, "current_step_id", None),
                "step_type": getattr(current_step, "step_type", "") if current_step is not None else "",
                "selected_tool": str((current_step.metadata or {}).get("selected_tool", "")) if current_step is not None else "",
            },
            last_outcome=last_outcome,
            active_constraints=active_constraints,
            retry_count=int(getattr(current_step, "retry_count", 0) or 0) if current_step is not None else 0,
            repair_count=repair_count,
            session_id=session_id or (working.session_id if working is not None else getattr(plan, "session_id", None)),
            hard_constraint_active=hard_constraint_active,
            goal_present=goal is not None,
            metadata={
                "goal_type_source": self._goal_type_source(goal=goal),
                "plan_id": getattr(plan, "plan_id", None),
            },
        )

    @staticmethod
    def _goal_type(goal: Goal | None, plan: TaskPlan | None, result: dict[str, Any] | None) -> str:
        if goal is not None:
            explicit = str(goal.metadata.get("goal_type", "")).strip()
            if explicit:
                return explicit
            if str(goal.intent).strip():
                return str(goal.intent).strip()
            return SimulationContextBuilder._infer_goal_type(goal.description)
        objective = str(getattr(plan, "objective", "")).strip()
        if objective:
            return SimulationContextBuilder._infer_goal_type(objective)
        if isinstance(result, dict) and result.get("ok"):
            return "execution"
        return "general"

    @staticmethod
    def _goal_type_source(goal: Goal | None) -> str:
        if goal is None:
            return "fallback"
        if str(goal.metadata.get("goal_type", "")).strip():
            return "metadata"
        if str(goal.intent).strip():
            return "intent"
        return "description"

    @staticmethod
    def _infer_goal_type(text: str) -> str:
        lowered = str(text).lower()
        if any(token in lowered for token in ("safety", "segur", "govern", "policy")):
            return "safety"
        if any(token in lowered for token in ("repair", "reparo", "fix", "patch")):
            return "repair"
        if any(token in lowered for token in ("plan", "workflow", "fluxo")):
            return "planning"
        return "execution"
