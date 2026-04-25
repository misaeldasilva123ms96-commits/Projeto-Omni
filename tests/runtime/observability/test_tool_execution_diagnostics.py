from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.observability.tool_execution_diagnostics import (  # noqa: E402
    build_tool_execution_diagnostic,
    summarize_tool_execution,
)


class ToolExecutionDiagnosticsTest(unittest.TestCase):
    def test_build_tool_execution_diagnostic_marks_success(self) -> None:
        diagnostic = build_tool_execution_diagnostic(
            selected_tool="read_file",
            result={"ok": True, "selected_tool": "read_file"},
            latency_ms=42,
            tool_available=True,
        )
        self.assertTrue(diagnostic["tool_requested"])
        self.assertEqual(diagnostic["tool_selected"], "read_file")
        self.assertTrue(diagnostic["tool_attempted"])
        self.assertTrue(diagnostic["tool_succeeded"])
        self.assertFalse(diagnostic["tool_failed"])
        self.assertFalse(diagnostic["tool_denied"])
        self.assertEqual(diagnostic["tool_latency_ms"], 42)

    def test_build_tool_execution_diagnostic_marks_denial(self) -> None:
        diagnostic = build_tool_execution_diagnostic(
            selected_tool="git_commit",
            result={
                "ok": False,
                "selected_tool": "git_commit",
                "error_payload": {
                    "kind": "permission_denied",
                    "message": "git_commit requires explicit approval.",
                },
            },
            latency_ms=7,
            tool_available=True,
        )
        self.assertTrue(diagnostic["tool_attempted"])
        self.assertFalse(diagnostic["tool_succeeded"])
        self.assertFalse(diagnostic["tool_failed"])
        self.assertTrue(diagnostic["tool_denied"])
        self.assertEqual(diagnostic["tool_failure_class"], "permission_denied")

    def test_summarize_tool_execution_prefers_latest_attempt(self) -> None:
        primary, diagnostics = summarize_tool_execution(
            step_results=[
                {
                    "selected_tool": "read_file",
                    "tool_execution": build_tool_execution_diagnostic(
                        selected_tool="read_file",
                        result={"ok": True, "selected_tool": "read_file"},
                        latency_ms=10,
                    ),
                },
                {
                    "selected_tool": "verification_runner",
                    "tool_execution": build_tool_execution_diagnostic(
                        selected_tool="verification_runner",
                        result={
                            "ok": False,
                            "selected_tool": "verification_runner",
                            "error_payload": {"kind": "verification_failed", "message": "Verification failed."},
                        },
                        latency_ms=50,
                    ),
                },
            ]
        )
        self.assertEqual(len(diagnostics), 2)
        self.assertEqual(primary["tool_selected"], "verification_runner")
        self.assertTrue(primary["tool_failed"])


if __name__ == "__main__":
    unittest.main()
