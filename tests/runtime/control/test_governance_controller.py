import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control.governance_controller import GovernanceResolutionController  # noqa: E402
from brain.runtime.control.governance_taxonomy import GovernanceReason  # noqa: E402
from brain.runtime.control.run_registry import RunRegistry, RunStatus  # noqa: E402
from brain.runtime.observability.run_reader import read_run  # noqa: E402


class GovernanceResolutionControllerTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-governance-controller"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"ctrl-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_preview_matches_applied_transition_governance(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            ctrl = GovernanceResolutionController(reg)
            ctrl.register_run_start(
                run_id="r1",
                goal_id=None,
                session_id="s1",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
            rec = reg.get("r1")
            self.assertIsNotNone(rec)
            preview = ctrl.preview_transition(
                rec,
                status=RunStatus.PAUSED,
                last_action="operator_pause",
                reason=GovernanceReason.OPERATOR_PAUSE.value,
                decision_source="operator_cli",
            )
            updated = ctrl.transition_run(
                run_id="r1",
                status=RunStatus.PAUSED,
                last_action="operator_pause",
                progress=0.3,
                reason=GovernanceReason.OPERATOR_PAUSE.value,
                decision_source="operator_cli",
                operator_id="op-1",
            )
            self.assertIsNotNone(updated)
            self.assertEqual(preview["event_type"], "pause")
            self.assertEqual(updated.resolution.reason, GovernanceReason.OPERATOR_PAUSE.value)
            last_tl = updated.governance_timeline[-1]
            self.assertEqual(last_tl["event_type"], preview["event_type"])
            self.assertEqual(last_tl["governance"]["reason"], preview["governance"]["reason"])

    def test_register_run_start_single_timeline_start_no_duplicate_resolution_row(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            ctrl = GovernanceResolutionController(reg)
            ctrl.register_run_start(
                run_id="r-start",
                goal_id=None,
                session_id="s1",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
            rec = reg.get("r-start")
            self.assertIsNotNone(rec)
            self.assertEqual(len(rec.resolution_history), 0)
            self.assertEqual(len(rec.governance_timeline), 1)
            self.assertEqual(rec.governance_timeline[0]["event_type"], "start")

    def test_operator_actions_via_controller(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            ctrl = GovernanceResolutionController(reg)
            ctrl.register_run_start(
                run_id="r-op",
                goal_id=None,
                session_id="s1",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
            ctrl.handle_operator_action(run_id="r-op", action="pause", progress=0.2, decision_source="operator_cli")
            ctrl.handle_operator_action(run_id="r-op", action="approve", progress=0.5, decision_source="operator_cli")
            ctrl.handle_operator_action(run_id="r-op", action="resume", progress=0.6, decision_source="operator_cli")
            types = [e.get("event_type") for e in reg.get("r-op").governance_timeline]
            self.assertIn("pause", types)
            self.assertIn("approve", types)
            self.assertIn("resume", types)

    def test_rollback_and_timeout_handlers(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            ctrl = GovernanceResolutionController(reg)
            ctrl.register_run_start(
                run_id="r-rb",
                goal_id=None,
                session_id="s1",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
            ctrl.handle_rollback(run_id="r-rb", progress=0.4)
            self.assertIn("rollback", [e.get("event_type") for e in reg.get("r-rb").governance_timeline])

            ctrl.register_run_start(
                run_id="r-to",
                goal_id=None,
                session_id="s1",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
            ctrl.handle_timeout(run_id="r-to", progress=0.1)
            self.assertIn("timeout", [e.get("event_type") for e in reg.get("r-to").governance_timeline])

    def test_completion_and_failure_coherent_with_timeline(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            ctrl = GovernanceResolutionController(reg)
            ctrl.register_run_start(
                run_id="r-ok",
                goal_id=None,
                session_id="s1",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
            ctrl.handle_completion(run_id="r-ok", last_action="goal_completed", progress=1.0)
            self.assertEqual(reg.get("r-ok").status, RunStatus.COMPLETED)
            self.assertIn("complete", [e.get("event_type") for e in reg.get("r-ok").governance_timeline])

            ctrl.register_run_start(
                run_id="r-bad",
                goal_id=None,
                session_id="s1",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
            ctrl.handle_failure(run_id="r-bad", last_action="goal_failed", progress=0.2, reason=None)
            self.assertEqual(reg.get("r-bad").status, RunStatus.FAILED)
            self.assertIn("fail", [e.get("event_type") for e in reg.get("r-bad").governance_timeline])

    def test_read_path_legacy_compatible_after_flush(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            ctrl = GovernanceResolutionController(reg)
            ctrl.register_run_start(
                run_id="r-legacy",
                goal_id=None,
                session_id="s1",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
            ctrl.transition_run(
                run_id="r-legacy",
                status=RunStatus.PAUSED,
                last_action="pause_plan",
                progress=0.3,
            )
            reg.reload_from_disk()
            payload = read_run(root, "r-legacy")
            self.assertIsNotNone(payload)
            self.assertIn("governance_timeline", payload)
            self.assertGreaterEqual(len(payload["governance_timeline"]), 2)
            self.assertIn("governance", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
