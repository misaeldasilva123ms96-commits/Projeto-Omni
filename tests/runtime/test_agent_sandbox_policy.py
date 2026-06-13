from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox import (
    AgentWorkflowPolicyDecision,
    AgentWorkflowRequest,
    evaluate_agent_workflow_request,
)
from brain.runtime.sandbox.agent_policy import (
    ADVISORY_ALLOWED_REASON,
    ALWAYS_BLOCKED_REASON,
    DISABLED_REASON,
    PR_BRANCH_BLOCKED_REASON,
    PR_PROPOSAL_ALLOWED_REASON,
    SANDBOX_REQUEST_ALLOWED_REASON,
    UNKNOWN_ACTION_REASON,
    UNKNOWN_AGENT_REASON,
)


def _request(
    action: str,
    *,
    agent_id: str = "codex",
    workflow_mode: str = "advisory_only",
    target_branch: str | None = None,
    base_branch: str = "main",
) -> AgentWorkflowRequest:
    return AgentWorkflowRequest(
        agent_id=agent_id,
        requested_action=action,
        workflow_mode=workflow_mode,
        target_branch=target_branch,
        base_branch=base_branch,
        requested_by="human",
        risk_context={"phase": "10"},
        related_phase="phase-10",
        related_pr="future",
    )


def _decision(
    action: str,
    *,
    agent_id: str = "codex",
    workflow_mode: str = "advisory_only",
    target_branch: str | None = None,
    base_branch: str = "main",
) -> AgentWorkflowPolicyDecision:
    return evaluate_agent_workflow_request(
        _request(
            action,
            agent_id=agent_id,
            workflow_mode=workflow_mode,
            target_branch=target_branch,
            base_branch=base_branch,
        )
    )


def test_disabled_mode_blocks_analyze_task() -> None:
    decision = _decision("analyze_task", workflow_mode="disabled")

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.requires_approval is True
    assert decision.reason == DISABLED_REASON
    assert decision.workflow_mode == "disabled"
    assert decision.main_branch_protected is True


def test_disabled_mode_blocks_request_sandbox_execution() -> None:
    decision = _decision("request_sandbox_execution", workflow_mode="disabled")

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.reason == DISABLED_REASON


def test_unknown_agent_is_blocked() -> None:
    decision = _decision("analyze_task", agent_id="unknown")

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.requires_approval is True
    assert decision.category == "unknown_agent"
    assert decision.risk_level == "high"
    assert decision.reason == UNKNOWN_AGENT_REASON
    assert decision.agent_role == "blocked by default"


def test_unknown_action_is_blocked() -> None:
    decision = _decision("invent_action")

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.requires_approval is True
    assert decision.category == "unknown"
    assert decision.risk_level == "high"
    assert decision.reason == UNKNOWN_ACTION_REASON


def test_advisory_only_allows_advisory_actions() -> None:
    actions = (
        "analyze_task",
        "create_plan",
        "assess_risk",
        "propose_commands",
        "propose_tests",
        "propose_patch",
        "review_diff",
        "generate_sandbox_report",
    )

    for action in actions:
        decision = _decision(action)

        assert decision.allowed is True
        assert decision.blocked is False
        assert decision.requires_approval is True
        assert decision.category == "advisory"
        assert decision.risk_level == "low"
        assert decision.reason == ADVISORY_ALLOWED_REASON
        assert decision.command_execution_allowed is False
        assert decision.direct_file_edit_allowed is False
        assert decision.git_push_allowed is False
        assert decision.git_merge_allowed is False
        assert decision.network_allowed is False
        assert decision.provider_call_allowed is False
        assert decision.vault_write_allowed is False
        assert decision.mcp_write_allowed is False
        assert decision.runtime_truth_required is True
        assert decision.sandbox_required is True


def test_advisory_only_blocks_execution_provider_network_and_vault_action() -> None:
    for action in ("execute_command", "provider_call", "network_fetch", "vault_write"):
        decision = _decision(action)

        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.requires_approval is True
        assert decision.risk_level == "critical"
        assert decision.reason == ALWAYS_BLOCKED_REASON


