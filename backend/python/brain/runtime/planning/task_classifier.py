from __future__ import annotations

from typing import Any

from .models import TaskClassification, TaskClassificationDecision


READ_ONLY_TOOLS = {
    "read_file",
    "filesystem_read",
    "directory_tree",
    "glob_search",
    "grep_search",
    "code_search",
    "dependency_inspection",
    "git_status",
    "git_diff",
}

MUTATING_OR_VALIDATING_TOOLS = {
    "write_file",
    "filesystem_write",
    "filesystem_patch_set",
    "git_commit",
    "test_runner",
    "verification_runner",
    "shell_command",
    "package_manager",
}


class DeterministicTaskClassifier:
    def classify(
        self,
        *,
        message: str,
        actions: list[dict[str, Any]],
        plan_kind: str = "linear",
        branch_plan: dict[str, Any] | None = None,
        start_index: int = 0,
        engineering_workflow: dict[str, Any] | None = None,
    ) -> TaskClassificationDecision:
        if not actions:
            return TaskClassificationDecision(
                classification=TaskClassification.NON_PLANNABLE,
                reason_code="no_actions",
                summary="The runtime request did not produce actionable steps for operational planning.",
                should_plan=False,
            )

        if start_index > 0:
            return TaskClassificationDecision(
                classification=TaskClassification.RESUMABLE_WORKFLOW,
                reason_code="resuming_from_nonzero_index",
                summary="The runtime is resuming from a later action index, so durable plan state is required.",
                should_plan=True,
            )

        tools = [str(action.get("selected_tool", "")).strip() for action in actions]
        action_count = len(actions)
        has_graph = plan_kind == "graph"
        has_branches = bool(branch_plan and branch_plan.get("branches"))
        has_engineering_workflow = bool(engineering_workflow)
        has_mutation = any(tool in MUTATING_OR_VALIDATING_TOOLS for tool in tools)
        has_retries = any(int((action.get("retry_policy", {}) or {}).get("max_attempts", 1) or 1) > 1 for action in actions)

        if has_graph or has_branches or action_count >= 4:
            return TaskClassificationDecision(
                classification=TaskClassification.LONG_RUNNING_WORK,
                reason_code="graph_branch_or_large_action_set",
                summary="The runtime has graph, branch, or high-step execution characteristics that require durable continuity.",
                should_plan=True,
            )

        if has_engineering_workflow or has_retries:
            return TaskClassificationDecision(
                classification=TaskClassification.RESUMABLE_WORKFLOW,
                reason_code="workflow_or_retry_driven_execution",
                summary="The runtime has workflow or retry characteristics that benefit from resumable planning.",
                should_plan=True,
            )

        if action_count > 1 or has_mutation:
            return TaskClassificationDecision(
                classification=TaskClassification.MULTI_STEP,
                reason_code="multiple_actions_or_mutation",
                summary="The runtime request spans multiple operational steps or includes stateful execution.",
                should_plan=True,
            )

        normalized_message = " ".join(str(message or "").strip().lower().split())
        single_tool = tools[0]
        if single_tool in READ_ONLY_TOOLS and len(normalized_message) < 220:
            return TaskClassificationDecision(
                classification=TaskClassification.SINGLE_STEP,
                reason_code="single_safe_read_action",
                summary="The request is a short, safe, single-step read operation and does not need durable planning.",
                should_plan=False,
            )

        return TaskClassificationDecision(
            classification=TaskClassification.SINGLE_STEP,
            reason_code="single_action_execution",
            summary="The runtime request is operational but short enough to run without a persisted plan.",
            should_plan=False,
        )
