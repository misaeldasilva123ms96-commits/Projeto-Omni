"""Runtime Truth evidence for post-patch validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

POST_PATCH_VALIDATION_EVIDENCE_VERSION = "1.0"
POST_PATCH_VALIDATION_EVENT_TYPE = "sandbox.post_patch_validation.loop"


@dataclass(frozen=True)
class PostPatchValidationEvidence:
    event_type: str
    evidence_version: str
    validator_mode: str
    loop_mode: str
    runner_mode: str
    command_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    current_branch: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    patch_was_applied: bool
    patch_apply_event_type: Optional[str]
    patch_apply_governance_decision: Optional[str]
    patch_apply_files_applied_count: int
    patch_apply_hunks_applied_count: int
    validation_commands_count: int
    commands_executed_count: int
    commands_blocked_count: int
    validated: bool
    blocked: bool
    dry_run: bool
    success: bool
    failed: bool
    timed_out: bool
    partial: bool
    ready_for_commit: bool
    ready_for_pr: bool
    requires_repair_cycle: bool
    code_edited: bool
    patch_applied: bool
    files_written: bool
    command_executed: bool
    git_mutated: bool
    pr_created: bool
    pr_merged: bool
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


def build_post_patch_validation_evidence(
    *,
    validator_mode: str,
    loop_mode: str,
    runner_mode: str,
    command_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    current_branch: str | None,
    target_branch: str | None,
    base_branch: str,
    patch_was_applied: bool,
    patch_apply_event_type: str | None,
    patch_apply_governance_decision: str | None,
    patch_apply_files_applied_count: int,
    patch_apply_hunks_applied_count: int,
    validation_commands_count: int,
    commands_executed_count: int,
    commands_blocked_count: int,
    validated: bool,
    blocked: bool,
    dry_run: bool,
    success: bool,
    failed: bool,
    timed_out: bool,
    partial: bool,
    ready_for_commit: bool,
    ready_for_pr: bool,
    requires_repair_cycle: bool,
    command_executed: bool,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> PostPatchValidationEvidence:
    return PostPatchValidationEvidence(
        event_type=POST_PATCH_VALIDATION_EVENT_TYPE,
        evidence_version=POST_PATCH_VALIDATION_EVIDENCE_VERSION,
        validator_mode=validator_mode,
        loop_mode=loop_mode,
        runner_mode=runner_mode,
        command_mode=command_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=base_branch,
        patch_was_applied=patch_was_applied,
        patch_apply_event_type=patch_apply_event_type,
        patch_apply_governance_decision=patch_apply_governance_decision,
        patch_apply_files_applied_count=patch_apply_files_applied_count,
        patch_apply_hunks_applied_count=patch_apply_hunks_applied_count,
        validation_commands_count=validation_commands_count,
        commands_executed_count=commands_executed_count,
        commands_blocked_count=commands_blocked_count,
        validated=validated,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        failed=failed,
        timed_out=timed_out,
        partial=partial,
        ready_for_commit=ready_for_commit,
        ready_for_pr=ready_for_pr,
        requires_repair_cycle=requires_repair_cycle,
        code_edited=False,
        patch_applied=False,
        files_written=False,
        command_executed=command_executed,
        git_mutated=False,
        pr_created=False,
        pr_merged=False,
        network_used=False,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        vault_written=False,
        main_modified=False,
        secrets_detected=secrets_detected,
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            success=success,
            failed=failed,
            timed_out=timed_out,
            secrets_detected=secrets_detected,
            human_intervention_required=human_intervention_required,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
        child_runtime_truth_events=child_runtime_truth_events,
    )


def _governance_decision(
    *,
    blocked: bool,
    dry_run: bool,
    success: bool,
    failed: bool,
    timed_out: bool,
    secrets_detected: bool,
    human_intervention_required: bool,
) -> str:
    if blocked or secrets_detected:
        return "blocked"
    if human_intervention_required:
        return "requires_human_intervention"
    if dry_run:
        return "dry_run"
    if timed_out:
        return "post_patch_validation_timed_out"
    if failed:
        return "post_patch_validation_failed"
    if success:
        return "post_patch_validation_passed"
    return "blocked"
