from __future__ import annotations

from typing import Any

from brain.runtime.planning import TaskPlan
from brain.runtime.simulation import SimulationResult

from .base_specialist import BaseSpecialist
from .models import PlanDecision


class PlannerSpecialist(BaseSpecialist):
    def plan(
        self,
        *,
        goal_id: str | None,
        action: dict[str, Any],
        plan: TaskPlan | None,
        simulation_result: SimulationResult | None,
        replan: bool = False,
    ) -> PlanDecision:
        goal = self.lookup_goal(goal_id)
        goal_metadata = dict(getattr(goal, "metadata", {}) or {})
        explicit_goal_type = str(goal_metadata.get("goal_type", "")).strip()
        goal_type = explicit_goal_type or str(getattr(goal, "intent", "") or "general").strip() or "general"
        plan_steps: list[dict[str, Any]] = []
        if plan is not None:
            for step in plan.steps[:5]:
                plan_steps.append(
                    {
                        "step_id": step.step_id,
                        "title": step.title,
                        "status": step.status.value,
                        "step_type": step.step_type,
                    }
                )
        if not plan_steps:
            plan_steps.append(
                {
                    "step_id": str(action.get("step_id", "runtime-step")),
                    "title": str(action.get("title", action.get("description", "Execute runtime action"))),
                    "status": "pending",
                    "step_type": str(action.get("step_type", "execute_action")),
                }
            )
        procedural_hint = None
        if self.memory_facade is not None:
            procedural_hint = self.memory_facade.get_procedural_recommendation(goal_type, constraint_types=None)
        reasoning_parts = [
            "Planner specialist produced a bounded step view anchored to the active goal."
            if goal_id
            else "Planner specialist produced a bounded step view without an active goal.",
            "Replan mode is active." if replan else "Initial plan mode is active.",
        ]
        confidence = 0.72 if replan else 0.78
        if procedural_hint is not None:
            reasoning_parts.append(f"Procedural memory suggested route '{procedural_hint.recommended_route}'.")
            confidence = min(0.92, confidence + 0.05)
        if simulation_result is not None:
            reasoning_parts.append(
                f"Simulation currently favors '{simulation_result.recommended_route.value}' as a bounded continuation route."
            )
            confidence = min(0.94, confidence + 0.04)
        return PlanDecision.build(
            goal_id=goal_id,
            simulation_id=simulation_result.simulation_id if simulation_result is not None else None,
            reasoning=" ".join(reasoning_parts),
            confidence=confidence,
            plan_steps=plan_steps,
            estimated_cycles=max(1, len(plan_steps)),
            replan=replan,
            metadata={
                "goal_type": goal_type,
                "explicit_goal_type": explicit_goal_type,
                "plan_id": getattr(plan, "plan_id", None),
                "hard_constraint_violation": bool(action.get("hard_constraint_violation")),
            },
        )
