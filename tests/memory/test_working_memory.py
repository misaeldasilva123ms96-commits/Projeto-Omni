from __future__ import annotations

import sys
import unittest
from pathlib import Path
import shutil
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.working_memory import WorkingMemoryStore  # noqa: E402


class WorkingMemoryStoreTest(unittest.TestCase):
    def test_session_updates_are_stored_and_replaced(self) -> None:
        temp_root = PROJECT_ROOT / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        temp_dir = temp_root / f"working-{uuid.uuid4().hex}"
        temp_dir.mkdir(exist_ok=True)
        try:
            store = WorkingMemoryStore(temp_dir / "working-memory.json")
            first = store.update_session("session-a", {"current_task_summary": "task one", "current_mode": "PLAN"})
            second = store.update_session("session-a", {"current_task_summary": "task two", "current_mode": "EXECUTE"})

            self.assertEqual(first["current_task_summary"], "task one")
            self.assertEqual(second["current_task_summary"], "task two")
            loaded = store.load_session("session-a")
            self.assertEqual(loaded["current_task_summary"], "task two")
            self.assertEqual(loaded["current_mode"], "EXECUTE")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
