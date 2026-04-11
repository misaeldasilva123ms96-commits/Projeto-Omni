from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.learning import LearningSignalType  # noqa: E402
from brain.runtime.learning.learning_executor import LearningExecutor  # noqa: E402
from brain.runtime.learning.models import LearningPolicy, LearningSignal, PatternRecord  # noqa: E402
from brain.runtime.learning.strategy_ranker import StrategyRanker  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402


class OperationalLearningTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-learning"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"phase18-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def make_executor(self, workspace_root: Path, **policy_overrides) -> LearningExecutor:
        policy = LearningPolicy(**policy_overrides) if policy_overrides else None
        return LearningExecutor(workspace_root, policy=policy)

    def test_execution_receipt_is_normalized_into_learning_evidence(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = self.make_executor(workspace_root)
            action = {"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read", "session_id": "s1", "task_id": "t1"}
            result = {
                "execution_receipt": {
                    "receipt_id": "receipt-exec",
                    "timestamp": "2026-04-11T12:00:00+00:00",
                    "action_type": "read",
                    "execution_status": "succeeded",
                    "verification_status": "passed",
                    "retry_count": 0,
                    "session_id": "s1",
                    "task_id": "t1",
                    "metadata": {},
                }
            }
            update = executor.ingest_runtime_artifacts(action=action, result=result)

            self.assertEqual(update["ingested_evidence"], 1)
            evidence_file = workspace_root / ".logs" / "fusion-runtime" / "learning" / "evidence" / "execution_receipt.jsonl"
            payload = json.loads(evidence_file.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(payload["source_type"], "execution_receipt")
            self.assertTrue(payload["success"])

    def test_repair_receipt_is_normalized_into_learning_evidence(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = self.make_executor(workspace_root)
            action = {"step_id": "patch", "selected_tool": "filesystem_patch_set", "action_type": "mutate"}
            result = {
                "repair_receipt": {
                    "repair_receipt_id": "repair-1",
                    "timestamp": "2026-04-11T12:00:01+00:00",
                    "promotion_status": "promoted",
                    "attempt_count": 1,
                    "repair_strategy": "normalize_result_payload_shape",
                    "cause_category": "shape_mismatch",
                }
            }
            update = executor.ingest_runtime_artifacts(action=action, result=result)

            self.assertEqual(update["ingested_evidence"], 1)
            evidence_file = workspace_root / ".logs" / "fusion-runtime" / "learning" / "evidence" / "repair_receipt.jsonl"
            payload = json.loads(evidence_file.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(payload["source_type"], "repair_receipt")
            self.assertTrue(payload["repair_promoted"])

    def test_continuation_decision_is_normalized_into_learning_evidence(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = self.make_executor(workspace_root)
            update = executor.ingest_runtime_artifacts(
                continuation_decision={
                    "decision_id": "continuation-1",
                    "plan_id": "plan-1",
                    "task_id": "task-1",
                    "decision_type": "retry_step",
                    "timestamp": "2026-04-11T12:00:02+00:00",
                }
            )

            self.assertEqual(update["ingested_evidence"], 1)
            evidence_file = workspace_root / ".logs" / "fusion-runtime" / "learning" / "evidence" / "continuation_decision.jsonl"
            payload = json.loads(evidence_file.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(payload["continuation_decision_type"], "retry_step")

    def test_pattern_registry_aggregates_successes_and_failures_correctly(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = self.make_executor(workspace_root, min_pattern_samples=1)
            action = {"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"}
            success = {
                "execution_receipt": {
                    "receipt_id": "receipt-success",
                    "timestamp": "2026-04-11T12:00:00+00:00",
                    "action_type": "read",
                    "execution_status": "succeeded",
                    "verification_status": "passed",
                    "retry_count": 0,
                }
            }
            failure = {
                "execution_receipt": {
                    "receipt_id": "receipt-failure",
                    "timestamp": "2026-04-11T12:00:01+00:00",
                    "action_type": "read",
                    "execution_status": "failed",
                    "verification_status": "failed",
                    "retry_count": 1,
                    "error_details": {"kind": "verification_failed"},
                }
            }
            executor.ingest_runtime_artifacts(action=action, result=success)
            executor.ingest_runtime_artifacts(action=action, result=failure)
            records = executor.store.load_patterns(category="execution")

            self.assertTrue(records)
            self.assertEqual(records[0].total_count, 2)
            self.assertEqual(records[0].success_count + records[0].failure_count, 2)

    def test_strategy_ranking_reflects_evidence_backed_preference(self) -> None:
        ranker = StrategyRanker()
        policy = LearningPolicy(min_pattern_samples=3)
        preferred = PatternRecord.build(pattern_key="repair:a", category="repair")
        for _ in range(4):
            preferred.register_outcome(success=True, timestamp="2026-04-11T12:00:00+00:00")
        weak = PatternRecord.build(pattern_key="repair:b", category="repair")
        for _ in range(4):
            weak.register_outcome(success=False, timestamp="2026-04-11T12:00:00+00:00")

        rankings = ranker.rank(records=[weak, preferred], policy=policy)

        self.assertGreater(rankings[0].score, rankings[1].score)
        self.assertEqual(rankings[0].strategy_key, "repair:a")

    def test_low_sample_pattern_does_not_produce_strong_signal(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = self.make_executor(workspace_root, min_pattern_samples=3)
            action = {"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"}
            result = {
                "execution_receipt": {
                    "receipt_id": "receipt-low-sample",
                    "timestamp": "2026-04-11T12:00:00+00:00",
                    "action_type": "read",
                    "execution_status": "succeeded",
                    "verification_status": "passed",
                    "retry_count": 0,
                }
            }
            update = executor.ingest_runtime_artifacts(action=action, result=result)

            self.assertEqual(update["signals"], [])

    def test_stale_pattern_is_ignored_by_ranking_policy(self) -> None:
        stale_record = PatternRecord.build(pattern_key="continuation:retry_step:healthy:ready", category="continuation")
        stale_record.success_count = 5
        stale_record.total_count = 5
        stale_record.success_ratio = 1.0
        stale_record.last_seen = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        rankings = StrategyRanker().rank(records=[stale_record], policy=LearningPolicy(stale_pattern_days=30))

        self.assertEqual(rankings, [])

    def test_learning_signal_serialization_works(self) -> None:
        signal = LearningSignal.build(
            signal_type=LearningSignalType.PREFERRED_CONTINUATION_DECISION,
            source_pattern_key="continuation:continue_execution:healthy:ready",
            confidence=0.8,
            weight=0.2,
            recommendation="Prefer continue_execution for healthy plans.",
            evidence_summary={"evidence_count": 4},
        )
        payload = signal.as_dict()

        self.assertEqual(payload["signal_type"], "preferred_continuation_decision")
        self.assertTrue(payload["advisory"])

    def test_orchestrator_runtime_integration_does_not_break_flow(self) -> None:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        actions = [
            {"step_id": "read-a", "selected_tool": "filesystem_read", "selected_agent": "engineering-specialist", "tool_arguments": {"path": "README.md"}},
            {"step_id": "read-b", "selected_tool": "filesystem_read", "selected_agent": "engineering-specialist", "tool_arguments": {"path": "package.json"}},
        ]
        with patch(
            "brain.runtime.orchestrator.execute_engineering_action",
            side_effect=[
                {"ok": True, "result_payload": {"file": {"content": "a"}}},
                {"ok": True, "result_payload": {"file": {"content": "b"}}},
            ],
        ):
            results = orchestrator._execute_runtime_actions(
                session_id=f"phase18-session-{uuid4().hex[:8]}",
                message="inspecionar dois arquivos",
                actions=actions,
                task_id=f"phase18-task-{uuid4().hex[:8]}",
                run_id=f"phase18-run-{uuid4().hex[:8]}",
                provider="test-provider",
                intent="execution",
                delegation={},
                plan_kind="linear",
            )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.get("ok") for item in results))
        self.assertTrue(all("learning_signals" in item for item in results))

    def test_learning_signals_remain_advisory_by_default(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = self.make_executor(workspace_root, min_pattern_samples=1)
            action = {"step_id": "patch", "selected_tool": "filesystem_patch_set", "action_type": "mutate"}
            for index in range(3):
                executor.ingest_runtime_artifacts(
                    action=action,
                    result={
                        "repair_receipt": {
                            "repair_receipt_id": f"repair-{index}",
                            "timestamp": f"2026-04-11T12:00:0{index}+00:00",
                            "promotion_status": "promoted",
                            "attempt_count": 1,
                            "repair_strategy": "normalize_result_payload_shape",
                            "cause_category": "shape_mismatch",
                        }
                    },
                )
            signals = executor.store.load_recent_signals(limit=20)

            self.assertTrue(signals)
            self.assertTrue(all(signal.advisory for signal in signals))


if __name__ == "__main__":
    unittest.main()
