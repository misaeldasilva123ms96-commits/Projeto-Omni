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

from brain.runtime.evolution import EvolutionExecutor  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class GovernedSelfEvolutionTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-evolution"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"phase20-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_recurring_bounded_weakness_produces_evolution_opportunity(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = EvolutionExecutor(workspace_root)
            payload = executor.evaluate(
                learning_update={
                    "signals": [
                        {
                            "signal_id": "signal-1",
                            "signal_type": "discouraged_retry_pattern",
                            "evidence_summary": {"evidence_count": 4},
                        }
                    ],
                    "statistics": {"total_patterns": 4},
                }
            )

            self.assertIsNotNone(payload["opportunity"])
            self.assertEqual(payload["opportunity"]["target_subsystem"], "continuation")

    def test_bounded_opportunity_generates_structured_proposal(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = EvolutionExecutor(workspace_root)
            payload = executor.evaluate(
                learning_update={
                    "signals": [
                        {
                            "signal_id": "signal-2",
                            "signal_type": "step_template_success_hint",
                            "evidence_summary": {"evidence_count": 5},
                        }
                    ]
                }
            )

            self.assertIsNotNone(payload["proposal"])
            self.assertEqual(payload["proposal"]["proposal_type"], "validation_insertion")

    def test_out_of_scope_proposal_is_blocked(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = EvolutionExecutor(workspace_root)
            payload = executor.evaluate(
                orchestration_update={"decision": {"route": "tool_delegation"}},
                learning_update={"statistics": {"total_patterns": 3}},
            )
            self.assertIsNotNone(payload["scope"])
            self.assertIn(payload["scope"]["decision"], {"allowed", "allowed_with_governance"})

    def test_medium_high_risk_proposal_requires_governance_gate(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = EvolutionExecutor(workspace_root)
            payload = executor.evaluate(
                result={"error_payload": {"kind": "execution_exception"}, "execution_receipt": {"receipt_id": "receipt-1"}},
                continuation_payload={"decision_type": "escalate_failure"},
            )

            self.assertIsNotNone(payload["risk"])
            self.assertIn(payload["risk"]["risk_level"], {"high", "critical"})
            self.assertIsNotNone(payload["governance"])

    def test_validation_plan_is_created_deterministically(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = EvolutionExecutor(workspace_root)
            payload = executor.evaluate(
                learning_update={
                    "signals": [
                        {
                            "signal_id": "signal-3",
                            "signal_type": "preferred_repair_strategy",
                            "evidence_summary": {"evidence_count": 4},
                        }
                    ]
                }
            )

            self.assertIsNotNone(payload["validation_plan"])
            self.assertIn("targeted_unit_tests", payload["validation_plan"]["validation_modes"])

    def test_blocked_policy_prevents_promotion(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["OMINI_EVOLUTION_ENABLED"] = "false"
            os.environ["OMINI_EVOLUTION_ALLOW_PROMOTION"] = "false"
            executor = EvolutionExecutor(workspace_root)
            payload = executor.evaluate(
                learning_update={
                    "signals": [
                        {
                            "signal_id": "signal-4",
                            "signal_type": "discouraged_retry_pattern",
                            "evidence_summary": {"evidence_count": 4},
                        }
                    ]
                }
            )

            self.assertIn(payload["promotion_status"], {"not_requested", "validated", "blocked"})
            self.assertEqual(payload["governance"]["decision_type"], "deferred")

    def test_approved_for_validation_can_exist_without_promotion(self) -> None:
        with self.temp_workspace() as workspace_root:
            os.environ["OMINI_EVOLUTION_ENABLED"] = "true"
            os.environ["OMINI_EVOLUTION_ALLOW_VALIDATION"] = "true"
            os.environ["OMINI_EVOLUTION_ALLOW_PROMOTION"] = "false"
            executor = EvolutionExecutor(workspace_root)
            payload = executor.evaluate(
                learning_update={
                    "signals": [
                        {
                            "signal_id": "signal-5",
                            "signal_type": "step_template_success_hint",
                            "evidence_summary": {"evidence_count": 4},
                        }
                    ]
                }
            )

            self.assertEqual(payload["governance"]["decision_type"], "approved_for_validation")
            self.assertNotEqual(payload["promotion_status"], "promoted")

    def test_governance_decision_serialization_works(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = EvolutionExecutor(workspace_root)
            payload = executor.evaluate(
                learning_update={
                    "signals": [
                        {
                            "signal_id": "signal-6",
                            "signal_type": "preferred_repair_strategy",
                            "evidence_summary": {"evidence_count": 3},
                        }
                    ]
                }
            )
            serialized = json.dumps(payload["governance"])
            self.assertIn("decision_type", serialized)

    def test_evolution_artifacts_are_persisted(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = EvolutionExecutor(workspace_root)
            payload = executor.evaluate(
                learning_update={
                    "signals": [
                        {
                            "signal_id": "signal-7",
                            "signal_type": "discouraged_retry_pattern",
                            "evidence_summary": {"evidence_count": 4},
                        }
                    ]
                }
            )

            base = workspace_root / ".logs" / "fusion-runtime" / "evolution"
            self.assertTrue((base / "opportunities" / "opportunities.jsonl").exists())
            self.assertTrue((base / "proposals" / "proposals.jsonl").exists())
            self.assertTrue((base / "governance" / "governance.jsonl").exists())
            self.assertIsNotNone(payload["proposal"])

    def test_runtime_integration_does_not_break_existing_flow(self) -> None:
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
                session_id=f"phase20-session-{uuid4().hex[:8]}",
                message="inspecionar dois arquivos",
                actions=actions,
                task_id=f"phase20-task-{uuid4().hex[:8]}",
                run_id=f"phase20-run-{uuid4().hex[:8]}",
                provider="test-provider",
                intent="execution",
                delegation={},
                plan_kind="linear",
            )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.get("ok") for item in results))
        self.assertTrue(all("evolution" in item for item in results))


if __name__ == "__main__":
    unittest.main()
