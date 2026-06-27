"""Runtime Truth evidence for controlled CI monitoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

CI_MONITOR_EVIDENCE_VERSION = "1.0"
CI_MONITOR_EVENT_TYPE = "sandbox.ci_monitor.monitor"


@dataclass(frozen=True)
class ControlledCIMonitorEvidence:
    event_type: str
    evidence_version: str
    monitor_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    repository_full_name: Optional[str]
    pr_number: Optional[int]
    pr_url: Optional[str]
    pr_state: Optional[str]
    pr_draft: Optional[bool]
    source_branch: Optional[str]
    head_branch: Optional[str]
    base_branch: str
    head_sha: Optional[str]
    commit_sha: Optional[str]
    monitored: bool
    blocked: bool
    dry_run: bool
    partial: bool
    ci_monitor_gate_eligible: bool
    pr_was_created: bool
    aggregate_status: str
    aggregate_conclusion: str
    terminal: bool
    passed: bool
    failed: bool
    pending: bool
    cancelled: bool
    timed_out: bool
    action_required: bool
    checks_observed_count: int
    workflows_observed_count: int
    missing_required_checks_count: int
    failing_checks_count: int
    pending_checks_count: int
    successful_checks_count: int
    unknown_checks_count: int
    ci_status_fetched: bool
    workflow_runs_fetched: bool
    check_runs_fetched: bool
    github_actions_read: bool
    logs_downloaded: bool
    workflow_retried: bool
    workflow_triggered: bool
    repair_loop_started: bool
    pr_created: bool
    pr_updated: bool
    pr_merged: bool
    auto_merge_enabled: bool
    approval_submitted: bool
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
    secrets_detected: bool
    governance_decision: str
    human_intervention_required: bool
    escalation_reason: Optional[str]
    child_runtime_truth_events: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_ci_monitor_evidence(
    *,
    monitor_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    repository_full_name: str | None,
    pr_number: int | None,
    pr_url: str | None,
    pr_state: str | None,
    pr_draft: bool | None,
    source_branch: str | None,
    head_branch: str | None,
    base_branch: str,
    head_sha: str | None,
    commit_sha: str | None,
    monitored: bool,
    blocked: bool,
    dry_run: bool,
    partial: bool,
    ci_monitor_gate_eligible: bool,
    pr_was_created: bool,
    aggregate_status: str,
    aggregate_conclusion: str,
    terminal: bool,
    passed: bool,
    failed: bool,
    pending: bool,
    cancelled: bool,
    timed_out: bool,
    action_required: bool,
    checks_observed_count: int,
    workflows_observed_count: int,
    missing_required_checks_count: int,
    failing_checks_count: int,
    pending_checks_count: int,
    successful_checks_count: int,
    unknown_checks_count: int,
    ci_status_fetched: bool,
    workflow_runs_fetched: bool,
    check_runs_fetched: bool,
    github_actions_read: bool,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> ControlledCIMonitorEvidence:
    return ControlledCIMonitorEvidence(
        event_type=CI_MONITOR_EVENT_TYPE,
        evidence_version=CI_MONITOR_EVIDENCE_VERSION,
        monitor_mode=monitor_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        repository_full_name=repository_full_name,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        pr_draft=pr_draft,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        commit_sha=commit_sha,
        monitored=monitored,
        blocked=blocked,
        dry_run=dry_run,
        partial=partial,
        ci_monitor_gate_eligible=ci_monitor_gate_eligible,
        pr_was_created=pr_was_created,
        aggregate_status=aggregate_status,
        aggregate_conclusion=aggregate_conclusion,
        terminal=terminal,
        passed=passed,
        failed=failed,
        pending=pending,
        cancelled=cancelled,
        timed_out=timed_out,
        action_required=action_required,
        checks_observed_count=checks_observed_count,
        workflows_observed_count=workflows_observed_count,
        missing_required_checks_count=missing_required_checks_count,
        failing_checks_count=failing_checks_count,
        pending_checks_count=pending_checks_count,
        successful_checks_count=successful_checks_count,
        unknown_checks_count=unknown_checks_count,
        ci_status_fetched=ci_status_fetched,
        workflow_runs_fetched=workflow_runs_fetched,
        check_runs_fetched=check_runs_fetched,
        github_actions_read=github_actions_read,
        logs_downloaded=False,
        workflow_retried=False,
        workflow_triggered=False,
        repair_loop_started=False,
        pr_created=False,
        pr_updated=False,
        pr_merged=False,
        auto_merge_enabled=False,
        approval_submitted=False,
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
        network_used=ci_status_fetched,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        vault_written=False,
        main_modified=False,
        secrets_detected=secrets_detected,
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            passed=passed,
            failed=failed,
            pending=pending,
            partial=partial,
            missing_required_checks_count=missing_required_checks_count,
            aggregate_conclusion=aggregate_conclusion,
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
    passed: bool,
    failed: bool,
    pending: bool,
    partial: bool,
    missing_required_checks_count: int,
    aggregate_conclusion: str,
    secrets_detected: bool,
    human_intervention_required: bool,
) -> str:
    if secrets_detected or blocked:
        return "blocked"
    if dry_run:
        return "dry_run"
    if human_intervention_required:
        return "requires_human_intervention"
    if missing_required_checks_count:
        return "ci_missing_required_checks"
    if passed:
        return "ci_passed"
    if failed:
        return "ci_failed"
    if pending:
        return "ci_pending"
    if partial or aggregate_conclusion == "inconclusive":
        return "ci_inconclusive"
    return "blocked"
