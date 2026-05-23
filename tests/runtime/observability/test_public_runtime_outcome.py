import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PYTHON_ROOT = PROJECT_ROOT / "backend" / "python"
sys.path.insert(0, str(PYTHON_ROOT))

from brain.runtime.observability.public_runtime_outcome import normalize_public_runtime_outcome

class TestPublicRuntimeOutcome(unittest.TestCase):
    def test_success_read_file(self):
        runtime_mode = "FULL_COGNITIVE_RUNTIME"
        signals = {
            "tool_execution": {
                "tool_selected": "read_file",
                "tool_attempted": True,
                "tool_succeeded": True,
                "tool_failed": False,
            },
            "fallback_triggered": False,
            "execution_path_used": "node_execution",
        }
        result = normalize_public_runtime_outcome(
            runtime_mode=runtime_mode,
            signals=signals,
            response="file content",
        )
        self.assertEqual(result["tool_status"], "succeeded")
        self.assertEqual(result["public_runtime_outcome"], "full_success")
        self.assertFalse(result["controlled_tool_error"])
        self.assertFalse(result["partial_result"])

    def test_direct_local_no_tool(self):
        runtime_mode = "DIRECT_LOCAL_RESPONSE"
        signals = {
            "execution_path_used": "compatibility_execution",
            "fallback_triggered": False,
        }
        result = normalize_public_runtime_outcome(
            runtime_mode=runtime_mode,
            signals=signals,
            response="",
        )
        self.assertEqual(result["tool_status"], "not_requested")
        self.assertEqual(result["tool_skip_reason"], "not_applicable")
        self.assertEqual(result["public_runtime_outcome"], "direct_local_response")

    def test_missing_file_preflight(self):
        runtime_mode = "NODE_EXECUTION_SUCCESS"
        signals = {
            "tool_execution": {
                "tool_selected": "read_file",
                "tool_attempted": False,
                "tool_succeeded": False,
                "tool_failed": False,
            },
            "fallback_triggered": False,
        }
        response = "Error: No such file or directory"
        result = normalize_public_runtime_outcome(
            runtime_mode=runtime_mode,
            signals=signals,
            response=response,
        )
        self.assertEqual(result["tool_status"], "skipped")
        self.assertEqual(result["tool_skip_reason"], "preflight_failed")
        self.assertTrue(result["controlled_tool_error"])
        self.assertEqual(result["error_type"], "file_not_found")
        self.assertEqual(result["public_runtime_outcome"], "controlled_tool_error")

    def test_missing_cargo_partial(self):
        runtime_mode = "NODE_EXECUTION_SUCCESS"
        signals = {
            "tool_execution": {
                "tool_selected": "grep_search",
                "tool_attempted": True,
                "tool_succeeded": False,
                "tool_failed": True,
                "tool_failure_reason": "[Errno 2] No such file or directory: 'cargo'",
            },
            "fallback_triggered": False,
        }
        response = "partial result list..."
        result = normalize_public_runtime_outcome(
            runtime_mode=runtime_mode,
            signals=signals,
            response=response,
        )
        self.assertEqual(result["tool_status"], "failed")
        self.assertEqual(result["error_type"], "missing_dependency")
        self.assertTrue(result["partial_result"])
        self.assertEqual(result["public_runtime_outcome"], "tool_failure_partial_result")

    def test_safe_fallback(self):
        runtime_mode = "SAFE_FALLBACK"
        signals = {"fallback_triggered": True}
        result = normalize_public_runtime_outcome(
            runtime_mode=runtime_mode,
            signals=signals,
            response="",
        )
        self.assertEqual(result["public_runtime_outcome"], "fallback")

if __name__ == '__main__':
    unittest.main()
