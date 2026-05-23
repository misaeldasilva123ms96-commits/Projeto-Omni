import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control.governance_read_model import (  # noqa: E402
    attention_priority_for_run,
    build_governance_run_view,
    build_operational_governance_snapshot,
    list_blocked_by_policy_runs,
    list_operator_attention_runs,
    list_rollback_affected_runs,
    list_waiting_operator_runs,
)
from brain.runtime.control.governance_taxonomy import GovernanceReason  # noqa: E402
from brain.runtime.control.run_registry import RunRecord, RunRegistry, RunStatus  # noqa: E402
from brain.runtime.observability.run_reader import read_operational_governance  # noqa: E402


class GovernanceReadModelTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-governance-read"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"read-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_build_governance_run_view_coherent(self) -> None:
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
            rec = reg.get("r1")
            self.assertIsNotNone(rec)
            view = build_governance_run_view(rec)
            self.assertEqual(view["run_id"], "r1")
            self.assertIn("governance", view)
            self.assertIn("reason", view["governance"])
            self.assertIn("latest_governance_event", view)

    def test_waiting_operator_and_rollback_views(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            reg.register(
                RunRecord.build(
                    run_id="wait-1",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.AWAITING_APPROVAL,
                    last_action="governance_hold",
                    progress_score=0.2,
                )
            )
            reg.register(
                RunRecord.build(
                    run_id="rb-1",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.FAILED,
                    last_action="engine_promotion_rollback",
                    progress_score=0.3,
                )
            )
            reg.update_status(
                "rb-1",
                RunStatus.FAILED,
                "engine_promotion_rollback",
                0.3,
                reason="promotion_rollback_threshold",
            )
            waiting = list_waiting_operator_runs(reg)
            self.assertEqual(len(waiting), 1)
            self.assertEqual(waiting[0]["run_id"], "wait-1")
            rollback = list_rollback_affected_runs(reg)
            self.assertEqual(rollback[0]["run_id"], "rb-1")

    def test_blocked_by_policy_runs(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            reg.register(
                RunRecord.build(
                    run_id="pol-1",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.RUNNING,
                    last_action="execution_started",
                    progress_score=0.0,
                )
            )
            reg.update_status(
                "pol-1",
                RunStatus.RUNNING,
                "control_layer_blocked",
                0.1,
                reason="policy_block",
            )
            blocked = list_blocked_by_policy_runs(reg)
            self.assertEqual(len(blocked), 1)
            self.assertEqual(blocked[0]["run_id"], "pol-1")
            self.assertEqual(blocked[0]["governance"]["reason"], GovernanceReason.POLICY_BLOCK.value)

    def test_latest_governance_event_by_run_and_attention_order(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            reg.register(
                RunRecord.build(
                    run_id="p1",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.RUNNING,
                    last_action="execution_started",
                    progress_score=0.0,
                )
            )
            reg.update_status("p1", RunStatus.RUNNING, "control_layer_blocked", 0.1, reason="policy_block")
            reg.register(
                RunRecord.build(
                    run_id="w1",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.PAUSED,
                    last_action="operator_pause",
                    progress_score=0.2,
                )
            )
            reg.update_status(
                "w1",
                RunStatus.PAUSED,
                "operator_pause",
                0.2,
                reason="operator_pause",
                decision_source="operator_cli",
            )
            att = list_operator_attention_runs(reg)
            self.assertGreaterEqual(len(att), 2)
            priorities = [a["attention_priority"] for a in att]
            self.assertEqual(min(priorities), 0)
            self.assertTrue(all(p < 99 for p in priorities))
            self.assertEqual(att[0]["attention_priority"], 0)
            self.assertEqual(att[0]["run_id"], "p1")

    def test_operational_snapshot_and_read_helper_legacy_json(self) -> None:
        with self.temp_workspace() as root:
            control_dir = root / ".logs" / "fusion-runtime" / "control"
            control_dir.mkdir(parents=True, exist_ok=True)
            legacy = {
                "runs": {
                    "legacy-1": {
                        "run_id": "legacy-1",
                        "goal_id": None,
                        "session_id": "s1",
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
                        "resolution_history": [],
                    }
                }
            }
            (control_dir / "run_registry.json").write_text(
                json.dumps(legacy, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            reg = RunRegistry(root)
            snap = build_operational_governance_snapshot(reg)
            self.assertIn("summary", snap)
            self.assertIn("waiting_operator_runs", snap)
            self.assertIn("latest_governance_event_by_run", snap)
            read_back = read_operational_governance(root)
            self.assertEqual(read_back["total_runs"], snap["total_runs"])

    def test_attention_priority_for_run_deterministic(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            reg.register(
                RunRecord.build(
                    run_id="idle",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.COMPLETED,
                    last_action="goal_completed",
                    progress_score=1.0,
                )
            )
            r = reg.get("idle")
            self.assertEqual(attention_priority_for_run(r), (99, "none"))


if __name__ == "__main__":
    unittest.main()
