from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.goals import CriterionType, Goal, GoalEvaluationResult, SuccessCriterion  # noqa: E402
from brain.runtime.specialists import ValidatorSpecialist  # noqa: E402


class ValidatorSpecialistTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-specialists"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"validator-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_validator_distinguishes_met_failed_and_pending(self) -> None:
        with self.temp_workspace() as workspace_root:
            goal = Goal.build(
                description="Validate bounded output.",
                intent="validation",
                subgoals=[],
                constraints=[],
                success_criteria=[
                    SuccessCriterion.build(
                        description="Execution succeeds",
                        criterion_type=CriterionType.FUNCTIONAL,
                        weight=1.0,
                        required=True,
                        evaluation_fn="always_true",
                    ),
                    SuccessCriterion.build(
                        description="Human-quality synthesis",
                        criterion_type=CriterionType.EVALUATIVE,
                        weight=1.0,
                        required=True,
                        evaluation_fn="pending_eval",
                    ),
                ],
                failure_tolerances=[],
                stop_conditions=[],
                priority=1,
            )
            specialist = ValidatorSpecialist(root=workspace_root)
            decision = specialist.validate(
                goal=goal,
                result={"ok": True},
                goal_evaluation=GoalEvaluationResult(
                    should_stop=False,
                    should_fail=False,
                    is_achieved=False,
                    progress_score=0.5,
                    violated_constraints=[],
                    triggered_stop_conditions=[],
                    unmet_criteria=[],
                    reasoning="partial",
                ),
            )

            self.assertIn("Execution succeeds", decision.criteria_met)
            self.assertIn("Human-quality synthesis", decision.criteria_pending)
            self.assertEqual(decision.criteria_failed, [])
