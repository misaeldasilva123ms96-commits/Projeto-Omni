from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.execution import ExecutionIntent, ExecutionPolicy, RiskLevel, TrustedExecutor  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class TrustedExecutionLayerTest(unittest.TestCase):
    def test_low_risk_allowed_action(self) -> None:
        executor = TrustedExecutor(available_tools={"filesystem_read"})
        result = executor.execute(
            intent=ExecutionIntent(
                action_id="read-1",
                action_type="read",
                capability="filesystem_read",
                description="Read a file",
                input_payload_summary={"tool_arguments": {"path": "README.md"}},
                expected_outcome="File content is returned.",
                reversible=True,
                target_subsystem="engineering_tools",
                session_id="sess-1",
            ),
            execute_callback=lambda: {
                "ok": True,
                "result_payload": {"file": {"content": "hello world"}},
            },
        )

        self.assertTrue(result.result["ok"])
        self.assertEqual(result.risk.level, RiskLevel.LOW)
        self.assertEqual(result.receipt.execution_status, "succeeded")
        self.assertEqual(result.receipt.verification_status, "passed")

    def test_blocked_critical_action_under_restrictive_policy(self) -> None:
        executor = TrustedExecutor(
            available_tools={"shell_command"},
            policy=ExecutionPolicy(
                max_risk=RiskLevel.HIGH,
                allow_high_risk=True,
                allow_critical=False,
            ),
        )
        invoked = {"value": False}

        result = executor.execute(
            intent=ExecutionIntent(
                action_id="shell-1",
                action_type="execute",
                capability="shell_command",
                description="Run a shell command",
                input_payload_summary={"tool_arguments": {"command": "rm -rf ."}},
                expected_outcome="Command runs.",
                reversible=False,
                target_subsystem="rust_bridge",
                session_id="sess-1",
            ),
            execute_callback=lambda: invoked.update(value=True) or {"ok": True, "result_payload": {"stdout": "nope"}},
        )

        self.assertFalse(invoked["value"])
        self.assertFalse(result.result["ok"])
        self.assertEqual(result.result["error_payload"]["kind"], "critical_risk_blocked")
        self.assertEqual(result.receipt.execution_status, "denied")

    def test_failed_preflight(self) -> None:
        executor = TrustedExecutor(available_tools=set())
        result = executor.execute(
            intent=ExecutionIntent(
                action_id="unknown-1",
                action_type="read",
                capability="filesystem_read",
                description="Read file with missing registration",
                input_payload_summary={"tool_arguments": {"path": "README.md"}},
                expected_outcome="File content is returned.",
                reversible=True,
                target_subsystem="engineering_tools",
                session_id="sess-1",
            ),
            execute_callback=lambda: {"ok": True, "result_payload": {"file": {"content": "hello"}}},
        )

        self.assertFalse(result.result["ok"])
        self.assertEqual(result.result["error_payload"]["kind"], "preflight_failed")
        self.assertEqual(result.receipt.preflight_status, "failed")

    def test_successful_execution_with_successful_verification(self) -> None:
        executor = TrustedExecutor(available_tools={"filesystem_write"})
        result = executor.execute(
            intent=ExecutionIntent(
                action_id="write-1",
                action_type="mutate",
                capability="filesystem_write",
                description="Write a file",
                input_payload_summary={"tool_arguments": {"path": "notes.txt", "content": "done"}},
                expected_outcome="Patch is applied to the workspace.",
                reversible=False,
                target_subsystem="engineering_tools",
                session_id="sess-1",
            ),
            execute_callback=lambda: {
                "ok": True,
                "result_payload": {
                    "workspace_root": str(PROJECT_ROOT),
                    "patch": {"operations": [{"kind": "write"}]},
                },
            },
        )

        self.assertTrue(result.result["ok"])
        self.assertEqual(result.receipt.execution_status, "succeeded")
        self.assertEqual(result.receipt.verification_status, "passed")
        self.assertIn("workspace_root", result.verification.observed_effects)

    def test_execution_failure_generates_proper_receipt(self) -> None:
        executor = TrustedExecutor(available_tools={"filesystem_read"})
        result = executor.execute(
            intent=ExecutionIntent(
                action_id="read-2",
                action_type="read",
                capability="filesystem_read",
                description="Read a missing file",
                input_payload_summary={"tool_arguments": {"path": "missing.txt"}},
                expected_outcome="File content is returned.",
                reversible=True,
                target_subsystem="engineering_tools",
                session_id="sess-1",
            ),
            execute_callback=lambda: {
                "ok": False,
                "error_payload": {"kind": "file_not_found", "message": "File missing"},
            },
        )

        self.assertFalse(result.result["ok"])
        self.assertEqual(result.receipt.execution_status, "failed")
        self.assertEqual(result.receipt.error_details["kind"], "file_not_found")

    def test_verification_failure_generates_proper_receipt(self) -> None:
        executor = TrustedExecutor(available_tools={"filesystem_read"})
        result = executor.execute(
            intent=ExecutionIntent(
                action_id="read-3",
                action_type="read",
                capability="filesystem_read",
                description="Read file but return invalid payload",
                input_payload_summary={"tool_arguments": {"path": "README.md"}},
                expected_outcome="File content is returned.",
                reversible=True,
                target_subsystem="engineering_tools",
                session_id="sess-1",
            ),
            execute_callback=lambda: {"ok": True, "result_payload": {}},
        )

        self.assertFalse(result.result["ok"])
        self.assertEqual(result.result["error_payload"]["kind"], "verification_failed")
        self.assertEqual(result.receipt.verification_status, "failed")

    def test_receipt_serialization(self) -> None:
        executor = TrustedExecutor(available_tools={"filesystem_read"})
        result = executor.execute(
            intent=ExecutionIntent(
                action_id="read-4",
                action_type="read",
                capability="filesystem_read",
                description="Read file for serialization",
                input_payload_summary={"tool_arguments": {"path": "README.md"}},
                expected_outcome="File content is returned.",
                reversible=True,
                target_subsystem="engineering_tools",
                session_id="sess-1",
            ),
            execute_callback=lambda: {
                "ok": True,
                "result_payload": {"file": {"content": "serialized"}},
            },
        )

        payload = result.receipt.as_dict()
        self.assertIn("receipt_id", payload)
        self.assertIsInstance(json.dumps(payload), str)

    def test_orchestrator_backward_compatibility_path(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        action = {
            "step_id": "compat-1",
            "selected_tool": "filesystem_read",
            "selected_agent": "engineering-specialist",
            "tool_arguments": {"path": "README.md"},
        }

        with patch(
            "brain.runtime.orchestrator.execute_engineering_action",
            return_value={"ok": True, "result_payload": {"file": {"content": "ok from trusted execution"}}},
        ):
            result = orchestrator._execute_single_action(
                action=action,
                step_results=[],
                semantic_retrieval=None,
                learning_guidance=None,
                session_id="compat-session",
                task_id="compat-task",
                run_id="compat-run",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["evaluation"]["decision"], "continue")
        self.assertIn("execution_receipt", result)
        self.assertIn("trusted_execution", result)


if __name__ == "__main__":
    unittest.main()
