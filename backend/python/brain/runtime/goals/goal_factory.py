from __future__ import annotations

from typing import Any

from .models import (
    Constraint,
    ConstraintType,
    CriterionType,
    FailureTolerance,
    Goal,
    GoalStatus,
    Severity,
    StopCondition,
    StopConditionType,
    SuccessCriterion,
    ToleranceType,
)


class GoalFactory:
    def create_goal(
        self,
        *,
        description: str,
        intent: str,
        subgoals: list | None = None,
        constraints: list[Constraint] | None = None,
        success_criteria: list[SuccessCriterion] | None = None,
        failure_tolerances: list[FailureTolerance] | None = None,
        stop_conditions: list[StopCondition] | None = None,
        priority: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> Goal:
        description = str(description).strip()
        if not description:
            raise ValueError("Goal description is required.")
        criteria = list(success_criteria or [])
        if not any(criterion.required for criterion in criteria):
            criteria.append(
                SuccessCriterion.build(
                    description="The runtime produces a coherent successful outcome for the goal.",
                    criterion_type=CriterionType.EVALUATIVE,
                    weight=1.0,
                    required=True,
                    evaluation_fn="result_ok",
                )
            )
        return Goal.build(
            description=description,
            intent=str(intent or "execution").strip() or "execution",
            subgoals=list(subgoals or []),
            constraints=list(constraints or []),
            success_criteria=criteria,
            failure_tolerances=list(
                failure_tolerances
                or [
                    FailureTolerance.build(
                        description="Bound retries during goal pursuit.",
                        tolerance_type=ToleranceType.MAX_RETRIES,
                        threshold=2,
                    )
                ]
            ),
            stop_conditions=list(
                stop_conditions
                or [
                    StopCondition.build(
                        description="Stop if execution cycles exceed the bounded runtime window.",
                        condition_type=StopConditionType.MAX_CYCLES,
                        trigger_fn="max_cycles_not_reached",
                        metadata={"max_cycles": 12},
                    )
                ]
            ),
            priority=max(1, min(5, int(priority or 3))),
            status=GoalStatus.ACTIVE,
            metadata=metadata or {},
        )

    def infer_from_task(self, task: str, context: dict[str, Any] | None = None) -> Goal:
        context = context or {}
        normalized = str(task).strip() or "Complete the current bounded runtime task."
        actions = [action for action in context.get("actions", []) if isinstance(action, dict)]
        selected_tools = [str(action.get("selected_tool", "")).strip() for action in actions]
        constraints: list[Constraint] = []
        if selected_tools:
            constraints.append(
                Constraint.build(
                    description="Stay within the subsystems implied by the current task.",
                    constraint_type=ConstraintType.SCOPE_LIMIT,
                    severity=Severity.HARD,
                    evaluation_fn="proposal_within_goal_scope",
                    metadata={"allowed_subsystems": self._allowed_subsystems_from_tools(selected_tools)},
                )
            )
        if len(actions) > 1:
            criteria = [
                SuccessCriterion.build(
                    description="The inferred operational workflow reaches full bounded completion.",
                    criterion_type=CriterionType.COMPOSITE,
                    weight=1.0,
                    required=True,
                    evaluation_fn="goal_plan_complete",
                    metadata={"required_progress": 1.0},
                )
            ]
        else:
            criteria = [
                SuccessCriterion.build(
                    description="The goal reaches a coherent successful result.",
                    criterion_type=CriterionType.EVALUATIVE,
                    weight=1.0,
                    required=True,
                    evaluation_fn="result_ok",
                )
            ]
        return self.create_goal(
            description=normalized,
            intent=str(context.get("intent", "execution") or "execution"),
            constraints=constraints,
            success_criteria=criteria,
            priority=int(context.get("priority", 3) or 3),
            metadata={"inferred": True, "selected_tools": selected_tools},
        )

    @staticmethod
    def _allowed_subsystems_from_tools(selected_tools: list[str]) -> list[str]:
        subsystems: set[str] = set()
        for tool in selected_tools:
            if tool in {"filesystem_read", "read_file", "filesystem_write", "filesystem_patch_set", "grep_search", "glob_search"}:
                subsystems.add("planning")
                subsystems.add("orchestration")
                subsystems.add("continuation")
            if tool in {"verification_runner", "test_runner"}:
                subsystems.add("continuation")
            if tool in {"filesystem_patch_set", "filesystem_write"}:
                subsystems.add("self_repair")
        return sorted(subsystems)
