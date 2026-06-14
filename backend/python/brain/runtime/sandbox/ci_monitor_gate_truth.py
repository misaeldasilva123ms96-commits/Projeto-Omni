"""Runtime Truth evidence for CI monitor gate decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

CI_MONITOR_GATE_EVIDENCE_VERSION = "1.0"
CI_MONITOR_GATE_EVENT_TYPE = "sandbox.ci_monitor_gate.decision"


@dataclass(frozen=True)
class CIMonitorGateEvidence:
    event_type: str
    evidence_version: str
    ci_monitor_gate_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    repository_full_name: Optional[str]
    pr_number: Optional[int]
    pr_url: Optional[str]
    pr_state: Optional[str]
    pr_draft: Optional[bool]
    source_branch: Optional[str]
    head_branch: Optional[str]
    base_branch: str
    head_sha: Optional[str]
    base_sha: Optional[str]
    merge_commit_sha: Optional[str]
    commit_sha: Optional[str]
    evaluated: bool
    blocked: bool
    dry_run: bool
    ci_monitor_eligible: bool
    ci_monitor_ready_metadata_only: bool
    pr_was_created: bool
    pr_evidence_clean: bool
    repository_safe: bool
    pr_safe: bool
    branch_safe: bool
    base_safe: bool
    head_sha_safe: bool
    expected_ci_providers_safe: bool
    expected_workflows_safe: bool
    expected_required_checks_safe: bool
    secrets_detected: bool
    protected_branch_detected: bool
    main_head_detected: bool
    merged_pr_detected: bool
    closed_pr_detected: bool
    unsafe_repository_detected: bool
    ci_monitored: bool
    ci_status_fetched: bool
    workflow_runs_fetched: bool
    check_runs_fetched: bool
    logs_downloaded: bool
    workflow_retried: bool
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
    governance_decision: str
    human_intervention_required: bool
    escalation_reason: Optional[str]
    child_runtime_truth_events: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_ci_monitor_gate_evidence(
    *,
    ci_monitor_gate_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    workspace_root: str | None,
    repository_full_name: str | None,
    pr_number: int | None,
    pr_url: str | None,
    pr_state: str | None,
    pr_draft: bool | None,
    source_branch: str | None,
    head_branch: str | None,
    base_branch: str,
    head_sha: str | None,
    base_sha: str | None,
    merge_commit_sha: str | None,
    commit_sha: str | None,
    evaluated: bool,
    blocked: bool,
    dry_run: bool,
    ci_monitor_eligible: bool,
    ci_monitor_ready_metadata_only: bool,
    pr_was_created: bool,
    pr_evidence_clean: bool,
    repository_safe: bool,
    pr_safe: bool,
    branch_safe: bool,
    base_safe: bool,
    head_sha_safe: bool,
    expected_ci_providers_safe: bool,
    expected_workflows_safe: bool,
    expected_required_checks_safe: bool,
    secrets_detected: bool,
    protected_branch_detected: bool,
    main_head_detected: bool,
    merged_pr_detected: bool,
    closed_pr_detected: bool,
    unsafe_repository_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
    child_runtime_truth_events: list[dict[str, object]],
) -> CIMonitorGateEvidence:
    return CIMonitorGateEvidence(
        event_type=CI_MONITOR_GATE_EVENT_TYPE,
        evidence_version=CI_MONITOR_GATE_EVIDENCE_VERSION,
        ci_monitor_gate_mode=ci_monitor_gate_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        repository_full_name=repository_full_name,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        pr_draft=pr_draft,
        source_branch=source_branch,
        head_branch=head_branch,
        base_branch=base_branch,
        head_sha=head_sha,
        base_sha=base_sha,
        merge_commit_sha=merge_commit_sha,
        commit_sha=commit_sha,
        evaluated=evaluated,
        blocked=blocked,
        dry_run=dry_run,
        ci_monitor_eligible=ci_monitor_eligible,
        ci_monitor_ready_metadata_only=ci_monitor_ready_metadata_only,
        pr_was_created=pr_was_created,
        pr_evidence_clean=pr_evidence_clean,
        repository_safe=repository_safe,
        pr_safe=pr_safe,
        branch_safe=branch_safe,
        base_safe=base_safe,
        head_sha_safe=head_sha_safe,
        expected_ci_providers_safe=expected_ci_providers_safe,
        expected_workflows_safe=expected_workflows_safe,
        expected_required_checks_safe=expected_required_checks_safe,
        secrets_detected=secrets_detected,
        protected_branch_detected=protected_branch_detected,
        main_head_detected=main_head_detected,
        merged_pr_detected=merged_pr_detected,
        closed_pr_detected=closed_pr_detected,
        unsafe_repository_detected=unsafe_repository_detected,
        ci_monitored=False,
        ci_status_fetched=False,
        workflow_runs_fetched=False,
        check_runs_fetched=False,
        logs_downloaded=False,
        workflow_retried=False,
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
        network_used=False,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        vault_written=False,
        main_modified=False,
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            ci_monitor_eligible=ci_monitor_eligible,
            pr_was_created=pr_was_created,
            pr_safe=pr_safe,
            branch_safe=branch_safe,
            repository_safe=repository_safe,
            head_sha_safe=head_sha_safe,
            secrets_detected=secrets_detected,
            merged_pr_detected=merged_pr_detected,
            closed_pr_detected=closed_pr_detected,
            protected_branch_detected=protected_branch_detected,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
        child_runtime_truth_events=child_runtime_truth_events,
    )


def _governance_decision(
    *,
    blocked: bool,
    dry_run: bool,
    ci_monitor_eligible: bool,
    pr_was_created: bool,
    pr_safe: bool,
    branch_safe: bool,
    repository_safe: bool,
    head_sha_safe: bool,
    secrets_detected: bool,
    merged_pr_detected: bool,
    closed_pr_detected: bool,
    protected_branch_detected: bool,
) -> str:
    if secrets_detected or blocked:
        if not pr_was_created:
            return "ci_monitor_not_eligible_missing_pr"
        if not pr_safe:
            return "ci_monitor_not_eligible_pr_state"
        if not branch_safe:
            return "ci_monitor_not_eligible_branch_risk"
        if not repository_safe:
            return "ci_monitor_not_eligible_repository_risk"
        if not head_sha_safe:
            return "ci_monitor_not_eligible_missing_head_sha"
        return "blocked"
    if dry_run:
        return "dry_run"
    if merged_pr_detected or closed_pr_detected:
        return "requires_human_intervention"
    if protected_branch_detected:
        return "requires_human_intervention"
    if ci_monitor_eligible:
        return "ci_monitor_eligible"
    return "blocked"
