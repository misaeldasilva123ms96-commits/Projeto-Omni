import io
import json
import shutil
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import RunRecord, RunRegistry, RunStatus  # noqa: E402
from brain.runtime.observability.cli import main as observability_cli_main  # noqa: E402
from brain.runtime.observability.run_reader import read_active_runs, read_run  # noqa: E402


class RunRegistryTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-run-control"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"run-registry-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_register_update_and_read_active_runs(self) -> None:
        with self.temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-1",
                    goal_id="goal-1",
                    session_id="sess-1",
                    status=RunStatus.RUNNING,
                    last_action="execution_started",
                    progress_score=0.0,
                    metadata={"task_id": "task-1"},
                )
            )
            registry.update_status("run-1", RunStatus.PAUSED, "pause_plan", 0.4)

            stored = registry.get("run-1")
            self.assertIsNotNone(stored)
            self.assertEqual(stored.status, RunStatus.PAUSED)
            self.assertEqual(stored.last_action, "pause_plan")
            self.assertAlmostEqual(stored.progress_score, 0.4)
            self.assertEqual(stored.resolution.current_resolution, "paused")
            self.assertEqual(stored.resolution.reason, "operator_pause")

            active_runs = read_active_runs(workspace_root)
            self.assertEqual(len(active_runs), 1)
            self.assertEqual(active_runs[0]["run_id"], "run-1")
            self.assertEqual(active_runs[0]["status"], "paused")

            loaded = read_run(workspace_root, "run-1")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["goal_id"], "goal-1")

    def test_get_all_includes_completed_and_failed_runs(self) -> None:
        with self.temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-complete",
                    goal_id=None,
                    session_id="sess-1",
                    status=RunStatus.COMPLETED,
                    last_action="goal_completed",
                    progress_score=1.0,
                )
            )
            registry.register(
                RunRecord.build(
                    run_id="run-failed",
                    goal_id=None,
                    session_id="sess-1",
                    status=RunStatus.FAILED,
                    last_action="goal_failed",
                    progress_score=0.3,
                )
            )
            all_runs = registry.get_all(limit=10)
            self.assertEqual(len(all_runs), 2)
            self.assertEqual({item.status for item in all_runs}, {RunStatus.COMPLETED, RunStatus.FAILED})
            self.assertEqual(read_active_runs(workspace_root), [])

    def test_cli_runs_returns_valid_json(self) -> None:
        with self.temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-cli",
                    goal_id="goal-cli",
                    session_id="sess-cli",
                    status=RunStatus.AWAITING_APPROVAL,
                    last_action="governance_hold",
                    progress_score=0.2,
                )
            )
            stream = io.StringIO()
            with patch.object(sys, "argv", ["observability-cli", "--root", str(workspace_root), "runs"]):
                with redirect_stdout(stream):
                    result = observability_cli_main()
            self.assertEqual(result, 0)
            payload = json.loads(stream.getvalue())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["runs"][0]["status"], "awaiting_approval")

    def test_resolution_summary_waiting_and_rollback_views(self) -> None:
        with self.temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-waiting",
                    goal_id=None,
                    session_id="sess-1",
                    status=RunStatus.AWAITING_APPROVAL,
                    last_action="governance_hold",
                    progress_score=0.3,
                )
            )
            registry.register(
                RunRecord.build(
                    run_id="run-rollback",
                    goal_id=None,
                    session_id="sess-2",
                    status=RunStatus.FAILED,
                    last_action="engine_promotion_rollback",
                    progress_score=0.5,
                )
            )
            registry.update_status(
                "run-rollback",
                RunStatus.FAILED,
                "engine_promotion_rollback",
                0.5,
                reason="promotion_rollback_threshold",
            )
            summary = registry.get_resolution_summary()
            self.assertEqual(summary["total_runs"], 2)
            self.assertGreaterEqual(summary["resolution_counts"]["hold"], 1)
            self.assertGreaterEqual(summary["reason_counts"]["promotion_rollback_threshold"], 1)
            self.assertIn("timeline_event_counts", summary["governance"])
            self.assertGreaterEqual(sum(summary["governance"]["timeline_event_counts"].values()), 1)
            waiting = registry.get_runs_waiting_operator()
            self.assertEqual(waiting[0].run_id, "run-waiting")
            rollback = registry.get_runs_with_rollback()
            self.assertEqual(rollback[0].run_id, "run-rollback")
            events = registry.recent_resolution_events(limit=10)
            self.assertGreaterEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main()
