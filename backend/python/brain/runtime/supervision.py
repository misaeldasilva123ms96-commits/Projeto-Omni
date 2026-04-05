from __future__ import annotations

from typing import Any


class CognitiveSupervisor:
    def __init__(self, *, max_nodes: int = 24, max_branches: int = 2, max_negotiation_turns: int = 6) -> None:
        self.max_nodes = max_nodes
        self.max_branches = max_branches
        self.max_negotiation_turns = max_negotiation_turns

    def inspect(
        self,
        *,
        execution_tree: dict[str, Any] | None,
        branch_plan: dict[str, Any] | None,
        negotiation_summary: dict[str, Any] | None,
        executed_steps: int,
        max_steps: int,
    ) -> dict[str, Any]:
        alerts: list[dict[str, Any]] = []
        stop = False

        node_count = len(execution_tree.get("nodes", [])) if isinstance(execution_tree, dict) and isinstance(execution_tree.get("nodes"), list) else 0
        branch_count = len(branch_plan.get("branches", [])) if isinstance(branch_plan, dict) and isinstance(branch_plan.get("branches"), list) else 0
        negotiation_turns = len(negotiation_summary.get("turns", [])) if isinstance(negotiation_summary, dict) and isinstance(negotiation_summary.get("turns"), list) else 0

        if node_count > self.max_nodes:
          alerts.append({"kind": "tree_limit", "message": "Execution tree exceeded supervision node limit."})
          stop = True
        if branch_count > self.max_branches:
          alerts.append({"kind": "branch_limit", "message": "Branch count exceeded supervision limit."})
          stop = True
        if negotiation_turns > self.max_negotiation_turns:
          alerts.append({"kind": "negotiation_limit", "message": "Negotiation depth exceeded supervision limit."})
          stop = True
        if executed_steps > max_steps:
          alerts.append({"kind": "step_limit", "message": "Execution exceeded configured step limit."})
          stop = True

        return {
            "invoked": True,
            "alerts": alerts,
            "stop_execution": stop,
            "metrics": {
                "node_count": node_count,
                "branch_count": branch_count,
                "negotiation_turns": negotiation_turns,
                "executed_steps": executed_steps,
                "max_steps": max_steps,
            },
        }
