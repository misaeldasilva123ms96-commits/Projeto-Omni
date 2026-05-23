from __future__ import annotations

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

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.planning import (  # noqa: E402
    PlanCheckpoint,
    ResumeDecisionType,
    TaskClassification,
    TaskPlan,
)
from brain.runtime.planning.planning_executor import PlanningExecutor  # noqa: E402


class OperationalPlanningTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-planning"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"phase16-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_single_step_task_is_classified_without_planning(self) -> None:
        executor = PlanningExecutor(PROJECT_ROOT)
        decision = executor.classify_task(
            message="ler README",
            actions=[{"step_id": "read-1", "selected_tool": "filesystem_read"}],
            plan_kind="linear",
        )

        self.assertEqual(decision.classification, TaskClassification.SINGLE_STEP)
        self.assertFalse(decision.should_plan)

    def test_multi_step_task_creates_structured_plan(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = PlanningExecutor(workspace_root)
            decision, plan = executor.ensure_plan(
                session_id="sess-phase16",
                task_id="task-phase16",
                run_id="run-phase16",
                message="inspecionar, alterar e validar codigo",
                actions=[
                    {"step_id": "inspect", "selected_tool": "filesystem_read"},
                    {"step_id": "patch", "selected_tool": "filesystem_patch_set"},
                ],
                plan_kind="linear",
            )

            self.assertTrue(decision.should_plan)
            self.assertIsNotNone(plan)
            assert plan is not None
            self.assertEqual(plan.classification, TaskClassification.MULTI_STEP)
            self.assertGreaterEqual(plan.total_step_count, 4)
            self.assertEqual(plan.steps[0].step_id, "inspect_context")

    def test_step_progress_transitions_are_persisted_correctly(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = PlanningExecutor(workspace_root)
            _, plan = executor.ensure_plan(
                session_id="sess-progress",
                task_id="task-progress",
                run_id="run-progress",
                message="ajustar e testar",
                actions=[
                    {"step_id": "patch", "selected_tool": "filesystem_patch_set"},
                    {"step_id": "verify", "selected_tool": "verification_runner"},
                ],
                plan_kind="linear",
            )
            assert plan is not None
            action = {"step_id": "patch", "selected_tool": "filesystem_patch_set"}
            executor.record_step_started(plan, action=action)
            executor.record_step_result(
                plan,
                action=action,
                result={
                    "ok": True,
                    "execution_receipt": {"receipt_id": "receipt-progress"},
                },
            )

            persisted = executor.store.load_plan(plan.plan_id)
            assert persisted is not None
            step = executor.tracker.step_for_action(persisted, "patch")
            assert step is not None
            self.assertEqual(step.status.value, "completed")
            self.assertIn("receipt-progress", persisted.linked_execution_receipt_ids)

    def test_checkpoint_creation_works(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = PlanningExecutor(workspace_root)
            _, plan = executor.ensure_plan(
                session_id="sess-checkpoint",
                task_id="task-checkpoint",
                run_id="run-checkpoint",
                message="workflow com checkpoint",
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read"},
                    {"step_id": "write", "selected_tool": "filesystem_write"},
                ],
                plan_kind="linear",
            )
            assert plan is not None

            checkpoints = executor.store.load_checkpoints(plan.plan_id)
            self.assertGreaterEqual(len(checkpoints), 1)
            self.assertEqual(checkpoints[0].snapshot_summary, "Operational plan initialized.")

    def test_resume_engine_resumes_from_latest_valid_checkpoint(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = PlanningExecutor(workspace_root)
            _, plan = executor.ensure_plan(
                session_id="sess-resume",
                task_id="task-resume",
                run_id="run-resume",
                message="continuar workflow",
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read"},
                    {"step_id": "write", "selected_tool": "filesystem_write"},
                ],
                plan_kind="linear",
            )
            assert plan is not None
            executor.record_step_started(plan, action={"step_id": "read", "selected_tool": "filesystem_read"})
            executor.record_step_result(
                plan,
                action={"step_id": "read", "selected_tool": "filesystem_read"},
                result={"ok": True, "execution_receipt": {"receipt_id": "receipt-resume"}},
            )

            decision = executor.resume_decision(plan)

            assert decision is not None
            self.assertEqual(decision.decision, ResumeDecisionType.RESUME_FROM_CHECKPOINT)
            self.assertTrue(decision.step_id)

    def test_resume_engine_safely_refuses_inconsistent_state(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = PlanningExecutor(workspace_root)
            _, plan = executor.ensure_plan(
                session_id="sess-bad-resume",
                task_id="task-bad-resume",
                run_id="run-bad-resume",
                message="workflow inconsistente",
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read"},
                    {"step_id": "write", "selected_tool": "filesystem_write"},
                ],
                plan_kind="linear",
            )
            assert plan is not None
            bad_checkpoint = PlanCheckpoint.build(
                plan_id=plan.plan_id,
                step_id="missing-step",
                snapshot_summary="bad checkpoint",
                resumable_state_payload={"current_step_id": "missing-step"},
                last_outcome_summary="checkpoint inconsistente",
            )
            executor.store.append_checkpoint(bad_checkpoint)

            decision = executor.resume_decision(plan)

            assert decision is not None
            self.assertEqual(decision.decision, ResumeDecisionType.MANUAL_INTERVENTION_REQUIRED)
            self.assertEqual(decision.reason_code, "checkpoint_step_missing")

    def test_operational_summary_reflects_current_plan_state(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = PlanningExecutor(workspace_root)
            _, plan = executor.ensure_plan(
                session_id="sess-summary",
                task_id="task-summary",
                run_id="run-summary",
                message="resumir plano operacional",
                actions=[
                    {"step_id": "inspect", "selected_tool": "filesystem_read"},
                    {"step_id": "patch", "selected_tool": "filesystem_patch_set"},
                ],
                plan_kind="linear",
            )
            assert plan is not None
            executor.record_step_started(plan, action={"step_id": "inspect", "selected_tool": "filesystem_read"})
            executor.record_step_result(
                plan,
                action={"step_id": "inspect", "selected_tool": "filesystem_read"},
                result={"ok": True, "execution_receipt": {"receipt_id": "receipt-summary"}},
            )

            summary = executor.summary_for_plan(plan)

            assert summary is not None
            self.assertEqual(summary.plan_id, plan.plan_id)
            self.assertIn("Inspect", " ".join(summary.completed_steps))
            self.assertEqual(summary.resumability_state, "resumable")

    def test_orchestrator_integration_does_not_break_existing_runtime_flow(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        session_id = f"phase16-session-{uuid4().hex[:8]}"
        task_id = f"phase16-task-{uuid4().hex[:8]}"
        run_id = f"phase16-run-{uuid4().hex[:8]}"
        actions = [
            {"step_id": "read-a", "selected_tool": "filesystem_read", "selected_agent": "engineering-specialist", "tool_arguments": {"path": "README.md"}},
            {"step_id": "read-b", "selected_tool": "filesystem_read", "selected_agent": "engineering-specialist", "tool_arguments": {"path": "package.json"}},
        ]

        with patch(
            "brain.runtime.orchestrator.execute_engineering_action",
            side_effect=[
                {"ok": True, "result_payload": {"file": {"content": "hello"}}},
                {"ok": True, "result_payload": {"file": {"content": "world"}}},
            ],
        ):
            results = orchestrator._execute_runtime_actions(
                session_id=session_id,
                message="inspecionar dois arquivos",
                actions=actions,
                task_id=task_id,
                run_id=run_id,
                provider="test-provider",
                intent="execution",
                delegation={},
                plan_kind="linear",
            )

        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.get("ok") for item in results))
        plan = orchestrator.planning_executor.store.find_plan(session_id=session_id, task_id=task_id, run_id=run_id)
        assert plan is not None
        self.assertEqual(plan.status.value, "completed")

    def test_planning_layer_coexists_with_execution_and_repair_receipts(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        os.environ["OMINI_ENABLE_SELF_REPAIR"] = "true"
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        session_id = f"phase16-repair-session-{uuid4().hex[:8]}"
        task_id = f"phase16-repair-task-{uuid4().hex[:8]}"
        run_id = f"phase16-repair-run-{uuid4().hex[:8]}"
        actions = [
            {"step_id": "broken-read", "selected_tool": "filesystem_read", "selected_agent": "engineering-specialist", "tool_arguments": {"path": "README.md"}},
            {"step_id": "follow-up", "selected_tool": "filesystem_read", "selected_agent": "engineering-specialist", "tool_arguments": {"path": "package.json"}},
        ]

        from brain.runtime.self_repair import (  # noqa: E402
            CauseHypothesis,
            FailureEvidence,
            RepairEligibility,
            RepairEligibilityDecision,
            RepairOutcome,
            RepairReceipt,
            RepairStatus,
        )

        mocked_outcome = RepairOutcome(
            status=RepairStatus.REJECTED,
            evidence=FailureEvidence.build(
                action_id="broken-read",
                action_type="read",
                subsystem="engineering_tools",
                failure_type="verification_failed",
                failure_message_summary="Missing expected file.content field.",
            ),
            eligibility=RepairEligibility(
                decision=RepairEligibilityDecision.REPAIRABLE_WITHIN_SCOPE,
                reason_code="deterministic_repairable_failure",
                summary="Repairable failure.",
            ),
            hypothesis=CauseHypothesis(
                probable_cause_category="result_contract_mismatch",
                confidence_score=0.9,
                affected_component="engineering_tools",
                repair_strategy_class="ensure_file_content_contract",
                rationale="Structured contract mismatch.",
            ),
            scope=None,
            proposal=None,
            validation=None,
            receipt=RepairReceipt.build(
                evidence_id="evidence-phase16",
                proposal_id=None,
                eligibility_decision="repairable_within_scope",
                cause_category="result_contract_mismatch",
                repair_strategy="ensure_file_content_contract",
                validation_status="failed",
                promotion_status="rejected",
                rejection_reason="validation_failed",
                attempt_count=0,
                summary="Repair failed validation.",
            ),
            rerun_recommended=False,
        )

        with patch(
            "brain.runtime.orchestrator.execute_engineering_action",
            return_value={"ok": False, "error_payload": {"kind": "verification_failed", "message": "Missing expected file.content field."}},
        ), patch.object(orchestrator.self_repair_loop, "inspect_failure", return_value=mocked_outcome):
            results = orchestrator._execute_runtime_actions(
                session_id=session_id,
                message="ler arquivo com reparo controlado",
                actions=actions,
                task_id=task_id,
                run_id=run_id,
                provider="test-provider",
                intent="execution",
                delegation={},
                plan_kind="linear",
            )

        self.assertEqual(len(results), 1)
        plan = orchestrator.planning_executor.store.find_plan(session_id=session_id, task_id=task_id, run_id=run_id)
        assert plan is not None
        self.assertTrue(plan.linked_execution_receipt_ids)
        self.assertTrue(plan.linked_repair_receipt_ids)


if __name__ == "__main__":
    unittest.main()
