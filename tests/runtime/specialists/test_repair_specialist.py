from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.specialists import RepairSpecialist  # noqa: E402
from brain.runtime.artifact_paths import artifact_logs_root


class RepairSpecialistTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = artifact_logs_root(PROJECT_ROOT) / "test-specialists"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"repair-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_repair_specialist_can_require_replan(self) -> None:
        with self.temp_workspace() as workspace_root:
            specialist = RepairSpecialist(root=workspace_root)

            decision = specialist.advise(
                goal_id="goal-1",
                result={"ok": False, "progress_score": 0.4},
                simulation_route="replan",
                max_repairs=2,
                current_repairs=1,
            )

            self.assertIsNotNone(decision)
            self.assertTrue(decision.require_replan)

