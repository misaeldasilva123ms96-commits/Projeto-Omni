"""Runtime Truth evidence for controlled patch application."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

PATCH_APPLIER_EVIDENCE_VERSION = "1.0"
PATCH_APPLIER_EVENT_TYPE = "sandbox.patch_applier.apply"


@dataclass(frozen=True)
class ControlledPatchApplierEvidence:
    event_type: str
    evidence_version: str
    applier_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    current_branch: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    applied: bool
    blocked: bool
    dry_run: bool
    partial: bool
    files_requested_count: int
    files_considered_count: int
    files_applied_count: int
    files_blocked_count: int
    hunks_requested_count: int
    hunks_applied_count: int
    hunks_blocked_count: int
    files_written: bool
    code_edited: bool
    patch_applied: bool
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

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_patch_applier_evidence(
    *,
    applier_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    current_branch: str | None,
    target_branch: str | None,
    base_branch: str,
    applied: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    files_requested_count: int,
    files_considered_count: int,
    files_applied_count: int,
    files_blocked_count: int,
    hunks_requested_count: int,
    hunks_applied_count: int,
    hunks_blocked_count: int,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
) -> ControlledPatchApplierEvidence:
    return ControlledPatchApplierEvidence(
        event_type=PATCH_APPLIER_EVENT_TYPE,
        evidence_version=PATCH_APPLIER_EVIDENCE_VERSION,
        applier_mode=applier_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=base_branch,
        applied=applied,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        files_requested_count=files_requested_count,
        files_considered_count=files_considered_count,
        files_applied_count=files_applied_count,
        files_blocked_count=files_blocked_count,
        hunks_requested_count=hunks_requested_count,
        hunks_applied_count=hunks_applied_count,
        hunks_blocked_count=hunks_blocked_count,
        files_written=applied,
        code_edited=applied,
        patch_applied=applied,
        command_executed=False,
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
            applied=applied,
            blocked=blocked,
            dry_run=dry_run,
            partial=partial,
            secrets_detected=secrets_detected,
            human_intervention_required=human_intervention_required,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
    )


def _governance_decision(
    *,
    applied: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    secrets_detected: bool,
    human_intervention_required: bool,
) -> str:
    if blocked or secrets_detected:
        return "blocked"
    if human_intervention_required:
        return "requires_human_intervention"
    if dry_run:
        return "dry_run"
    if partial:
        return "partial_patch_applied"
    if applied:
        return "patch_applied"
    return "blocked"
