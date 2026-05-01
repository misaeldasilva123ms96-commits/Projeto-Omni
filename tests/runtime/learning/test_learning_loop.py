from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class LearningLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="omni-phase10-", dir=str(PROJECT_ROOT / ".logs")))
        self._old_base_dir = os.environ.get("BASE_DIR")
        self._old_python_base_dir = os.environ.get("PYTHON_BASE_DIR")
        os.environ["BASE_DIR"] = str(self.workspace)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        self.orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )

    def tearDown(self) -> None:
        if self._old_base_dir is None:
            os.environ.pop("BASE_DIR", None)
        else:
            os.environ["BASE_DIR"] = self._old_base_dir
        if self._old_python_base_dir is None:
            os.environ.pop("PYTHON_BASE_DIR", None)
        else:
            os.environ["PYTHON_BASE_DIR"] = self._old_python_base_dir
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_prompt_creates_controlled_learning_record(self) -> None:
        response = self.orchestrator.run("o que e uma api?")
        self.assertTrue(response.strip())

        records = self.orchestrator.learning_logger.store.read_recent_learning_records(limit=1)
        self.assertEqual(len(records), 1)
        record = records[0]

        self.assertTrue(record["record_id"])
        self.assertEqual(record["selected_strategy"], "DIRECT_RESPONSE")
        self.assertTrue(record["execution_path"])
        self.assertTrue(record["runtime_mode"])
        self.assertIn("decision_evaluation", record)
        self.assertIn("execution_outcome", record)
        self.assertIn("learning_safety", record)
        self.assertIn("positive_training_candidate", record["learning_safety"])
        self.assertIn("learning_classification", record["learning_safety"])
        self.assertIn("success", record)
        self.assertIsNotNone(record["decision_evaluation"]["decision_correct"])

        signals = self.orchestrator.learning_logger.store.read_recent_improvement_signals(limit=5)
        self.assertIsInstance(signals, list)

        inspection = dict(self.orchestrator.last_cognitive_runtime_inspection or {})
        runtime_signals = dict(inspection.get("signals") or {})
        self.assertTrue(runtime_signals.get("learning_record_created"))
        self.assertIn("decision_correct", runtime_signals)


if __name__ == "__main__":
    unittest.main()
