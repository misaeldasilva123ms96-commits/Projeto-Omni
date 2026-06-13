"""Policy-only classification for future governed sandbox agent workflows.

This module does not execute agents, commands, providers, MCP tools, network
calls, file edits, vault writes, or Git mutations.
"""

from __future__ import annotations

from .agent_types import AgentWorkflowPolicyDecision, AgentWorkflowRequest

AGENT_POLICY_EVIDENCE_VERSION = "1.0"

AGENT_ROLES = {
    "omni": "governance, routing, runtime truth, approval boundary",
    "hermes": "analysis, planning, risk review",
    "aider": "supervised code editing proposal",
    "codex": "investigation, command proposal, code review proposal",
    "claude": "optional code review/planning proposal",
    "unknown": "blocked by default",
}

WORKFLOW_MODE_DISABLED = "disabled"
WORKFLOW_MODE_ADVISORY_ONLY = "advisory_only"
WORKFLOW_MODE_SUPERVISED_SANDBOX = "supervised_sandbox"
WORKFLOW_MODE_PR_PROPOSAL_ONLY = "pr_proposal_only"
WORKFLOW_MODE_BLOCKED = "blocked"

ADVISORY_ACTIONS = frozenset(
    {
        "analyze_task",
        "create_plan",
        "assess_risk",
        "propose_commands",
        "propose_tests",
        "propose_patch",
        "review_diff",
        "generate_sandbox_report",
    }
)

SUPERVISED_SANDBOX_ACTIONS = frozenset(
    {
        "request_sandbox_execution",
        "request_test_run",
        "request_patch_application",
        "request_branch_creation",
        "request_pr_creation",
    }
)

PR_PROPOSAL_ACTIONS = frozenset(
    {
        "propose_pr_title",
        "propose_pr_body",
        "request_pr_open",
    }
)

ALWAYS_BLOCKED_ACTIONS = frozenset(
    {
        "execute_command",
        "run_shell",
        "apply_patch_directly",
        "edit_main",
        "push_main",
        "merge_main",
        "gh_pr_merge",
        "auto_merge",
        "delete_branch",
        "read_env",
        "read_secrets",
        "exfiltrate_data",
        "network_fetch",
        "provider_call",
        "mcp_write",
        "vault_write",
        "approve_vault_note",
        "edit_approved_vault_note",
        "bypass_governance",
        "disable_tests",
        "lower_ci_threshold",
        "skip_security_scan",
    }
)

SUPPORTED_ACTIONS = ADVISORY_ACTIONS | SUPERVISED_SANDBOX_ACTIONS | PR_PROPOSAL_ACTIONS
SUPPORTED_MODES = frozenset(
    {
        WORKFLOW_MODE_DISABLED,
        WORKFLOW_MODE_ADVISORY_ONLY,
        WORKFLOW_MODE_SUPERVISED_SANDBOX,
        WORKFLOW_MODE_PR_PROPOSAL_ONLY,
        WORKFLOW_MODE_BLOCKED,
    }
)

DISABLED_REASON = "Agent workflow is disabled by default."
BLOCKED_MODE_REASON = "Agent workflow mode is blocked by governance policy."
UNKNOWN_AGENT_REASON = "Unknown agent identity is blocked by default."
UNKNOWN_ACTION_REASON = "Unknown agent workflow action is blocked by default."
ALWAYS_BLOCKED_REASON = "Agent workflow action is always blocked by governance policy."
ADVISORY_ALLOWED_REASON = "Advisory-only mode permits this proposal action."
SANDBOX_REQUEST_ALLOWED_REASON = "Supervised sandbox mode permits this request only."
PR_PROPOSAL_ALLOWED_REASON = "PR proposal mode permits this proposal action."
PR_BRANCH_BLOCKED_REASON = "PR opening requests require a non-main target branch."
UNSUPPORTED_MODE_REASON = "Unsupported agent workflow mode is blocked."


