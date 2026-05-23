"""Checkpoint persistence for orchestrator flows (Phase 30.10 decomposition)."""

from __future__ import annotations

from typing import Any

from brain.runtime.checkpoint_store import CheckpointStore


class SessionService:
    __slots__ = ("_checkpoint_store",)

    def __init__(self, checkpoint_store: CheckpointStore) -> None:
        self._checkpoint_store = checkpoint_store

    def write_checkpoint(
        self,
        *,
        run_id: str,
        task_id: str,
        session_id: str,
        message: str,
        actions: list[dict[str, Any]],
        next_step_index: int,
        completed_steps: list[dict[str, Any]],
        plan_graph: dict[str, Any] | None,
        plan_hierarchy: dict[str, Any] | None,
        plan_signature: str,
        status: str,
        branch_state: dict[str, Any] | None,
        simulation_summary: dict[str, Any] | None,
        cooperative_plan: dict[str, Any] | None,
        strategy_suggestions: object,
        policy_summary: object = None,
        execution_tree: dict[str, Any] | None = None,
        negotiation_summary: dict[str, Any] | None = None,
        strategy_optimization: dict[str, Any] | None = None,
        supervision: dict[str, Any] | None = None,
        repository_analysis: dict[str, Any] | None = None,
        engineering_data: dict[str, Any] | None = None,
    ) -> None:
        remaining_actions = actions[next_step_index:] if next_step_index < len(actions) else []
        self._checkpoint_store.save(
            run_id,
            {
                "task_id": task_id,
                "session_id": session_id,
                "message": message,
                "status": status,
                "next_step_index": next_step_index,
                "completed_steps": completed_steps,
                "remaining_actions": remaining_actions,
                "total_actions": len(actions),
                "plan_graph": plan_graph,
                "plan_hierarchy": plan_hierarchy,
                "plan_signature": plan_signature,
                "branch_state": branch_state,
                "simulation_summary": simulation_summary,
                "cooperative_plan": cooperative_plan,
                "strategy_suggestions": strategy_suggestions if isinstance(strategy_suggestions, list) else [],
                "policy_summary": policy_summary if isinstance(policy_summary, list) else [],
                "execution_tree": execution_tree,
                "negotiation_summary": negotiation_summary,
                "strategy_optimization": strategy_optimization,
                "supervision": supervision,
                "repository_analysis": repository_analysis,
                "engineering_data": engineering_data,
            },
        )
