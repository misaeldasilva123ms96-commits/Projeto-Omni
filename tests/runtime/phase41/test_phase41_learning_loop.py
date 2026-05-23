from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.evolution.pattern_analyzer import PatternAnalyzer  # noqa: E402
from brain.runtime.experience.experience_models import ExperienceRecord, new_experience_id, new_turn_id  # noqa: E402
from brain.runtime.experience.experience_store import ExperienceStore  # noqa: E402
from brain.runtime.feedback.feedback_models import combine_feedback  # noqa: E402
from brain.runtime.feedback.signals import derive_implicit_signals, parse_explicit_feedback  # noqa: E402
from brain.runtime.learning.runtime_learning_store import RuntimeLearningStore  # noqa: E402
from brain.runtime.language import normalize_input_to_oil_request  # noqa: E402
from brain.runtime.policy.performance_store import PerformanceStore  # noqa: E402
from brain.runtime.policy.policy_router import PolicyRouter  # noqa: E402
from brain.runtime.strategy.strategy_engine import StrategyEngine  # noqa: E402


def _minimal_learning_row(session_id: str, outcome: str, rid: str) -> dict:
    return {
        "record_id": rid,
        "session_id": session_id,
        "run_id": "",
        "assessment": {"outcome_class": outcome, "duration_ms": 120},
        "signals": [{"polarity": "positive" if outcome == "success" else "negative"}],
        "summary": {"headline": f"test-{outcome}"},
        "metadata": {"phase": "34"},
    }


