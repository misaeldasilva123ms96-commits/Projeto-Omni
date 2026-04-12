from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.specialists import DecisionStatus, PlanDecision, SpecialistType  # noqa: E402


class SpecialistModelsTest(unittest.TestCase):
    def test_specialist_decision_models_serialize(self) -> None:
        decision = PlanDecision.build(
            goal_id="goal-1",
            simulation_id="simulation-1",
            reasoning="bounded planning",
            confidence=0.8,
            plan_steps=[{"step_id": "step-1", "title": "Do work"}],
            estimated_cycles=1,
            replan=False,
        )

        payload = decision.as_dict()

        self.assertEqual(payload["specialist_type"], SpecialistType.PLANNER.value)
        self.assertEqual(payload["status"], DecisionStatus.DECIDED.value)
        self.assertEqual(payload["plan_steps"][0]["step_id"], "step-1")
