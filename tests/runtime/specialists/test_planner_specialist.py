from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.goals import Goal, GoalStore  # noqa: E402
from brain.runtime.specialists import PlannerSpecialist  # noqa: E402


class PlannerSpecialistTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-specialists"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"planner-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_planner_produces_different_plan_and_replan_output(self) -> None:
        with self.temp_workspace() as workspace_root:
            goal = Goal.build(
                description="Ship a safe runtime change.",
                intent="delivery",
                subgoals=[],
                constraints=[],
                success_criteria=[],
                failure_tolerances=[],
                stop_conditions=[],
                priority=2,
                metadata={"goal_type": "delivery"},
            )
            GoalStore(workspace_root).save_goal(goal)
            specialist = PlannerSpecialist(root=workspace_root)

            plan_decision = specialist.plan(goal_id=goal.goal_id, action={"step_id": "step-1"}, plan=None, simulation_result=None, replan=False)
            replan_decision = specialist.plan(goal_id=goal.goal_id, action={"step_id": "step-1"}, plan=None, simulation_result=None, replan=True)

            self.assertFalse(plan_decision.replan)
            self.assertTrue(replan_decision.replan)
            self.assertNotEqual(plan_decision.reasoning, replan_decision.reasoning)