class Phase41LearningLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = PROJECT_ROOT / ".logs" / "test-phase41" / f"p41-{uuid4().hex[:10]}"
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root.parent, ignore_errors=True)

    def test_experience_store_session_isolation(self) -> None:
        store = ExperienceStore(self.root)
        tid_a = new_turn_id()
        tid_b = new_turn_id()
        a = ExperienceRecord(
            experience_id=new_experience_id("sess-a", tid_a),
            session_id="sess-a",
            turn_id=tid_a,
            timestamp="t",
            user_input="hi",
            normalized_intent="x",
            provider_selected="openai",
            model_selected="m",
            tools_selected=[],
            strategy_selected="fast",
            latency_ms=10,
            cost_estimate=None,
            fallback_used=False,
            error_class="",
            response_quality_score=0.9,
            feedback_class="neutral",
            feedback_source="none",
            success_outcome=True,
            agent_trace_summary="",
            learning_signals_summary="",
        )
        b = ExperienceRecord(
            experience_id=new_experience_id("sess-b", tid_b),
            session_id="sess-b",
            turn_id=tid_b,
            timestamp="t",
            user_input="yo",
            normalized_intent="y",
            provider_selected="anthropic",
            model_selected="m2",
            tools_selected=["read_file"],
            strategy_selected="deep",
            latency_ms=20,
            cost_estimate=None,
            fallback_used=True,
            error_class="empty_swarm_response",
            response_quality_score=0.2,
            feedback_class="negative",
            feedback_source="explicit",
            success_outcome=False,
            agent_trace_summary="",
            learning_signals_summary="",
        )
        store.append(a)
        store.append(b)
        ra = store.read_recent_for_session("sess-a", limit=5)
        rb = store.read_recent_for_session("sess-b", limit=5)
        self.assertEqual(len(ra), 1)
        self.assertEqual(len(rb), 1)
        self.assertEqual(ra[0]["session_id"], "sess-a")
        self.assertEqual(rb[0]["session_id"], "sess-b")
        self.assertNotEqual(ra[0]["experience_id"], rb[0]["experience_id"])

    def test_feedback_explicit_implicit_mixed(self) -> None:
        ex = parse_explicit_feedback({"thumb": "up", "rating": 5.0})
        self.assertIsNotNone(ex)
        tags = derive_implicit_signals(message="try again that was wrong", history=[])
        b = combine_feedback(ex, tags)
        self.assertEqual(b.feedback_source, "mixed")
        self.assertEqual(b.feedback_class, "negative")

    def test_performance_store_aggregates(self) -> None:
        ps = PerformanceStore(self.root)
        row = {
            "provider_selected": "openai",
            "model_selected": "gpt",
            "normalized_intent": "code",
            "strategy_selected": "fast",
            "success_outcome": True,
            "fallback_used": False,
            "latency_ms": 100,
            "response_quality_score": 0.8,
            "feedback_class": "positive",
            "cost_estimate": 0.01,
        }
        ps.update_from_experience_row(row)
        ps.update_from_experience_row({**row, "success_outcome": False, "feedback_class": "negative"})
        top = ps.top_buckets(limit=3)
        self.assertGreaterEqual(len(top), 1)
        self.assertGreaterEqual(top[0]["metrics"]["attempts"], 2)

    def test_policy_router_shadow_vs_active_env(self) -> None:
        router = PolicyRouter(self.root, performance_store=PerformanceStore(self.root))
        with patch("brain.runtime.policy.policy_router.get_available_providers", return_value=["openai", "anthropic"]):
            with patch.dict(os.environ, {"OMINI_PHASE41_POLICY_ACTIVE": ""}, clear=False):
                h = router.compute_hint(
                    session_id="s1",
                    normalized_intent="test",
                    baseline_provider="openai",
                    strategy_mode="fast",
                    recent_experience_rows=[],
                )
                self.assertTrue(h.shadow_only)
                self.assertIsNone(router.hint_to_env_json(h))
            with patch.dict(os.environ, {"OMINI_PHASE41_POLICY_ACTIVE": "1"}, clear=False):
                h2 = router.compute_hint(
                    session_id="s1",
                    normalized_intent="test",
                    baseline_provider="openai",
                    strategy_mode="fast",
                    recent_experience_rows=[],
                )
                self.assertFalse(h2.shadow_only)
                envj = router.hint_to_env_json(h2)
                self.assertIsInstance(envj, str)
                parsed = json.loads(envj or "{}")
                self.assertIn("recommended_provider", parsed)

    def test_policy_invalid_provider_falls_back(self) -> None:
        """Unavailable recommendation must not be passed as preferred (handled in router)."""
        router = PolicyRouter(self.root, performance_store=PerformanceStore(self.root))
        with patch("brain.runtime.policy.policy_router.get_available_providers", return_value=["openai"]):
            h = router.compute_hint(
                session_id="s1",
                normalized_intent="x",
                baseline_provider="openai",
                strategy_mode=None,
                recent_experience_rows=[
                    {"success_outcome": False},
                    {"success_outcome": False},
                    {"success_outcome": False},
                ],
            )
            self.assertEqual(h.recommended_provider, "openai")

    def test_strategy_engine_session_scoped_learning_not_global(self) -> None:
        ls = RuntimeLearningStore(self.root)
        ls.append_record(_minimal_learning_row("sess-b", "success", "lr-b-1"))
        ls.append_record(_minimal_learning_row("sess-a", "failure", "lr-a-1"))
        eng = StrategyEngine(self.root)
        oil_b = normalize_input_to_oil_request(
            "short",
            session_id="sess-b",
            run_id="",
            metadata={"source_component": "test", "confidence": 0.5},
        )
        dec_b = eng.select(
            session_id="sess-b",
            run_id="",
            message="short",
            oil_request=oil_b,
            memory_context={"selected_count": 0},
            learning_record=None,
        )
        self.assertIn("learning_outcome:success", dec_b.signals_used)
        self.assertNotIn("learning_outcome:failure", dec_b.signals_used)
        oil_a = normalize_input_to_oil_request(
            "short",
            session_id="sess-a",
            run_id="",
            metadata={"source_component": "test", "confidence": 0.5},
        )
        dec_a = eng.select(
            session_id="sess-a",
            run_id="",
            message="short",
            oil_request=oil_a,
            memory_context={"selected_count": 0},
            learning_record=None,
        )
        self.assertIn("learning_outcome:failure", dec_a.signals_used)

    def test_pattern_analyzer_accepts_phase41_sketch(self) -> None:
        pa = PatternAnalyzer()
        out = pa.analyze(
            evaluations=[{"session_id": "s", "overall": 0.7, "flags": [], "timestamp": "2020-01-01T12:00:00+00:00"}],
            learning={"capability_usage": {}},
            sessions=[{"session_id": "s", "swarm": {"intent": "execution"}}],
            phase41_performance_sketch={"top_provider_buckets": []},
        )
        self.assertIn("phase41_performance_sketch", out)


if __name__ == "__main__":
    unittest.main()
