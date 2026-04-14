from __future__ import annotations

import io
import json
import shutil
import sys
import threading
import time
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import RunRecord, RunRegistry, RunStatus  # noqa: E402
from brain.runtime.control.cli import main as control_cli_main  # noqa: E402
from brain.runtime.observability.timeline_reader import TimelineReader  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator  # noqa: E402


class ControlCliTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-run-control-cli"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"control-cli-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_pause_resume_and_approve_record_operator_control_events(self) -> None:
        with self.temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-control",
                    goal_id="goal-control",
                    session_id="sess-control",
                    status=RunStatus.AWAITING_APPROVAL,
                    last_action="governance_hold",
                    progress_score=0.2,
                )
            )

            for command in ("pause", "resume", "approve"):
                stream = io.StringIO()
                with patch.object(sys, "argv", ["control-cli", "--root", str(workspace_root), command, "run-control"]):
                    with redirect_stdout(stream):
                        result = control_cli_main()
                self.assertEqual(result, 0)
                payload = json.loads(stream.getvalue())
                self.assertEqual(payload["status"], "ok")
                self.assertEqual(payload["action"], command)

            stored = registry.get("run-control")
            self.assertIsNotNone(stored)
            self.assertEqual(stored.status, RunStatus.RUNNING)
            timeline = TimelineReader(workspace_root).read_recent_events(limit=5)
            operator_events = [event for event in timeline if event.event_type == "operator_control"]
            self.assertEqual(len(operator_events), 3)
            self.assertEqual(operator_events[-1].metadata.get("action"), "approve")
            self.assertEqual(stored.resolution.current_resolution, "approved")
            self.assertEqual(stored.resolution.reason, "operator_approve")

    def test_orchestrator_waits_for_run_to_resume(self) -> None:
        with self.temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-pause",
                    goal_id=None,
                    session_id="sess-pause",
                    status=RunStatus.PAUSED,
                    last_action="operator_pause",
                    progress_score=0.4,
                    metadata={"operator_control_enabled": True},
                )
            )
            orchestrator = object.__new__(BrainOrchestrator)
            orchestrator.run_registry = registry
            updates: list[tuple[str, RunStatus, str, float]] = []

            def update_run_status(*, run_id: str, status: RunStatus, last_action: str, progress_score: float) -> None:
                updates.append((run_id, status, last_action, progress_score))
                registry.update_status(run_id, status, last_action, progress_score)

            orchestrator._update_run_status = update_run_status  # type: ignore[attr-defined]

            def release_run() -> None:
                time.sleep(0.12)
                registry.update_status("run-pause", RunStatus.RUNNING, "operator_resume", 0.4)

            with patch.dict(
                "os.environ",
                {
                    "OMINI_RUN_CONTROL_POLL_SECONDS": "0.05",
                    "OMINI_RUN_CONTROL_MAX_WAIT_SECONDS": "1",
                },
                clear=False,
            ):
                worker = threading.Thread(target=release_run, daemon=True)
                worker.start()
                started = time.monotonic()
                clearance = BrainOrchestrator._await_run_control_clearance(orchestrator, run_id="run-pause")
                elapsed = time.monotonic() - started
                worker.join(timeout=1)

            self.assertEqual(clearance["status"], "running")
            self.assertGreaterEqual(elapsed, 0.1)
            self.assertEqual(updates, [])

    def test_orchestrator_times_out_when_run_stays_paused(self) -> None:
        with self.temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-timeout",
                    goal_id=None,
                    session_id="sess-timeout",
                    status=RunStatus.PAUSED,
                    last_action="operator_pause",
                    progress_score=0.35,
                    metadata={"operator_control_enabled": True},
                )
            )
            orchestrator = object.__new__(BrainOrchestrator)
            orchestrator.run_registry = registry
            updates: list[tuple[str, RunStatus, str, float]] = []

            def update_run_status(*, run_id: str, status: RunStatus, last_action: str, progress_score: float) -> None:
                updates.append((run_id, status, last_action, progress_score))
                registry.update_status(run_id, status, last_action, progress_score)

            orchestrator._update_run_status = update_run_status  # type: ignore[attr-defined]

            with patch.dict(
                "os.environ",
                {
                    "OMINI_RUN_CONTROL_POLL_SECONDS": "0.05",
                    "OMINI_RUN_CONTROL_MAX_WAIT_SECONDS": "0.15",
                },
                clear=False,
            ):
                clearance = BrainOrchestrator._await_run_control_clearance(orchestrator, run_id="run-timeout")

            self.assertEqual(clearance["status"], "failed")
            self.assertEqual(clearance["error"], "operator_timeout")
            self.assertEqual(updates[0][1], RunStatus.FAILED)
            self.assertEqual(updates[0][2], "operator_timeout")

    def test_cli_read_model_commands_return_structured_json(self) -> None:
        with self.temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-observe",
                    goal_id="goal-observe",
                    session_id="sess-observe",
                    status=RunStatus.AWAITING_APPROVAL,
                    last_action="governance_hold",
                    progress_score=0.45,
                )
            )
            registry.update_status(
                "run-observe",
                RunStatus.FAILED,
                "engine_promotion_rollback",
                0.45,
                reason="promotion_rollback_threshold",
            )
            for argv in (
                ["control-cli", "--root", str(workspace_root), "inspect_run", "run-observe"],
                ["control-cli", "--root", str(workspace_root), "list_runs", "--limit", "10"],
                ["control-cli", "--root", str(workspace_root), "resolution_summary"],
                ["control-cli", "--root", str(workspace_root), "runs_waiting_operator"],
                ["control-cli", "--root", str(workspace_root), "runs_with_rollback"],
            ):
                stream = io.StringIO()
                with patch.object(sys, "argv", argv):
                    with redirect_stdout(stream):
                        result = control_cli_main()
                self.assertEqual(result, 0)
                payload = json.loads(stream.getvalue())
                self.assertEqual(payload["status"], "ok")


if __name__ == "__main__":
    unittest.main()
