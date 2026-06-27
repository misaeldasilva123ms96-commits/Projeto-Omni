"""Types for CI monitor gate decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class CIMonitorGateRequest:
    pr_creator_result: Optional[dict[str, Any]] = None
    pr_creation_gate_result: Optional[dict[str, Any]] = None
    push_executor_result: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    ci_monitor_gate_mode: str = "disabled"
    workspace_root: Optional[str] = None
    repository_full_name: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    pr_state: Optional[str] = None
    pr_draft: Optional[bool] = None
    source_branch: Optional[str] = None
    head_branch: Optional[str] = None
    base_branch: str = "main"
    head_sha: Optional[str] = None
    base_sha: Optional[str] = None
    merge_commit_sha: Optional[str] = None
    commit_sha: Optional[str] = None
    expected_ci_providers: list[str] = field(default_factory=lambda: ["github_actions"])
    expected_workflows: list[str] = field(default_factory=list)
    expected_required_checks: list[str] = field(default_factory=list)
    allowed_statuses: list[str] = field(
        default_factory=lambda: [
            "queued",
            "in_progress",
            "pending",
            "success",
            "failure",
            "cancelled",
            "skipped",
            "neutral",
            "timed_out",
            "action_required",
        ]
    )
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    require_pr_created: bool = True
    require_pr_open: bool = True
    require_non_main_head: bool = True
    require_base_main: bool = True
    require_runtime_truth: bool = True
    require_clean_pr_evidence: bool = True
    require_head_sha: bool = True
    require_repository_safe: bool = True
    allow_ci_monitoring: bool = False
    allow_github_api: bool = False
    allow_log_download: bool = False
    allow_workflow_retry: bool = False
    allow_repair_loop: bool = False
    allow_merge: bool = False
    allow_auto_merge: bool = False
    allow_pr_update: bool = False
    allow_push: bool = False
    allow_force_push: bool = False
    allow_main_push: bool = False
    allow_git_mutation: bool = False
    allow_command_execution: bool = False
    allow_network: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CIMonitorGateResult:
    evaluated: bool
    blocked: bool
    dry_run: bool
    success: bool
    ci_monitor_eligible: bool
    ci_monitor_ready_metadata_only: bool
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
    ci_monitor_plan: dict[str, object]
    required_pre_ci_monitor_checks: list[str]
    can_monitor_ci: bool
    can_call_github_api: bool
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
    can_use_network: bool
    requires_ci_monitor_executor_phase: bool
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
