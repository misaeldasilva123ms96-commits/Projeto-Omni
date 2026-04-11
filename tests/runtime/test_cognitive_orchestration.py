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

from brain.runtime.orchestration import OrchestrationExecutor  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.planning.planning_executor import PlanningExecutor  # noqa: E402


class CognitiveOrchestrationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-orchestration"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"phase19-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def make_plan(self, workspace_root: Path, *, actions: list[dict[str, object]]):
        planning = PlanningExecutor(workspace_root)
        _, plan = planning.ensure_plan(
            session_id="sess-phase19",
            task_id="task-phase19",
            run_id="run-phase19",
            message="workflow cognitivo",
            actions=actions,
            plan_kind="linear",
        )
        assert plan is not None
        return planning, plan

    def test_context_construction_is_deterministic(self) -> None:
        with self.temp_workspace() as workspace_root:
            _, plan = self.make_plan(
                workspace_root,
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read"},
                    {"step_id": "write", "selected_tool": "filesystem_write"},
                ],
            )
            executor = OrchestrationExecutor(workspace_root)

            payload = executor.orchestrate(
                session_id="sess-phase19",
                task_id="task-phase19",
                run_id="run-phase19",
                action={"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"},
                plan=plan,
                step_results=[],
                learning_signals=[],
                engineering_tool=True,
            )

            context = payload["context"]
            self.assertEqual(context["plan_id"], plan.plan_id)
            self.assertEqual(context["action"]["selected_tool"], "filesystem_read")

    def test_route_selection_prefers_tool_delegation_for_engineering_tools(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = OrchestrationExecutor(workspace_root)

            payload = executor.orchestrate(
                session_id="sess-phase19",
                task_id="task-phase19",
                run_id="run-phase19",
                action={"step_id": "patch", "selected_tool": "filesystem_patch_set", "action_type": "mutate"},
                learning_signals=[],
                engineering_tool=True,
            )

            self.assertEqual(payload["decision"]["route"], "tool_delegation")
            self.assertEqual(payload["decision"]["selected_capability_id"], "engineering_tool_execution")

    def test_conflict_resolution_keeps_continuation_authoritative_over_learning(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = OrchestrationExecutor(workspace_root)

            payload = executor.orchestrate(
                session_id="sess-phase19",
                task_id="task-phase19",
                run_id="run-phase19",
                action={"step_id": "retry", "selected_tool": "filesystem_write", "action_type": "mutate"},
                continuation_decision={"decision_type": "retry_step"},
                learning_signals=[
                    {"signal_type": "discouraged_retry_pattern", "metadata": {"failure_class": "execution_exception"}},
                ],
                engineering_tool=True,
            )

            self.assertEqual(payload["decision"]["route"], "retry_execution")
            self.assertIn("learning_discourages_retry", payload["resolution"]["conflicts"])

    def test_result_synthesis_preserves_artifact_references(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = OrchestrationExecutor(workspace_root)

            payload = executor.orchestrate(
                session_id="sess-phase19",
                task_id="task-phase19",
                run_id="run-phase19",
                action={"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"},
                step_results=[
                    {
                        "execution_receipt": {"receipt_id": "receipt-a"},
                        "repair_receipt": {"repair_receipt_id": "repair-a"},
                    }
                ],
                primary_result={"ok": True, "result_payload": {"file": {"content": "ok"}}},
                engineering_tool=True,
            )

            result = payload["result"]
            self.assertIn("receipt-a", result["artifact_references"]["execution_receipt_ids"])
            self.assertIn("repair-a", result["artifact_references"]["repair_receipt_ids"])

    def test_integration_with_planning_state_is_preserved(self) -> None:
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
            executor = OrchestrationExecutor(workspace_root)

            payload = executor.orchestrate(
                session_id="sess-phase19",
                task_id="task-phase19",
                run_id="run-phase19",
                action={"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"},
                plan=plan,
                checkpoint=planning.store.load_latest_checkpoint(plan.plan_id),
                summary=planning.store.load_summary(plan.plan_id),
                engineering_tool=True,
            )

            self.assertEqual(payload["context"]["current_step_id"], plan.current_step_id)

    def test_integration_with_continuation_rebuild_routes_to_planning(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = OrchestrationExecutor(workspace_root)

            payload = executor.orchestrate(
                session_id="sess-phase19",
                task_id="task-phase19",
                run_id="run-phase19",
                action={"step_id": "repair", "selected_tool": "filesystem_patch_set", "action_type": "mutate"},
                continuation_decision={"decision_type": "rebuild_plan"},
                engineering_tool=True,
            )

            self.assertEqual(payload["decision"]["route"], "plan_rebuild")
            self.assertEqual(payload["decision"]["selected_capability_id"], "planning_execution")

    def test_learning_signals_integration_is_advisory_only(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = OrchestrationExecutor(workspace_root)

            payload = executor.orchestrate(
                session_id="sess-phase19",
                task_id="task-phase19",
                run_id="run-phase19",
                action={"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"},
                learning_signals=[
                    {"signal_type": "step_template_success_hint", "metadata": {"require_validation_after_tool": True}},
                ],
                engineering_tool=True,
            )

            self.assertEqual(payload["decision"]["route"], "analysis_step")
            self.assertTrue(payload["policy"]["allow_learning_hints"])

    def test_orchestration_artifacts_are_persisted(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = OrchestrationExecutor(workspace_root)
            payload = executor.orchestrate(
                session_id="sess-phase19",
                task_id="task-phase19",
                run_id="run-phase19",
                action={"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"},
                engineering_tool=True,
            )

            plan_key = "runtime"
            context_path = workspace_root / ".logs" / "fusion-runtime" / "orchestration" / "context" / f"{plan_key}.jsonl"
            decision_path = workspace_root / ".logs" / "fusion-runtime" / "orchestration" / "decisions" / f"{plan_key}.jsonl"
            self.assertTrue(context_path.exists())
            self.assertTrue(decision_path.exists())
            decision_payload = json.loads(decision_path.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(decision_payload["decision_id"], payload["decision"]["decision_id"])

    def test_orchestrator_integration_keeps_runtime_stable(self) -> None:
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
                session_id=f"phase19-session-{uuid4().hex[:8]}",
                message="inspecionar dois arquivos",
                actions=actions,
                task_id=f"phase19-task-{uuid4().hex[:8]}",
                run_id=f"phase19-run-{uuid4().hex[:8]}",
                provider="test-provider",
                intent="execution",
                delegation={},
                plan_kind="linear",
            )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.get("ok") for item in results))
        self.assertTrue(all("orchestration" in item for item in results))
        self.assertTrue(all("continuation_decision" in item for item in results))


if __name__ == "__main__":
    unittest.main()
