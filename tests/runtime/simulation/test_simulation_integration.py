from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.continuation.continuation_decider import ContinuationDecider  # noqa: E402
from brain.runtime.continuation.models import ContinuationDecisionType, ContinuationPolicy, PlanHealth, PlanEvaluation  # noqa: E402
from brain.runtime.evolution import EvolutionExecutor  # noqa: E402
from brain.runtime.goals import GoalFactory  # noqa: E402
from brain.runtime.memory import MemoryFacade  # noqa: E402
from brain.runtime.planning.planning_executor import PlanningExecutor  # noqa: E402
from brain.runtime.planning.progress_tracker import ProgressTracker  # noqa: E402
from brain.runtime.simulation import RouteSimulation, RouteType, SimulationBasis, SimulationResult, SimulationStore  # noqa: E402


class StubSimulator:
    def __init__(self, result: SimulationResult) -> None:
        self.result = result

    def simulate(self, *, context):  # noqa: ANN001
        return self.result


class StubContextBuilder:
    def build(self, *, plan, goal, result, session_id=None):  # noqa: ANN001
        return {"plan": plan.plan_id if plan else None, "goal": getattr(goal, "goal_id", None), "session_id": session_id, "result": result}


class SimulationIntegrationTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-simulation"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"integration-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def _plan_and_evaluation(self, workspace_root: Path):
        planning = PlanningExecutor(workspace_root)
        _, plan = planning.ensure_plan(
            session_id="sess-int",
            task_id="task-int",
            run_id="run-int",
            message="Read, patch and validate the runtime path.",
            actions=[
                {"step_id": "read", "selected_tool": "filesystem_read"},
                {"step_id": "patch", "selected_tool": "filesystem_patch_set"},
            ],
            plan_kind="linear",
        )
        assert plan is not None
        evaluation = PlanEvaluation.build(
            plan_id=plan.plan_id,
            current_step_id=plan.current_step_id,
            plan_health=PlanHealth.DEGRADED,
            progress_ratio=0.4,
            failed_step_count=1,
            blocked_step_count=0,
            retry_pressure=0.3,
            repair_outcome_summary="none",
            resumability_state="resumable",
            dependency_health="healthy",
            recent_receipt_summary={},
            recommendation_hints=[],
        )
        return plan, evaluation

    def test_continuation_behaves_like_pre_f23_when_simulator_is_absent(self) -> None:
        with self.temp_workspace() as workspace_root:
            plan, evaluation = self._plan_and_evaluation(workspace_root)
            decider = ContinuationDecider(ProgressTracker())

            decision = decider.decide(
                plan=plan,
                evaluation=evaluation,
                policy=ContinuationPolicy(),
                checkpoint_id=None,
                result={"ok": False, "error_payload": {"kind": "transient_failure"}},
            )

            self.assertEqual(decision.decision_type, ContinuationDecisionType.RETRY_STEP)

    def test_continuation_can_follow_simulator_recommendation_when_confidence_is_high(self) -> None:
        with self.temp_workspace() as workspace_root:
            plan, evaluation = self._plan_and_evaluation(workspace_root)
            sim_result = SimulationResult.build(
                recommended_route=RouteType.REPLAN,
                routes=[
                    RouteSimulation(RouteType.RETRY, 0.4, 0.3, 0.5, 0.7, [], "retry", 0.5),
                    RouteSimulation(RouteType.REPAIR, 0.45, 0.4, 0.4, 0.75, [], "repair", 0.5),
                    RouteSimulation(RouteType.REPLAN, 0.8, 0.35, 0.2, 0.8, [], "replan", 0.9),
                    RouteSimulation(RouteType.PAUSE, 0.25, 0.05, 0.1, 0.25, [], "pause", 0.6),
                ],
                simulation_basis=SimulationBasis(0, [], None, True),
                goal_id=plan.goal_id,
            )
            decider = ContinuationDecider(
                ProgressTracker(),
                simulator=StubSimulator(sim_result),
                simulation_context_builder=StubContextBuilder(),
            )

            decision = decider.decide(
                plan=plan,
                evaluation=evaluation,
                policy=ContinuationPolicy(),
                checkpoint_id=None,
                result={"ok": False, "error_payload": {"kind": "transient_failure"}},
            )

            self.assertEqual(decision.decision_type, ContinuationDecisionType.REBUILD_PLAN)
            self.assertEqual(decision.metadata["simulation_id"], sim_result.simulation_id)

    def test_continuation_blends_simulator_when_confidence_is_low(self) -> None:
        with self.temp_workspace() as workspace_root:
            plan, evaluation = self._plan_and_evaluation(workspace_root)
            sim_result = SimulationResult.build(
                recommended_route=RouteType.PAUSE,
                routes=[
                    RouteSimulation(RouteType.RETRY, 0.5, 0.3, 0.4, 0.7, [], "retry", 0.4),
                    RouteSimulation(RouteType.REPAIR, 0.55, 0.35, 0.3, 0.75, [], "repair", 0.4),
                    RouteSimulation(RouteType.REPLAN, 0.45, 0.45, 0.35, 0.55, [], "replan", 0.4),
                    RouteSimulation(RouteType.PAUSE, 0.3, 0.05, 0.1, 0.2, [], "pause", 0.45),
                ],
                simulation_basis=SimulationBasis(0, [], None, True),
                goal_id=plan.goal_id,
            )
            decider = ContinuationDecider(
                ProgressTracker(),
                simulator=StubSimulator(sim_result),
                simulation_context_builder=StubContextBuilder(),
            )

            decision = decider.decide(
                plan=plan,
                evaluation=evaluation,
                policy=ContinuationPolicy(),
                checkpoint_id=None,
                result={"ok": False, "error_payload": {"kind": "transient_failure"}},
            )

            self.assertEqual(decision.decision_type, ContinuationDecisionType.RETRY_STEP)
            self.assertEqual(decision.metadata["simulation_recommended_route"], "pause")

    def test_simulation_store_persists_and_loads_recent_entries(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = SimulationStore(workspace_root)
            result = SimulationResult.build(
                recommended_route=RouteType.RETRY,
                routes=[
                    RouteSimulation(RouteType.RETRY, 0.6, 0.3, 0.2, 0.7, [], "retry", 0.6),
                    RouteSimulation(RouteType.REPAIR, 0.55, 0.4, 0.3, 0.75, [], "repair", 0.6),
                    RouteSimulation(RouteType.REPLAN, 0.45, 0.45, 0.4, 0.5, [], "replan", 0.6),
                    RouteSimulation(RouteType.PAUSE, 0.2, 0.05, 0.1, 0.2, [], "pause", 0.6),
                ],
                simulation_basis=SimulationBasis(0, [], None, True),
                goal_id="goal-store",
            )
            store.append(result)

            recent = store.load_recent(limit=5)
            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0]["simulation_id"], result.simulation_id)

    def test_evolution_route_impact_proposals_can_be_checked_with_simulator(self) -> None:
        with self.temp_workspace() as workspace_root:
            goal = GoalFactory().create_goal(
                description="Keep the runtime inside safety boundaries.",
                intent="safety",
            )
            executor = EvolutionExecutor(workspace_root)

            payload = executor.evaluate(
                goal=goal,
                learning_update={"signals": [], "statistics": {"total_patterns": 4}},
                orchestration_update={"decision": {"route": "analysis_step"}},
                result={"error_payload": {"kind": "dependency_missing"}},
                continuation_payload={"decision_type": "pause_plan"},
            )

            self.assertIn("simulation_precheck", payload["governance"]["metadata"])

    def test_episode_metadata_can_carry_simulation_id(self) -> None:
        with self.temp_workspace() as workspace_root:
            memory = MemoryFacade(workspace_root)
            self.addCleanup(memory.close)
            goal = GoalFactory().create_goal(description="Close a goal after simulation.", intent="execution")
            memory.set_active_goal(session_id="sess-episode", goal_id=goal.goal_id, active_plan_id="plan-episode", goal_context=None)
            episode = memory.close_goal_episode(
                outcome="achieved",
                description="Goal resolved after simulated choice.",
                metadata={"goal_type": "execution", "recommended_route": "retry", "decision_type": "retry", "simulation_id": "simulation-123"},
            )

            assert episode is not None
            self.assertEqual(episode.metadata["simulation_id"], "simulation-123")
