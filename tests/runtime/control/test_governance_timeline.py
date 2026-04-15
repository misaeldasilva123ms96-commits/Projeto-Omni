import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control.governance_taxonomy import GovernanceReason  # noqa: E402
from brain.runtime.control.governance_timeline import (  # noqa: E402
    GovernanceTimelineEventType,
    build_governance_timeline_event,
    infer_event_type_from_transition,
    synthesize_timeline_from_legacy,
    timeline_event_from_resolution_dict,
)
from brain.runtime.control.run_registry import RunRecord, RunRegistry, RunStatus  # noqa: E402
from brain.runtime.observability.observability_reader import ObservabilityReader  # noqa: E402
from brain.runtime.observability.run_reader import (  # noqa: E402
    read_latest_governance_event_by_run,
    read_recent_governance_timeline_events,
    read_run,
)


class GovernanceTimelineTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-governance-timeline"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"timeline-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_timeline_event_serializes_and_includes_governance(self) -> None:
        ev = build_governance_timeline_event(
            event_type=GovernanceTimelineEventType.PAUSE.value,
            timestamp="2026-04-14T12:00:00+00:00",
            current_resolution="paused",
            previous_resolution="running",
            reason=GovernanceReason.OPERATOR_PAUSE.value,
            decision_source="operator_cli",
            run_status="paused",
            operator_id="op-1",
        )
        raw = json.dumps(ev)
        loaded = json.loads(raw)
        self.assertEqual(loaded["event_type"], "pause")
        self.assertEqual(loaded["resolution"], "paused")
        self.assertIn("governance", loaded)
        self.assertEqual(loaded["governance"]["reason"], GovernanceReason.OPERATOR_PAUSE.value)

    def test_infer_event_type_normalization_consistency(self) -> None:
        cases: list[tuple[str, str, str, str, str]] = [
            (GovernanceReason.OPERATOR_PAUSE.value, "running", "paused", "running", "pause"),
            (GovernanceReason.OPERATOR_RESUME.value, "running", "resumed", "paused", "resume"),
            (GovernanceReason.OPERATOR_APPROVE.value, "running", "approved", "hold", "approve"),
            (GovernanceReason.GOVERNANCE_HOLD.value, "awaiting_approval", "hold", "running", "hold"),
            (GovernanceReason.PROMOTION_ROLLBACK_THRESHOLD.value, "failed", "rollback", "running", "rollback"),
            (GovernanceReason.TIMEOUT.value, "failed", "running", "running", "timeout"),
            (GovernanceReason.POLICY_BLOCK.value, "running", "blocked", "running", "blocked"),
            (GovernanceReason.COMPLETED.value, "completed", "completed", "running", "complete"),
            (GovernanceReason.FAILED.value, "failed", "failed", "running", "fail"),
        ]
        for reason, run_status, cur, prev, expected in cases:
            got = infer_event_type_from_transition(
                reason=reason,
                run_status=run_status,
                current_resolution=cur,
                previous_resolution=prev,
            )
            self.assertEqual(got, expected, msg=f"reason={reason} status={run_status} cur={cur}")

    def test_registry_transitions_append_timeline(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            reg.register(
                RunRecord.build(
                    run_id="r1",
                    goal_id="g1",
                    session_id="s1",
                    status=RunStatus.RUNNING,
                    last_action="execution_started",
                    progress_score=0.0,
                )
            )
            reg.update_status("r1", RunStatus.PAUSED, "pause_plan", 0.2, reason="operator_pause")
            rec = reg.get("r1")
            self.assertIsNotNone(rec)
            types = [e.get("event_type") for e in rec.governance_timeline]
            self.assertIn("start", types)
            self.assertIn("pause", types)

    def test_operator_pause_approve_resume_events(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            reg.register(
                RunRecord.build(
                    run_id="r-op",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.RUNNING,
                    last_action="execution_started",
                    progress_score=0.0,
                )
            )
            reg.update_status("r-op", RunStatus.PAUSED, "operator_pause", 0.1, reason="operator_pause")
            reg.update_status("r-op", RunStatus.RUNNING, "operator_approve", 0.5, reason="operator_approve")
            reg.update_status("r-op", RunStatus.PAUSED, "operator_pause", 0.5, reason="operator_pause")
            reg.update_status("r-op", RunStatus.RUNNING, "operator_resume", 0.6, reason="operator_resume")
            types = [e.get("event_type") for e in reg.get("r-op").governance_timeline]
            self.assertGreaterEqual(types.count("pause"), 2)
            self.assertIn("approve", types)
            self.assertIn("resume", types)

    def test_rollback_and_timeout_visible(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            reg.register(
                RunRecord.build(
                    run_id="r-term",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.RUNNING,
                    last_action="execution_started",
                    progress_score=0.0,
                )
            )
            reg.update_status(
                "r-term",
                RunStatus.FAILED,
                "engine_promotion_rollback",
                0.4,
                reason="promotion_rollback_threshold",
            )
            reg.register(
                RunRecord.build(
                    run_id="r-to",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.RUNNING,
                    last_action="execution_started",
                    progress_score=0.0,
                )
            )
            reg.update_status("r-to", RunStatus.FAILED, "operator_timeout", 0.2, reason="timeout")
            self.assertIn("rollback", [e.get("event_type") for e in reg.get("r-term").governance_timeline])
            self.assertIn("timeout", [e.get("event_type") for e in reg.get("r-to").governance_timeline])

    def test_legacy_record_without_timeline_is_readable(self) -> None:
        with self.temp_workspace() as root:
            control_dir = root / ".logs" / "fusion-runtime" / "control"
            control_dir.mkdir(parents=True, exist_ok=True)
            legacy = {
                "runs": {
                    "legacy-1": {
                        "run_id": "legacy-1",
                        "goal_id": None,
                        "session_id": "s-legacy",
                        "status": "running",
                        "started_at": "2026-01-01T00:00:00+00:00",
                        "updated_at": "2026-01-02T00:00:00+00:00",
                        "last_action": "execution_started",
                        "progress_score": 0.1,
                        "metadata": {},
                        "resolution": {
                            "current_resolution": "running",
                            "previous_resolution": "running",
                            "reason": "running",
                            "decision_source": "runtime_orchestrator",
                            "timestamp": "2026-01-02T00:00:00+00:00",
                        },
                        "resolution_history": [
                            {
                                "current_resolution": "running",
                                "previous_resolution": "running",
                                "reason": "running",
                                "decision_source": "runtime_orchestrator",
                                "timestamp": "2026-01-01T00:00:00+00:00",
                            },
                            {
                                "current_resolution": "paused",
                                "previous_resolution": "running",
                                "reason": "operator_pause",
                                "decision_source": "operator_cli",
                                "timestamp": "2026-01-02T00:00:00+00:00",
                            },
                        ],
                    }
                }
            }
            (control_dir / "run_registry.json").write_text(
                json.dumps(legacy, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            reg = RunRegistry(root)
            rec = reg.get("legacy-1")
            self.assertIsNotNone(rec)
            self.assertGreaterEqual(len(rec.governance_timeline), 1)
            loaded = read_run(root, "legacy-1")
            self.assertIsNotNone(loaded)
            self.assertGreaterEqual(len(loaded.get("governance_timeline", [])), 1)

    def test_synthesize_from_legacy_matches_resolution_rows(self) -> None:
        hist = [
            {
                "current_resolution": "running",
                "previous_resolution": "running",
                "reason": "running",
                "decision_source": "runtime_orchestrator",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
            {
                "current_resolution": "paused",
                "previous_resolution": "running",
                "reason": "operator_pause",
                "decision_source": "operator_cli",
                "timestamp": "2026-01-02T00:00:00+00:00",
            },
        ]
        tl = synthesize_timeline_from_legacy(
            resolution_history=hist,
            resolution=None,
            run_status="paused",
        )
        self.assertEqual(tl[0]["event_type"], "start")
        self.assertEqual(tl[1]["event_type"], "pause")

    def test_timeline_event_from_resolution_dict_preserves_row(self) -> None:
        row = {
            "current_resolution": "rollback",
            "previous_resolution": "running",
            "reason": "promotion_rollback_threshold",
            "decision_source": "runtime_orchestrator",
            "timestamp": "2026-04-01T00:00:00+00:00",
        }
        ev = timeline_event_from_resolution_dict(row, run_status="failed")
        self.assertEqual(ev["event_type"], "rollback")

    def test_observability_recent_governance_events_and_summary_counts(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            reg.register(
                RunRecord.build(
                    run_id="obs-run",
                    goal_id=None,
                    session_id="s-obs",
                    status=RunStatus.RUNNING,
                    last_action="execution_started",
                    progress_score=0.0,
                )
            )
            reg.update_status("obs-run", RunStatus.PAUSED, "operator_pause", 0.2, reason="operator_pause")
            recent = read_recent_governance_timeline_events(root, limit=10)
            self.assertGreaterEqual(len(recent), 1)
            self.assertTrue(any(e.get("run_id") == "obs-run" for e in recent))
            by_run = read_latest_governance_event_by_run(root)
            self.assertIn("obs-run", by_run)
            snap = ObservabilityReader(root).snapshot()
            self.assertGreaterEqual(len(snap.recent_governance_timeline_events), 1)
            self.assertIn("obs-run", snap.latest_governance_event_by_run)
            summary = snap.governance_summary
            self.assertIn("timeline_event_counts", summary.get("governance", {}))


if __name__ == "__main__":
    unittest.main()
