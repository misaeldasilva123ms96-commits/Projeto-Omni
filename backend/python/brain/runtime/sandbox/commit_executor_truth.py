"""Runtime Truth evidence for controlled commit execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

COMMIT_EXECUTOR_EVIDENCE_VERSION = "1.0"
COMMIT_EXECUTOR_EVENT_TYPE = "sandbox.commit_executor.commit"


@dataclass(frozen=True)
class ControlledCommitExecutorEvidence:
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
    committed: bool
    blocked: bool
    dry_run: bool
    partial: bool
    commit_gate_eligible: bool
    files_requested_count: int
    files_considered_count: int
    files_staged_count: int
    files_blocked_count: int
    commit_sha: Optional[str]
    pre_commit_head: Optional[str]
    post_commit_head: Optional[str]
    git_operations_attempted: list[str]
    git_operations_completed: list[str]
    git_operations_blocked: list[str]
    commit_executed: bool
    files_staged: bool
    command_executed: bool
    git_mutated: bool
    code_edited: bool
    patch_applied: bool
    files_written: bool
    pushed: bool
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


def build_commit_executor_evidence(
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
    committed: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    commit_gate_eligible: bool,
    files_requested_count: int,
    files_considered_count: int,
    files_staged_count: int,
    files_blocked_count: int,
    commit_sha: str | None,
    pre_commit_head: str | None,
    post_commit_head: str | None,
    git_operations_attempted: list[str],
    git_operations_completed: list[str],
    git_operations_blocked: list[str],
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> ControlledCommitExecutorEvidence:
    return ControlledCommitExecutorEvidence(
        event_type=COMMIT_EXECUTOR_EVENT_TYPE,
        evidence_version=COMMIT_EXECUTOR_EVIDENCE_VERSION,
        executor_mode=executor_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        verified_current_branch=verified_current_branch,
        target_branch=target_branch,
        base_branch=base_branch,
        committed=committed,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        commit_gate_eligible=commit_gate_eligible,
        files_requested_count=files_requested_count,
        files_considered_count=files_considered_count,
        files_staged_count=files_staged_count,
        files_blocked_count=files_blocked_count,
        commit_sha=commit_sha,
        pre_commit_head=pre_commit_head,
        post_commit_head=post_commit_head,
        git_operations_attempted=git_operations_attempted,
        git_operations_completed=git_operations_completed,
        git_operations_blocked=git_operations_blocked,
        commit_executed=committed,
        files_staged=committed,
        command_executed=bool(git_operations_attempted),
        git_mutated=committed,
        code_edited=False,
        patch_applied=False,
        files_written=False,
        pushed=False,
        pr_created=False,
        pr_merged=False,
        branch_created=False,
        checkout_performed=False,
        rebase_performed=False,
        merge_performed=False,
        network_used=False,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        vault_written=False,
        main_modified=False,
        secrets_detected=secrets_detected,
        governance_decision=_governance_decision(
            committed=committed,
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
    committed: bool,
    blocked: bool,
    dry_run: bool,
    secrets_detected: bool,
) -> str:
    if secrets_detected or blocked:
        return "blocked"
    if dry_run:
        return "dry_run"
    if committed:
        return "commit_created"
    return "commit_failed"
