from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class OrchestratorSmokeTest(unittest.TestCase):
    def test_orchestrator_returns_non_empty_response(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        os.environ["AI_SESSION_ID"] = "phase2-orchestrator-smoke"

        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )

        response = orchestrator.run("ola")
        self.assertIsInstance(response, str)
        self.assertTrue(response.strip())


if __name__ == "__main__":
    unittest.main()
