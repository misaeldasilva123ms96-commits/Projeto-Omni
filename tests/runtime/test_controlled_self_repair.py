from __future__ import annotations

import hashlib
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

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.self_repair import (  # noqa: E402
    CauseHypothesis,
    FailureEvidence,
    RepairEligibility,
    RepairEligibilityDecision,
    RepairOutcome,
    RepairProposal,
    RepairReceipt,
    RepairStatus,
    RepairValidationPlan,
    SelfRepairPolicy,
)
from brain.runtime.self_repair.repair_executor import SelfRepairExecutor  # noqa: E402
from brain.runtime.self_repair.repair_scope import RepairScopeEnforcer  # noqa: E402


class ControlledSelfRepairTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-self-repair"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"phase15-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def make_policy(self, *, enable: bool = True, allow_promotion: bool = False) -> SelfRepairPolicy:
        return SelfRepairPolicy(
            enable_self_repair=enable,
            allow_promotion=allow_promotion,
            max_files=1,
            max_attempts_per_action=1,
            max_recurrence=2,
            allowed_root="backend/python/brain/runtime",
        )

    def test_eligible_deterministic_failure_produces_repair_proposal(self) -> None:
        with self.temp_workspace() as workspace_root:
            target = workspace_root / "backend" / "python" / "brain" / "runtime" / "engineering_tools.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                'def _ok(tool, payload):\n'
                '    return payload\n'
                'def repair_target(tool, target):\n'
                '    return _ok(tool, {"file": {"filePath": str(target)}})\n',
                encoding="utf-8",
            )
            executor = SelfRepairExecutor(workspace_root=workspace_root, policy=self.make_policy(enable=True, allow_promotion=False))
            evidence = FailureEvidence.build(
                action_id="step-1",
                action_type="read",
                subsystem="engineering_tools",
                failure_type="verification_failed",
                failure_message_summary="Missing expected file.content field.",
                verification_details={"missing_fields": ["file.content"]},
                capability="filesystem_read",
            )

            outcome = executor.handle_failure(evidence=evidence)

            self.assertEqual(outcome.eligibility.decision, RepairEligibilityDecision.REPAIRABLE_WITHIN_SCOPE)
            self.assertIsNotNone(outcome.proposal)
            self.assertEqual(outcome.proposal.repair_strategy_class, "ensure_file_content_contract")
            self.assertEqual(outcome.status, RepairStatus.VALIDATED)

    def test_non_eligible_failure_is_rejected_by_policy(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = SelfRepairExecutor(workspace_root=workspace_root, policy=self.make_policy(enable=True, allow_promotion=False))
            evidence = FailureEvidence.build(
                action_id="step-2",
                action_type="execute",
                subsystem="runtime_execution",
                failure_type="external_service_outage",
                failure_message_summary="Dependency API is unavailable.",
            )

            outcome = executor.handle_failure(evidence=evidence)

            self.assertEqual(outcome.status, RepairStatus.REJECTED)
            self.assertEqual(outcome.eligibility.decision, RepairEligibilityDecision.REQUIRES_HUMAN_OR_FUTURE_PHASE)

    def test_repair_scope_blocks_overly_broad_proposal(self) -> None:
        enforcer = RepairScopeEnforcer()
        proposal = RepairProposal.build(
            evidence_id="evidence-1",
            cause_category="result_contract_mismatch",
            repair_strategy_class="ensure_file_content_contract",
            target_file="frontend/src/App.tsx",
            proposed_action_summary="Touch frontend file",
            expected_fix_outcome="No-op",
            scope_classification="single_file_runtime_patch",
            confidence_score=0.5,
            validation_plan=RepairValidationPlan(
                validation_modes=["source-compile"],
                targeted_tests=[],
                require_import_validation=False,
                require_receipt_smoke_check=False,
                promotion_allowed=False,
            ),
            promotion_conditions=[],
            patch_payload={"file_path": "frontend/src/App.tsx", "new_content": "console.log('x')", "original_content_hash": "", "patch_diff": "", "confidence_score": 0.5},
        )
        with self.temp_workspace() as workspace_root:
            scope = enforcer.evaluate(
                workspace_root=workspace_root,
                proposal=proposal,
                policy=self.make_policy(enable=True, allow_promotion=False),
            )
        self.assertFalse(scope.within_scope)
        self.assertEqual(scope.reason_code, "target_outside_allowed_root")

    def test_validation_success_allows_promotion(self) -> None:
        with self.temp_workspace() as workspace_root:
            target = workspace_root / "backend" / "python" / "brain" / "runtime" / "engineering_tools.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            original = (
                "def _ok(tool, payload):\n"
                "    return payload\n"
                "def repair_target(tool, target, content, limit):\n"
                '    return _ok(tool, {"file": {"filePath": str(target)}})\n'
            )
            target.write_text(original, encoding="utf-8")
            executor = SelfRepairExecutor(workspace_root=workspace_root, policy=self.make_policy(enable=True, allow_promotion=True))
            evidence = FailureEvidence.build(
                action_id="step-3",
                action_type="read",
                subsystem="engineering_tools",
                failure_type="verification_failed",
                failure_message_summary="Missing expected file.content field.",
                verification_details={"missing_fields": ["file.content"]},
                capability="filesystem_read",
            )

            outcome = executor.handle_failure(evidence=evidence)

            self.assertEqual(outcome.status, RepairStatus.PROMOTED)
            self.assertIn('"content": content[:limit]', target.read_text(encoding="utf-8"))

    def test_validation_failure_rejects_promotion(self) -> None:
        with self.temp_workspace() as workspace_root:
            target = workspace_root / "backend" / "python" / "brain" / "runtime" / "execution" / "trusted_executor.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            original = "def noop():\n    return True\n"
            target.write_text(original, encoding="utf-8")
            executor = SelfRepairExecutor(workspace_root=workspace_root, policy=self.make_policy(enable=True, allow_promotion=True))
            evidence = FailureEvidence.build(
                action_id="step-4",
                action_type="execute",
                subsystem="execution_wrapper",
                failure_type="missing_result_payload",
                failure_message_summary="Missing result payload.",
            )

            bad_proposal = RepairProposal.build(
                evidence_id=evidence.evidence_id,
                cause_category="result_shape_mismatch",
                repair_strategy_class="normalize_result_payload_shape",
                target_file="backend/python/brain/runtime/execution/trusted_executor.py",
                proposed_action_summary="Inject invalid syntax",
                expected_fix_outcome="No-op",
                scope_classification="single_file_runtime_patch",
                confidence_score=0.2,
                validation_plan=RepairValidationPlan(
                    validation_modes=["source-compile"],
                    targeted_tests=[],
                    require_import_validation=True,
                    require_receipt_smoke_check=True,
                    promotion_allowed=True,
                ),
                promotion_conditions=[],
                patch_payload={
                    "file_path": "backend/python/brain/runtime/execution/trusted_executor.py",
                    "original_content_hash": hashlib.sha256(original.encode("utf-8")).hexdigest(),
                    "patch_diff": "",
                    "confidence_score": 0.2,
                    "original_content": original,
                    "new_content": "def broken(:\n",
                },
            )

            with patch.object(executor.proposer, "propose", return_value=bad_proposal):
                outcome = executor.handle_failure(evidence=evidence)

            self.assertEqual(outcome.status, RepairStatus.REJECTED)
            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_max_attempt_policy_blocks_repeated_unsafe_repair_attempts(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = SelfRepairExecutor(workspace_root=workspace_root, policy=self.make_policy(enable=True, allow_promotion=False))
            evidence = FailureEvidence.build(
                action_id="step-5",
                action_type="read",
                subsystem="engineering_tools",
                failure_type="verification_failed",
                failure_message_summary="Repeated mismatch.",
                retry_count=1,
                recurrence_count=3,
                verification_details={"missing_fields": ["file.content"]},
                capability="filesystem_read",
            )

            outcome = executor.handle_failure(evidence=evidence)

            self.assertEqual(outcome.status, RepairStatus.BLOCKED)
            self.assertEqual(outcome.eligibility.reason_code, "max_attempts_exceeded")

    def test_repair_receipt_serialization(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = SelfRepairExecutor(workspace_root=workspace_root, policy=self.make_policy(enable=False, allow_promotion=False))
            evidence = FailureEvidence.build(
                action_id="step-6",
                action_type="execute",
                subsystem="runtime_execution",
                failure_type="verification_failed",
                failure_message_summary="Repair disabled.",
            )

            outcome = executor.handle_failure(evidence=evidence)
            payload = outcome.receipt.as_dict()

            self.assertIn("repair_receipt_id", payload)
            self.assertIsInstance(json.dumps(payload), str)

    def test_orchestrator_integration_path_does_not_break_existing_flow(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        os.environ["OMINI_ENABLE_SELF_REPAIR"] = "false"
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        action = {
            "step_id": "self-repair-disabled",
            "selected_tool": "filesystem_read",
            "selected_agent": "engineering-specialist",
            "tool_arguments": {"path": "README.md"},
        }

        with patch(
            "brain.runtime.orchestrator.execute_engineering_action",
            return_value={"ok": False, "error_payload": {"kind": "verification_failed", "message": "Missing expected file.content field."}},
        ):
            result = orchestrator._execute_single_action(
                action=action,
                step_results=[],
                semantic_retrieval=None,
                learning_guidance=None,
                session_id="repair-disabled",
                task_id="repair-disabled-task",
                run_id="repair-disabled-run",
            )

        self.assertFalse(result["ok"])
        self.assertNotIn("self_repair", result)

    def test_disabled_policy_mode_prevents_self_repair_execution(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = SelfRepairExecutor(workspace_root=workspace_root, policy=self.make_policy(enable=False, allow_promotion=False))
            evidence = FailureEvidence.build(
                action_id="step-7",
                action_type="read",
                subsystem="engineering_tools",
                failure_type="verification_failed",
                failure_message_summary="Repair disabled.",
                verification_details={"missing_fields": ["file.content"]},
                capability="filesystem_read",
            )

            outcome = executor.handle_failure(evidence=evidence)

            self.assertEqual(outcome.status, RepairStatus.BLOCKED)
            self.assertEqual(outcome.eligibility.decision, RepairEligibilityDecision.BLOCKED_BY_POLICY)

    def test_orchestrator_attaches_repair_metadata_when_self_repair_runs(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        os.environ["OMINI_ENABLE_SELF_REPAIR"] = "true"
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        action = {
            "step_id": "self-repair-attached",
            "selected_tool": "filesystem_read",
            "selected_agent": "engineering-specialist",
            "tool_arguments": {"path": "README.md"},
        }
        mocked_outcome = RepairOutcome(
            status=RepairStatus.REJECTED,
            evidence=FailureEvidence.build(
                action_id="self-repair-attached",
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
                evidence_id="evidence-test",
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
            result = orchestrator._execute_single_action(
                action=action,
                step_results=[],
                semantic_retrieval=None,
                learning_guidance=None,
                session_id="repair-enabled",
                task_id="repair-enabled-task",
                run_id="repair-enabled-run",
            )

        self.assertFalse(result["ok"])
        self.assertIn("self_repair", result)
        self.assertIn("repair_receipt", result)


if __name__ == "__main__":
    unittest.main()
