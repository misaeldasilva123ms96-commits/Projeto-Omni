"""Runtime Truth evidence for scoped CI patch proposal engine decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

SCOPED_CI_PATCH_PROPOSAL_ENGINE_EVIDENCE_VERSION = "1.0"
SCOPED_CI_PATCH_PROPOSAL_ENGINE_EVENT_TYPE = "sandbox.scoped_ci_patch_proposal_engine.propose"


@dataclass(frozen=True)
class ScopedCIPatchProposalEngineEvidence:
    event_type: str
    evidence_version: str
    proposal_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    repository_full_name: Optional[str]
    pr_number: Optional[int]
    pr_url: Optional[str]
    pr_state: Optional[str]
    source_branch: Optional[str]
    head_branch: Optional[str]
    base_branch: str
    head_sha: Optional[str]
    commit_sha: Optional[str]
    proposal_created: bool
    blocked: bool
    dry_run: bool
    partial: bool
    gate_eligible: bool
    repair_plan_ready: bool
    ci_failed: bool
    ci_inconclusive: bool
    ci_passed: bool
    ci_pending: bool
    aggregate_status: str
    aggregate_conclusion: str
    failure_categories: list[str]
    blocked_failure_categories: list[str]
    safe_repair_steps_count: int
    unsafe_repair_steps_count: int
    skipped_repair_steps_count: int
    proposal_files_count: int
    proposal_hunks_count: int
    proposal_operations_count: int
    candidate_target_areas_count: int
    candidate_file_roots_count: int
    blocked_target_areas_count: int
    suggested_validation_commands_count: int
    patch_proposal_created: bool
    patch_hunks_generated: bool
    patch_applied: bool
    files_written: bool
    code_edited: bool
    source_inspected: bool
    logs_downloaded: bool
    workflow_retried: bool
    workflow_triggered: bool
    repair_loop_started: bool
    provider_called: bool
    agent_called: bool
    mcp_used: bool
    command_executed: bool
    git_mutated: bool
    commit_executed: bool
    push_executed: bool
    pr_updated: bool
    pr_merged: bool
    auto_merge_enabled: bool
    approval_submitted: bool
    main_modified: bool
    vault_written: bool
    secrets_detected: bool
    governance_decision: str
    human_intervention_required: bool
    escalation_reason: Optional[str]
    child_runtime_truth_events: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_scoped_ci_patch_proposal_engine_evidence(
    *,
    proposal_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    repository_full_name: str | None,
    pr_number: int | None,
    pr_url: str | None,
    pr_state: str | None,
    source_branch: str | None,
    head_branch: str | None,
    base_branch: str,
    head_sha: str | None,
    commit_sha: str | None,
    proposal_created: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    gate_eligible: bool,
    repair_plan_ready: bool,
    ci_failed: bool,
    ci_inconclusive: bool,
    ci_passed: bool,
    ci_pending: bool,
    aggregate_status: str,
    aggregate_conclusion: str,
    failure_categories: list[str],
    blocked_failure_categories: list[str],
    safe_repair_steps_count: int,
    unsafe_repair_steps_count: int,
    skipped_repair_steps_count: int,
    proposal_files_count: int,
    proposal_hunks_count: int,
    proposal_operations_count: int,
    candidate_target_areas_count: int,
    candidate_file_roots_count: int,
    blocked_target_areas_count: int,
    suggested_validation_commands_count: int,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> ScopedCIPatchProposalEngineEvidence:
    return ScopedCIPatchProposalEngineEvidence(
        event_type=SCOPED_CI_PATCH_PROPOSAL_ENGINE_EVENT_TYPE,
        evidence_version=SCOPED_CI_PATCH_PROPOSAL_ENGINE_EVIDENCE_VERSION,
        proposal_mode=proposal_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        repository_full_name=repository_full_name,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        commit_sha=commit_sha,
        proposal_created=proposal_created,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        gate_eligible=gate_eligible,
        repair_plan_ready=repair_plan_ready,
        ci_failed=ci_failed,
        ci_inconclusive=ci_inconclusive,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        failure_categories=failure_categories,
        blocked_failure_categories=blocked_failure_categories,
        safe_repair_steps_count=safe_repair_steps_count,
        unsafe_repair_steps_count=unsafe_repair_steps_count,
        skipped_repair_steps_count=skipped_repair_steps_count,
        proposal_files_count=proposal_files_count,
        proposal_hunks_count=proposal_hunks_count,
        proposal_operations_count=proposal_operations_count,
        candidate_target_areas_count=candidate_target_areas_count,
        candidate_file_roots_count=candidate_file_roots_count,
        blocked_target_areas_count=blocked_target_areas_count,
        suggested_validation_commands_count=suggested_validation_commands_count,
        patch_proposal_created=proposal_created,
        patch_hunks_generated=proposal_created and proposal_hunks_count > 0,
        patch_applied=False,
        files_written=False,
        code_edited=False,
        source_inspected=False,
        logs_downloaded=False,
        workflow_retried=False,
        workflow_triggered=False,
        repair_loop_started=False,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        command_executed=False,
        git_mutated=False,
        commit_executed=False,
        push_executed=False,
        pr_updated=False,
        pr_merged=False,
        auto_merge_enabled=False,
        approval_submitted=False,
        main_modified=False,
        vault_written=False,
        secrets_detected=secrets_detected,
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            proposal_created=proposal_created,
            partial=partial,
            repair_plan_ready=repair_plan_ready,
            gate_eligible=gate_eligible,
            ci_passed=ci_passed,
            ci_pending=ci_pending,
            secrets_detected=secrets_detected,
            human_intervention_required=human_intervention_required,
            blocked_failure_categories=blocked_failure_categories,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
        child_runtime_truth_events=child_runtime_truth_events,
    )


def _governance_decision(
    *,
    blocked: bool,
    dry_run: bool,
    proposal_created: bool,
    partial: bool,
    repair_plan_ready: bool,
    gate_eligible: bool,
    ci_passed: bool,
    ci_pending: bool,
    secrets_detected: bool,
    human_intervention_required: bool,
    blocked_failure_categories: list[str],
) -> str:
    if secrets_detected:
        return "blocked"
    if blocked:
        return "blocked"
    if dry_run:
        return "dry_run"
    if human_intervention_required:
        return "requires_human_intervention"
    if blocked_failure_categories:
        return "requires_human_intervention"
    if ci_passed:
        return "proposal_not_needed_ci_passed"
    if ci_pending:
        return "proposal_wait_for_ci"
    if partial:
        return "partial_scoped_ci_patch_proposal_created"
    if proposal_created:
        return "scoped_ci_patch_proposal_created"
    if not repair_plan_ready:
        return "proposal_not_created_missing_repair_plan"
    if not gate_eligible:
        return "proposal_not_created_gate_ineligible"
    return "blocked"