def evaluate_agent_workflow_request(
    request: AgentWorkflowRequest,
) -> AgentWorkflowPolicyDecision:
    agent_id = str(request.agent_id or "unknown").strip().lower() or "unknown"
    action = str(request.requested_action or "").strip()
    mode = str(request.workflow_mode or WORKFLOW_MODE_DISABLED).strip() or WORKFLOW_MODE_DISABLED
    target_branch = str(request.target_branch or "").strip()
    base_branch = str(request.base_branch or "main").strip() or "main"

    if mode == WORKFLOW_MODE_DISABLED:
        return _decision(
            allowed=False,
            request=request,
            agent_id=agent_id,
            action=action,
            mode=mode,
            target_branch=target_branch,
            base_branch=base_branch,
            category=_category_for_action(action),
            risk_level="high",
            reason=DISABLED_REASON,
        )

    if mode not in SUPPORTED_MODES:
        return _decision(
            allowed=False,
            request=request,
            agent_id=agent_id,
            action=action,
            mode=mode,
            target_branch=target_branch,
            base_branch=base_branch,
            category="unsupported_mode",
            risk_level="high",
            reason=UNSUPPORTED_MODE_REASON,
        )

    if mode == WORKFLOW_MODE_BLOCKED:
        return _decision(
            allowed=False,
            request=request,
            agent_id=agent_id,
            action=action,
            mode=mode,
            target_branch=target_branch,
            base_branch=base_branch,
            category=_category_for_action(action),
            risk_level="high",
            reason=BLOCKED_MODE_REASON,
        )

    if agent_id not in AGENT_ROLES or agent_id == "unknown":
        return _decision(
            allowed=False,
            request=request,
            agent_id=agent_id,
            action=action,
            mode=mode,
            target_branch=target_branch,
            base_branch=base_branch,
            category="unknown_agent",
            risk_level="high",
            reason=UNKNOWN_AGENT_REASON,
        )

    if action in ALWAYS_BLOCKED_ACTIONS:
        return _decision(
            allowed=False,
            request=request,
            agent_id=agent_id,
            action=action,
            mode=mode,
            target_branch=target_branch,
            base_branch=base_branch,
            category=_category_for_action(action),
            risk_level="critical",
            reason=ALWAYS_BLOCKED_REASON,
        )

    if action not in SUPPORTED_ACTIONS:
        return _decision(
            allowed=False,
            request=request,
            agent_id=agent_id,
            action=action,
            mode=mode,
            target_branch=target_branch,
            base_branch=base_branch,
            category="unknown",
            risk_level="high",
            reason=UNKNOWN_ACTION_REASON,
        )

    if mode == WORKFLOW_MODE_ADVISORY_ONLY and action in ADVISORY_ACTIONS:
        return _decision(
            allowed=True,
            request=request,
            agent_id=agent_id,
            action=action,
            mode=mode,
            target_branch=target_branch,
            base_branch=base_branch,
            category="advisory",
            risk_level="low",
            reason=ADVISORY_ALLOWED_REASON,
            runtime_truth_required=True,
            sandbox_required=True,
        )

    if mode == WORKFLOW_MODE_SUPERVISED_SANDBOX and action in SUPERVISED_SANDBOX_ACTIONS:
        if action == "request_branch_creation" and _is_main_branch(target_branch):
            return _decision(
                allowed=False,
                request=request,
                agent_id=agent_id,
                action=action,
                mode=mode,
                target_branch=target_branch,
                base_branch=base_branch,
                category="main_branch",
                risk_level="critical",
                reason=PR_BRANCH_BLOCKED_REASON,
            )
        return _decision(
            allowed=True,
            request=request,
            agent_id=agent_id,
            action=action,
            mode=mode,
            target_branch=target_branch,
            base_branch=base_branch,
            category="supervised_request",
            risk_level="medium",
            reason=SANDBOX_REQUEST_ALLOWED_REASON,
            runtime_truth_required=True,
            sandbox_required=True,
        )

    if mode == WORKFLOW_MODE_PR_PROPOSAL_ONLY and action in PR_PROPOSAL_ACTIONS:
        if action == "request_pr_open":
            if not target_branch or _is_main_branch(target_branch):
                return _decision(
                    allowed=False,
                    request=request,
                    agent_id=agent_id,
                    action=action,
                    mode=mode,
                    target_branch=target_branch,
                    base_branch=base_branch,
                    category="main_branch",
                    risk_level="critical",
                    reason=PR_BRANCH_BLOCKED_REASON,
                )
            return _decision(
                allowed=True,
                request=request,
                agent_id=agent_id,
                action=action,
                mode=mode,
                target_branch=target_branch,
                base_branch=base_branch,
                category="pr_proposal",
                risk_level="medium",
                reason=PR_PROPOSAL_ALLOWED_REASON,
                pr_open_allowed=True,
                runtime_truth_required=True,
            )
        return _decision(
            allowed=True,
            request=request,
            agent_id=agent_id,
            action=action,
            mode=mode,
            target_branch=target_branch,
            base_branch=base_branch,
            category="pr_proposal",
            risk_level="low",
            reason=PR_PROPOSAL_ALLOWED_REASON,
            runtime_truth_required=True,
        )

    return _decision(
        allowed=False,
        request=request,
        agent_id=agent_id,
        action=action,
        mode=mode,
        target_branch=target_branch,
        base_branch=base_branch,
        category="mode_mismatch",
        risk_level="high",
        reason=UNKNOWN_ACTION_REASON,
    )


