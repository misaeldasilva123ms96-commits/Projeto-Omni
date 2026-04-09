from __future__ import annotations

import sys
import unittest
from pathlib import Path
import shutil
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.decision_memory import DecisionMemoryStore  # noqa: E402


class DecisionMemoryStoreTest(unittest.TestCase):
    def test_decisions_are_recorded_and_retrievable(self) -> None:
        temp_root = PROJECT_ROOT / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        temp_dir = temp_root / f"decision-{uuid.uuid4().hex}"
        temp_dir.mkdir(exist_ok=True)
        try:
            store = DecisionMemoryStore(temp_dir / "decision-memory.json")
            store.record_decision(
                session_id="session-a",
                task_id="task-1",
                run_id="run-1",
                decision_type="routing_selection",
                task_type="code_mutation",
                reason_code="routing_selected",
                reason="selected engineering workflow",
                metadata={"execution_strategy": "plan_then_execute"},
            )
            store.record_decision(
                session_id="session-a",
                task_id="task-2",
                run_id="run-2",
                decision_type="policy_block",
                task_type="code_mutation",
                reason_code="insufficient_evidence",
                reason="blocked by evidence gate",
                metadata={},
            )

            matches = store.find_decisions(
                session_id="session-a",
                task_type="code_mutation",
                decision_type="policy_block",
                limit=5,
            )
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["reason_code"], "insufficient_evidence")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
