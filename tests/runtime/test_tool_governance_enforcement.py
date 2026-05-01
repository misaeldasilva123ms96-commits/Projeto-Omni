from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.engineering_tools import execute_engineering_action  # noqa: E402
from brain.runtime.observability.cognitive_runtime_inspector import build_cognitive_runtime_inspection  # noqa: E402
from brain.runtime.tool_governance_policy import evaluate_tool_governance  # noqa: E402


GOV_ENV_KEYS = {
    "ALLOW_SHELL",
    "OMNI_ALLOW_SHELL_TOOLS",
    "OMNI_PUBLIC_DEMO_MODE",
    "OMINI_ALLOW_SHELL_TOOLS",
    "OMINI_PUBLIC_DEMO_MODE",
}


def clean_env(**values: str) -> dict[str, str]:
    env = {key: "" for key in GOV_ENV_KEYS}
    env.update(values)
    return env


def _base_inspection_kwargs(**overrides):
    base = dict(
        response="blocked",
        safe_fallback="SAFE",
        node_fallback="NODE_FB",
        mock_response="MOCK",
        last_runtime_mode="live",
        last_runtime_reason="tool_blocked",
        reasoning_payload={"trace": {"validation_result": "valid"}},
        strategy_payload={"degraded": False},
        memory_context_payload={"selected_count": 1},
        planning_payload={"planning_trace": {"execution_ready": True}},
        swarm_result={"response": "blocked"},
        learning_record={"assessment": {"execution_path": "swarm"}},
        node_cognitive_hint=None,
        node_outcome=None,
        direct_memory_hit=False,
        self_improving_system_trace={},
        controlled_evolution_payload={},
        coordination_payload={},
        duration_ms=5,
    )
    base.update(overrides)
    return base


class ToolGovernanceEnforcementTest(unittest.TestCase):
    def test_read_safe_allowed(self) -> None:
        decision = evaluate_tool_governance({"selected_tool": "git_status", "tool_arguments": {}})
        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["category"], "read_safe")

    def test_read_sensitive_without_scope_requires_approval(self) -> None:
        decision = evaluate_tool_governance({"selected_tool": "read_file", "tool_arguments": {}})
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["category"], "read_sensitive")
        self.assertTrue(decision["approval_required"])
        self.assertEqual(decision["error_public_code"], "TOOL_APPROVAL_REQUIRED")

    def test_write_without_approval_is_blocked(self) -> None:
        result = execute_engineering_action(
            project_root=PROJECT_ROOT,
            action={"selected_tool": "write_file", "tool_arguments": {"path": "tmp.txt", "content": "x"}},
        )

        self.assert_governance_blocked(result, "TOOL_APPROVAL_REQUIRED")

    def test_destructive_operation_blocked(self) -> None:
        result = execute_engineering_action(
            project_root=PROJECT_ROOT,
            action={"selected_tool": "git_reset", "tool_arguments": {}},
        )

        self.assert_governance_blocked(result, "TOOL_APPROVAL_REQUIRED")
        self.assertEqual(result["governance_audit"]["category"], "destructive")

    def test_shell_blocked_in_public_demo_and_allow_shell_cannot_bypass(self) -> None:
        with patch.dict(os.environ, clean_env(ALLOW_SHELL="true", OMNI_PUBLIC_DEMO_MODE="true"), clear=False):
            result = execute_engineering_action(
                project_root=PROJECT_ROOT,
                action={"selected_tool": "shell_command", "tool_arguments": {"command": ["python", "--version"]}},
            )

        self.assert_governance_blocked(result, "TOOL_BLOCKED_PUBLIC_DEMO")
        self.assertTrue(result["governance_audit"]["public_demo_blocked"])

    def test_git_status_diff_allowed_by_governance_but_shell_policy_still_applies(self) -> None:
        status = evaluate_tool_governance({"selected_tool": "git_status", "tool_arguments": {}})
        diff = evaluate_tool_governance({"selected_tool": "git_diff", "tool_arguments": {}})

        self.assertTrue(status["allowed"])
        self.assertTrue(diff["allowed"])

    def test_git_reset_clean_blocked_and_commit_push_gated(self) -> None:
        for tool in ("git_reset", "git_clean"):
            with self.subTest(tool=tool):
                decision = evaluate_tool_governance({"selected_tool": tool, "tool_arguments": {}})
                self.assertFalse(decision["allowed"])
                self.assertEqual(decision["category"], "destructive")

        for tool in ("git_commit", "git_push"):
            with self.subTest(tool=tool):
                decision = evaluate_tool_governance({"selected_tool": tool, "tool_arguments": {}})
                self.assertFalse(decision["allowed"])
                self.assertEqual(decision["category"], "git_sensitive")
                self.assertTrue(decision["approval_required"])

    def test_network_like_tool_gated(self) -> None:
        decision = evaluate_tool_governance({"selected_tool": "web_request", "tool_arguments": {"url": "https://example.com"}})
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["category"], "network")
        self.assertEqual(decision["error_public_code"], "TOOL_APPROVAL_REQUIRED")

    def test_governance_block_is_public_safe(self) -> None:
        result = execute_engineering_action(
            project_root=PROJECT_ROOT,
            action={
                "selected_tool": "read_file",
                "tool_arguments": {
                    "env": {"TOKEN": "secret"},
                    "command": ["rm", "-rf", "/"],
                    "path": "",
                },
            },
        )

        self.assert_governance_blocked(result, "TOOL_APPROVAL_REQUIRED")
        serialized = str(result).lower()
        for forbidden in ("traceback", "stack", "env", "token", "stdout", "stderr", "rm -rf", "raw_payload"):
            self.assertNotIn(forbidden, serialized)

    def test_runtime_truth_marks_governance_blocked_tool(self) -> None:
        row = build_cognitive_runtime_inspection(
            **_base_inspection_kwargs(
                lora_payload={
                    "tool_execution": {
                        "tool_requested": True,
                        "tool_selected": "write_file",
                        "tool_available": True,
                        "tool_attempted": False,
                        "tool_succeeded": False,
                        "tool_denied": True,
                        "tool_failure_class": "TOOL_APPROVAL_REQUIRED",
                    }
                }
            )
        )

        self.assertEqual(row["runtime_truth"]["runtime_mode"], "TOOL_BLOCKED")
        self.assertTrue(row["runtime_truth"]["tool_invoked"])
        self.assertFalse(row["runtime_truth"]["tool_executed"])
        self.assertEqual(row["runtime_truth"]["tool_status"], "blocked")

    def assert_governance_blocked(self, result: dict, code: str) -> None:
        self.assertFalse(result["ok"])
        self.assertEqual(result["tool_status"], "blocked")
        self.assertEqual(result["error_public_code"], code)
        self.assertTrue(result["internal_error_redacted"])
        self.assertIn("governance_audit", result)
        self.assertIn(result["governance_audit"]["category"], {"read_sensitive", "write", "destructive", "shell"})


if __name__ == "__main__":
    unittest.main()
