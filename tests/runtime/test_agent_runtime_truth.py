from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox import (  # noqa: E402
    AgentWorkflowPolicyDecision,
    AgentWorkflowRequest,
    build_agent_workflow_evidence,
    evaluate_agent_workflow_request,
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
        risk_context={"phase": "11"},
        related_phase="phase-11",
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


def _evidence(decision: AgentWorkflowPolicyDecision):
    return build_agent_workflow_evidence(
        decision,
        requested_by="human",
        session_id="session-1",
        task_id="task-1",
        related_phase="phase-11",
        related_pr="future",
        notes="safe note",
        timestamp="2026-06-13T00:00:00+00:00",
    )


def test_creates_evidence_from_allowed_advisory_decision() -> None:
    evidence = _evidence(_decision("analyze_task"))

    assert evidence.event_type == "agent.workflow.policy_decision"
    assert evidence.runtime_mode == "AGENT_POLICY_ONLY"
    assert evidence.evidence_version == "1.0"
    assert evidence.agent_id == "codex"
    assert evidence.requested_action == "analyze_task"
    assert evidence.policy_allowed is True
    assert evidence.policy_blocked is False
    assert evidence.governance_decision == "requires_approval"
    assert evidence.runtime_truth_required is True


def test_creates_evidence_from_blocked_disabled_mode_decision() -> None:
    evidence = _evidence(_decision("analyze_task", workflow_mode="disabled"))

    assert evidence.policy_allowed is False
    assert evidence.policy_blocked is True
    assert evidence.workflow_mode == "disabled"
    assert evidence.governance_decision == "blocked"


def test_creates_evidence_from_requires_approval_supervised_decision() -> None:
    evidence = _evidence(
        _decision(
            "request_test_run",
            workflow_mode="supervised_sandbox",
            target_branch="sandbox/agent-runtime-truth",
        )
    )

    assert evidence.policy_allowed is True
    assert evidence.policy_requires_approval is True
    assert evidence.policy_category == "supervised_request"
    assert evidence.sandbox_required is True
    assert evidence.governance_decision == "requires_approval"


def test_creates_evidence_from_pr_proposal_decision() -> None:
    evidence = _evidence(
        _decision(
            "request_pr_open",
            workflow_mode="pr_proposal_only",
            target_branch="sandbox/agent-runtime-truth",
            base_branch="main",
        )
    )

    assert evidence.policy_allowed is True
    assert evidence.pr_open_allowed is True
    assert evidence.git_merge_allowed is False
    assert evidence.target_branch == "sandbox/agent-runtime-truth"
    assert evidence.base_branch == "main"


def test_safety_defaults_remain_false() -> None:
    evidence = _evidence(_decision("analyze_task"))

    assert evidence.agent_executed is False
    assert evidence.command_executed is False
    assert evidence.network_used is False
    assert evidence.provider_called is False
    assert evidence.mcp_used is False
    assert evidence.vault_written is False
    assert evidence.git_mutated is False
    assert evidence.pr_created is False
    assert evidence.main_modified is False
    assert evidence.user_approval_state == "not_requested"


def test_blocked_policy_maps_to_blocked() -> None:
    evidence = _evidence(_decision("merge_main"))

    assert evidence.policy_blocked is True
    assert evidence.governance_decision == "blocked"


def test_allowed_without_approval_maps_to_allowed() -> None:
    decision = replace(_decision("analyze_task"), requires_approval=False)
    evidence = _evidence(decision)

    assert evidence.policy_allowed is True
    assert evidence.policy_requires_approval is False
    assert evidence.governance_decision == "allowed"


def test_inconsistent_allowed_and_blocked_maps_to_blocked() -> None:
    decision = replace(_decision("analyze_task"), blocked=True)
    evidence = _evidence(decision)

    assert evidence.policy_allowed is True
    assert evidence.policy_blocked is True
    assert evidence.governance_decision == "blocked"
    assert "Inconsistent unsafe policy evidence" in (evidence.notes or "")


def test_unsafe_capability_flags_force_blocked() -> None:
    base_decision = _decision("analyze_task")
    unsafe_variants = (
        replace(base_decision, command_execution_allowed=True),
        replace(base_decision, direct_file_edit_allowed=True),
        replace(base_decision, git_push_allowed=True),
        replace(base_decision, network_allowed=True),
        replace(base_decision, provider_call_allowed=True),
        replace(base_decision, vault_write_allowed=True),
        replace(base_decision, mcp_write_allowed=True),
        replace(base_decision, git_merge_allowed=True),
        replace(base_decision, main_branch_protected=False),
    )

    for decision in unsafe_variants:
        evidence = _evidence(decision)

        assert evidence.policy_blocked is True
        assert evidence.governance_decision == "blocked"


def test_redacts_notes_with_key_like_placeholder() -> None:
    marker = "OPEN" + "AI" + "_API" + "_KEY"
    evidence = build_agent_workflow_evidence(
        _decision("analyze_task"),
        notes=f"{marker}=placeholder",
    )

    assert marker not in (evidence.notes or "")
    assert "[REDACTED]" in (evidence.notes or "")


def test_redacts_notes_with_authorization_bearer_placeholder() -> None:
    marker = "Authorization: " + "Bearer"
    evidence = build_agent_workflow_evidence(
        _decision("analyze_task"),
        notes=f"{marker} placeholder",
    )

    assert marker not in (evidence.notes or "")
    assert "[REDACTED]" in (evidence.notes or "")


def test_redacts_string_metadata() -> None:
    marker = "TO" + "KEN"
    evidence = build_agent_workflow_evidence(
        _decision("analyze_task"),
        session_id=f"session-{marker}",
        task_id="task-." + "env",
        requested_by="human",
    )

    assert marker not in (evidence.session_id or "")
    assert "." + "env" not in (evidence.task_id or "")
    assert "[REDACTED]" in (evidence.session_id or "")
    assert "[REDACTED]" in (evidence.task_id or "")


def test_evidence_is_json_serializable() -> None:
    evidence = _evidence(_decision("analyze_task"))

    encoded = json.dumps(evidence.to_dict(), sort_keys=True)

    assert '"event_type": "agent.workflow.policy_decision"' in encoded
    assert '"agent_executed": false' in encoded


def test_builds_evidence_from_decision_dict() -> None:
    decision = _decision("analyze_task").to_dict()
    evidence = build_agent_workflow_evidence(decision)

    assert evidence.agent_id == "codex"
    assert evidence.requested_action == "analyze_task"
    assert evidence.governance_decision == "requires_approval"


def test_integration_with_advisory_agent_policy() -> None:
    evidence = _evidence(_decision("analyze_task", workflow_mode="advisory_only"))

    assert evidence.policy_category == "advisory"
    assert evidence.command_execution_allowed is False


def test_integration_with_supervised_agent_policy() -> None:
    evidence = _evidence(
        _decision(
            "request_test_run",
            workflow_mode="supervised_sandbox",
            target_branch="sandbox/agent-runtime-truth",
        )
    )

    assert evidence.policy_category == "supervised_request"
    assert evidence.sandbox_required is True


def test_integration_with_pr_proposal_agent_policy() -> None:
    evidence = _evidence(
        _decision(
            "request_pr_open",
            workflow_mode="pr_proposal_only",
            target_branch="sandbox/agent-runtime-truth",
        )
    )

    assert evidence.policy_category == "pr_proposal"
    assert evidence.pr_open_allowed is True
    assert evidence.pr_created is False


def test_integration_with_blocked_merge_policy() -> None:
    evidence = _evidence(_decision("merge_main", workflow_mode="pr_proposal_only"))

    assert evidence.policy_blocked is True
    assert evidence.git_merge_allowed is False
    assert evidence.governance_decision == "blocked"
