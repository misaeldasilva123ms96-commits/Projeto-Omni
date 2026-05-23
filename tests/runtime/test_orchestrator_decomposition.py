"""Phase 30.10 — orchestrator decomposition regression and wiring checks."""

from __future__ import annotations

import os
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import RunStatus  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.orchestrator_services import (  # noqa: E402
    CompletionService,
    GovernanceIntegrationService,
    RunLifecycleService,
)


class OrchestratorDecompositionTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-orchestrator-decomposition"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"decomp-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_orchestrator_wires_phase_30_10_services(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orch = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))
            self.assertIsNotNone(orch._session_service)
            self.assertIsNotNone(orch._run_lifecycle)
            self.assertIsNotNone(orch._governance_integration)
            self.assertIsNotNone(orch._completion_service)
            self.assertIsNotNone(orch._execution_dispatch)

    def test_write_checkpoint_persists_via_session_service(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orch = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))
            orch._write_checkpoint(
                run_id="run-decomp",
                task_id="task-decomp",
                session_id="sess-decomp",
                message="m",
                actions=[{"step_id": "a"}],
                next_step_index=0,
                completed_steps=[],
                plan_graph=None,
                plan_hierarchy=None,
                plan_signature="sig-decomp",
                status="running",
                branch_state=None,
                simulation_summary=None,
                cooperative_plan=None,
                strategy_suggestions=[],
                policy_summary=[],
                execution_tree=None,
                negotiation_summary=None,
                strategy_optimization=None,
                supervision=None,
                repository_analysis=None,
                engineering_data=None,
            )
            payload = orch.checkpoint_store.load("run-decomp")
            self.assertEqual(payload.get("plan_signature"), "sig-decomp")
            self.assertEqual(payload.get("session_id"), "sess-decomp")

    def test_execute_single_action_delegates_to_execution_dispatch(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["BASE_DIR"] = str(workspace_root)
            os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
            orch = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))
            sentinel = {"ok": True, "delegated": True}
            mock_dispatch = MagicMock()
            mock_dispatch.execute_single_action_with_specialists.return_value = sentinel
            orch._execution_dispatch = mock_dispatch
            out = orch._execute_single_action(
                action={"step_id": "s1", "selected_tool": "read_file"},
                step_results=[],
                semantic_retrieval=None,
                session_id="s",
                task_id="t",
                run_id="r",
                learning_guidance=None,
                operational_plan=None,
            )
            self.assertIs(out, sentinel)
            mock_dispatch.execute_single_action_with_specialists.assert_called_once()

    def test_completion_service_success_calls_controller_handle_completion(self) -> None:
        ctrl = MagicMock()
        run_lc = MagicMock()
        svc = CompletionService(get_controller=lambda: ctrl, run_lifecycle=run_lc, progress_fn=BrainOrchestrator._progress_from_step_results)
        svc.apply_fusion_terminal_status(run_id="run-ok", step_results=[{"ok": True}])
        ctrl.handle_completion.assert_called_once()
        run_lc.update_run_status.assert_not_called()

    def test_completion_service_failure_calls_controller_handle_failure(self) -> None:
        ctrl = MagicMock()
        run_lc = MagicMock()
        svc = CompletionService(get_controller=lambda: ctrl, run_lifecycle=run_lc, progress_fn=BrainOrchestrator._progress_from_step_results)
        svc.apply_fusion_terminal_status(run_id="run-bad", step_results=[{"ok": False}])
        ctrl.handle_failure.assert_called_once()
        run_lc.update_run_status.assert_not_called()

    def test_completion_service_without_controller_updates_registry_via_run_lifecycle(self) -> None:
        run_lc = MagicMock()
        svc = CompletionService(get_controller=lambda: None, run_lifecycle=run_lc, progress_fn=BrainOrchestrator._progress_from_step_results)
        svc.apply_fusion_terminal_status(run_id="run-legacy", step_results=[{"ok": True}])
        run_lc.update_run_status.assert_called_once()
        kwargs = run_lc.update_run_status.call_args.kwargs
        self.assertEqual(kwargs["run_id"], "run-legacy")
        self.assertEqual(kwargs["status"], RunStatus.COMPLETED)

    def test_governance_integration_hold_delegates_to_controller(self) -> None:
        ctrl = MagicMock()
        run_lc = RunLifecycleService(run_registry=None, get_controller=lambda: ctrl)
        gov = GovernanceIntegrationService(run_registry=None, get_controller=lambda: ctrl, run_lifecycle=run_lc)
        gov.apply_governance_hold_after_specialist(run_id="run-hold", progress_score=0.33)
        ctrl.handle_governance_hold.assert_called_once_with(run_id="run-hold", progress=0.33)


if __name__ == "__main__":
    unittest.main()
