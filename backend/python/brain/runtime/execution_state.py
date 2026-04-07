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
    repository_analysis: dict[str, Any] | None = None,
    engineering_data: dict[str, Any] | None = None,
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
        "repository_analysis": repository_analysis or {},
        "impact_map": (engineering_data or {}).get("impact_map", {}),
        "milestone_tree": (engineering_data or {}).get("milestone_state", {}),
        "workspace_state": (engineering_data or {}).get("workspace_state", {}),
        "code_changes": (engineering_data or {}).get("patch_history", []),
        "patch_sets": (engineering_data or {}).get("patch_sets", []),
        "test_results": (engineering_data or {}).get("test_results", {}),
        "verification_status": (engineering_data or {}).get("verification_summary", {}),
        "integration_status": (engineering_data or {}).get("pr_summary", {}).get("merge_readiness", {}),
        "merge_readiness": (engineering_data or {}).get("pr_summary", {}).get("merge_readiness", {}),
        "unresolved_blockers": [
            blocker
            for milestone in (engineering_data or {}).get("milestone_state", {}).get("milestones", [])
            if milestone.get("state") == "blocked"
            for blocker in (milestone.get("blockers", []) or [])
        ],
        "pr_summary": (engineering_data or {}).get("pr_summary", {}),
        "debug_iterations": (engineering_data or {}).get("debug_iterations", []),
        "runtime_metrics": (supervision or {}).get("metrics", {}),
        "supervision": supervision or {},
    }
