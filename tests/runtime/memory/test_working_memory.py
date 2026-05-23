from __future__ import annotations

import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.memory.working import WorkingMemory  # noqa: E402


class WorkingMemoryTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-memory"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"working-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_working_memory_records_and_flushes_events(self) -> None:
        with self.temp_workspace() as workspace_root:
            memory = WorkingMemory(workspace_root)
            memory.start_new_session(session_id="sess-1", goal_id="goal-1", active_plan_id="plan-1")
            memory.record_event(
                event_type="continuation_decision",
                description="Continuar com a proxima etapa.",
                outcome="continue_execution",
                progress_score=0.5,
                evidence_ids=["receipt-1"],
            )

            payload = json.loads((workspace_root / ".logs" / "fusion-runtime" / "memory" / "working_memory.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["session_id"], "sess-1")
            self.assertEqual(payload["goal_id"], "goal-1")
            self.assertEqual(len(payload["recent_events"]), 1)
            self.assertEqual(payload["recent_events"][0]["event_type"], "continuation_decision")

    def test_working_memory_session_reset_and_close_behaves_correctly(self) -> None:
        with self.temp_workspace() as workspace_root:
            memory = WorkingMemory(workspace_root)
            memory.start_new_session(session_id="sess-2", goal_id="goal-2")
            closed = memory.close_session()
            self.assertEqual(closed.status, "closed")
            reset = memory.reset_session()
            self.assertEqual(reset.status, "idle")
            self.assertIsNone(reset.session_id)
            self.assertEqual(reset.recent_events, [])
