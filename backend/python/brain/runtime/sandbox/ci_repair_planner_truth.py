"""Runtime Truth evidence for CI repair planner decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

CI_REPAIR_PLANNER_EVIDENCE_VERSION = "1.0"
CI_REPAIR_PLANNER_EVENT_TYPE = "sandbox.ci_repair_planner.plan"


@dataclass(frozen=True)
class CIRepairPlannerEvidence:
    event_type: str
    evidence_version: str
    planner_mode: str
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
    planned: bool
    blocked: bool
    dry_run: bool
    partial: bool
    repair_plan_ready: bool
    repair_gate_eligible: bool
    ci_monitor_clean: bool
    ci_failed: bool
    ci_inconclusive: bool
    ci_passed: bool
    ci_pending: bool
    aggregate_status: str
    aggregate_conclusion: str
    failure_categories: list[str]
    blocked_failure_categories: list[str]
    failing_checks_count: int
    pending_checks_count: int
    missing_required_checks_count: int
    unknown_checks_count: int
    repair_plan_steps_count: int
    affected_areas_count: int
    suggested_validation_commands_count: int
    max_repair_attempts: int
    current_repair_attempt: int
    attempt_budget_remaining: int
    repair_plan_created: bool
    repair_loop_started: bool
    logs_downloaded: bool
    workflow_retried: bool
    workflow_triggered: bool
    provider_called: bool
    agent_called: bool
    mcp_used: bool
    patch_proposed: bool
    patch_applied: bool
    files_written: bool
    code_edited: bool
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


def build_ci_repair_planner_evidence(
    *,
    planner_mode: str,
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
    planned: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    repair_plan_ready: bool,
    repair_gate_eligible: bool,
    ci_monitor_clean: bool,
    ci_failed: bool,
    ci_inconclusive: bool,
    ci_passed: bool,
    ci_pending: bool,
    aggregate_status: str,
    aggregate_conclusion: str,
    failure_categories: list[str],
    blocked_failure_categories: list[str],
    failing_checks_count: int,
    pending_checks_count: int,
    missing_required_checks_count: int,
    unknown_checks_count: int,
    repair_plan_steps_count: int,
    affected_areas_count: int,
    suggested_validation_commands_count: int,
    max_repair_attempts: int,
    current_repair_attempt: int,
    attempt_budget_remaining: int,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> CIRepairPlannerEvidence:
    return CIRepairPlannerEvidence(
        event_type=CI_REPAIR_PLANNER_EVENT_TYPE,
        evidence_version=CI_REPAIR_PLANNER_EVIDENCE_VERSION,
        planner_mode=planner_mode,
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
        planned=planned,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        repair_plan_ready=repair_plan_ready,
        repair_gate_eligible=repair_gate_eligible,
        ci_monitor_clean=ci_monitor_clean,
        ci_failed=ci_failed,
        ci_inconclusive=ci_inconclusive,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        failure_categories=failure_categories,
        blocked_failure_categories=blocked_failure_categories,
        failing_checks_count=failing_checks_count,
        pending_checks_count=pending_checks_count,
        missing_required_checks_count=missing_required_checks_count,
        unknown_checks_count=unknown_checks_count,
        repair_plan_steps_count=repair_plan_steps_count,
        affected_areas_count=affected_areas_count,
        suggested_validation_commands_count=suggested_validation_commands_count,
        max_repair_attempts=max_repair_attempts,
        current_repair_attempt=current_repair_attempt,
        attempt_budget_remaining=attempt_budget_remaining,
        repair_plan_created=planned and not blocked and not dry_run and repair_plan_ready,
        repair_loop_started=False,
        logs_downloaded=False,
        workflow_retried=False,
        workflow_triggered=False,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        patch_proposed=False,
        patch_applied=False,
        files_written=False,
        code_edited=False,
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
            planned=planned,
            repair_plan_ready=repair_plan_ready,
            ci_passed=ci_passed,
            ci_pending=ci_pending,
            missing_required_checks_count=missing_required_checks_count,
            secrets_detected=secrets_detected,
            human_intervention_required=human_intervention_required,
            attempt_budget_remaining=attempt_budget_remaining,
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
    planned: bool,
    repair_plan_ready: bool,
    ci_passed: bool,
    ci_pending: bool,
    missing_required_checks_count: int,
    secrets_detected: bool,
    human_intervention_required: bool,
    attempt_budget_remaining: int,
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
    if attempt_budget_remaining <= 0:
        return "repair_budget_exceeded"
    if blocked_failure_categories:
        return "requires_human_intervention"
    if missing_required_checks_count:
        return "requires_human_intervention"
    if ci_passed:
        return "repair_not_needed"
    if ci_pending:
        return "repair_wait_for_ci"
    if planned and repair_plan_ready:
        return "ci_repair_plan_created"
    return "blocked"