def test_supervised_sandbox_allows_requests_only() -> None:
    actions = (
        "request_sandbox_execution",
        "request_test_run",
        "request_patch_application",
        "request_branch_creation",
    )

    for action in actions:
        decision = _decision(action, workflow_mode="supervised_sandbox", target_branch="sandbox/phase-10")

        assert decision.allowed is True
        assert decision.blocked is False
        assert decision.requires_approval is True
        assert decision.category == "supervised_request"
        assert decision.risk_level == "medium"
        assert decision.reason == SANDBOX_REQUEST_ALLOWED_REASON
        assert decision.command_execution_allowed is False
        assert decision.direct_file_edit_allowed is False
        assert decision.runtime_truth_required is True
        assert decision.sandbox_required is True


def test_supervised_sandbox_blocks_direct_execution_edit_and_secret_access() -> None:
    for action in ("run_shell", "apply_patch_directly", "read_env", "read_secrets"):
        decision = _decision(action, workflow_mode="supervised_sandbox")

        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.risk_level == "critical"
        assert decision.reason == ALWAYS_BLOCKED_REASON


def test_supervised_sandbox_blocks_main_branch_creation_request() -> None:
    decision = _decision(
        "request_branch_creation",
        workflow_mode="supervised_sandbox",
        target_branch="main",
    )

    assert decision.allowed is False
    assert decision.category == "main_branch"
    assert decision.risk_level == "critical"
    assert decision.reason == PR_BRANCH_BLOCKED_REASON


def test_pr_proposal_only_allows_title_body_and_non_main_open_request() -> None:
    title = _decision("propose_pr_title", workflow_mode="pr_proposal_only")
    body = _decision("propose_pr_body", workflow_mode="pr_proposal_only")
    open_request = _decision(
        "request_pr_open",
        workflow_mode="pr_proposal_only",
        target_branch="sandbox/agent-workflow-policy",
        base_branch="main",
    )

    assert title.allowed is True
    assert title.reason == PR_PROPOSAL_ALLOWED_REASON
    assert body.allowed is True
    assert body.reason == PR_PROPOSAL_ALLOWED_REASON
    assert open_request.allowed is True
    assert open_request.pr_open_allowed is True
    assert open_request.git_merge_allowed is False
    assert open_request.base_branch == "main"


def test_pr_proposal_only_blocks_main_target_branch_for_open_request() -> None:
    decision = _decision(
        "request_pr_open",
        workflow_mode="pr_proposal_only",
        target_branch="main",
    )

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.category == "main_branch"
    assert decision.reason == PR_BRANCH_BLOCKED_REASON


def test_pr_proposal_only_blocks_merge_actions() -> None:
    for action in ("gh_pr_merge", "auto_merge", "merge_main"):
        decision = _decision(action, workflow_mode="pr_proposal_only", target_branch="sandbox/branch")

        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.risk_level == "critical"
        assert decision.git_merge_allowed is False


def test_always_blocked_main_and_governance_actions_are_critical() -> None:
    for action in (
        "push_main",
        "merge_main",
        "edit_main",
        "bypass_governance",
        "lower_ci_threshold",
        "skip_security_scan",
    ):
        decision = _decision(action)

        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.risk_level == "critical"
        assert decision.main_branch_protected is True


def test_safety_flags_remain_false() -> None:
    decision = _decision("request_sandbox_execution", workflow_mode="supervised_sandbox")

    assert decision.main_branch_protected is True
    assert decision.command_execution_allowed is False
    assert decision.direct_file_edit_allowed is False
    assert decision.git_push_allowed is False
    assert decision.git_merge_allowed is False
    assert decision.network_allowed is False
    assert decision.provider_call_allowed is False
    assert decision.vault_write_allowed is False
    assert decision.mcp_write_allowed is False
    assert decision.runtime_truth_required is True
    assert decision.sandbox_required is True


def test_request_and_decision_objects_are_json_serializable() -> None:
    request = _request(
        "request_pr_open",
        workflow_mode="pr_proposal_only",
        target_branch="sandbox/agent-workflow-policy",
    )
    decision = evaluate_agent_workflow_request(request)

    request_json = json.dumps(request.to_dict(), sort_keys=True)
    decision_json = json.dumps(decision.to_dict(), sort_keys=True)

    assert '"requested_action": "request_pr_open"' in request_json
    assert '"allowed": true' in decision_json
    assert '"main_branch_protected": true' in decision_json
