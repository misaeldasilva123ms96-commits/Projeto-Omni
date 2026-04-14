import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import RunStatus  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class RunRegistryObservabilitySmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        self.orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        self.orchestrator.run_registry = None

    def test_none_safe_run_registry_helpers_do_not_raise(self) -> None:
        self.orchestrator._register_run_record(
            run_id="run-none-safe",
            session_id="sess-none-safe",
            goal_id=None,
            status=RunStatus.RUNNING,
            last_action="execution_started",
            progress_score=0.0,
        )
        self.orchestrator._update_run_status(
            run_id="run-none-safe",
            status=RunStatus.PAUSED,
            last_action="pause_plan",
            progress_score=0.4,
        )


if __name__ == "__main__":
    unittest.main()
