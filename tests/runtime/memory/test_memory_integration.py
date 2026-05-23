from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.continuation import ContinuationExecutor  # noqa: E402
from brain.runtime.goals import ConstraintRegistry, GoalEvaluator, GoalFactory  # noqa: E402
from brain.runtime.learning.learning_executor import LearningExecutor  # noqa: E402
from brain.runtime.memory import MemoryFacade  # noqa: E402
from brain.runtime.planning.planning_executor import PlanningExecutor  # noqa: E402


class MemoryIntegrationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-memory"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"integration-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_continuation_records_events_into_memory(self) -> None:
        with self.temp_workspace() as workspace_root:
            memory = MemoryFacade(workspace_root)
            self.addCleanup(memory.close)
            planning = PlanningExecutor(workspace_root)
            _, plan = planning.ensure_plan(
                session_id="sess-cont",
                task_id="task-cont",
                run_id="run-cont",
                message="Inspecionar e validar o arquivo.",
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read"},
                    {"step_id": "validate", "selected_tool": "verification_runner"},
                ],
                plan_kind="linear",
            )
            assert plan is not None
            goal_context = planning.goal_context_for_plan(plan)
            assert goal_context is not None
            memory.set_active_goal(
                session_id="sess-cont",
                goal_id=plan.goal_id or "",
                active_plan_id=plan.plan_id,
                goal_context=goal_context,
            )
            executor = ContinuationExecutor(workspace_root, memory_facade=memory)

            executor.evaluate_and_decide(plan=plan, result={"ok": False, "error_payload": {"kind": "transient_failure"}})

            snapshot = memory.working.snapshot()
            self.assertTrue(any(event.event_type == "continuation_decision" for event in snapshot.recent_events))

    def test_learning_records_evidence_linked_memory_events(self) -> None:
        with self.temp_workspace() as workspace_root:
            memory = MemoryFacade(workspace_root)
            self.addCleanup(memory.close)
            planning = PlanningExecutor(workspace_root)
            _, plan = planning.ensure_plan(
                session_id="sess-learning",
                task_id="task-learning",
                run_id="run-learning",
                message="Ler um arquivo e registrar contexto.",
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"},
                    {"step_id": "validate", "selected_tool": "verification_runner", "action_type": "validate"},
                ],
                plan_kind="linear",
            )
            assert plan is not None
            goal_context = planning.goal_context_for_plan(plan)
            assert goal_context is not None
            memory.set_active_goal(
                session_id="sess-learning",
                goal_id=plan.goal_id or "",
                active_plan_id=plan.plan_id,
                goal_context=goal_context,
            )
            executor = LearningExecutor(workspace_root, memory_facade=memory)
            executor.ingest_runtime_artifacts(
                action={"step_id": "read", "selected_tool": "filesystem_read", "goal_id": plan.goal_id},
                result={
                    "execution_receipt": {
                        "receipt_id": "receipt-learning",
                        "timestamp": "2026-04-11T12:00:00+00:00",
                        "execution_status": "succeeded",
                        "verification_status": "passed",
                    }
                },
                plan=plan,
            )

            snapshot = memory.working.snapshot()
            self.assertTrue(any(event.event_type == "learning_evidence" for event in snapshot.recent_events))

    def test_goal_evaluator_historical_context_remains_none_safe(self) -> None:
        goal = GoalFactory().create_goal(description="Concluir validacao com sucesso.", intent="execution")
        result = GoalEvaluator(ConstraintRegistry()).evaluate(goal=goal, runtime_state={"result_ok": False}, memory_facade=None)

        self.assertIsNone(result.historical_context)
