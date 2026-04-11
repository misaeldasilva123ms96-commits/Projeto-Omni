from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.continuation import ContinuationDecisionType, ContinuationExecutor  # noqa: E402
from brain.runtime.memory import MemoryFacade  # noqa: E402
from brain.runtime.planning import PlanStep, PlanStepStatus, TaskClassification, TaskPlan  # noqa: E402


class SpecialistIntegrationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-specialists"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"integration-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_continuation_works_with_and_without_coordination_trace(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = ContinuationExecutor(workspace_root, memory_facade=MemoryFacade(workspace_root), simulator=None)
            plan = TaskPlan.build(
                task_id="task-1",
                goal_id=None,
                title="Run test",
                objective="Run test",
                classification=TaskClassification.MULTI_STEP,
                steps=[
                    PlanStep(
                        step_id="step-1",
                        title="Execute",
                        description="Execute",
                        step_type="execute_action",
                        dependency_step_ids=[],
                        status=PlanStepStatus.PENDING,
                    )
                ],
                session_id="sess-1",
                run_id="run-1",
            )

            _, decision_plain, _ = executor.evaluate_and_decide(plan=plan, result={"ok": False, "error_payload": {"kind": "verification_failed"}})
            _, decision_trace, _ = executor.evaluate_and_decide(
                plan=plan,
                result={"ok": False, "error_payload": {"kind": "verification_failed"}},
                coordination_trace={"trace_id": "trace-1"},
            )

            self.assertEqual(decision_plain.decision_type, ContinuationDecisionType.REBUILD_PLAN)
            self.assertEqual(decision_trace.metadata.get("coordination_trace_id"), "trace-1")

    def test_memory_close_goal_episode_accepts_coordination_trace_id(self) -> None:
        with self.temp_workspace() as workspace_root:
            memory = MemoryFacade(workspace_root)
            self.addCleanup(memory.close)
            memory.start_new_session(session_id="sess-1", goal_id="goal-1")
            episode = memory.close_goal_episode(
                outcome="achieved",
                description="Goal resolved.",
                coordination_trace_id="trace-1",
            )

            self.assertIsNotNone(episode)
            self.assertEqual(episode.metadata.get("coordination_trace_id"), "trace-1")
