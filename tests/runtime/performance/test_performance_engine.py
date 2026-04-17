from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

import brain.runtime.performance.performance_engine as performance_engine_module  # noqa: E402
from brain.runtime.performance.compression import build_slim_swarm_context  # noqa: E402
from brain.runtime.performance.performance_engine import PerformanceEngine  # noqa: E402


class PerformanceEngineTest(unittest.TestCase):
    def test_compression_reduces_estimated_bytes(self) -> None:
        mem = {
            "context_id": "c1",
            "selected_count": 3,
            "total_candidates": 10,
            "sources_used": ["a", "b"],
            "context_summary": "x" * 2000,
            "scoring": {"max_score": 1.0, "min_score": 0.1, "extra": {"nested": list(range(40))}},
        }
        rh = {
            "proceed": True,
            "mode": "deep",
            "intent": "analyze",
            "task_type": "repository_analysis",
            "execution_strategy": "phased",
            "reasoning_summary": "y" * 900,
            "plan_steps": [f"step-{i}" for i in range(40)],
            "suggested_capabilities": [f"cap-{i}" for i in range(30)],
            "validation": {"outcome": "valid"},
            "governance": {"reason": "ok"},
        }
        plan = {
            "plan_id": "p1",
            "execution_ready": True,
            "planning_summary": "z" * 600,
            "steps": [
                {
                    "step_id": f"s{i}",
                    "step_type": "execution",
                    "summary": "s",
                    "description": "d" * 500,
                    "depends_on": [],
                    "requires_validation": False,
                }
                for i in range(40)
            ],
            "checkpoints": [{"checkpoint_id": f"c{i}"} for i in range(30)],
            "fallbacks": [{"fallback_id": f"f{i}"} for i in range(15)],
            "linked_reasoning": {"mode": "deep"},
        }
        pt = {
            "trace_id": "t1",
            "plan_id": "p1",
            "step_count": 6,
            "dependency_edge_count": 5,
            "checkpoint_count": 1,
            "fallback_count": 1,
            "execution_ready": True,
            "degraded": False,
            "fallback_branch_defined": True,
            "error": "",
        }
        planning = {"execution_plan": plan, "planning_trace": pt}
        sm = [{"content": "longtext " * 50, "meta": {"x": 1}} for _ in range(20)]
        full = {
            "context_budget": {"level": "normal"},
            "retrieval_plan": {"items": [1, 2, 3]},
            "structured_memory": sm,
            "reasoning_handoff": rh,
            "memory_intelligence": mem,
            "execution_plan": plan,
            "planning_trace": pt,
        }
        slim, stats = build_slim_swarm_context(
            budget_dict={"level": "normal"},
            retrieval_dict={"items": [1, 2, 3]},
            structured_memory=sm,
            memory_intelligence=mem,
            reasoning_handoff=rh,
            planning_payload=planning,
        )
        self.assertGreater(stats.estimated_bytes_before, stats.estimated_bytes_after)
        self.assertIn("memory_intelligence", stats.steps_applied)
        self.assertEqual(slim["phase36_boundary"], "slim_swarm_context_v1")

    def test_cache_hit_skips_recompression(self) -> None:
        eng = PerformanceEngine(max_cache_entries=8)
        mem = {"context_id": "cx", "selected_count": 1, "total_candidates": 2, "sources_used": [], "context_summary": "s", "scoring": {}}
        rh = {
            "proceed": True,
            "mode": "fast",
            "intent": "ask_question",
            "task_type": "simple_query",
            "execution_strategy": "direct",
            "reasoning_summary": "r",
            "plan_steps": ["a"],
            "suggested_capabilities": [],
            "validation": {},
            "governance": {},
        }
        plan = {"plan_id": "p9", "execution_ready": True, "planning_summary": "ps", "steps": [], "checkpoints": [], "fallbacks": [], "linked_reasoning": {}}
        kw = dict(
            session_id="s1",
            message="hello world",
            budget_dict={},
            retrieval_dict={},
            structured_memory=[],
            memory_intelligence=mem,
            reasoning_handoff=rh,
            planning_payload={"execution_plan": plan, "planning_trace": {"trace_id": "x", "plan_id": "p9"}},
        )
        r1 = eng.optimize_swarm_boundary(**kw)
        r2 = eng.optimize_swarm_boundary(**kw)
        self.assertFalse(r1.trace.cache_hit)
        self.assertTrue(r2.trace.cache_hit)
        self.assertGreater(r2.trace.redundant_dict_copies_avoided, r1.trace.redundant_dict_copies_avoided)

    def test_degraded_path_on_compression_error(self) -> None:
        eng = PerformanceEngine(max_cache_entries=4)

        def boom(**_kwargs: object) -> None:
            raise RuntimeError("forced")

        with patch.object(performance_engine_module, "build_slim_swarm_context", boom):
            res = eng.optimize_swarm_boundary(
                session_id="s",
                message="m",
                budget_dict={},
                retrieval_dict={},
                structured_memory={},
                memory_intelligence={"context_id": "c"},
                reasoning_handoff={"proceed": True, "intent": "x", "mode": "fast"},
                planning_payload={"execution_plan": {}, "planning_trace": {}},
            )
        self.assertTrue(res.trace.degraded)
        self.assertEqual(res.slim_swarm_context.get("phase36_boundary"), "fallback_uncompressed")


if __name__ == "__main__":
    unittest.main()