def _decision(
    *,
    allowed: bool,
    request: AgentWorkflowRequest,
    agent_id: str,
    action: str,
    mode: str,
    target_branch: str,
    base_branch: str,
    category: str,
    risk_level: str,
    reason: str,
    pr_open_allowed: bool = False,
    runtime_truth_required: bool = False,
    sandbox_required: bool = False,
) -> AgentWorkflowPolicyDecision:
    return AgentWorkflowPolicyDecision(
        allowed=allowed,
        blocked=not allowed,
        requires_approval=True,
        agent_id=agent_id,
        agent_role=AGENT_ROLES.get(agent_id, AGENT_ROLES["unknown"]),
        requested_action=action,
        workflow_mode=mode,
        category=category,
        risk_level=risk_level,
        reason=reason,
        target_branch=target_branch,
        base_branch=base_branch,
        main_branch_protected=True,
        command_execution_allowed=False,
        direct_file_edit_allowed=False,
        git_push_allowed=False,
        git_merge_allowed=False,
        pr_open_allowed=pr_open_allowed and allowed,
        network_allowed=False,
        provider_call_allowed=False,
        vault_write_allowed=False,
        mcp_write_allowed=False,
        runtime_truth_required=runtime_truth_required and allowed,
        sandbox_required=sandbox_required and allowed,
        evidence_version=AGENT_POLICY_EVIDENCE_VERSION,
    )


def _is_main_branch(branch: str) -> bool:
    return str(branch or "").strip().lower() == "main"


def _category_for_action(action: str) -> str:
    if action in ADVISORY_ACTIONS:
        return "advisory"
    if action in SUPERVISED_SANDBOX_ACTIONS:
        return "supervised_request"
    if action in PR_PROPOSAL_ACTIONS:
        return "pr_proposal"
    if action in {"push_main", "merge_main", "gh_pr_merge", "auto_merge", "edit_main"}:
        return "main_branch"
    if action in {"execute_command", "run_shell", "apply_patch_directly"}:
        return "execution_or_edit"
    if action in {"network_fetch", "provider_call", "exfiltrate_data"}:
        return "network_or_provider"
    if action in {"mcp_write", "vault_write", "approve_vault_note", "edit_approved_vault_note"}:
        return "governed_write"
    if action in {"read_env", "read_secrets"}:
        return "secret_access"
    if action in {"bypass_governance", "disable_tests", "lower_ci_threshold", "skip_security_scan"}:
        return "governance_bypass"
    return "unknown"
