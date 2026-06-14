"""Runtime Truth evidence for controlled commit eligibility decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

COMMIT_GATE_EVIDENCE_VERSION = "1.0"
COMMIT_GATE_EVENT_TYPE = "sandbox.commit_gate.decision"


@dataclass(frozen=True)
class ControlledCommitGateEvidence:
    event_type: str
    evidence_version: str
    commit_gate_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    current_branch: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    evaluated: bool
    blocked: bool
    dry_run: bool
    commit_eligible: bool
    commit_ready_metadata_only: bool
    patch_was_applied: bool
    post_patch_validated: bool
    validation_passed: bool
    validation_failed: bool
    validation_timed_out: bool
    files_considered_count: int
    files_eligible_count: int
    files_blocked_count: int
    protected_files_detected: bool
    secrets_detected: bool
    git_mutation_detected: bool
    main_modification_detected: bool
    commit_executed: bool
    files_staged: bool
    command_executed: bool
    code_edited: bool
    patch_applied: bool
    files_written: bool
    git_mutated: bool
    pr_created: bool
    pr_merged: bool
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


def build_commit_gate_evidence(
    *,
    commit_gate_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    current_branch: str | None,
    target_branch: str | None,
    base_branch: str,
    evaluated: bool,
    blocked: bool,
    dry_run: bool,
    commit_eligible: bool,
    commit_ready_metadata_only: bool,
    patch_was_applied: bool,
    post_patch_validated: bool,
    validation_passed: bool,
    validation_failed: bool,
    validation_timed_out: bool,
    files_considered_count: int,
    files_eligible_count: int,
    files_blocked_count: int,
    protected_files_detected: bool,
    secrets_detected: bool,
    git_mutation_detected: bool,
    main_modification_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> ControlledCommitGateEvidence:
    return ControlledCommitGateEvidence(
        event_type=COMMIT_GATE_EVENT_TYPE,
        evidence_version=COMMIT_GATE_EVIDENCE_VERSION,
        commit_gate_mode=commit_gate_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=base_branch,
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        commit_eligible=commit_eligible,
        commit_ready_metadata_only=commit_ready_metadata_only,
        patch_was_applied=patch_was_applied,
        post_patch_validated=post_patch_validated,
        validation_passed=validation_passed,
        validation_failed=validation_failed,
        validation_timed_out=validation_timed_out,
        files_considered_count=files_considered_count,
        files_eligible_count=files_eligible_count,
        files_blocked_count=files_blocked_count,
        protected_files_detected=protected_files_detected,
        secrets_detected=secrets_detected,
        git_mutation_detected=git_mutation_detected,
        main_modification_detected=main_modification_detected,
        commit_executed=False,
        files_staged=False,
        command_executed=False,
        code_edited=False,
        patch_applied=False,
        files_written=False,
        git_mutated=False,
        pr_created=False,
        pr_merged=False,
        network_used=False,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        vault_written=False,
        main_modified=False,
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            commit_eligible=commit_eligible,
            validation_failed=validation_failed,
            validation_timed_out=validation_timed_out,
            protected_files_detected=protected_files_detected,
            secrets_detected=secrets_detected,
            git_mutation_detected=git_mutation_detected,
            main_modification_detected=main_modification_detected,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
        child_runtime_truth_events=child_runtime_truth_events,
    )


def _governance_decision(
    *,
    blocked: bool,
    dry_run: bool,
    commit_eligible: bool,
    validation_failed: bool,
    validation_timed_out: bool,
    protected_files_detected: bool,
    secrets_detected: bool,
    git_mutation_detected: bool,
    main_modification_detected: bool,
) -> str:
    if secrets_detected or blocked:
        return "blocked"
    if dry_run:
        return "dry_run"
    if protected_files_detected or git_mutation_detected or main_modification_detected:
        return "requires_human_intervention"
    if commit_eligible:
        return "commit_eligible"
    if validation_failed or validation_timed_out:
        return "commit_not_eligible_validation_failed"
    return "commit_not_eligible_missing_evidence"
