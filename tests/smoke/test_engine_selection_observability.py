from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class EngineSelectionObservabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        self.orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        self.orchestrator.memory_facade.record_event = MagicMock()

    def test_records_engine_selection_event_when_metadata_exists(self) -> None:
        self.orchestrator._record_engine_selection_event(
            {
                "response": "ok",
                "metadata": {
                    "engine_mode": "packaged_upstream",
                    "engine_reason": "dist_candidate_selected",
                },
            }
        )

        self.orchestrator.memory_facade.record_event.assert_called_once_with(
            event_type="engine_selection",
            description="QueryEngine responded via packaged_upstream",
            metadata={
                "engine_mode": "packaged_upstream",
                "engine_reason": "dist_candidate_selected",
            },
        )

    def test_missing_metadata_is_ignored_without_exception(self) -> None:
        self.orchestrator._record_engine_selection_event({"response": "ok"})
        self.orchestrator._record_engine_selection_event(None)

        self.orchestrator.memory_facade.record_event.assert_not_called()


if __name__ == "__main__":
    unittest.main()
