from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.learning.learning_engine import LearningEngine  # noqa: E402
from brain.runtime.orchestrator import SAFE_FALLBACK_RESPONSE  # noqa: E402


class LearningEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = PROJECT_ROOT / ".logs" / "test-learning34" / f"lr-{uuid4().hex[:8]}"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def _engine(self) -> LearningEngine:
        return LearningEngine(self.workspace)

    def test_record_signals_and_persistence(self) -> None:
        eng = self._engine()
        reasoning = {"trace": {"trace_id": "r1", "validation_result": "valid"}}
        memory = {"selected_count": 2, "sources_used": ["transcript"]}
        planning = {
            "planning_trace": {"trace_id": "p1", "execution_ready": True, "degraded": False, "step_count": 3},
            "execution_plan": {"plan_id": "plan-x"},
        }
        evaluation = {"overall": 0.72, "flags": []}
        rec, tr = eng.assess_chat_turn(
            session_id="s1",
            run_id="",
            message="Explain the module.",
            response="Here is a concise explanation.",
            reasoning_payload=reasoning,
            memory_context_payload=memory,
            planning_payload=planning,
            swarm_result={},
            evaluation=evaluation,
            duration_ms=1200,
            last_runtime_reason="",
            last_runtime_mode="live",
            safe_fallback_response=SAFE_FALLBACK_RESPONSE,
            direct_memory_hit=False,
        )
        self.assertTrue(rec.persisted)
        self.assertGreater(len(rec.signals), 3)
        self.assertEqual(tr.signal_count, len(rec.signals))
        self.assertEqual(rec.assessment.outcome_class.value, "success")
        store_path = self.workspace / ".logs" / "fusion-runtime" / "learning" / "evidence" / "runtime_turn_records.jsonl"
        self.assertTrue(store_path.exists())
        lines = [json.loads(l) for l in store_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(lines[-1]["record_id"], rec.record_id)

    def test_safe_fallback_is_failure(self) -> None:
        eng = self._engine()
        rec, tr = eng.assess_chat_turn(
            session_id="s1",
            run_id="",
            message="x",
            response=SAFE_FALLBACK_RESPONSE,
            reasoning_payload={"trace": {"validation_result": "valid"}},
            memory_context_payload={"selected_count": 0},
            planning_payload={},
            swarm_result={},
            evaluation={"overall": 0.2, "flags": ["off_topic"]},
            duration_ms=100,
            last_runtime_reason="",
            last_runtime_mode="live",
            safe_fallback_response=SAFE_FALLBACK_RESPONSE,
            direct_memory_hit=False,
        )
        self.assertEqual(rec.assessment.outcome_class.value, "failure")
        self.assertTrue(rec.assessment.response_was_safe_fallback)
        self.assertGreaterEqual(tr.negative_count, 1)

    def test_persistence_failure_still_returns_record(self) -> None:
        eng = self._engine()
        with patch.object(eng._store, "append_record", return_value=False):
            rec, tr = eng.assess_chat_turn(
                session_id="s1",
                run_id="",
                message="hi",
                response="hello there",
                reasoning_payload={"trace": {"validation_result": "valid"}},
                memory_context_payload={"selected_count": 1},
                planning_payload={
                    "planning_trace": {"execution_ready": True, "degraded": False},
                    "execution_plan": {"plan_id": "z"},
                },
                swarm_result={},
                evaluation={"overall": 0.8, "flags": []},
                duration_ms=50,
                last_runtime_reason="",
                last_runtime_mode="live",
                safe_fallback_response=SAFE_FALLBACK_RESPONSE,
                direct_memory_hit=True,
            )
        self.assertFalse(rec.persisted)
        self.assertFalse(tr.persisted)

    def test_internal_error_degraded_record(self) -> None:
        eng = self._engine()

        def boom(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("forced")

        with patch.object(LearningEngine, "_synthesize", boom):
            rec, tr = eng.assess_chat_turn(
                session_id="s1",
                run_id="",
                message="m",
                response="r",
                reasoning_payload={},
                memory_context_payload={},
                planning_payload={},
                swarm_result={},
                evaluation={},
                duration_ms=1,
                last_runtime_reason="",
                last_runtime_mode="live",
                safe_fallback_response=SAFE_FALLBACK_RESPONSE,
                direct_memory_hit=False,
            )
        self.assertTrue(tr.degraded_assessment)
        self.assertIn("forced", tr.error)
        self.assertFalse(rec.persisted)


if __name__ == "__main__":
    unittest.main()
