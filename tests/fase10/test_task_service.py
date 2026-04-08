from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.task_service import TaskService  # noqa: E402


class _FakeCheckpointStore:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def load(self, run_id: str) -> dict[str, object]:
        return {**self.payload, "loaded_run_id": run_id}


class _FakeOrchestrator:
    def __init__(self) -> None:
        self.checkpoint_store = _FakeCheckpointStore(
            {
                "task_id": "task-u-s",
                "session_id": "s",
                "status": "completed",
                "plan_hierarchy": {"root_goal_id": "goal:root"},
                "branch_state": {"branches": []},
                "execution_tree": {"nodes": []},
                "repository_analysis": {"root": "repo"},
                "engineering_data": {
                    "milestone_state": {"completed_milestones": 1},
                    "patch_sets": [{"patch_set_id": "ps-1"}],
                    "verification_summary": {"ok": True},
                    "pr_summary": {"title": "PR"},
                    "patch_history": [{"file_path": "a.py"}],
                    "debug_iterations": [{"iteration": 1}],
                    "workspace_state": {"file_count": 1},
                },
                "simulation_summary": {"invoked": True},
                "policy_summary": [{"decision": "allow"}],
                "cooperative_plan": {"mode": "cooperative"},
                "strategy_suggestions": [{"strategy_type": "safe"}],
                "negotiation_summary": {"final_decision": "proceed"},
                "supervision": {"alerts": []},
            }
        )
        self.paths = type("Paths", (), {"root": PROJECT_ROOT})()

    def run(self, message: str) -> str:
        return f"echo:{message}"

    def resume_run(self, run_id: str) -> dict[str, object]:
        return {"status": "completed", "run_id": run_id}


class TaskServiceTest(unittest.TestCase):
    def build_service(self) -> TaskService:
        service = object.__new__(TaskService)
        service.orchestrator = _FakeOrchestrator()
        return service

    def test_execute_task_returns_structured_envelope(self) -> None:
        service = self.build_service()
        payload = service.execute_task(user_id="u", session_id="s", message="hello")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["task_id"], "task-u-s")
        self.assertIn("inspect_run_intelligence", payload["links"])

    def test_execute_task_rejects_invalid_input(self) -> None:
        service = self.build_service()
        with self.assertRaises(ValueError):
            service.execute_task(user_id="", session_id="s", message="hello")

    def test_inspection_views_return_expected_shapes(self) -> None:
        service = self.build_service()
        self.assertIn("milestone_state", service.inspect_plan_hierarchy(run_id="r1"))
        self.assertIn("patch_sets", service.inspect_patch_sets(run_id="r1"))
        self.assertIn("verification_summary", service.inspect_verification(run_id="r1"))
        self.assertIn("pr_summary", service.inspect_pr_summary(run_id="r1"))
        self.assertIn("workspace_state", service.inspect_workspace_state(run_id="r1"))
        status = service.task_status(run_id="r1")
        self.assertEqual(status["status"], "completed")


if __name__ == "__main__":
    unittest.main()
