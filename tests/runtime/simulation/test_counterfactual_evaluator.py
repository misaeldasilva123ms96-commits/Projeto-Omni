from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.memory.semantic import SemanticFact  # noqa: E402
from brain.runtime.simulation import RouteSimulation, RouteType, SimulationContext  # noqa: E402
from brain.runtime.simulation.counterfactual_evaluator import CounterfactualEvaluator  # noqa: E402


class CounterfactualEvaluatorTest(unittest.TestCase):
    def test_semantic_adjustments_are_bounded(self) -> None:
        evaluator = CounterfactualEvaluator()
        route = RouteSimulation(
            route=RouteType.RETRY,
            estimated_success_rate=0.5,
            estimated_cost=0.3,
            constraint_risk=0.4,
            goal_alignment=0.7,
            supporting_episodes=[],
            reasoning="baseline",
            confidence=0.4,
        )
        context = SimulationContext(
            goal_id=None,
            goal_description="",
            goal_type="general",
            current_progress=0.4,
            last_action={},
            last_outcome="failure",
            active_constraints=[],
            retry_count=1,
            repair_count=0,
            session_id="sess-counterfactual",
            goal_present=False,
        )
        facts = [
            SemanticFact(
                fact_id=f"fact-{index}",
                subject="retry",
                predicate="tends_to_result_in",
                object_value="retry",
                confidence=0.99,
                source_episode_ids=[],
                goal_types=[],
                created_at="2026-04-11T12:00:00+00:00",
                last_reinforced_at="2026-04-11T12:00:00+00:00",
                metadata={},
            )
            for index in range(5)
        ]

        updated, _ = evaluator.enrich(route_simulation=route, context=context, semantic_facts=facts)

        self.assertLessEqual(updated.estimated_success_rate, 0.75)
        self.assertGreaterEqual(updated.estimated_success_rate, 0.25)
