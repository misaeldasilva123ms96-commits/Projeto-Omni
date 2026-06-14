"""Types for controlled CI monitoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ControlledCIMonitorRequest:
    ci_monitor_gate_result: Optional[dict[str, Any]] = None
    pr_creator_result: Optional[dict[str, Any]] = None
    pr_creation_gate_result: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    monitor_mode: str = "disabled"
    repository_full_name: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    pr_state: Optional[str] = None
    pr_draft: Optional[bool] = None
    source_branch: Optional[str] = None
    head_branch: Optional[str] = None
    base_branch: str = "main"
    head_sha: Optional[str] = None
    commit_sha: Optional[str] = None
    expected_ci_providers: list[str] = field(default_factory=lambda: ["github_actions", "circleci"])
    expected_workflows: list[str] = field(default_factory=list)
    expected_required_checks: list[str] = field(default_factory=list)
    polling_strategy: str = "single_snapshot"
    max_poll_attempts: int = 1
    poll_interval_seconds: int = 0
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    require_ci_monitor_gate_eligible: bool = True
    require_pr_created: bool = True
    require_pr_open: bool = True
    require_non_main_head: bool = True
    require_base_main: bool = True
    require_runtime_truth: bool = True
    require_clean_evidence: bool = True
    require_head_sha: bool = True
    allow_ci_monitoring: bool = True
    allow_github_actions_read: bool = True
    allow_circleci_read: bool = True
    allow_log_download: bool = False
    allow_workflow_retry: bool = False
    allow_workflow_trigger: bool = False
    allow_repair_loop: bool = False
    allow_pr_update: bool = False
    allow_merge: bool = False
    allow_auto_merge: bool = False
    allow_push: bool = False
    allow_git_mutation: bool = False
    allow_command_execution: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledCIMonitorResult:
    monitored: bool
    blocked: bool
    dry_run: bool
    success: bool
    partial: bool
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
    ci_monitor_gate_eligible: bool
    pr_was_created: bool
    ci_status_summary: dict[str, object]
    aggregate_status: str
    aggregate_conclusion: str
    github_actions_status: dict[str, object]
    circleci_status: dict[str, object]
    checks_observed: list[dict[str, object]]
    workflows_observed: list[dict[str, object]]
    required_checks_observed: list[dict[str, object]]
    missing_required_checks: list[str]
    failing_checks: list[dict[str, object]]
    pending_checks: list[dict[str, object]]
    skipped_or_neutral_checks: list[dict[str, object]]
    successful_checks: list[dict[str, object]]
    unknown_checks: list[dict[str, object]]
    terminal: bool
    passed: bool
    failed: bool
    pending: bool
    cancelled: bool
    timed_out: bool
    action_required: bool
    logs_downloaded: bool
    workflow_retried: bool
    repair_loop_started: bool
    ci_operations_attempted: list[str]
    ci_operations_completed: list[str]
    ci_operations_blocked: list[str]
    can_download_logs: bool
    can_retry_workflows: bool
    can_start_repair_loop: bool
    can_update_pr: bool
    can_merge: bool
    can_auto_merge: bool
    can_push: bool
    can_force_push: bool
    can_push_main: bool
    can_rebase: bool
    can_create_branch: bool
    can_checkout: bool
    can_edit_code: bool
    can_apply_patch: bool
    can_call_provider: bool
    can_call_agent: bool
    requires_repair_loop_gate_phase: bool
    requires_merge_gate_phase: bool
    requires_human_intervention: bool
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
