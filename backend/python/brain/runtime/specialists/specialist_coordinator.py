from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from brain.runtime.goals import ConstraintRegistry, GoalEvaluator, GoalStore, ToleranceType
from brain.runtime.language.protocol import (
    build_specialist_request,
    build_tool_execution,
    runtime_protocol_to_legacy_dict,
)
from brain.runtime.memory import MemoryFacade
from brain.runtime.planning import TaskPlan
from brain.runtime.simulation import ActionSimulator, SimulationContextBuilder, SimulationStore

from .executor_specialist import ExecutorSpecialist
from .governance_specialist import GovernanceSpecialist
from .models import CoordinationTrace, GovernanceVerdict
from .planner_specialist import PlannerSpecialist
from .repair_specialist import RepairSpecialist
from .specialist_store import SpecialistStore
from .synthesis_specialist import SynthesisSpecialist
from .validator_specialist import ValidatorSpecialist


class SpecialistCoordinator:
    def __init__(
        self,
        root: Path,
        *,
        memory_facade: MemoryFacade | None = None,
        simulator: ActionSimulator | None = None,
        simulation_store: SimulationStore | None = None,
    ) -> None:
        self.root = root
        self.memory_facade = memory_facade
        self.goal_store = GoalStore(root)
        self.goal_evaluator = GoalEvaluator(ConstraintRegistry())
        self.simulator = simulator
        self.simulation_store = simulation_store or SimulationStore(root)
        self.simulation_context_builder = SimulationContextBuilder(memory_facade=memory_facade)
        self.store = SpecialistStore(root)
        self.planner = PlannerSpecialist(root=root, goal_store=self.goal_store, memory_facade=memory_facade, simulation_store=self.simulation_store)
        self.executor = ExecutorSpecialist(root=root, goal_store=self.goal_store, memory_facade=memory_facade, simulation_store=self.simulation_store)
        self.validator = ValidatorSpecialist(
            root=root,
            goal_store=self.goal_store,
            memory_facade=memory_facade,
            simulation_store=self.simulation_store,
            goal_evaluator=self.goal_evaluator,
        )
        self.repair = RepairSpecialist(root=root, goal_store=self.goal_store, memory_facade=memory_facade, simulation_store=self.simulation_store)
        self.governance = GovernanceSpecialist(root=root, goal_store=self.goal_store, memory_facade=memory_facade, simulation_store=self.simulation_store)
        self.synthesis = SynthesisSpecialist(root=root, goal_store=self.goal_store, memory_facade=memory_facade, simulation_store=self.simulation_store)
        self._locks_guard = threading.RLock()
        self._session_locks: dict[str, threading.RLock] = {}

    @contextmanager
    def _session_lock(self, session_id: str | None):
        key = session_id or "default-session"
        with self._locks_guard:
            lock = self._session_locks.setdefault(key, threading.RLock())
        with lock:
            yield

    def coordinate(
        self,
        *,
        session_id: str | None,
        goal_id: str | None,
        action: dict[str, Any],
        plan: TaskPlan | None,
        execute_callback: Callable[[], dict[str, Any]],
        goal_evaluation_state: dict[str, Any] | None = None,
    ) -> CoordinationTrace:
        with self._session_lock(session_id):
            goal = self.goal_store.get_by_id(goal_id) if goal_id else None
            simulation_result = self._simulation_for(plan=plan, goal=goal)
            trace = CoordinationTrace.build(
                goal_id=goal_id,
                session_id=session_id,
                metadata={"plan_id": getattr(plan, "plan_id", None), "step_id": action.get("step_id")},
            )
            intent_hint = None
            if isinstance(action, dict):
                raw_intent = action.get("intent") or action.get("selected_tool")
                if raw_intent is not None:
                    intent_hint = str(raw_intent).strip() or None
            run_id = str(action.get("run_id")).strip() if action.get("run_id") not in (None, "") else None
            open_proto = build_specialist_request(
                source_component="specialist_coordinator",
                target_component="planner",
                session_id=session_id,
                run_id=run_id,
                trace_id=trace.trace_id,
                intent=intent_hint or "specialist_coordination",
                payload={
                    "entities": {"action": dict(action)},
                    "constraints": {},
                },
                routing={"stage": "coordination_open", "replan": bool(action.get("replan", False))},
            )
            trace.metadata.setdefault("oil_runtime_protocol_envelopes", []).append(open_proto.serialize())
            trace.metadata["oil_runtime_protocol_open_legacy"] = runtime_protocol_to_legacy_dict(open_proto)
            decisions = []

            plan_decision = self.planner.plan(
                goal_id=goal_id,
                action=action,
                plan=plan,
                simulation_result=simulation_result,
                replan=bool(action.get("replan", False)),
            )
            decisions.append(plan_decision)
            trace.append_decision(plan_decision)

            governance_plan = self.governance.review(
                decision=plan_decision,
                goal=goal,
                constraint_registry_available=bool(goal is not None),
            )
            decisions.append(governance_plan)
            trace.append_decision(governance_plan)
            if governance_plan.verdict == GovernanceVerdict.BLOCK:
                return self._finish(trace=trace, final_outcome="blocked_by_governance")

            tool_proto = build_tool_execution(
                source_component="specialist_coordinator",
                target_component="executor",
                session_id=session_id,
                run_id=run_id,
                trace_id=trace.trace_id,
                intent=intent_hint or "execute_tool_like_action",
                payload={
                    "entities": {"action": dict(action)},
                    "constraints": {},
                },
                routing={"stage": "pre_execution"},
            )
            trace.metadata.setdefault("oil_runtime_protocol_envelopes", []).append(tool_proto.serialize())

            execution_decision = self.executor.execute(
                goal_id=goal_id,
                simulation_id=simulation_result.simulation_id if simulation_result is not None else None,
                action=action,
                execute_callback=execute_callback,
            )
            execution_decision.metadata["result_ok"] = bool(execution_decision.result.get("ok"))
            execution_decision.metadata["constraint_risk"] = float(
                ((simulation_result.route_for(simulation_result.recommended_route).constraint_risk) if simulation_result and simulation_result.route_for(simulation_result.recommended_route) else 0.0)
            )
            decisions.append(execution_decision)
            trace.append_decision(execution_decision)

            governance_execution = self.governance.review(
                decision=execution_decision,
                goal=goal,
                constraint_registry_available=bool(goal is not None),
            )
            decisions.append(governance_execution)
            trace.append_decision(governance_execution)
            if governance_execution.verdict == GovernanceVerdict.BLOCK:
                return self._finish(trace=trace, final_outcome="blocked_after_execution")

            goal_eval = None
            if goal is not None:
                goal_eval = self.goal_evaluator.evaluate(
                    goal=goal,
                    runtime_state=goal_evaluation_state or execution_decision.result,
                    memory_facade=self.memory_facade,
                )
            validation_decision = self.validator.validate(
                goal=goal,
                result=execution_decision.result,
                goal_evaluation=goal_eval,
                simulation_id=simulation_result.simulation_id if simulation_result is not None else None,
            )
            decisions.append(validation_decision)
            trace.append_decision(validation_decision)

            if validation_decision.should_fail:
                repair_limit = self._repair_limit(goal=goal)
                repair_decision = self.repair.advise(
                    goal_id=goal_id,
                    result=execution_decision.result,
                    simulation_id=simulation_result.simulation_id if simulation_result is not None else None,
                    simulation_route=simulation_result.recommended_route.value if simulation_result is not None else None,
                    max_repairs=repair_limit,
                    current_repairs=int(action.get("repair_count", 0) or 0),
                )
                if repair_decision is not None:
                    decisions.append(repair_decision)
                    trace.append_decision(repair_decision)
                    governance_repair = self.governance.review(
                        decision=repair_decision,
                        goal=goal,
                        constraint_registry_available=bool(goal is not None),
                    )
                    decisions.append(governance_repair)
                    trace.append_decision(governance_repair)
                    if governance_repair.verdict == GovernanceVerdict.BLOCK:
                        return self._finish(trace=trace, final_outcome="repair_blocked")

            final_outcome = "achieved" if validation_decision.is_achieved else ("failed" if validation_decision.should_fail else "completed_step")
            synthesis = self.synthesis.synthesize(
                goal_id=goal_id,
                simulation_id=simulation_result.simulation_id if simulation_result is not None else None,
                decisions=decisions,
                final_outcome=final_outcome,
            )
            trace.append_decision(synthesis)
            return self._finish(trace=trace, final_outcome=final_outcome)

    def _finish(self, *, trace: CoordinationTrace, final_outcome: str) -> CoordinationTrace:
        trace.finish(final_outcome)
        self.store.append_trace(trace)
        return trace

    def _simulation_for(self, *, plan: TaskPlan | None, goal: Any) -> Any:
        if self.simulator is None or plan is None:
            return None
        context = self.simulation_context_builder.build(
            plan=plan,
            goal=goal,
            result=None,
            session_id=plan.session_id,
        )
        return self.simulator.simulate(context=context)

    @staticmethod
    def _repair_limit(*, goal: Any) -> int:
        if goal is None:
            return 2
        for tolerance in getattr(goal, "failure_tolerances", []):
            if tolerance.tolerance_type == ToleranceType.MAX_REPAIRS:
                return max(1, int(tolerance.threshold or 1))
        return 2
