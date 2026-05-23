from __future__ import annotations

from typing import Any

from .constraint_registry import ConstraintRegistry
from .models import Goal, GoalEvaluationResult, Severity, ToleranceType


class GoalEvaluator:
    def __init__(self, registry: ConstraintRegistry) -> None:
        self.registry = registry

    def evaluate(
        self,
        *,
        goal: Goal,
        runtime_state: dict[str, object] | None = None,
        memory_facade: Any | None = None,
    ) -> GoalEvaluationResult:
        runtime_state = dict(runtime_state or {})
        violated_constraints: list[str] = []
        soft_violations: list[str] = []
        triggered_stop_conditions: list[str] = []
        unmet_criteria: list[str] = []

        hard_failure = False
        for constraint in goal.constraints:
            if not constraint.active:
                continue
            passed, reason = self.registry.evaluate(constraint.evaluation_fn, constraint, runtime_state)
            if passed:
                continue
            entry = f"{constraint.description}: {reason}"
            if constraint.severity == Severity.HARD:
                violated_constraints.append(entry)
                hard_failure = True
            else:
                soft_violations.append(entry)

        should_stop = False
        for condition in goal.stop_conditions:
            if not condition.active:
                continue
            passed, reason = self.registry.evaluate(condition.trigger_fn, condition, runtime_state)
            if not passed:
                triggered_stop_conditions.append(f"{condition.description}: {reason}")
                should_stop = True

        tolerance_failure = False
        for tolerance in goal.failure_tolerances:
            current_value = float(runtime_state.get(tolerance.tolerance_type.value, tolerance.current_value) or 0.0)
            tolerance.current_value = current_value
            if tolerance.tolerance_type in {ToleranceType.MAX_RETRIES, ToleranceType.MAX_REPAIRS} and current_value > tolerance.threshold:
                tolerance_failure = True
            elif tolerance.tolerance_type == ToleranceType.ERROR_RATE and current_value > tolerance.threshold:
                tolerance_failure = True
            elif tolerance.tolerance_type == ToleranceType.PARTIAL_SUCCESS and current_value < tolerance.threshold:
                tolerance_failure = True

        total_weight = sum(max(criterion.weight, 0.0) for criterion in goal.success_criteria) or 1.0
        achieved_weight = 0.0
        required_ok = True
        unmet_required = False
        for criterion in goal.success_criteria:
            passed, reason = self.registry.evaluate(criterion.evaluation_fn, criterion, runtime_state)
            if passed:
                achieved_weight += max(criterion.weight, 0.0)
            else:
                unmet_criteria.append(f"{criterion.description}: {reason}")
                if criterion.required:
                    required_ok = False
                    unmet_required = True
        progress_score = max(0.0, min(1.0, achieved_weight / total_weight))
        is_achieved = required_ok and not unmet_required
        should_fail = hard_failure or tolerance_failure
        reasoning_parts = []
        if is_achieved:
            reasoning_parts.append("All required success criteria passed.")
        if violated_constraints:
            reasoning_parts.append("Hard constraints were violated.")
        if soft_violations:
            reasoning_parts.append("Soft constraints were violated but tracked explicitly.")
        if triggered_stop_conditions:
            reasoning_parts.append("Stop conditions were triggered.")
        if tolerance_failure:
            reasoning_parts.append("Failure tolerance threshold was exceeded.")
        if not reasoning_parts:
            reasoning_parts.append("Goal remains active with partial progress.")
        historical_context = None
        if memory_facade is not None and not is_achieved:
            try:
                similar = memory_facade.recall_similar(
                    event_type=str(runtime_state.get("event_type", "goal_resolution")),
                    progress=progress_score,
                    limit=3,
                )
                procedural = memory_facade.get_procedural_recommendation(goal.intent)
                semantic = memory_facade.get_semantic_facts(goal.intent, limit=3)
                if similar or procedural is not None or semantic:
                    historical_context = {
                        "similar_episodes": [episode.as_dict() for episode in similar],
                        "procedural_recommendation": procedural.as_dict() if procedural is not None else None,
                        "semantic_facts": [fact.as_dict() for fact in semantic],
                    }
            except Exception:
                historical_context = None
        return GoalEvaluationResult(
            should_stop=should_stop,
            should_fail=should_fail,
            is_achieved=is_achieved,
            progress_score=progress_score,
            violated_constraints=violated_constraints,
            triggered_stop_conditions=triggered_stop_conditions,
            unmet_criteria=unmet_criteria,
            reasoning=" ".join(reasoning_parts),
            soft_constraint_violations=soft_violations,
            historical_context=historical_context,
        )
