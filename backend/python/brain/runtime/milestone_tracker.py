from __future__ import annotations

from typing import Any

from brain.runtime.milestone_manager import MilestoneManager


class MilestoneTracker:
    def __init__(self) -> None:
        self._current_plan: dict[str, Any] = {}
        self._current_state: dict[str, Any] = {}

    def load_plan(self, milestone_plan: dict[str, Any] | None) -> dict[str, Any]:
        self._current_plan = dict(milestone_plan) if isinstance(milestone_plan, dict) else {}
        self._current_state = (
            MilestoneManager(self._current_plan).initialize_state()
            if isinstance(self._current_plan, dict) and self._current_plan
            else {}
        )
        return self._current_state

    def update_from_step_results(
        self,
        step_results: list[dict[str, Any]],
        milestone_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = milestone_state or self._current_state
        milestone_plan = self._current_plan

        manager = MilestoneManager(milestone_plan)
        updated = manager.update_from_step_results(state, step_results) if milestone_plan else state
        self._current_state = dict(updated) if isinstance(updated, dict) else {}
        return self._current_state

    def get_current_state(self) -> dict[str, Any]:
        return dict(self._current_state)

    def get_current_milestones_from_strategy(
        self, strategy_state: dict[str, Any]
    ) -> list[dict[str, Any]]:
        if not isinstance(strategy_state, dict):
            return []
        milestones = strategy_state.get("milestones", [])
        if isinstance(milestones, list):
            return [m for m in milestones if isinstance(m, dict)]
        return []

    def extract_milestone_id(self, action: dict[str, Any]) -> str:
        return str(action.get("milestone_id", "")).strip()

    def extract_milestone_plan(self, execution_request: dict[str, Any]) -> dict[str, Any]:
        return dict(execution_request.get("milestone_plan", {})) if isinstance(execution_request.get("milestone_plan"), dict) else {}
