from __future__ import annotations

from typing import Any


class MilestoneManager:
    def __init__(self, milestone_plan: dict[str, Any] | None = None) -> None:
        self.milestone_plan = milestone_plan or {}

    def initialize_state(self) -> dict[str, Any]:
        milestones = []
        for milestone in self.milestone_plan.get("milestone_tree", {}).get("milestones", []):
            if not isinstance(milestone, dict):
                continue
            milestones.append(
                {
                    "milestone_id": milestone.get("milestone_id"),
                    "title": milestone.get("title"),
                    "state": milestone.get("state", "pending"),
                    "step_ids": milestone.get("step_ids", []),
                    "blockers": milestone.get("blockers", []),
                    "progress": milestone.get("progress", 0),
                }
            )
        return {
            "root_milestone_id": self.milestone_plan.get("milestone_tree", {}).get("root_milestone_id"),
            "milestones": milestones,
            "completed_milestones": 0,
            "blocked_milestones": 0,
        }

    def update_from_step_results(self, state: dict[str, Any], step_results: list[dict[str, Any]]) -> dict[str, Any]:
        state = {
            **(state or {}),
            "milestones": [dict(item) for item in (state or {}).get("milestones", []) if isinstance(item, dict)],
        }
        if not state["milestones"]:
            return state
        for milestone in state["milestones"]:
            related = [
                item for item in step_results
                if item.get("action", {}).get("milestone_id") == milestone.get("milestone_id")
                or item.get("milestone_id") == milestone.get("milestone_id")
            ]
            if not related:
                continue
            total = len(milestone.get("step_ids", [])) or len(related)
            completed = len([item for item in related if item.get("ok")])
            failed = len([item for item in related if not item.get("ok")])
            milestone["progress"] = min(100, int((completed / max(1, total)) * 100))
            if failed > 0:
                milestone["state"] = "blocked"
                milestone["blockers"] = [item.get("error_payload", {}).get("kind", "step_failed") for item in related if not item.get("ok")]
            elif completed >= total:
                milestone["state"] = "completed"
            elif completed > 0:
                milestone["state"] = "in_progress"
        state["completed_milestones"] = len([item for item in state["milestones"] if item.get("state") == "completed"])
        state["blocked_milestones"] = len([item for item in state["milestones"] if item.get("state") == "blocked"])
        return state
