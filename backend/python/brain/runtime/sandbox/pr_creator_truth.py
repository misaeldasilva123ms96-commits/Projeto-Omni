"""Runtime Truth evidence for controlled PR creation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

PR_CREATOR_EVIDENCE_VERSION = "1.0"
PR_CREATOR_EVENT_TYPE = "sandbox.pr_creator.create"


@dataclass(frozen=True)
class ControlledPRCreatorEvidence:
    event_type: str
    evidence_version: str
    creator_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    repository_full_name: Optional[str]
    source_branch: Optional[str]
    head_branch: Optional[str]
    base_branch: str
    current_branch: Optional[str]
    remote_branch: Optional[str]
    pushed_ref: Optional[str]
    pushed_remote: Optional[str]
    commit_sha: Optional[str]
    pr_created: bool
    blocked: bool
    dry_run: bool
    partial: bool
    pr_gate_eligible: bool
    push_was_executed: bool
    title_safe: bool
    body_safe: bool
    repository_safe: bool
    branch_safe: bool
    labels_safe: bool
    reviewers_safe: bool
    assignees_safe: bool
    duplicate_pr_detected: bool
    pr_number: Optional[int]
    pr_url: Optional[str]
    pr_state: Optional[str]
    github_operations_attempted: list[str]
    github_operations_completed: list[str]
    github_operations_blocked: list[str]
    pr_merged: bool
    auto_merge_enabled: bool
    approval_submitted: bool
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


def build_pr_creator_evidence(
    *,
    creator_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    repository_full_name: str | None,
    source_branch: str | None,
    head_branch: str | None,
    base_branch: str,
    current_branch: str | None,
    remote_branch: str | None,
    pushed_ref: str | None,
    pushed_remote: str | None,
    commit_sha: str | None,
    pr_created: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    pr_gate_eligible: bool,
    push_was_executed: bool,
    title_safe: bool,
    body_safe: bool,
    repository_safe: bool,
    branch_safe: bool,
    labels_safe: bool,
    reviewers_safe: bool,
    assignees_safe: bool,
    duplicate_pr_detected: bool,
    pr_number: int | None,
    pr_url: str | None,
    pr_state: str | None,
    github_operations_attempted: list[str],
    github_operations_completed: list[str],
    github_operations_blocked: list[str],
    github_client_called: bool,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> ControlledPRCreatorEvidence:
    return ControlledPRCreatorEvidence(
        event_type=PR_CREATOR_EVENT_TYPE,
        evidence_version=PR_CREATOR_EVIDENCE_VERSION,
        creator_mode=creator_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        repository_full_name=repository_full_name,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        current_branch=current_branch,
        remote_branch=remote_branch,
        pushed_ref=pushed_ref,
        pushed_remote=pushed_remote,
        commit_sha=commit_sha,
        pr_created=pr_created,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        pr_gate_eligible=pr_gate_eligible,
        push_was_executed=push_was_executed,
        title_safe=title_safe,
        body_safe=body_safe,
        repository_safe=repository_safe,
        branch_safe=branch_safe,
        labels_safe=labels_safe,
        reviewers_safe=reviewers_safe,
        assignees_safe=assignees_safe,
        duplicate_pr_detected=duplicate_pr_detected,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        github_operations_attempted=github_operations_attempted,
        github_operations_completed=github_operations_completed,
        github_operations_blocked=github_operations_blocked,
        pr_merged=False,
        auto_merge_enabled=False,
        approval_submitted=False,
        push_executed=False,
        force_push_executed=False,
        main_pushed=False,
        command_executed=False,
        git_mutated=False,
        commit_executed=False,
        files_staged=False,
        code_edited=False,
        patch_applied=False,
        files_written=False,
        branch_created=False,
        checkout_performed=False,
        rebase_performed=False,
        merge_performed=False,
        network_used=github_client_called,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        vault_written=False,
        main_modified=False,
        secrets_detected=secrets_detected,
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            pr_created=pr_created,
            duplicate_pr_detected=duplicate_pr_detected,
            secrets_detected=secrets_detected,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
        child_runtime_truth_events=child_runtime_truth_events,
    )


def _governance_decision(
    *,
    blocked: bool,
    dry_run: bool,
    pr_created: bool,
    duplicate_pr_detected: bool,
    secrets_detected: bool,
) -> str:
    if secrets_detected or blocked:
        return "blocked"
    if dry_run:
        return "dry_run"
    if duplicate_pr_detected:
        return "existing_pr_detected"
    if pr_created:
        return "pr_created"
    return "pr_creation_failed"
