from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.continuation import ContinuationDecisionType, ContinuationExecutor  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.planning.planning_executor import PlanningExecutor  # noqa: E402


class AdaptiveContinuationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-continuation"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"phase17-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def make_plan(self, workspace_root: Path, *, actions: list[dict[str, object]]):
        planning = PlanningExecutor(workspace_root)
        _, plan = planning.ensure_plan(
            session_id="sess-phase17",
            task_id="task-phase17",
            run_id="run-phase17",
            message="workflow operacional",
            actions=actions,
            plan_kind="linear",
        )
        assert plan is not None
        return planning, plan

    def test_healthy_plan_with_satisfied_dependencies_produces_continue_execution(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning, plan = self.make_plan(
                workspace_root,
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read"},
                    {"step_id": "write", "selected_tool": "filesystem_write"},
                ],
            )
            action = {"step_id": "read", "selected_tool": "filesystem_read"}
            plan = planning.record_step_started(plan, action=action)
            plan = planning.record_step_result(
                plan,
                action=action,
                result={"ok": True, "execution_receipt": {"receipt_id": "receipt-healthy"}},
            )
            executor = ContinuationExecutor(workspace_root)

            evaluation, decision, updated = executor.evaluate_and_decide(plan=plan, result={"ok": True})

            assert evaluation is not None and decision is not None and updated is not None
            self.assertEqual(decision.decision_type, ContinuationDecisionType.CONTINUE_EXECUTION)
            self.assertEqual(evaluation.plan_health.value, "healthy")

    def test_failed_step_within_retry_budget_produces_retry_step(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning, plan = self.make_plan(
                workspace_root,
                actions=[
                    {"step_id": "mutate", "selected_tool": "filesystem_write"},
                    {"step_id": "verify", "selected_tool": "verification_runner"},
                ],
            )
            action = {"step_id": "mutate", "selected_tool": "filesystem_write"}
            plan = planning.record_step_started(plan, action=action)
            plan = planning.record_step_result(
                plan,
                action=action,
                result={
                    "ok": False,
                    "error_payload": {"kind": "execution_exception", "message": "temporary failure"},
                    "execution_receipt": {"receipt_id": "receipt-retry"},
                },
            )
            executor = ContinuationExecutor(workspace_root)

            _, decision, updated = executor.evaluate_and_decide(
                plan=plan,
                result={
                    "ok": False,
                    "error_payload": {"kind": "execution_exception", "message": "temporary failure"},
                },
            )

            assert decision is not None and updated is not None
            self.assertEqual(decision.decision_type, ContinuationDecisionType.RETRY_STEP)
            current_step = executor.tracker.step_by_id(updated, updated.current_step_id)
            assert current_step is not None
            self.assertEqual(current_step.status.value, "pending")

    def test_blocked_dependency_produces_pause_plan(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning, plan = self.make_plan(
                workspace_root,
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read"},
                    {"step_id": "write", "selected_tool": "filesystem_write", "depends_on_step_ids": ["missing"]},
                ],
            )
            action = {"step_id": "read", "selected_tool": "filesystem_read"}
            plan = planning.record_step_started(plan, action=action)
            plan = planning.record_step_result(
                plan,
                action=action,
                result={
                    "ok": False,
                    "error_payload": {"kind": "dependency_missing", "message": "dependency unavailable"},
                    "execution_receipt": {"receipt_id": "receipt-pause"},
                },
            )
            executor = ContinuationExecutor(workspace_root)

            _, decision, updated = executor.evaluate_and_decide(
                plan=plan,
                result={
                    "ok": False,
                    "error_payload": {"kind": "dependency_missing", "message": "dependency unavailable"},
                },
            )

            assert decision is not None and updated is not None
            self.assertEqual(decision.decision_type, ContinuationDecisionType.PAUSE_PLAN)
            self.assertEqual(updated.status.value, "paused")

    def test_repeated_unsafe_failure_produces_escalate_failure(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning, plan = self.make_plan(
                workspace_root,
                actions=[
                    {"step_id": "mutate", "selected_tool": "filesystem_write"},
                    {"step_id": "verify", "selected_tool": "verification_runner"},
                ],
            )
            action = {"step_id": "mutate", "selected_tool": "filesystem_write"}
            plan = planning.record_step_started(plan, action=action)
            plan = planning.record_step_result(
                plan,
                action=action,
                result={
                    "ok": False,
                    "error_payload": {"kind": "execution_exception", "message": "persistent failure"},
                    "execution_receipt": {"receipt_id": "receipt-escalate"},
                    "repair_receipt": {
                        "repair_receipt_id": "repair-escalate",
                        "promotion_status": "rejected",
                        "rejection_reason": "validation_failed",
                    },
                },
            )
            current_step = planning.tracker.step_for_action(plan, "mutate")
            assert current_step is not None
            current_step.retry_count = 2
            executor = ContinuationExecutor(workspace_root)

            _, decision, updated = executor.evaluate_and_decide(
                plan=plan,
                result={
                    "ok": False,
                    "error_payload": {"kind": "execution_exception", "message": "persistent failure"},
                    "repair_receipt": {
                        "repair_receipt_id": "repair-escalate",
                        "promotion_status": "rejected",
                        "rejection_reason": "validation_failed",
                    },
                },
            )

            assert decision is not None and updated is not None
            self.assertEqual(decision.decision_type, ContinuationDecisionType.ESCALATE_FAILURE)
            self.assertEqual(updated.status.value, "blocked")

    def test_completed_plan_produces_complete_plan(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning, plan = self.make_plan(
                workspace_root,
                actions=[{"step_id": "read", "selected_tool": "filesystem_read"}, {"step_id": "write", "selected_tool": "filesystem_write"}],
            )
            for action in [{"step_id": "read", "selected_tool": "filesystem_read"}, {"step_id": "write", "selected_tool": "filesystem_write"}]:
                plan = planning.record_step_started(plan, action=action)
                plan = planning.record_step_result(
                    plan,
                    action=action,
                    result={"ok": True, "execution_receipt": {"receipt_id": f"receipt-{action['step_id']}"}},
                )
            plan = planning.finalize_plan(plan, status_hint="completed", step_results=[{"ok": True}, {"ok": True}])
            executor = ContinuationExecutor(workspace_root)

            _, decision, updated = executor.evaluate_and_decide(plan=plan, result={"ok": True})

            assert decision is not None and updated is not None
            self.assertEqual(decision.decision_type, ContinuationDecisionType.COMPLETE_PLAN)
            self.assertEqual(updated.status.value, "completed")

    def test_bounded_replan_modifies_only_remaining_plan_segment_safely(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning, plan = self.make_plan(
                workspace_root,
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read"},
                    {"step_id": "patch", "selected_tool": "filesystem_patch_set"},
                ],
            )
            action = {"step_id": "read", "selected_tool": "filesystem_read"}
            plan = planning.record_step_started(plan, action=action)
            plan = planning.record_step_result(
                plan,
                action=action,
                result={
                    "ok": False,
                    "error_payload": {"kind": "verification_failed", "message": "shape mismatch"},
                    "execution_receipt": {"receipt_id": "receipt-replan"},
                },
            )
            executor = ContinuationExecutor(workspace_root)

            _, decision, updated = executor.evaluate_and_decide(
                plan=plan,
                result={
                    "ok": False,
                    "error_payload": {"kind": "verification_failed", "message": "shape mismatch"},
                },
            )

            assert decision is not None and updated is not None
            self.assertEqual(decision.decision_type, ContinuationDecisionType.REBUILD_PLAN)
            self.assertEqual(updated.metadata.get("continuation_replan_count"), 1)
            self.assertTrue(any(step.step_id.startswith("replan:") for step in updated.steps))

    def test_pause_persists_resumability_metadata(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning, plan = self.make_plan(
                workspace_root,
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read"},
                    {"step_id": "write", "selected_tool": "filesystem_write"},
                ],
            )
            action = {"step_id": "read", "selected_tool": "filesystem_read"}
            plan = planning.record_step_started(plan, action=action)
            plan = planning.record_step_result(
                plan,
                action=action,
                result={"ok": False, "error_payload": {"kind": "dependency_missing", "message": "missing dependency"}},
            )
            executor = ContinuationExecutor(workspace_root)

            _, decision, updated = executor.evaluate_and_decide(
                plan=plan,
                result={"ok": False, "error_payload": {"kind": "dependency_missing", "message": "missing dependency"}},
            )

            assert decision is not None and updated is not None
            checkpoint = executor.store.load_latest_checkpoint(updated.plan_id)
            assert checkpoint is not None
            self.assertEqual(decision.decision_type, ContinuationDecisionType.PAUSE_PLAN)
            self.assertEqual(checkpoint.resumable_state_payload.get("status"), "paused")

    def test_escalation_persists_structured_artifact(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning, plan = self.make_plan(
                workspace_root,
                actions=[{"step_id": "write", "selected_tool": "filesystem_write"}],
            )
            action = {"step_id": "write", "selected_tool": "filesystem_write"}
            plan = planning.record_step_started(plan, action=action)
            plan = planning.record_step_result(
                plan,
                action=action,
                result={
                    "ok": False,
                    "error_payload": {"kind": "critical_risk_blocked", "message": "unsafe mutation"},
                },
            )
            executor = ContinuationExecutor(workspace_root)

            _, decision, updated = executor.evaluate_and_decide(
                plan=plan,
                result={"ok": False, "error_payload": {"kind": "critical_risk_blocked", "message": "unsafe mutation"}},
            )

            assert decision is not None and updated is not None
            path = workspace_root / ".logs" / "fusion-runtime" / "continuation" / "escalations" / f"{updated.plan_id}.jsonl"
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(payload["decision"]["decision_type"], "escalate_failure")

    def test_orchestrator_integration_does_not_break_current_runtime_flow(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        actions = [
            {"step_id": "read-a", "selected_tool": "filesystem_read", "selected_agent": "engineering-specialist", "tool_arguments": {"path": "README.md"}},
            {"step_id": "read-b", "selected_tool": "filesystem_read", "selected_agent": "engineering-specialist", "tool_arguments": {"path": "package.json"}},
        ]
        with patch(
            "brain.runtime.orchestrator.execute_engineering_action",
            side_effect=[
                {"ok": True, "result_payload": {"file": {"content": "a"}}},
                {"ok": True, "result_payload": {"file": {"content": "b"}}},
            ],
        ):
            results = orchestrator._execute_runtime_actions(
                session_id=f"phase17-session-{uuid4().hex[:8]}",
                message="inspecionar dois arquivos",
                actions=actions,
                task_id=f"phase17-task-{uuid4().hex[:8]}",
                run_id=f"phase17-run-{uuid4().hex[:8]}",
                provider="test-provider",
                intent="execution",
                delegation={},
                plan_kind="linear",
            )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.get("ok") for item in results))
        self.assertTrue(all("continuation_decision" in item for item in results))

    def test_continuation_layer_coexists_with_execution_repair_and_planning_receipts(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning, plan = self.make_plan(
                workspace_root,
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read"},
                    {"step_id": "patch", "selected_tool": "filesystem_patch_set"},
                ],
            )
            action = {"step_id": "read", "selected_tool": "filesystem_read"}
            plan = planning.record_step_started(plan, action=action)
            plan = planning.record_step_result(
                plan,
                action=action,
                result={
                    "ok": False,
                    "error_payload": {"kind": "execution_exception", "message": "temporary failure"},
                    "execution_receipt": {"receipt_id": "receipt-coexist"},
                    "repair_receipt": {
                        "repair_receipt_id": "repair-coexist",
                        "promotion_status": "rejected",
                        "rejection_reason": "validation_failed",
                    },
                },
            )
            executor = ContinuationExecutor(workspace_root)

            evaluation, decision, updated = executor.evaluate_and_decide(
                plan=plan,
                result={
                    "ok": False,
                    "error_payload": {"kind": "execution_exception", "message": "temporary failure"},
                    "repair_receipt": {
                        "repair_receipt_id": "repair-coexist",
                        "promotion_status": "rejected",
                        "rejection_reason": "validation_failed",
                    },
                },
            )

            assert evaluation is not None and decision is not None and updated is not None
            self.assertIn("receipt-coexist", decision.linked_execution_receipt_ids)
            self.assertIn("repair-coexist", decision.linked_repair_receipt_ids)


if __name__ == "__main__":
    unittest.main()
