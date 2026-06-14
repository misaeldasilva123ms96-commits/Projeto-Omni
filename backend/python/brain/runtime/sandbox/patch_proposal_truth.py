"""Runtime Truth evidence for scoped patch proposal planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

PATCH_PROPOSAL_EVIDENCE_VERSION = "1.0"
PATCH_PROPOSAL_EVENT_TYPE = "sandbox.patch_proposal.plan"


@dataclass(frozen=True)
class ScopedPatchProposalEvidence:
    event_type: str
    evidence_version: str
    proposal_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    repair_category: str
    failure_classification: Optional[str]
    patch_scope: str
    patch_complexity: str
    risk_level: str
    proposed: bool
    blocked: bool
    dry_run: bool
    files_considered_count: int
    files_proposed_count: int
    files_blocked_count: int
    patch_proposals_count: int
    total_hunks_count: int
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

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_patch_proposal_evidence(
    *,
    proposal_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    target_branch: str | None,
    base_branch: str,
    repair_category: str,
    failure_classification: str | None,
    patch_scope: str,
    patch_complexity: str,
    risk_level: str,
    proposed: bool,
    blocked: bool,
    dry_run: bool,
    files_considered_count: int,
    files_proposed_count: int,
    files_blocked_count: int,
    patch_proposals_count: int,
    total_hunks_count: int,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
) -> ScopedPatchProposalEvidence:
    return ScopedPatchProposalEvidence(
        event_type=PATCH_PROPOSAL_EVENT_TYPE,
        evidence_version=PATCH_PROPOSAL_EVIDENCE_VERSION,
        proposal_mode=proposal_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        target_branch=target_branch,
        base_branch=base_branch,
        repair_category=repair_category,
        failure_classification=failure_classification,
        patch_scope=patch_scope,
        patch_complexity=patch_complexity,
        risk_level=risk_level,
        proposed=proposed,
        blocked=blocked,
        dry_run=dry_run,
        files_considered_count=files_considered_count,
        files_proposed_count=files_proposed_count,
        files_blocked_count=files_blocked_count,
        patch_proposals_count=patch_proposals_count,
        total_hunks_count=total_hunks_count,
        code_edited=False,
        patch_applied=False,
        files_written=False,
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
            blocked=blocked,
            dry_run=dry_run,
            proposed=proposed,
            secrets_detected=secrets_detected,
            human_intervention_required=human_intervention_required,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
    )


def _governance_decision(
    *,
    blocked: bool,
    dry_run: bool,
    proposed: bool,
    secrets_detected: bool,
    human_intervention_required: bool,
) -> str:
    if blocked or secrets_detected:
        return "blocked"
    if human_intervention_required:
        return "requires_human_intervention"
    if dry_run:
        return "dry_run"
    if proposed:
        return "patch_proposal_created"
    return "blocked"
