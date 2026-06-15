"""Types for the scoped CI patch proposal gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ScopedCIPatchProposalGateRequest:
    ci_repair_planner_result: Optional[dict[str, Any]] = None
    ci_repair_loop_gate_result: Optional[dict[str, Any]] = None
    ci_monitor_result: Optional[dict[str, Any]] = None
    ci_monitor_gate_result: Optional[dict[str, Any]] = None
    pr_creator_result: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    patch_proposal_gate_mode: str = "disabled"
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
    failure_categories: Optional[list[str]] = None
    blocked_failure_categories: Optional[list[str]] = None
    repair_plan: Optional[dict[str, Any]] = None
    repair_plan_steps: Optional[list[dict[str, Any]]] = None
    affected_areas: Optional[list[str]] = None
    suggested_validation_commands: Optional[list[str]] = None
    required_pre_patch_proposal_checks: Optional[list[str]] = None
    max_repair_attempts: int = 3
    current_repair_attempt: int = 0
    max_files_to_change: int = 5
    max_hunks_total: int = 20
    max_patch_proposal_files: int = 5
    max_patch_proposal_hunks: int = 20
    max_hunks_per_file: int = 8
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
            "dependency_audit_failure",
            "deployment_failure",
            "production_deploy_failure",
            "billing_failure",
            "permission_failure",
            "protected_branch_failure",
            "infrastructure_outage",
            "unknown_infrastructure_failure",
            "flaky_external_service_failure",
            "policy_failure",
            "coverage_threshold_lowering_request",
        ]
    )
    allowed_file_roots: list[str] = field(
        default_factory=lambda: [
            "backend/python",
            "backend/rust/src",
            "frontend/src",
            "tests",
            "docs",
            "sandbox/local",
        ]
    )
    blocked_file_roots: list[str] = field(
        default_factory=lambda: [
            ".git",
            ".github/workflows",
            ".circleci",
            "docs/security",
            "docs/governance",
            "vault/08_ADR",
            ".env",
            "secrets",
            "deploy",
            "billing",
            "production",
        ]
    )
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    require_repair_plan_ready: bool = True
    require_repair_planner_success: bool = True
    require_non_main_head: bool = True
    require_base_main: bool = True
    require_runtime_truth: bool = True
    require_clean_repair_plan_evidence: bool = True
    require_pr_open: bool = True
    require_head_sha: bool = True
    allow_patch_proposal_eligibility: bool = True
    allow_patch_proposal_creation: bool = False
    allow_patch_hunk_generation: bool = False
    allow_patch_apply: bool = False
    allow_file_write: bool = False
    allow_log_download: bool = False
    allow_workflow_retry: bool = False
    allow_workflow_trigger: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
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
class ScopedCIPatchProposalGateResult:
    evaluated: bool
    blocked: bool
    dry_run: bool
    success: bool
    patch_proposal_eligible: bool
    patch_proposal_ready_metadata_only: bool
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
    repair_plan: dict[str, object]
    repair_plan_steps: list[dict[str, object]]
    affected_areas: list[str]
    suggested_validation_commands: list[str]
    required_pre_patch_proposal_checks: list[str]
    scoped_patch_proposal_plan: dict[str, object]
    patch_proposal_scope: list[str]
    candidate_target_areas: list[str]
    candidate_file_roots: list[str]
    blocked_target_areas: list[str]
    unsafe_repair_steps: list[dict[str, object]]
    safe_repair_steps: list[dict[str, object]]
    attempt_budget_remaining: int
    max_patch_proposal_files: int
    max_patch_proposal_hunks: int
    max_hunks_per_file: int
    can_create_patch_proposal: bool
    can_generate_patch_hunks: bool
    can_apply_patch: bool
    can_write_files: bool
    can_download_logs: bool
    can_retry_workflows: bool
    can_trigger_workflows: bool
    can_call_provider: bool
    can_call_agent: bool
    can_commit: bool
    can_push: bool
    can_update_pr: bool
    can_merge: bool
    can_auto_merge: bool
    can_mutate_git: bool
    can_execute_commands: bool
    requires_scoped_patch_proposal_phase: bool
    requires_patch_application_gate_phase: bool
    requires_human_intervention: bool
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
