from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.planning.planning_engine import PlanningEngine  # noqa: E402


class PlanningEngineTest(unittest.TestCase):
    def _handoff(self, **kwargs: object) -> dict:
        base = {
            "proceed": True,
            "mode": "deep",
            "intent": "analyze",
            "task_type": "repository_analysis",
            "execution_strategy": "phased",
            "suggested_capabilities": ["read_file", "code_search"],
            "reasoning_summary": "Analyze structure",
            "governance": {},
            "observability": {},
            "plan_steps": ["interpret", "plan", "validate", "handoff_to_execution"],
            "validation": {"outcome": "valid", "issues": []},
            "metadata": {},
        }
        base.update(kwargs)
        return base

    def test_multi_step_dependencies_and_order(self) -> None:
        eng = PlanningEngine()
        plan, trace = eng.build_execution_plan(
            handoff=self._handoff(),
            reasoning_trace={"trace_id": "reason-abc"},
            session_id="s1",
            run_id="r1",
            task_id="t1",
            normalized_input="hello",
            control_routing={"task_type": "repository_analysis", "risk_level": "low", "verification_intensity": "low"},
        )
        self.assertTrue(plan.execution_ready)
        self.assertEqual(len(plan.steps), 4)
        self.assertEqual(plan.steps[0].depends_on, [])
        for i in range(1, len(plan.steps)):
            self.assertEqual(plan.steps[i].depends_on, [plan.steps[i - 1].step_id])
        self.assertGreater(trace.dependency_edge_count, 0)
        self.assertEqual(trace.step_count, 4)

    def test_checkpoints_on_validation_stages(self) -> None:
        eng = PlanningEngine()
        plan, trace = eng.build_execution_plan(
            handoff=self._handoff(),
            reasoning_trace={"trace_id": "reason-x"},
            session_id="s1",
            run_id="",
            task_id="",
            normalized_input="x",
            control_routing={},
        )
        validate_steps = [s for s in plan.steps if s.requires_validation]
        self.assertGreaterEqual(len(validate_steps), 1)
        self.assertGreaterEqual(len(plan.checkpoints), 1)
        self.assertGreaterEqual(trace.checkpoint_count, 1)
        for cp in plan.checkpoints:
            self.assertTrue(any(s.step_id == cp.after_step_id for s in plan.steps))

    def test_fallback_when_multiple_steps(self) -> None:
        eng = PlanningEngine()
        plan, trace = eng.build_execution_plan(
            handoff=self._handoff(
                plan_steps=["a", "b"],
                execution_strategy="phased",
            ),
            reasoning_trace={},
            session_id=None,
            run_id="",
            task_id="",
            normalized_input="n",
            control_routing={},
        )
        self.assertGreaterEqual(len(plan.fallbacks), 1)
        self.assertTrue(trace.fallback_branch_defined)
        fb = plan.fallbacks[0]
        self.assertEqual(fb.trigger_step_id, plan.steps[-1].step_id)
        self.assertEqual(fb.target_step_id, plan.steps[0].step_id)

    def test_guarded_second_fallback(self) -> None:
        eng = PlanningEngine()
        plan, _trace = eng.build_execution_plan(
            handoff=self._handoff(
                plan_steps=["s0", "s1", "s2", "s3"],
                execution_strategy="guarded",
            ),
            reasoning_trace={},
            session_id="s",
            run_id="",
            task_id="",
            normalized_input="n",
            control_routing={},
        )
        self.assertGreaterEqual(len(plan.fallbacks), 2)

    def test_high_risk_adds_control_checkpoint(self) -> None:
        eng = PlanningEngine()
        plan_low, _ = eng.build_execution_plan(
            handoff=self._handoff(plan_steps=["a", "b"]),
            reasoning_trace={},
            session_id="s",
            run_id="",
            task_id="",
            normalized_input="n",
            control_routing={"risk_level": "low", "verification_intensity": "low"},
        )
        plan_high, _ = eng.build_execution_plan(
            handoff=self._handoff(plan_steps=["a", "b"]),
            reasoning_trace={},
            session_id="s",
            run_id="",
            task_id="",
            normalized_input="n",
            control_routing={"risk_level": "high", "verification_intensity": "high"},
        )
        self.assertLessEqual(len(plan_low.checkpoints), len(plan_high.checkpoints))

    def test_empty_plan_steps_becomes_single_objective(self) -> None:
        eng = PlanningEngine()
        plan, trace = eng.build_execution_plan(
            handoff=self._handoff(plan_steps=[]),
            reasoning_trace={"trace_id": "t"},
            session_id="s",
            run_id="",
            task_id="",
            normalized_input="do something",
            control_routing={},
        )
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(trace.step_count, 1)
        self.assertEqual(plan.steps[0].metadata.get("reasoning_stage"), "execute_primary_objective")

    def test_degraded_path_on_synthesis_error(self) -> None:
        eng = PlanningEngine()
        with patch.object(PlanningEngine, "_synthesize", side_effect=RuntimeError("forced")):
            plan, trace = eng.build_execution_plan(
                handoff=self._handoff(plan_steps=["x", "y"]),
                reasoning_trace={"trace_id": "r"},
                session_id="s",
                run_id="",
                task_id="",
                normalized_input="n",
                control_routing={},
            )
        self.assertTrue(trace.degraded)
        self.assertIn("forced", trace.error)
        self.assertEqual(len(plan.steps), 1)
        self.assertTrue(plan.execution_ready)


if __name__ == "__main__":
    unittest.main()
