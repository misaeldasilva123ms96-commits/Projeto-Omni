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
        self.assertEqual(orchestrator.last_strategy_execution["execution_runtime_lane"], "true_action_execution")
        self.assertFalse(orchestrator.last_strategy_execution["compatibility_execution_active"])
        self.assertEqual(orchestrator.last_strategy_execution["execution_path_used"], "node_execution")


if __name__ == "__main__":
    unittest.main()
