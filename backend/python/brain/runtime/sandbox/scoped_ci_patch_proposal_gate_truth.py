"""Runtime Truth evidence for scoped CI patch proposal gate decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

SCOPED_CI_PATCH_PROPOSAL_GATE_EVIDENCE_VERSION = "1.0"
SCOPED_CI_PATCH_PROPOSAL_GATE_EVENT_TYPE = "sandbox.scoped_ci_patch_proposal_gate.decision"


@dataclass(frozen=True)
class ScopedCIPatchProposalGateEvidence:
    event_type: str
    evidence_version: str
    patch_proposal_gate_mode: str
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
    evaluated: bool
    blocked: bool
    dry_run: bool
    patch_proposal_eligible: bool
    patch_proposal_ready_metadata_only: bool
    repair_planner_clean: bool
    repair_plan_ready: bool
    ci_failed: bool
    ci_inconclusive: bool
    ci_passed: bool
    ci_pending: bool
    aggregate_status: str
    aggregate_conclusion: str
    failure_categories: list[str]
    blocked_failure_categories: list[str]
    repair_plan_steps_count: int
    safe_repair_steps_count: int
    unsafe_repair_steps_count: int
    affected_areas_count: int
    candidate_target_areas_count: int
    candidate_file_roots_count: int
    blocked_target_areas_count: int
    suggested_validation_commands_count: int
    max_patch_proposal_files: int
    max_patch_proposal_hunks: int
    max_hunks_per_file: int
    scoped_patch_proposal_plan_created: bool
    patch_proposal_created: bool
    patch_hunks_generated: bool
    patch_applied: bool
    files_written: bool
    code_edited: bool
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


def build_scoped_ci_patch_proposal_gate_evidence(
    *,
    patch_proposal_gate_mode: str,
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
    evaluated: bool,
    blocked: bool,
    dry_run: bool,
    patch_proposal_eligible: bool,
    patch_proposal_ready_metadata_only: bool,
    repair_planner_clean: bool,
    repair_plan_ready: bool,
    ci_failed: bool,
    ci_inconclusive: bool,
    ci_passed: bool,
    ci_pending: bool,
    aggregate_status: str,
    aggregate_conclusion: str,
    failure_categories: list[str],
    blocked_failure_categories: list[str],
    repair_plan_steps_count: int,
    safe_repair_steps_count: int,
    unsafe_repair_steps_count: int,
    affected_areas_count: int,
    candidate_target_areas_count: int,
    candidate_file_roots_count: int,
    blocked_target_areas_count: int,
    suggested_validation_commands_count: int,
    max_patch_proposal_files: int,
    max_patch_proposal_hunks: int,
    max_hunks_per_file: int,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> ScopedCIPatchProposalGateEvidence:
    return ScopedCIPatchProposalGateEvidence(
        event_type=SCOPED_CI_PATCH_PROPOSAL_GATE_EVENT_TYPE,
        evidence_version=SCOPED_CI_PATCH_PROPOSAL_GATE_EVIDENCE_VERSION,
        patch_proposal_gate_mode=patch_proposal_gate_mode,
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
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        patch_proposal_eligible=patch_proposal_eligible,
        patch_proposal_ready_metadata_only=patch_proposal_ready_metadata_only,
        repair_planner_clean=repair_planner_clean,
        repair_plan_ready=repair_plan_ready,
        ci_failed=ci_failed,
        ci_inconclusive=ci_inconclusive,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        failure_categories=failure_categories,
        blocked_failure_categories=blocked_failure_categories,
        repair_plan_steps_count=repair_plan_steps_count,
        safe_repair_steps_count=safe_repair_steps_count,
        unsafe_repair_steps_count=unsafe_repair_steps_count,
        affected_areas_count=affected_areas_count,
        candidate_target_areas_count=candidate_target_areas_count,
        candidate_file_roots_count=candidate_file_roots_count,
        blocked_target_areas_count=blocked_target_areas_count,
        suggested_validation_commands_count=suggested_validation_commands_count,
        max_patch_proposal_files=max_patch_proposal_files,
        max_patch_proposal_hunks=max_patch_proposal_hunks,
        max_hunks_per_file=max_hunks_per_file,
        scoped_patch_proposal_plan_created=patch_proposal_eligible and not blocked and not dry_run,
        patch_proposal_created=False,
        patch_hunks_generated=False,
        patch_applied=False,
        files_written=False,
        code_edited=False,
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
            patch_proposal_eligible=patch_proposal_eligible,
            patch_proposal_ready_metadata_only=patch_proposal_ready_metadata_only,
            repair_plan_ready=repair_plan_ready,
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
    patch_proposal_eligible: bool,
    patch_proposal_ready_metadata_only: bool,
    repair_plan_ready: bool,
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
        return "patch_proposal_not_needed_ci_passed"
    if ci_pending:
        return "patch_proposal_wait_for_ci"
    if patch_proposal_eligible and patch_proposal_ready_metadata_only:
        return "scoped_ci_patch_proposal_eligible"
    if not repair_plan_ready:
        return "patch_proposal_not_eligible_missing_repair_plan"
    return "blocked"
