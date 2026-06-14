"""Runtime Truth evidence for PR creation eligibility decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

PR_CREATION_GATE_EVIDENCE_VERSION = "1.0"
PR_CREATION_GATE_EVENT_TYPE = "sandbox.pr_creation_gate.decision"


@dataclass(frozen=True)
class PRCreationGateEvidence:
    event_type: str
    evidence_version: str
    pr_gate_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    repository_full_name: Optional[str]
    source_branch: Optional[str]
    head_branch: Optional[str]
    base_branch: str
    current_branch: Optional[str]
    remote_name: str
    remote_branch: Optional[str]
    pushed_ref: Optional[str]
    pushed_remote: Optional[str]
    commit_sha: Optional[str]
    evaluated: bool
    blocked: bool
    dry_run: bool
    pr_eligible: bool
    pr_ready_metadata_only: bool
    push_was_executed: bool
    push_evidence_clean: bool
    branch_safe: bool
    base_safe: bool
    repository_safe: bool
    title_safe: bool
    body_safe: bool
    labels_safe: bool
    reviewers_safe: bool
    assignees_safe: bool
    secrets_detected: bool
    protected_branch_detected: bool
    main_source_branch_detected: bool
    unsafe_repository_detected: bool
    duplicate_pr_risk: bool
    pr_created: bool
    pr_merged: bool
    auto_merge_enabled: bool
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
    governance_decision: str
    human_intervention_required: bool
    escalation_reason: Optional[str]
    child_runtime_truth_events: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_pr_creation_gate_evidence(
    *,
    pr_gate_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    repository_full_name: str | None,
    source_branch: str | None,
    head_branch: str | None,
    base_branch: str,
    current_branch: str | None,
    remote_name: str,
    remote_branch: str | None,
    pushed_ref: str | None,
    pushed_remote: str | None,
    commit_sha: str | None,
    evaluated: bool,
    blocked: bool,
    dry_run: bool,
    pr_eligible: bool,
    pr_ready_metadata_only: bool,
    push_was_executed: bool,
    push_evidence_clean: bool,
    branch_safe: bool,
    base_safe: bool,
    repository_safe: bool,
    title_safe: bool,
    body_safe: bool,
    labels_safe: bool,
    reviewers_safe: bool,
    assignees_safe: bool,
    secrets_detected: bool,
    protected_branch_detected: bool,
    main_source_branch_detected: bool,
    unsafe_repository_detected: bool,
    duplicate_pr_risk: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> PRCreationGateEvidence:
    return PRCreationGateEvidence(
        event_type=PR_CREATION_GATE_EVENT_TYPE,
        evidence_version=PR_CREATION_GATE_EVIDENCE_VERSION,
        pr_gate_mode=pr_gate_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        repository_full_name=repository_full_name,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        current_branch=current_branch,
        remote_name=remote_name,
        remote_branch=remote_branch,
        pushed_ref=pushed_ref,
        pushed_remote=pushed_remote,
        commit_sha=commit_sha,
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        pr_eligible=pr_eligible,
        pr_ready_metadata_only=pr_ready_metadata_only,
        push_was_executed=push_was_executed,
        push_evidence_clean=push_evidence_clean,
        branch_safe=branch_safe,
        base_safe=base_safe,
        repository_safe=repository_safe,
        title_safe=title_safe,
        body_safe=body_safe,
        labels_safe=labels_safe,
        reviewers_safe=reviewers_safe,
        assignees_safe=assignees_safe,
        secrets_detected=secrets_detected,
        protected_branch_detected=protected_branch_detected,
        main_source_branch_detected=main_source_branch_detected,
        unsafe_repository_detected=unsafe_repository_detected,
        duplicate_pr_risk=duplicate_pr_risk,
        pr_created=False,
        pr_merged=False,
        auto_merge_enabled=False,
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
        network_used=False,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        vault_written=False,
        main_modified=False,
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            pr_eligible=pr_eligible,
            push_was_executed=push_was_executed,
            branch_safe=branch_safe,
            repository_safe=repository_safe,
            duplicate_pr_risk=duplicate_pr_risk,
            secrets_detected=secrets_detected,
            protected_branch_detected=protected_branch_detected,
            main_source_branch_detected=main_source_branch_detected,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
        child_runtime_truth_events=child_runtime_truth_events,
    )


def _governance_decision(
    *,
    blocked: bool,
    dry_run: bool,
    pr_eligible: bool,
    push_was_executed: bool,
    branch_safe: bool,
    repository_safe: bool,
    duplicate_pr_risk: bool,
    secrets_detected: bool,
    protected_branch_detected: bool,
    main_source_branch_detected: bool,
) -> str:
    if secrets_detected or main_source_branch_detected:
        return "blocked"
    if protected_branch_detected or duplicate_pr_risk:
        return "requires_human_intervention"
    if blocked:
        if not push_was_executed:
            return "pr_not_eligible_missing_push"
        if not branch_safe:
            return "pr_not_eligible_branch_risk"
        if not repository_safe:
            return "pr_not_eligible_repository_risk"
        return "blocked"
    if dry_run:
        return "dry_run"
    if pr_eligible:
        return "pr_creation_eligible"
    return "blocked"
