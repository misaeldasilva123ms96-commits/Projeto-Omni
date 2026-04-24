from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.experience.experience_builder import build_experience_record  # noqa: E402
from brain.runtime.feedback.feedback_models import combine_feedback  # noqa: E402
from brain.runtime.policy.performance_store import PerformanceStore  # noqa: E402
from brain.runtime.provenance.provenance_parser import parse_execution_provenance  # noqa: E402


class Phase42ProvenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = PROJECT_ROOT / ".logs" / "test-phase42" / f"p42-{uuid4().hex[:10]}"
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root.parent, ignore_errors=True)

    def test_parser_full_node_payload(self) -> None:
        swarm = {
            "metadata": {
                "execution_provenance": {
                    "provider_actual": "openai",
                    "model_actual": "gpt-4.1-mini",
                    "provider_recommended": "openai",
                    "tool_calls": ["read_file"],
                    "tool_count": 1,
                    "execution_mode": "node_local_tool_run",
                    "policy_applied": True,
                    "policy_match": True,
                    "usage_tokens_input": 120,
                    "usage_tokens_output": 40,
                    "cost_estimate": None,
                    "provider_failed": False,
                    "failure_class": "",
                    "provenance_source": "node_authority",
                    "provenance_confidence": 0.9,
                }
            }
        }
        p = parse_execution_provenance(
            swarm,
            orchestrator_context={"policy_recommended": "openai", "policy_shadow_only": False},
            strategy_mode="fast",
            fallback_used=False,
            latency_total_ms=500,
        )
        self.assertEqual(p.provider_actual, "openai")
        self.assertEqual(p.model_actual, "gpt-4.1-mini")
        self.assertTrue(p.policy_match)
        self.assertEqual(p.usage_tokens_input, 120)

    def test_parser_sparse_no_crash(self) -> None:
        p = parse_execution_provenance({}, orchestrator_context=None, strategy_mode="", fallback_used=True, latency_total_ms=0)
        self.assertEqual(p.provider_actual, "")
        self.assertIsNone(p.policy_match)

    def test_parser_policy_mismatch(self) -> None:
        swarm = {
            "metadata": {
                "execution_provenance": {
                    "provider_actual": "anthropic",
                    "provider_recommended": "openai",
                    "policy_match": False,
                    "provider_failed": True,
                    "failure_class": "provider_timeout",
                }
            }
        }
        p = parse_execution_provenance(swarm, orchestrator_context={}, strategy_mode="deep", fallback_used=False, latency_total_ms=1)
        self.assertFalse(p.policy_match)
        self.assertTrue(p.provider_failed)
        self.assertEqual(p.failure_class, "provider_timeout")

    def test_performance_uses_provider_actual(self) -> None:
        ps = PerformanceStore(self.root)
        row = {
            "normalized_intent": "x",
            "strategy_selected": "fast",
            "provider_selected": "",
            "model_selected": "",
            "success_outcome": True,
            "fallback_used": False,
            "latency_ms": 50,
            "response_quality_score": 0.7,
            "feedback_class": "neutral",
            "execution_provenance": {
                "provider_actual": "groq",
                "model_actual": "llama",
                "strategy_actual": "fast",
            },
        }
        ps.update_from_experience_row(row)
        top = ps.top_buckets(limit=3)
        self.assertTrue(any(b.get("provider") == "groq" for b in top))

    def test_build_experience_merges_provenance(self) -> None:
        fb = combine_feedback(None, [])
        swarm = {"metadata": {"provider": "legacy", "model": "old"}}
        ep = {
            "provider_actual": "openai",
            "model_actual": "gpt-test",
            "tool_calls": ["grep_search"],
            "tool_count": 1,
            "policy_match": True,
        }
        r = build_experience_record(
            session_id="sx",
            user_input="hi",
            normalized_intent="n",
            swarm_result=swarm,
            strategy_payload={"selected_strategy": {"mode": "fast"}},
            latency_ms=10,
            fallback_used=False,
            error_class="",
            response_quality_score=0.8,
            feedback=fb,
            success_outcome=True,
            learning_summary="ok",
            agent_trace_summary="",
            execution_provenance=ep,
        )
        self.assertEqual(r.provider_selected, "openai")
        self.assertEqual(r.model_selected, "gpt-test")
        self.assertIsInstance(r.metadata.get("execution_provenance"), dict)


if __name__ == "__main__":
    unittest.main()
