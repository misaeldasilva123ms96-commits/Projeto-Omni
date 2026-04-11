from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.goals import (  # noqa: E402
    Constraint,
    ConstraintRegistry,
    ConstraintType,
    CriterionType,
    GoalEvaluator,
    GoalFactory,
    Severity,
    StopCondition,
    StopConditionType,
    SuccessCriterion,
)


class GoalEvaluatorTest(unittest.TestCase):
    def test_goal_evaluator_achieves_success_when_required_criteria_pass(self) -> None:
        factory = GoalFactory()
        goal = factory.create_goal(
            description="Concluir objetivo funcional.",
            intent="execution",
            success_criteria=[
                SuccessCriterion.build(
                    description="Resultado bem-sucedido.",
                    criterion_type=CriterionType.FUNCTIONAL,
                    weight=1.0,
                    required=True,
                    evaluation_fn="result_ok",
                )
            ],
        )
        result = GoalEvaluator(ConstraintRegistry()).evaluate(goal=goal, runtime_state={"result_ok": True})

        self.assertTrue(result.is_achieved)
        self.assertFalse(result.should_fail)
        self.assertEqual(result.progress_score, 1.0)

    def test_hard_constraint_violation_produces_fail_state(self) -> None:
        goal = GoalFactory().create_goal(
            description="Nao sair do escopo permitido.",
            intent="execution",
            constraints=[
                Constraint.build(
                    description="Somente planning e permitido.",
                    constraint_type=ConstraintType.SCOPE_LIMIT,
                    severity=Severity.HARD,
                    evaluation_fn="proposal_within_goal_scope",
                    metadata={"allowed_subsystems": ["planning"]},
                )
            ],
        )
        result = GoalEvaluator(ConstraintRegistry()).evaluate(
            goal=goal,
            runtime_state={"proposal_target_subsystem": "continuation"},
        )

        self.assertTrue(result.should_fail)
        self.assertFalse(result.is_achieved)
        self.assertTrue(result.violated_constraints)

    def test_stop_condition_produces_stop_state(self) -> None:
        goal = GoalFactory().create_goal(
            description="Parar quando ciclos excederem limite.",
            intent="execution",
            stop_conditions=[
                StopCondition.build(
                    description="Parar apos dois ciclos.",
                    condition_type=StopConditionType.MAX_CYCLES,
                    trigger_fn="max_cycles_not_reached",
                    metadata={"max_cycles": 2},
                )
            ],
        )
        result = GoalEvaluator(ConstraintRegistry()).evaluate(
            goal=goal,
            runtime_state={"cycle_count": 2},
        )

        self.assertTrue(result.should_stop)
        self.assertTrue(result.triggered_stop_conditions)

    def test_progress_score_is_computed_deterministically(self) -> None:
        goal = GoalFactory().create_goal(
            description="Avaliar progresso parcial.",
            intent="execution",
            success_criteria=[
                SuccessCriterion.build(
                    description="Passou funcional.",
                    criterion_type=CriterionType.FUNCTIONAL,
                    weight=2.0,
                    required=True,
                    evaluation_fn="result_ok",
                ),
                SuccessCriterion.build(
                    description="Existe passo bem-sucedido.",
                    criterion_type=CriterionType.STRUCTURAL,
                    weight=1.0,
                    required=False,
                    evaluation_fn="successful_steps_exist",
                ),
            ],
        )
        result = GoalEvaluator(ConstraintRegistry()).evaluate(
            goal=goal,
            runtime_state={"result_ok": True, "successful_steps_count": 0},
        )

        self.assertAlmostEqual(result.progress_score, 2.0 / 3.0, places=4)
        self.assertTrue(result.is_achieved)


if __name__ == "__main__":
    unittest.main()
