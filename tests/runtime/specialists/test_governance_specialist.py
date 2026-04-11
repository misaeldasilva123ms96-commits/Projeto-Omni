from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.goals import Constraint, ConstraintType, Goal, Severity  # noqa: E402
from brain.runtime.specialists import DecisionStatus, GovernanceSpecialist, PlanDecision  # noqa: E402


class GovernanceSpecialistTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-specialists"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"governance-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_governance_blocks_high_risk_routes(self) -> None:
        with self.temp_workspace() as workspace_root:
            specialist = GovernanceSpecialist(root=workspace_root)
            goal = Goal.build(
                description="Stay inside hard safety boundaries.",
                intent="safety",
                subgoals=[],
                constraints=[
                    Constraint.build(
                        description="No hard-risk route",
                        constraint_type=ConstraintType.SAFETY_LIMIT,
                        severity=Severity.HARD,
                        evaluation_fn="noop",
                    )
                ],
                success_criteria=[],
                failure_tolerances=[],
                stop_conditions=[],
                priority=1,
            )
            decision = PlanDecision.build(
                goal_id=goal.goal_id,
                simulation_id=None,
                reasoning="unsafe plan",
                confidence=0.9,
                plan_steps=[],
                estimated_cycles=1,
                replan=False,
                metadata={"hard_constraint_violation": True},
            )

            governance = specialist.review(decision=decision, goal=goal, constraint_registry_available=True)

            self.assertEqual(governance.verdict.value, "block")

    def test_governance_holds_moderate_risk_without_registry_context(self) -> None:
        with self.temp_workspace() as workspace_root:
            specialist = GovernanceSpecialist(root=workspace_root)
            decision = PlanDecision.build(
                goal_id="goal-1",
                simulation_id=None,
                reasoning="replan",
                confidence=0.7,
                plan_steps=[],
                estimated_cycles=1,
                replan=True,
            )

            governance = specialist.review(decision=decision, goal=None, constraint_registry_available=False)

            self.assertEqual(governance.status, DecisionStatus.DEFERRED)

