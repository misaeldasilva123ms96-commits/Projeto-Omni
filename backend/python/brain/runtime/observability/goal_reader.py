from __future__ import annotations

from pathlib import Path

from brain.runtime.goals.models import Goal

from ._reader_utils import read_json_resilient
from .models import GoalCriterionSnapshot, GoalSnapshot, SubGoalSnapshot


class GoalReader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / ".logs" / "fusion-runtime" / "goals" / "goal_store.json"

    def read_active_goal(self, *, progress_score: float | None = None) -> GoalSnapshot | None:
        goals = self._load_goals()
        active = [goal for goal in goals if goal.status.value in {"active", "paused"}]
        if not active:
            return None
        active.sort(key=lambda goal: (-goal.priority, goal.created_at))
        return self._to_snapshot(active[0], progress_score=progress_score)

    def read_goal_history(self, *, limit: int = 10) -> list[GoalSnapshot]:
        goals = self._load_goals()
        goals.sort(key=lambda goal: goal.created_at, reverse=True)
        return [self._to_snapshot(goal, progress_score=None) for goal in goals[: max(1, limit)]]

    def _load_goals(self) -> list[Goal]:
        payload = read_json_resilient(self.path)
        if not isinstance(payload, dict):
            return []
        raw_goals = payload.get("goals", {})
        if not isinstance(raw_goals, dict):
            return []
        goals: list[Goal] = []
        for raw_goal in raw_goals.values():
            if not isinstance(raw_goal, dict):
                continue
            try:
                goals.append(Goal.from_dict(raw_goal))
            except Exception:
                continue
        return goals

    @staticmethod
    def _to_snapshot(goal: Goal, *, progress_score: float | None) -> GoalSnapshot:
        return GoalSnapshot(
            goal_id=goal.goal_id,
            description=goal.description,
            intent=goal.intent,
            status=goal.status.value,
            priority=goal.priority,
            progress_score=progress_score,
            active_constraints=[constraint.description for constraint in goal.constraints if constraint.active],
            success_criteria=[
                GoalCriterionSnapshot(
                    description=criterion.description,
                    criterion_type=criterion.criterion_type.value,
                    required=criterion.required,
                    weight=criterion.weight,
                )
                for criterion in goal.success_criteria
            ],
            subgoals=[
                SubGoalSnapshot(
                    subgoal_id=subgoal.subgoal_id,
                    description=subgoal.description,
                    status=subgoal.status.value,
                    order=subgoal.order,
                    depends_on_subgoal_ids=list(subgoal.depends_on_subgoal_ids),
                )
                for subgoal in sorted(goal.subgoals, key=lambda item: item.order)
            ],
            created_at=goal.created_at,
            resolved_at=goal.resolved_at,
            metadata=dict(goal.metadata),
        )
