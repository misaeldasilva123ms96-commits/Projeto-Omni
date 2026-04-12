from __future__ import annotations

from typing import Any

from pathlib import Path

from brain.runtime.goals import ConstraintRegistry, CriterionType, Goal, GoalEvaluationResult, GoalEvaluator

from .base_specialist import BaseSpecialist
from .models import ValidationDecision


class ValidatorSpecialist(BaseSpecialist):
    def __init__(
        self,
        *,
        root: Path,
        goal_store=None,
        memory_facade=None,
        simulation_store=None,
        goal_evaluator: GoalEvaluator | None = None,
    ) -> None:
        super().__init__(root=root, goal_store=goal_store, memory_facade=memory_facade, simulation_store=simulation_store)
        self.goal_evaluator = goal_evaluator or GoalEvaluator(ConstraintRegistry())

    def validate(
        self,
        *,
        goal: Goal | None,
        result: dict[str, Any],
        goal_evaluation: GoalEvaluationResult | None = None,
        simulation_id: str | None = None,
    ) -> ValidationDecision:
        if goal is None:
            progress = float(result.get("progress_score", 0.0) or 0.0)
            return ValidationDecision.build(
                goal_id=None,
                simulation_id=simulation_id,
                reasoning="Validator specialist remained goal-none-safe and validated only bounded runtime progress.",
                confidence=0.6,
                criteria_met=[],
                criteria_failed=[],
                criteria_pending=[],
                progress_score=max(0.0, min(1.0, progress)),
                should_stop=False,
                should_fail=False,
                is_achieved=bool(result.get("ok")),
            )

        evaluation = goal_evaluation or self.goal_evaluator.evaluate(goal=goal, runtime_state=result, memory_facade=self.memory_facade)
        unmet = set(evaluation.unmet_criteria)
        validated = set(str(item) for item in result.get("validated_criteria", []) if str(item).strip())
        criteria_met: list[str] = []
        criteria_failed: list[str] = []
        criteria_pending: list[str] = []
        for criterion in goal.success_criteria:
            label = criterion.description
            if criterion.criterion_type == CriterionType.EVALUATIVE:
                if label in validated:
                    criteria_met.append(label)
                else:
                    criteria_pending.append(label)
                continue
            if label in unmet:
                criteria_failed.append(label)
            else:
                criteria_met.append(label)
        reasoning_parts = [
            f"Validator specialist checked {len(goal.success_criteria)} goal criteria.",
            f"Pending evaluative criteria: {len(criteria_pending)}." if criteria_pending else "No pending evaluative criteria remain.",
        ]
        return ValidationDecision.build(
            goal_id=goal.goal_id,
            simulation_id=simulation_id,
            reasoning=" ".join(reasoning_parts),
            confidence=0.88 if not evaluation.should_fail else 0.92,
            criteria_met=criteria_met,
            criteria_failed=criteria_failed,
            criteria_pending=criteria_pending,
            progress_score=evaluation.progress_score,
            should_stop=evaluation.should_stop,
            should_fail=evaluation.should_fail,
            is_achieved=evaluation.is_achieved and not criteria_pending,
            metadata={
                "violated_constraints": list(evaluation.violated_constraints),
                "soft_constraint_violations": list(evaluation.soft_constraint_violations),
                "triggered_stop_conditions": list(evaluation.triggered_stop_conditions),
            },
        )
