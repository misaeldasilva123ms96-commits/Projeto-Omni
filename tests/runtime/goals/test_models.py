from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.goals import Constraint, ConstraintType, CriterionType, GoalFactory, Severity, SuccessCriterion  # noqa: E402


class GoalModelsTest(unittest.TestCase):
    def test_goal_creation_from_structured_input(self) -> None:
        factory = GoalFactory()
        goal = factory.create_goal(
            description="Atualizar a camada de planejamento com segurança.",
            intent="implementation",
            constraints=[
                Constraint.build(
                    description="Permanecer no subsistema de planning.",
                    constraint_type=ConstraintType.SCOPE_LIMIT,
                    severity=Severity.HARD,
                    evaluation_fn="proposal_within_goal_scope",
                    metadata={"allowed_subsystems": ["planning"]},
                )
            ],
            success_criteria=[
                SuccessCriterion.build(
                    description="O resultado final precisa ser coerente.",
                    criterion_type=CriterionType.EVALUATIVE,
                    weight=1.0,
                    required=True,
                    evaluation_fn="result_ok",
                )
            ],
            priority=4,
        )

        self.assertEqual(goal.intent, "implementation")
        self.assertEqual(goal.priority, 4)
        self.assertEqual(len(goal.success_criteria), 1)
        self.assertEqual(goal.success_criteria[0].evaluation_fn, "result_ok")

    def test_fallback_goal_inference_from_raw_task(self) -> None:
        factory = GoalFactory()
        goal = factory.infer_from_task(
            "Inspecionar, editar e validar o fluxo do runtime.",
            context={
                "intent": "runtime_execution",
                "actions": [
                    {"selected_tool": "filesystem_read"},
                    {"selected_tool": "filesystem_patch_set"},
                ],
            },
        )

        self.assertTrue(goal.description.startswith("Inspecionar"))
        self.assertTrue(any(criterion.required for criterion in goal.success_criteria))
        self.assertTrue(goal.metadata.get("inferred"))


if __name__ == "__main__":
    unittest.main()
