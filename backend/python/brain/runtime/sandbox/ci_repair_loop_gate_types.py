"""Types for CI repair loop gate decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class CIRepairLoopGateRequest:
    ci_monitor_result: Optional[dict[str, Any]] = None
    ci_monitor_gate_result: Optional[dict[str, Any]] = None
    pr_creator_result: Optional[dict[str, Any]] = None
    pr_creation_gate_result: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    repair_gate_mode: str = "disabled"
    workspace_root: Optional[str] = None
    repository_full_name: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    pr_state: Optional[str] = None
    source_branch: Optional[str] = None
    head_branch: Optional[str] = None
    base_branch: str = "main"
    head_sha: Optional[str] = None
    commit_sha: Optional[str] = None
    aggregate_status: Optional[str] = None
    aggregate_conclusion: Optional[str] = None
    failing_checks: Optional[list[str]] = None
    pending_checks: Optional[list[str]] = None
    missing_required_checks: Optional[list[str]] = None
    unknown_checks: Optional[list[str]] = None
    successful_checks: Optional[list[str]] = None
    skipped_or_neutral_checks: Optional[list[str]] = None
    repair_scope: Optional[list[dict[str, Any]]] = None
    max_repair_attempts: int = 3
    current_repair_attempt: int = 0
    max_files_to_change: int = 5
    max_hunks_total: int = 20
    allowed_repair_categories: list[str] = field(
        default_factory=lambda: [
            "test_failure",
            "typecheck_failure",
            "lint_failure",
            "format_failure",
            "build_failure",
        ]
    )
    blocked_repair_categories: list[str] = field(
        default_factory=lambda: [
            "security_failure",
            "secret_failure",
            "deployment_failure",
            "billing_failure",
            "permission_failure",
            "unknown_infrastructure_failure",
        ]
    )
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    require_ci_monitor_failed: bool = True
    require_non_main_head: bool = True
    require_base_main: bool = True
    require_runtime_truth: bool = True
    require_clean_ci_evidence: bool = True
    require_pr_open: bool = True
    require_head_sha: bool = True
    allow_repair_loop: bool = False
    allow_log_download: bool = False
    allow_workflow_retry: bool = False
    allow_workflow_trigger: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    allow_patch_proposal: bool = False
    allow_patch_apply: bool = False
    allow_file_write: bool = False
    allow_commit: bool = False
    allow_push: bool = False
    allow_pr_update: bool = False
    allow_merge: bool = False
    allow_auto_merge: bool = False
    allow_git_mutation: bool = False
    allow_command_execution: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CIRepairLoopGateResult:
    evaluated: bool
    blocked: bool
    dry_run: bool
    success: bool
    repair_loop_eligible: bool
    repair_loop_ready_metadata_only: bool
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
    ci_monitor_clean: bool
    ci_failed: bool
    ci_passed: bool
    ci_pending: bool
    ci_inconclusive: bool
    aggregate_status: str
    aggregate_conclusion: str
    failing_checks: list[dict[str, object]]
    pending_checks: list[dict[str, object]]
    missing_required_checks: list[str]
    unknown_checks: list[dict[str, object]]
    successful_checks: list[dict[str, object]]
    skipped_or_neutral_checks: list[dict[str, object]]
    failure_categories: list[str]
    blocked_failure_categories: list[str]
    repair_scope: list[dict[str, object]]
    repair_plan: dict[str, object]
    required_pre_repair_checks: list[str]
    max_repair_attempts: int
    current_repair_attempt: int
    attempt_budget_remaining: int
    can_start_repair_loop: bool
    can_download_logs: bool
    can_retry_workflows: bool
    can_trigger_workflows: bool
    can_call_provider: bool
    can_call_agent: bool
    can_create_patch_proposal: bool
    can_apply_patch: bool
    can_write_files: bool
    can_commit: bool
    can_push: bool
    can_update_pr: bool
    can_merge: bool
    can_auto_merge: bool
    can_mutate_git: bool
    can_execute_commands: bool
    requires_repair_planner_phase: bool
    requires_patch_proposal_phase: bool
    requires_human_intervention: bool
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
