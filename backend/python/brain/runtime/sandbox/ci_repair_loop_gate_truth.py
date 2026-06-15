"""Runtime Truth evidence for CI repair loop gate decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

CI_REPAIR_LOOP_GATE_EVIDENCE_VERSION = "1.0"
CI_REPAIR_LOOP_GATE_EVENT_TYPE = "sandbox.ci_repair_loop_gate.decision"


@dataclass(frozen=True)
class CIRepairLoopGateEvidence:
    event_type: str
    evidence_version: str
    repair_gate_mode: str
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
    repair_loop_eligible: bool
    repair_loop_ready_metadata_only: bool
    ci_monitor_clean: bool
    ci_failed: bool
    ci_passed: bool
    ci_pending: bool
    ci_inconclusive: bool
    aggregate_status: str
    aggregate_conclusion: str
    failing_checks_count: int
    pending_checks_count: int
    missing_required_checks_count: int
    unknown_checks_count: int
    failure_categories: list[str]
    blocked_failure_categories: list[str]
    max_repair_attempts: int
    current_repair_attempt: int
    attempt_budget_remaining: int
    repair_loop_started: bool
    repair_plan_created: bool
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


def build_ci_repair_loop_gate_evidence(
    *,
    repair_gate_mode: str,
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
    repair_loop_eligible: bool,
    repair_loop_ready_metadata_only: bool,
    ci_monitor_clean: bool,
    ci_failed: bool,
    ci_passed: bool,
    ci_pending: bool,
    ci_inconclusive: bool,
    aggregate_status: str,
    aggregate_conclusion: str,
    failing_checks_count: int,
    pending_checks_count: int,
    missing_required_checks_count: int,
    unknown_checks_count: int,
    failure_categories: list[str],
    blocked_failure_categories: list[str],
    max_repair_attempts: int,
    current_repair_attempt: int,
    attempt_budget_remaining: int,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> CIRepairLoopGateEvidence:
    return CIRepairLoopGateEvidence(
        event_type=CI_REPAIR_LOOP_GATE_EVENT_TYPE,
        evidence_version=CI_REPAIR_LOOP_GATE_EVIDENCE_VERSION,
        repair_gate_mode=repair_gate_mode,
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
        repair_loop_eligible=repair_loop_eligible,
        repair_loop_ready_metadata_only=repair_loop_ready_metadata_only,
        ci_monitor_clean=ci_monitor_clean,
        ci_failed=ci_failed,
        ci_passed=ci_passed,
        ci_pending=ci_pending,
        ci_inconclusive=ci_inconclusive,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        failing_checks_count=failing_checks_count,
        pending_checks_count=pending_checks_count,
        missing_required_checks_count=missing_required_checks_count,
        unknown_checks_count=unknown_checks_count,
        failure_categories=failure_categories,
        blocked_failure_categories=blocked_failure_categories,
        max_repair_attempts=max_repair_attempts,
        current_repair_attempt=current_repair_attempt,
        attempt_budget_remaining=attempt_budget_remaining,
        repair_loop_started=False,
        repair_plan_created=False,
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
            ci_passed=ci_passed,
            ci_failed=ci_failed,
            ci_pending=ci_pending,
            ci_inconclusive=ci_inconclusive,
            missing_required_checks_count=missing_required_checks_count,
            secrets_detected=secrets_detected,
            human_intervention_required=human_intervention_required,
            repair_loop_eligible=repair_loop_eligible,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
        child_runtime_truth_events=child_runtime_truth_events,
    )


def _governance_decision(
    *,
    blocked: bool,
    dry_run: bool,
    ci_passed: bool,
    ci_failed: bool,
    ci_pending: bool,
    ci_inconclusive: bool,
    missing_required_checks_count: int,
    secrets_detected: bool,
    human_intervention_required: bool,
    repair_loop_eligible: bool,
) -> str:
    if secrets_detected or blocked:
        return "blocked"
    if dry_run:
        return "dry_run"
    if human_intervention_required:
        return "requires_human_intervention"
    if missing_required_checks_count:
        return "requires_human_intervention"
    if ci_passed:
        return "repair_not_needed"
    if ci_pending:
        return "repair_wait_for_ci"
    if ci_inconclusive:
        return "repair_loop_eligible_inconclusive"
    if ci_failed and not repair_loop_eligible:
        return "repair_budget_exceeded"
    if ci_failed and repair_loop_eligible:
        return "repair_loop_eligible"
    return "blocked"
