from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.specialists import PlanDecision, SynthesisSpecialist  # noqa: E402


class SynthesisSpecialistTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-specialists"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"synthesis-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_synthesis_specialist_produces_coherent_summary(self) -> None:
        with self.temp_workspace() as workspace_root:
            specialist = SynthesisSpecialist(root=workspace_root)
            decision = PlanDecision.build(
                goal_id="goal-1",
                simulation_id="simulation-1",
                reasoning="plan",
                confidence=0.8,
                plan_steps=[],
                estimated_cycles=1,
                replan=False,
            )

            synthesis = specialist.synthesize(
                goal_id="goal-1",
                simulation_id="simulation-1",
                decisions=[decision],
                final_outcome="completed_step",
            )

            self.assertIn("completed_step", synthesis.summary)
            self.assertTrue(synthesis.artifact_refs)

