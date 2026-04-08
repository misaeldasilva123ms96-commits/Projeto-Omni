from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.service_contracts import (  # noqa: E402
    build_task_envelope,
    build_task_status,
    validate_start_task_request,
)


class ServiceContractsTest(unittest.TestCase):
    def test_validate_start_task_request_returns_normalized_fields(self) -> None:
        payload = validate_start_task_request(user_id=" user ", session_id=" s1 ", message=" hi ")
        self.assertEqual(payload, {"user_id": "user", "session_id": "s1", "message": "hi"})

    def test_validate_start_task_request_rejects_missing_fields(self) -> None:
        with self.assertRaises(ValueError):
            validate_start_task_request(user_id="", session_id="s1", message="hello")
        with self.assertRaises(ValueError):
            validate_start_task_request(user_id="u", session_id="", message="hello")
        with self.assertRaises(ValueError):
            validate_start_task_request(user_id="u", session_id="s1", message="")

    def test_build_task_envelope_exposes_operator_links(self) -> None:
        envelope = build_task_envelope(user_id="u", session_id="s", task_id="t", response="ok")
        self.assertEqual(envelope["status"], "completed")
        self.assertIn("inspect_execution_state", envelope["links"])
        self.assertIn("inspect_workspace_state", envelope["links"])

    def test_build_task_status_keeps_runtime_metadata(self) -> None:
        status = build_task_status(
            run_id="r1",
            checkpoint={
                "task_id": "t1",
                "session_id": "s1",
                "status": "blocked",
                "next_step_index": 2,
                "total_actions": 5,
                "plan_hierarchy": {"root_goal_id": "goal:root"},
                "branch_state": {"branches": []},
                "execution_tree": {"nodes": []},
                "repository_analysis": {"root": "repo"},
                "engineering_data": {"milestone_state": {"completed_milestones": 1}},
                "reflection_summary": {"summary": "x"},
            },
        )
        self.assertEqual(status["status"], "blocked")
        self.assertTrue(status["reflection_available"])
        self.assertIn("inspect_patch_sets", status["operator_links"])


if __name__ == "__main__":
    unittest.main()
