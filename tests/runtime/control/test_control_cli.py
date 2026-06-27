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
from brain.memory.memory_facade import MemoryFacade as StructuredMemoryFacade  # noqa: E402
from brain.memory.memory_models import AutonomySessionStateRecord  # noqa: E402
from brain.runtime.observability.timeline_reader import TimelineReader  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator  # noqa: E402
from brain.runtime.orchestrator_services import GovernanceIntegrationService  # noqa: E402

_CLEANUP_RESULT_FIELDS = {
    "operation_id",
    "operation_type",
    "attempted",
    "supported",
    "dry_run",
    "sqlite_path_fingerprint",
    "sqlite_path_present",
    "would_delete_count",
    "deleted_count",
    "degraded",
    "error_category",
    "attempted_at",
    "sqlite_enabled",
    "sqlite_connected",
    "cutoff_time",
}


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

            class TrackingRunLifecycle:
                __slots__ = ("_registry", "_updates")

                def __init__(self, reg: RunRegistry, upd: list[tuple[str, RunStatus, str, float]]) -> None:
                    self._registry = reg
                    self._updates = upd

                def update_run_status(self, *, run_id: str, status: RunStatus, last_action: str, progress_score: float) -> None:
                    self._updates.append((run_id, status, last_action, progress_score))
                    self._registry.update_status(run_id, status, last_action, progress_score)

            run_lifecycle = TrackingRunLifecycle(registry, updates)
            orchestrator._governance_integration = GovernanceIntegrationService(
                run_registry=registry,
                get_controller=lambda: None,
                run_lifecycle=run_lifecycle,  # type: ignore[arg-type]
            )

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

            class TrackingRunLifecycle:
                __slots__ = ("_registry", "_updates")

                def __init__(self, reg: RunRegistry, upd: list[tuple[str, RunStatus, str, float]]) -> None:
                    self._registry = reg
                    self._updates = upd

                def update_run_status(self, *, run_id: str, status: RunStatus, last_action: str, progress_score: float) -> None:
                    self._updates.append((run_id, status, last_action, progress_score))
                    self._registry.update_status(run_id, status, last_action, progress_score)

            run_lifecycle = TrackingRunLifecycle(registry, updates)
            orchestrator._governance_integration = GovernanceIntegrationService(
                run_registry=registry,
                get_controller=lambda: None,
                run_lifecycle=run_lifecycle,  # type: ignore[arg-type]
            )

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
                ["control-cli", "--root", str(workspace_root), "governance_operational"],
                ["control-cli", "--root", str(workspace_root), "governance_snapshot"],
                ["control-cli", "--root", str(workspace_root), "governance_attention"],
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
                if argv[3] == "inspect_run":
                    run_payload = payload.get("run")
                    self.assertIsInstance(run_payload, dict)
                    self.assertIn("governance_timeline", run_payload)
                    self.assertGreaterEqual(len(run_payload["governance_timeline"]), 1)
                if argv[3] in {"governance_operational", "governance_snapshot"}:
                    gov = payload.get("governance")
                    self.assertIsInstance(gov, dict)
                    self.assertIn("operator_attention_runs", gov)
                    self.assertIn("summary", gov)
                if argv[3] == "governance_attention":
                    self.assertIsInstance(payload.get("operator_attention_runs"), list)

    def test_pause_rejects_invalid_run_id_without_mutating_registry(self) -> None:
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
            stream = io.StringIO()
            with patch.object(
                sys,
                "argv",
                ["control-cli", "--root", str(workspace_root), "pause", "bad/run"],
            ):
                with redirect_stdout(stream):
                    result = control_cli_main()
            self.assertEqual(result, 0)
            payload = json.loads(stream.getvalue())
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["error"], "invalid_run_id")
            stored = registry.get("run-control")
            self.assertIsNotNone(stored)
            self.assertEqual(stored.status, RunStatus.AWAITING_APPROVAL)

    def test_cleanup_autonomy_session_states_noops_when_sqlite_disabled(self) -> None:
        with self.temp_workspace() as workspace_root:
            sqlite_path = workspace_root / "memory.sqlite"
            jsonl_path = workspace_root / "audit.jsonl"
            stream = io.StringIO()
            with patch.dict("os.environ", {"OMINI_ENABLE_SQLITE_MEMORY": "false"}, clear=False):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "control-cli",
                        "--root",
                        str(workspace_root),
                        "cleanup_autonomy_session_states",
                        "--sqlite-path",
                        str(sqlite_path),
                        "--jsonl-path",
                        str(jsonl_path),
                        "--now",
                        "2026-06-27T00:00:00+00:00",
                    ],
                ):
                    with redirect_stdout(stream):
                        result = control_cli_main()

            payload = json.loads(stream.getvalue())
            cleanup = payload["cleanup"]
            self.assertEqual(result, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertTrue(cleanup["attempted"])
            self.assertFalse(cleanup["supported"])
            self.assertFalse(cleanup["dry_run"])
            self.assertEqual(cleanup["would_delete_count"], 0)
            self.assertEqual(cleanup["deleted_count"], 0)
            self.assertFalse(cleanup["degraded"])
            self.assertEqual(cleanup["error_category"], "")
            self.assertFalse(cleanup["sqlite_enabled"])
            self.assertFalse(cleanup["sqlite_connected"])
            self.assertTrue(cleanup["sqlite_path_present"])
            self.assertTrue(cleanup["sqlite_path_fingerprint"].startswith("sha256:"))
            self.assertEqual(cleanup["operation_type"], "cleanup_autonomy_session_states")
            self.assertTrue(cleanup["operation_id"].startswith("cleanup-"))
            self.assertEqual(cleanup["cutoff_time"], "2026-06-27T00:00:00+00:00")
            self.assertNotIn(str(sqlite_path), str(payload))
            self.assertNotIn(sqlite_path.name, str(payload))

    def test_cleanup_autonomy_session_states_deletes_only_expired_rows(self) -> None:
        with self.temp_workspace() as workspace_root:
            sqlite_path = workspace_root / "memory.sqlite"
            jsonl_path = workspace_root / "audit.jsonl"
            facade = StructuredMemoryFacade(
                enable_sqlite=True,
                sqlite_path=sqlite_path,
                jsonl_path=jsonl_path,
            )
            facade.initialize()
            try:
                facade.record_autonomy_session_state(
                    AutonomySessionStateRecord(
                        session_id="old",
                        last_error_type="timeout",
                        current_error_count=1,
                        distinct_error_count=1,
                        distinct_error_types=["timeout"],
                        updated_at="2026-06-27T00:00:00+00:00",
                        expires_at="2026-06-01T00:00:00+00:00",
                    )
                )
                facade.record_autonomy_session_state(
                    AutonomySessionStateRecord(
                        session_id="fresh",
                        last_error_type="timeout",
                        current_error_count=1,
                        distinct_error_count=1,
                        distinct_error_types=["timeout"],
                        updated_at="2026-06-27T00:00:00+00:00",
                        expires_at="2999-01-01T00:00:00+00:00",
                    )
                )
            finally:
                facade.close()

            stream = io.StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "control-cli",
                    "--root",
                    str(workspace_root),
                    "cleanup_autonomy_session_states",
                    "--enable-sqlite",
                    "--sqlite-path",
                    str(sqlite_path),
                    "--jsonl-path",
                    str(jsonl_path),
                    "--now",
                    "2026-06-27T00:00:00+00:00",
                ],
            ):
                with redirect_stdout(stream):
                    result = control_cli_main()

            payload = json.loads(stream.getvalue())
            cleanup = payload["cleanup"]
            self.assertEqual(result, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(set(cleanup), _CLEANUP_RESULT_FIELDS)
            self.assertTrue(cleanup["supported"])
            self.assertFalse(cleanup["dry_run"])
            self.assertEqual(cleanup["would_delete_count"], 0)
            self.assertEqual(cleanup["deleted_count"], 1)
            self.assertFalse(cleanup["degraded"])
            self.assertTrue(cleanup["sqlite_enabled"])
            self.assertTrue(cleanup["sqlite_connected"])
            self.assertTrue(cleanup["sqlite_path_present"])
            self.assertTrue(cleanup["sqlite_path_fingerprint"].startswith("sha256:"))
            self.assertEqual(cleanup["operation_type"], "cleanup_autonomy_session_states")
            self.assertTrue(cleanup["operation_id"].startswith("cleanup-"))
            self.assertNotIn("session_id", str(cleanup))
            self.assertNotIn("raw_prompt", str(cleanup))
            self.assertNotIn(str(sqlite_path), str(payload))
            self.assertNotIn(sqlite_path.name, str(payload))

            verifier = StructuredMemoryFacade(enable_sqlite=True, sqlite_path=sqlite_path, jsonl_path=jsonl_path)
            verifier.initialize()
            try:
                self.assertIsNone(verifier.get_autonomy_session_state("old"))
                self.assertIsNotNone(verifier.get_autonomy_session_state("fresh"))
            finally:
                verifier.close()

    def test_cleanup_autonomy_session_states_dry_run_counts_without_deleting(self) -> None:
        with self.temp_workspace() as workspace_root:
            sqlite_path = workspace_root / "memory.sqlite"
            jsonl_path = workspace_root / "audit.jsonl"
            facade = StructuredMemoryFacade(
                enable_sqlite=True,
                sqlite_path=sqlite_path,
                jsonl_path=jsonl_path,
            )
            facade.initialize()
            try:
                facade.record_autonomy_session_state(
                    AutonomySessionStateRecord(
                        session_id="old",
                        last_error_type="timeout",
                        current_error_count=1,
                        distinct_error_count=1,
                        distinct_error_types=["timeout"],
                        updated_at="2026-06-27T00:00:00+00:00",
                        expires_at="2026-06-01T00:00:00+00:00",
                    )
                )
                facade.record_autonomy_session_state(
                    AutonomySessionStateRecord(
                        session_id="fresh",
                        last_error_type="timeout",
                        current_error_count=1,
                        distinct_error_count=1,
                        distinct_error_types=["timeout"],
                        updated_at="2026-06-27T00:00:00+00:00",
                        expires_at="2999-01-01T00:00:00+00:00",
                    )
                )
            finally:
                facade.close()

            stream = io.StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "control-cli",
                    "--root",
                    str(workspace_root),
                    "cleanup_autonomy_session_states",
                    "--dry-run",
                    "--enable-sqlite",
                    "--sqlite-path",
                    str(sqlite_path),
                    "--jsonl-path",
                    str(jsonl_path),
                    "--now",
                    "2026-06-27T00:00:00+00:00",
                ],
            ):
                with redirect_stdout(stream):
                    result = control_cli_main()

            payload = json.loads(stream.getvalue())
            cleanup = payload["cleanup"]
            self.assertEqual(result, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(set(cleanup), _CLEANUP_RESULT_FIELDS)
            self.assertTrue(cleanup["supported"])
            self.assertTrue(cleanup["dry_run"])
            self.assertEqual(cleanup["would_delete_count"], 1)
            self.assertEqual(cleanup["deleted_count"], 0)
            self.assertFalse(cleanup["degraded"])
            self.assertEqual(cleanup["cutoff_time"], "2026-06-27T00:00:00+00:00")
            self.assertTrue(cleanup["sqlite_path_present"])
            self.assertTrue(cleanup["sqlite_path_fingerprint"].startswith("sha256:"))
            self.assertEqual(cleanup["operation_type"], "cleanup_autonomy_session_states")
            self.assertTrue(cleanup["operation_id"].startswith("cleanup-"))
            self.assertNotIn("session_id", str(cleanup))
            self.assertNotIn("old", str(cleanup))
            self.assertNotIn(str(sqlite_path), str(payload))
            self.assertNotIn(sqlite_path.name, str(payload))

            verifier = StructuredMemoryFacade(enable_sqlite=True, sqlite_path=sqlite_path, jsonl_path=jsonl_path)
            verifier.initialize()
            try:
                self.assertEqual(verifier._sqlite.table_count("autonomy_session_states"), 2)  # type: ignore[union-attr]
                self.assertIsNotNone(verifier.get_autonomy_session_state("fresh"))
            finally:
                verifier.close()

    def test_cleanup_autonomy_session_states_failure_degrades_safely(self) -> None:
        class FailingFacade:
            sqlite_enabled = True
            is_sqlite_connected = True

            def __init__(self, **_kwargs: object) -> None:
                pass

            def initialize(self) -> None:
                pass

            def close(self) -> None:
                pass

            def cleanup_expired_autonomy_session_states(self, now: str | None = None) -> int:
                raise RuntimeError("cleanup failed with sk-test-secret")

            def get_autonomy_session_state_lifecycle_diagnostics(self, now: str | None = None) -> dict[str, object]:
                return {
                    "cleanup_degraded": True,
                    "cleanup_last_error_category": "Bearer sk-test-secret",
                    "last_cleanup_attempted_at": "2026-06-27T00:00:00+00:00",
                }

        with self.temp_workspace() as workspace_root:
            stream = io.StringIO()
            with patch("brain.runtime.control.cli.StructuredMemoryFacade", FailingFacade):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "control-cli",
                        "--root",
                        str(workspace_root),
                        "cleanup_autonomy_session_states",
                        "--enable-sqlite",
                    ],
                ):
                    with redirect_stdout(stream):
                        result = control_cli_main()

            payload = json.loads(stream.getvalue())
            cleanup = payload["cleanup"]
            self.assertEqual(result, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertTrue(cleanup["attempted"])
            self.assertTrue(cleanup["supported"])
            self.assertFalse(cleanup["dry_run"])
            self.assertEqual(cleanup["would_delete_count"], 0)
            self.assertEqual(cleanup["deleted_count"], 0)
            self.assertTrue(cleanup["degraded"])
            self.assertEqual(cleanup["error_category"], "cleanup_failed")
            self.assertNotIn("sk-test-secret", str(payload))
            self.assertNotIn("Traceback", str(payload))

    def test_cleanup_autonomy_session_states_dry_run_path_fingerprint_is_stable(self) -> None:
        with self.temp_workspace() as workspace_root:
            sqlite_path = workspace_root / "memory.sqlite"
            jsonl_path = workspace_root / "audit.jsonl"
            outputs: list[dict[str, object]] = []

            for _ in range(2):
                stream = io.StringIO()
                with patch.object(
                    sys,
                    "argv",
                    [
                        "control-cli",
                        "--root",
                        str(workspace_root),
                        "cleanup_autonomy_session_states",
                        "--dry-run",
                        "--enable-sqlite",
                        "--sqlite-path",
                        str(sqlite_path),
                        "--jsonl-path",
                        str(jsonl_path),
                        "--now",
                        "2026-06-27T00:00:00+00:00",
                    ],
                ):
                    with redirect_stdout(stream):
                        result = control_cli_main()

                self.assertEqual(result, 0)
                payload = json.loads(stream.getvalue())
                outputs.append(payload["cleanup"])

            first, second = outputs
            self.assertNotEqual(first["operation_id"], second["operation_id"])
            self.assertEqual(first["sqlite_path_fingerprint"], second["sqlite_path_fingerprint"])
            self.assertTrue(str(first["sqlite_path_fingerprint"]).startswith("sha256:"))
            self.assertNotIn(str(sqlite_path), str(first))
            self.assertNotIn(sqlite_path.name, str(first))


if __name__ == "__main__":
    unittest.main()
