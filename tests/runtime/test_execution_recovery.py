from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class ExecutionRecoveryTest(unittest.TestCase):
    def test_tool_capable_prompt_uses_real_primary_execution_path(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        with patch.object(BrainOrchestrator, "_answer_from_memory", return_value=""):
            response = orchestrator.run("analise o arquivo package.json")
        self.assertTrue(response.strip())
        inspection = orchestrator.last_cognitive_runtime_inspection or {}
        self.assertNotEqual(inspection.get("runtime_mode"), "SAFE_FALLBACK")
        self.assertEqual(inspection.get("runtime_mode"), "FULL_COGNITIVE_RUNTIME")
        self.assertEqual(inspection.get("runtime_reason"), "node_execution_request")
        self.assertEqual(inspection.get("signals", {}).get("execution_path_used"), "node_execution")
        self.assertFalse(inspection.get("signals", {}).get("fallback_triggered", True))
        tool_execution = inspection.get("signals", {}).get("tool_execution", {})
        self.assertTrue(tool_execution.get("tool_requested"))
        self.assertTrue(str(tool_execution.get("tool_selected", "")).strip())
        self.assertTrue(tool_execution.get("tool_attempted"))
        self.assertTrue(
            tool_execution.get("tool_succeeded")
            or tool_execution.get("tool_failed")
            or tool_execution.get("tool_denied")
        )
        self.assertEqual(orchestrator.last_strategy_execution["execution_runtime_lane"], "true_action_execution")
        self.assertFalse(orchestrator.last_strategy_execution["compatibility_execution_active"])
        self.assertEqual(orchestrator.last_strategy_execution["execution_path_used"], "node_execution")
        self.assertTrue(str(orchestrator.last_strategy_execution["tool_execution"]["tool_selected"]).strip())

    def test_primary_local_tool_path_executes_real_read_file(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        payload = orchestrator._execute_primary_local_tool_path(
            session_id="local-tool-recovery",
            runtime_message="leia o arquivo package.json",
            predicted_intent="inspect",
            selected_tools=["read_file"],
        )
        self.assertTrue(str(payload.get("response", "")).strip())
        self.assertEqual(payload.get("execution_runtime_lane"), "local_tool_execution")
        tool_execution = payload.get("tool_execution", {})
        self.assertTrue(tool_execution.get("tool_requested"))
        self.assertEqual(tool_execution.get("tool_selected"), "read_file")
        self.assertTrue(tool_execution.get("tool_attempted"))
        self.assertTrue(tool_execution.get("tool_succeeded"))


if __name__ == "__main__":
    unittest.main()
