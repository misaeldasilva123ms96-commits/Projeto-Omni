from __future__ import annotations

import sys
import unittest
from pathlib import Path
import shutil
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.evidence_memory import EvidenceMemoryStore  # noqa: E402


class EvidenceMemoryStoreTest(unittest.TestCase):
    def test_evidence_categories_are_stored_and_returned(self) -> None:
        temp_root = PROJECT_ROOT / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        temp_dir = temp_root / f"evidence-{uuid.uuid4().hex}"
        temp_dir.mkdir(exist_ok=True)
        try:
            store = EvidenceMemoryStore(temp_dir / "evidence-memory.json")
            store.record_evidence(
                session_id="session-a",
                task_id="task-1",
                run_id="run-1",
                task_type="verification",
                evidence={
                    "file_evidence": True,
                    "runtime_evidence": False,
                    "test_evidence": True,
                    "dependency_evidence": False,
                },
                metadata={"target_files": ["a.py"]},
            )

            matches = store.get_evidence(session_id="session-a", task_id="task-1", limit=2)
            self.assertEqual(len(matches), 1)
            self.assertTrue(matches[0]["evidence"]["file_evidence"])
            self.assertTrue(matches[0]["evidence"]["test_evidence"])
            self.assertFalse(matches[0]["evidence"]["runtime_evidence"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
