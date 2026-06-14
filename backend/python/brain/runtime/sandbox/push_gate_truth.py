"""Runtime Truth evidence for controlled push eligibility decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

PUSH_GATE_EVIDENCE_VERSION = "1.0"
PUSH_GATE_EVENT_TYPE = "sandbox.push_gate.decision"


@dataclass(frozen=True)
class ControlledPushGateEvidence:
    event_type: str
    evidence_version: str
    push_gate_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    current_branch: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    remote_name: str
    remote_branch: Optional[str]
    proposed_push_ref: Optional[str]
    evaluated: bool
    blocked: bool
    dry_run: bool
    push_eligible: bool
    push_ready_metadata_only: bool
    commit_was_executed: bool
    commit_sha: Optional[str]
    pre_commit_head: Optional[str]
    post_commit_head: Optional[str]
    commit_evidence_clean: bool
    branch_safe: bool
    remote_safe: bool
    protected_branch_detected: bool
    force_push_detected: bool
    main_push_detected: bool
    secrets_detected: bool
    git_mutation_issue_detected: bool
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
    governance_decision: str
    human_intervention_required: bool
    escalation_reason: Optional[str]
    child_runtime_truth_events: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_push_gate_evidence(
    *,
    push_gate_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    current_branch: str | None,
    target_branch: str | None,
    base_branch: str,
    remote_name: str,
    remote_branch: str | None,
    proposed_push_ref: str | None,
    evaluated: bool,
    blocked: bool,
    dry_run: bool,
    push_eligible: bool,
    push_ready_metadata_only: bool,
    commit_was_executed: bool,
    commit_sha: str | None,
    pre_commit_head: str | None,
    post_commit_head: str | None,
    commit_evidence_clean: bool,
    branch_safe: bool,
    remote_safe: bool,
    protected_branch_detected: bool,
    force_push_detected: bool,
    main_push_detected: bool,
    secrets_detected: bool,
    git_mutation_issue_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> ControlledPushGateEvidence:
    return ControlledPushGateEvidence(
        event_type=PUSH_GATE_EVENT_TYPE,
        evidence_version=PUSH_GATE_EVIDENCE_VERSION,
        push_gate_mode=push_gate_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=base_branch,
        remote_name=remote_name,
        remote_branch=remote_branch,
        proposed_push_ref=proposed_push_ref,
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        push_eligible=push_eligible,
        push_ready_metadata_only=push_ready_metadata_only,
        commit_was_executed=commit_was_executed,
        commit_sha=commit_sha,
        pre_commit_head=pre_commit_head,
        post_commit_head=post_commit_head,
        commit_evidence_clean=commit_evidence_clean,
        branch_safe=branch_safe,
        remote_safe=remote_safe,
        protected_branch_detected=protected_branch_detected,
        force_push_detected=force_push_detected,
        main_push_detected=main_push_detected,
        secrets_detected=secrets_detected,
        git_mutation_issue_detected=git_mutation_issue_detected,
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
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            push_eligible=push_eligible,
            commit_was_executed=commit_was_executed,
            branch_safe=branch_safe,
            remote_safe=remote_safe,
            protected_branch_detected=protected_branch_detected,
            force_push_detected=force_push_detected,
            main_push_detected=main_push_detected,
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
    push_eligible: bool,
    commit_was_executed: bool,
    branch_safe: bool,
    remote_safe: bool,
    protected_branch_detected: bool,
    force_push_detected: bool,
    main_push_detected: bool,
    secrets_detected: bool,
) -> str:
    if secrets_detected or force_push_detected or main_push_detected or blocked:
        return "blocked"
    if protected_branch_detected:
        return "requires_human_intervention"
    if dry_run:
        return "dry_run"
    if push_eligible:
        return "push_eligible"
    if not commit_was_executed:
        return "push_not_eligible_missing_commit"
    if not branch_safe:
        return "push_not_eligible_branch_risk"
    if not remote_safe:
        return "push_not_eligible_remote_risk"
    return "blocked"
