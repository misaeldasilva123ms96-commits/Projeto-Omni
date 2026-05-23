"""Specialist coordination and guarded execution dispatch (Phase 30.10 decomposition)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ExecutionDispatchService:
    """Delegates specialist coordination; execution core stays on the orchestrator."""

    __slots__ = ("_governance", "_orch", "_progress_fn")

    def __init__(
        self,
        orchestrator: object,
        *,
        governance: object,
        progress_fn: Callable[[list[dict[str, Any]]], float],
    ) -> None:
        self._orch = orchestrator
        self._governance = governance
        self._progress_fn = progress_fn

    def execute_single_action_with_specialists(
        self,
        *,
        action: dict[str, Any],
        step_results: list[dict[str, Any]],
        semantic_retrieval: object,
        session_id: str,
        task_id: str,
        run_id: str,
        learning_guidance: object = None,
        operational_plan: Any = None,
    ) -> dict[str, Any]:
        o = self._orch
        if operational_plan is None or not getattr(operational_plan, "goal_id", None):
            return o._execute_single_action_core(
                action=action,
                step_results=step_results,
                semantic_retrieval=semantic_retrieval,
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                learning_guidance=learning_guidance,
                operational_plan=operational_plan,
            )
        trace = o.specialist_coordinator.coordinate(
            session_id=session_id,
            goal_id=operational_plan.goal_id,
            action=action,
            plan=operational_plan,
            execute_callback=lambda: o._execute_single_action_core(
                action=action,
                step_results=step_results,
                semantic_retrieval=semantic_retrieval,
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                learning_guidance=learning_guidance,
                operational_plan=operational_plan,
            ),
        )
        if o._coordination_trace_has_governance_hold(trace.as_dict()):
            self._governance.apply_governance_hold_after_specialist(
                run_id=run_id,
                progress_score=self._progress_fn(step_results),
            )
        result = o._result_from_coordination_trace(trace.as_dict()) or o._execute_single_action_core(
            action=action,
            step_results=step_results,
            semantic_retrieval=semantic_retrieval,
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            learning_guidance=learning_guidance,
            operational_plan=operational_plan,
        )
        result["coordination_trace"] = trace.as_dict()
        return result
