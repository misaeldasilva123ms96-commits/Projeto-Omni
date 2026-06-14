"""Runtime Truth evidence for controlled push execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

PUSH_EXECUTOR_EVIDENCE_VERSION = "1.0"
PUSH_EXECUTOR_EVENT_TYPE = "sandbox.push_executor.push"


@dataclass(frozen=True)
class ControlledPushExecutorEvidence:
    event_type: str
    evidence_version: str
    executor_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    current_branch: Optional[str]
    verified_current_branch: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    remote_name: str
    remote_branch: Optional[str]
    proposed_push_ref: Optional[str]
    final_push_ref: Optional[str]
    pushed: bool
    blocked: bool
    dry_run: bool
    partial: bool
    push_gate_eligible: bool
    commit_was_executed: bool
    commit_sha: Optional[str]
    pre_push_head: Optional[str]
    post_push_head: Optional[str]
    git_operations_attempted: list[str]
    git_operations_completed: list[str]
    git_operations_blocked: list[str]
    push_executed: bool
    force_push_executed: bool
    main_pushed: bool
    command_executed: bool
    git_mutated: bool
    commit_executed: bool
    files_staged: bool
    code_edited: bool
    patch_applied: bool
    files_written: bool
    pr_created: bool
    pr_merged: bool
    branch_created: bool
    checkout_performed: bool
    rebase_performed: bool
    merge_performed: bool
    network_used: bool
    provider_called: bool
    agent_called: bool
    mcp_used: bool
    vault_written: bool
    main_modified: bool
    secrets_detected: bool
    governance_decision: str
    human_intervention_required: bool
    escalation_reason: Optional[str]
    child_runtime_truth_events: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_push_executor_evidence(
    *,
    executor_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    current_branch: str | None,
    verified_current_branch: str | None,
    target_branch: str | None,
    base_branch: str,
    remote_name: str,
    remote_branch: str | None,
    proposed_push_ref: str | None,
    final_push_ref: str | None,
    pushed: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    push_gate_eligible: bool,
    commit_was_executed: bool,
    commit_sha: str | None,
    pre_push_head: str | None,
    post_push_head: str | None,
    git_operations_attempted: list[str],
    git_operations_completed: list[str],
    git_operations_blocked: list[str],
    push_attempted: bool,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> ControlledPushExecutorEvidence:
    return ControlledPushExecutorEvidence(
        event_type=PUSH_EXECUTOR_EVENT_TYPE,
        evidence_version=PUSH_EXECUTOR_EVIDENCE_VERSION,
        executor_mode=executor_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        verified_current_branch=verified_current_branch,
        target_branch=target_branch,
        base_branch=base_branch,
        remote_name=remote_name,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        final_push_ref=final_push_ref,
        pushed=pushed,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        push_gate_eligible=push_gate_eligible,
        commit_was_executed=commit_was_executed,
        commit_sha=commit_sha,
        pre_push_head=pre_push_head,
        post_push_head=post_push_head,
        git_operations_attempted=git_operations_attempted,
        git_operations_completed=git_operations_completed,
        git_operations_blocked=git_operations_blocked,
        push_executed=pushed,
        force_push_executed=False,
        main_pushed=False,
        command_executed=bool(git_operations_attempted),
        git_mutated=pushed,
        commit_executed=False,
        files_staged=False,
        code_edited=False,
        patch_applied=False,
        files_written=False,
        pr_created=False,
        pr_merged=False,
        branch_created=False,
        checkout_performed=False,
        rebase_performed=False,
        merge_performed=False,
        network_used=push_attempted,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        vault_written=False,
        main_modified=False,
        secrets_detected=secrets_detected,
        governance_decision=_governance_decision(
            pushed=pushed,
            blocked=blocked,
            dry_run=dry_run,
            secrets_detected=secrets_detected,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
        child_runtime_truth_events=child_runtime_truth_events,
    )


def _governance_decision(
    *,
    pushed: bool,
    blocked: bool,
    dry_run: bool,
    secrets_detected: bool,
) -> str:
    if secrets_detected or blocked:
        return "blocked"
    if dry_run:
        return "dry_run"
    if pushed:
        return "branch_pushed"
    return "push_failed"
