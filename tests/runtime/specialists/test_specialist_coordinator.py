from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.goals import FailureTolerance, Goal, GoalStore, ToleranceType  # noqa: E402
from brain.runtime.specialists import SpecialistCoordinator  # noqa: E402


class SpecialistCoordinatorTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-specialists"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"coordinator-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_coordinator_stops_on_governance_block(self) -> None:
        with self.temp_workspace() as workspace_root:
            goal = Goal.build(
                description="Stay safe.",
                intent="safety",
                subgoals=[],
                constraints=[],
                success_criteria=[],
                failure_tolerances=[],
                stop_conditions=[],
                priority=1,
            )
            GoalStore(workspace_root).save_goal(goal)
            coordinator = SpecialistCoordinator(workspace_root)

            trace = coordinator.coordinate(
                session_id="sess-1",
                goal_id=goal.goal_id,
                action={"step_id": "step-1", "hard_constraint_violation": True},
                plan=None,
                execute_callback=lambda: {"ok": True},
            )

            self.assertEqual(trace.final_outcome, "blocked_by_governance")

    def test_coordinator_persists_trace_and_respects_repair_limits(self) -> None:
        with self.temp_workspace() as workspace_root:
            goal = Goal.build(
                description="Recover boundedly.",
                intent="recovery",
                subgoals=[],
                constraints=[],
                success_criteria=[],
                failure_tolerances=[
                    FailureTolerance.build(
                        description="repair budget",
                        tolerance_type=ToleranceType.MAX_REPAIRS,
                        threshold=1,
                    ),
                    FailureTolerance.build(
                        description="must preserve progress",
                        tolerance_type=ToleranceType.PARTIAL_SUCCESS,
                        threshold=0.8,
                    ),
                ],
                stop_conditions=[],
                priority=1,
            )
            GoalStore(workspace_root).save_goal(goal)
            coordinator = SpecialistCoordinator(workspace_root)

            trace = coordinator.coordinate(
                session_id="sess-2",
                goal_id=goal.goal_id,
                action={"step_id": "step-1", "repair_count": 1},
                plan=None,
                execute_callback=lambda: {"ok": False, "progress_score": 0.2},
            )

            self.assertTrue((workspace_root / ".logs" / "fusion-runtime" / "specialists" / "coordination_log.jsonl").exists())
            self.assertIn(trace.final_outcome, {"achieved", "failed", "completed_step"})
            self.assertTrue(any(item.get("specialist_type") == "repair" for item in trace.decisions))
