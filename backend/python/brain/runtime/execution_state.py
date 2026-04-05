from __future__ import annotations

from typing import Any


def build_execution_state(
    *,
    session_id: str,
    task_id: str,
    run_id: str,
    execution_tree: dict[str, Any] | None,
    branch_state: dict[str, Any] | None,
    cooperative_plan: dict[str, Any] | None,
    negotiation_summary: dict[str, Any] | None,
    simulation_summary: dict[str, Any] | None,
    strategy_suggestions: list[dict[str, Any]] | None,
    policy_summary: list[dict[str, Any]] | None,
    fusion_summary: dict[str, Any] | None,
    supervision: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "task_id": task_id,
        "run_id": run_id,
        "goal_tree": execution_tree or {},
        "branch_states": branch_state or {},
        "agent_contributions": cooperative_plan or {},
        "negotiation": negotiation_summary or {},
        "simulation_results": simulation_summary or {},
        "strategy_usage": strategy_suggestions or [],
        "policy_decisions": policy_summary or [],
        "fusion_outputs": fusion_summary or {},
        "runtime_metrics": (supervision or {}).get("metrics", {}),
        "supervision": supervision or {},
    }
