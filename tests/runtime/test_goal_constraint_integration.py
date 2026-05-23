from __future__ import annotations

import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.continuation import ContinuationDecisionType, ContinuationExecutor  # noqa: E402
from brain.runtime.evolution import EvolutionExecutor  # noqa: E402
from brain.runtime.goals import Constraint, ConstraintType, GoalFactory, GoalStatus, GoalStore, Severity  # noqa: E402
from brain.runtime.learning.learning_executor import LearningExecutor  # noqa: E402
from brain.runtime.orchestration import OrchestrationExecutor  # noqa: E402
from brain.runtime.planning.planning_executor import PlanningExecutor  # noqa: E402


class GoalConstraintIntegrationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-goal-integration"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"phase21-int-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_planning_flow_embeds_goal_id(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = PlanningExecutor(workspace_root)
            _, plan = executor.ensure_plan(
                session_id="sess-goal-plan",
                task_id="task-goal-plan",
                run_id="run-goal-plan",
                message="Inspecionar, editar e validar um fluxo.",
                actions=[
                    {"step_id": "inspect", "selected_tool": "filesystem_read"},
                    {"step_id": "patch", "selected_tool": "filesystem_patch_set"},
                ],
                plan_kind="linear",
            )

            assert plan is not None
            self.assertIsNotNone(plan.goal_id)
            self.assertTrue(plan.metadata.get("goal_prompt_block"))

    def test_continuation_consults_goal_evaluator_before_retry_or_replan(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning = PlanningExecutor(workspace_root)
            explicit_goal = GoalFactory().create_goal(
                description="Concluir imediatamente quando o passo atual estiver ok.",
                intent="bounded_completion",
            )
            _, plan = planning.ensure_plan(
                session_id="sess-goal-cont",
                task_id="task-goal-cont",
                run_id="run-goal-cont",
                message="Executar um fluxo coerente em mais de uma etapa.",
                actions=[
                    {"step_id": "inspect", "selected_tool": "filesystem_read"},
                    {"step_id": "validate", "selected_tool": "verification_runner"},
                ],
                plan_kind="linear",
                goal=explicit_goal,
            )
            assert plan is not None
            executor = ContinuationExecutor(workspace_root)

            _, decision, _ = executor.evaluate_and_decide(plan=plan, result={"ok": True})

            assert decision is not None
            self.assertEqual(decision.decision_type, ContinuationDecisionType.COMPLETE_PLAN)
            self.assertEqual(decision.reason_code, "goal_achieved")

    def test_learning_evidence_carries_goal_id(self) -> None:
        with self.temp_workspace() as workspace_root:
            planning = PlanningExecutor(workspace_root)
            _, plan = planning.ensure_plan(
                session_id="sess-goal-learning",
                task_id="task-goal-learning",
                run_id="run-goal-learning",
                message="Ler e validar um arquivo do projeto.",
                actions=[
                    {"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"},
                    {"step_id": "validate", "selected_tool": "verification_runner", "action_type": "validate"},
                ],
                plan_kind="linear",
            )
            assert plan is not None
            executor = LearningExecutor(workspace_root)
            update = executor.ingest_runtime_artifacts(
                action={"step_id": "read", "selected_tool": "filesystem_read", "goal_id": plan.goal_id},
                result={
                    "execution_receipt": {
                        "receipt_id": "goal-learning-receipt",
                        "timestamp": "2026-04-11T12:00:00+00:00",
                        "execution_status": "succeeded",
                        "verification_status": "passed",
                    }
                },
                plan=plan,
            )

            self.assertEqual(update["ingested_evidence"], 1)
            evidence_path = workspace_root / ".logs" / "fusion-runtime" / "learning" / "evidence" / "execution_receipt.jsonl"
            payload = json.loads(evidence_path.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(payload["goal_id"], plan.goal_id)

    def test_evolution_proposal_validation_respects_active_constraints(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = GoalStore(workspace_root)
            goal = GoalFactory().create_goal(
                description="Nao mexer fora de planning.",
                intent="governance",
                constraints=[
                    Constraint.build(
                        description="Somente planning e permitido para evolucao.",
                        constraint_type=ConstraintType.SCOPE_LIMIT,
                        severity=Severity.HARD,
                        evaluation_fn="proposal_within_goal_scope",
                        metadata={"allowed_subsystems": ["planning"]},
                    )
                ],
            )
            store.save_goal(goal)
            executor = EvolutionExecutor(workspace_root)

            payload = executor.evaluate(
                goal=goal,
                learning_update={
                    "goal_id": goal.goal_id,
                    "signals": [
                        {
                            "signal_id": "signal-goal-block",
                            "signal_type": "discouraged_retry_pattern",
                            "evidence_summary": {"evidence_count": 4},
                        }
                    ],
                },
            )

            self.assertEqual(payload["governance"]["decision_type"], "blocked_by_policy")
            self.assertIn("goal_constraint_block", payload["governance"]["reason_code"])

    def test_orchestration_remains_stable_when_goal_context_is_none(self) -> None:
        with self.temp_workspace() as workspace_root:
            executor = OrchestrationExecutor(workspace_root)
            payload = executor.orchestrate(
                session_id="sess-goal-orch",
                task_id="task-goal-orch",
                run_id="run-goal-orch",
                action={"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"},
                goal_context=None,
            )

            self.assertIsNone(payload["context"]["goal_context"])
            self.assertIn("decision", payload)


if __name__ == "__main__":
    unittest.main()
