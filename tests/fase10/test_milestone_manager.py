from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.milestone_manager import MilestoneManager  # noqa: E402


class MilestoneManagerTest(unittest.TestCase):
    def test_initialize_state_builds_expected_shape(self) -> None:
        manager = MilestoneManager(
            {
                "milestone_tree": {
                    "root_milestone_id": "m-root",
                    "milestones": [
                        {"milestone_id": "m-1", "title": "Analyze", "step_ids": ["s1"]},
                        {"milestone_id": "m-2", "title": "Verify", "step_ids": ["s2"], "progress": 10},
                    ],
                }
            }
        )

        state = manager.initialize_state()
        self.assertEqual(state["root_milestone_id"], "m-root")
        self.assertEqual(len(state["milestones"]), 2)
        self.assertEqual(state["milestones"][0]["state"], "pending")

    def test_update_from_step_results_marks_completed_and_blocked(self) -> None:
        manager = MilestoneManager()
        state = {
            "milestones": [
                {"milestone_id": "m-1", "step_ids": ["s1"], "state": "pending", "blockers": [], "progress": 0},
                {"milestone_id": "m-2", "step_ids": ["s2"], "state": "pending", "blockers": [], "progress": 0},
            ]
        }

        updated = manager.update_from_step_results(
            state,
            [
                {"milestone_id": "m-1", "ok": True},
                {"milestone_id": "m-2", "ok": False, "error_payload": {"kind": "test_failed"}},
            ],
        )
        self.assertEqual(updated["completed_milestones"], 1)
        self.assertEqual(updated["blocked_milestones"], 1)
        blocked = next(item for item in updated["milestones"] if item["milestone_id"] == "m-2")
        self.assertEqual(blocked["state"], "blocked")
        self.assertIn("test_failed", blocked["blockers"])

    def test_update_with_empty_state_is_safe(self) -> None:
        manager = MilestoneManager()
        self.assertEqual(manager.update_from_step_results({}, []), {"milestones": []})


if __name__ == "__main__":
    unittest.main()
