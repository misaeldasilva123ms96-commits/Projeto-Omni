from __future__ import annotations

import json
import threading
from pathlib import Path

from .models import Goal, GoalStatus


class GoalStore:
    def __init__(self, root: Path) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "goals"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "goal_store.json"
        self._lock = threading.RLock()
        self._goals: dict[str, Goal] = {}
        if self.path.exists():
            self.reload_from_disk()

    def save_goal(self, goal: Goal) -> Goal:
        with self._lock:
            self._goals[goal.goal_id] = goal
            self.flush()
            return goal

    def get_by_id(self, goal_id: str) -> Goal | None:
        with self._lock:
            return self._goals.get(goal_id)

    def get_active_goals(self) -> list[Goal]:
        with self._lock:
            return [goal for goal in self._goals.values() if goal.status in {GoalStatus.ACTIVE, GoalStatus.PAUSED}]

    def update_status(self, goal_id: str, status: GoalStatus) -> Goal | None:
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = status
            if status in {GoalStatus.ACHIEVED, GoalStatus.FAILED, GoalStatus.ABANDONED}:
                goal.resolved_at = goal.resolved_at or goal.created_at
            self.flush()
            return goal

    def reload_from_disk(self) -> None:
        with self._lock:
            if not self.path.exists():
                self._goals = {}
                return
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as error:
                raise ValueError(f"Invalid goal store data: {error}") from error
            if not isinstance(payload, dict):
                raise ValueError("Invalid goal store data: root payload must be an object.")
            raw_goals = payload.get("goals", {})
            if not isinstance(raw_goals, dict):
                raise ValueError("Invalid goal store data: goals must be a mapping.")
            self._goals = {
                str(goal_id): Goal.from_dict(item)
                for goal_id, item in raw_goals.items()
                if isinstance(item, dict)
            }

    def flush(self) -> None:
        with self._lock:
            payload = {
                "goals": {goal_id: goal.as_dict() for goal_id, goal in self._goals.items()},
            }
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
