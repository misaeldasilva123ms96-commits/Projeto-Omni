from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.specialists import ExecutorSpecialist  # noqa: E402


class ExecutorSpecialistTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-specialists"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"executor-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_executor_delegates_execution_callback(self) -> None:
        with self.temp_workspace() as workspace_root:
            specialist = ExecutorSpecialist(root=workspace_root)
            calls = {"count": 0}

            def callback():
                calls["count"] += 1
                return {"ok": True, "execution_receipt": {"receipt_id": "receipt-1"}}

            decision = specialist.execute(
                goal_id="goal-1",
                simulation_id="simulation-1",
                action={"step_id": "step-1", "selected_tool": "verification_runner"},
                execute_callback=callback,
            )

            self.assertEqual(calls["count"], 1)
            self.assertTrue(decision.delegated_execution)
            self.assertEqual(decision.evidence_ids, ["receipt-1"])
