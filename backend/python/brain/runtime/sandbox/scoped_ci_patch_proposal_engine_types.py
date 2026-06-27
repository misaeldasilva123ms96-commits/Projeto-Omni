"""Types for the scoped CI patch proposal engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ScopedCIPatchProposalEngineRequest:
    scoped_ci_patch_proposal_gate_result: Optional[dict[str, Any]] = None
    ci_repair_planner_result: Optional[dict[str, Any]] = None
    ci_repair_loop_gate_result: Optional[dict[str, Any]] = None
    ci_monitor_result: Optional[dict[str, Any]] = None
    ci_monitor_gate_result: Optional[dict[str, Any]] = None
    pr_creator_result: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    proposal_mode: str = "disabled"
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
    scoped_patch_proposal_plan: Optional[dict[str, Any]] = None
    patch_proposal_scope: Optional[dict[str, Any]] = None
    candidate_target_areas: Optional[list[str]] = None
    candidate_file_roots: Optional[list[str]] = None
    suggested_validation_commands: Optional[list[str]] = None
    required_pre_patch_proposal_checks: Optional[list[str]] = None
    max_repair_attempts: int = 3
    current_repair_attempt: int = 0
    max_files_to_change: int = 5
    max_hunks_total: int = 20
    max_patch_proposal_files: int = 5
    max_patch_proposal_hunks: int = 20
    max_hunks_per_file: int = 8
    allowed_operations: list[str] = field(
        default_factory=lambda: ["modify_existing", "add_test", "add_documentation"]
    )
    blocked_operations: list[str] = field(
        default_factory=lambda: [
            "delete_file", "rename_file", "move_file", "chmod_change",
            "dependency_upgrade", "ci_threshold_change", "security_policy_change",
            "governance_policy_change", "production_deploy_change",
            "billing_change", "secret_change",
        ]
    )
    allowed_repair_categories: list[str] = field(
        default_factory=lambda: [
            "test_failure", "typecheck_failure", "lint_failure",
            "format_failure", "build_failure",
        ]
    )
    blocked_repair_categories: list[str] = field(
        default_factory=lambda: [
            "security_failure", "secret_failure", "dependency_audit_failure",
            "deployment_failure", "production_deploy_failure", "billing_failure",
            "permission_failure", "protected_branch_failure", "infrastructure_outage",
            "unknown_infrastructure_failure", "flaky_external_service_failure",
            "policy_failure", "coverage_threshold_lowering_request",
        ]
    )
    allowed_file_roots: list[str] = field(
        default_factory=lambda: [
            "backend/python", "backend/rust/src", "frontend/src",
            "tests", "docs", "sandbox/local",
        ]
    )
    blocked_file_roots: list[str] = field(
        default_factory=lambda: [
            ".git", ".github/workflows",
            "docs/security", "docs/governance", "vault/08_ADR",
            ".env", "secrets", "deploy", "billing", "production",
        ]
    )
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    require_gate_eligible: bool = True
    require_gate_success: bool = True
    require_repair_plan_ready: bool = True
    require_non_main_head: bool = True
    require_base_main: bool = True
    require_runtime_truth: bool = True
    require_clean_gate_evidence: bool = True
    require_pr_open: bool = True
    require_head_sha: bool = True
    allow_proposal_generation: bool = True
    allow_patch_application: bool = False
    allow_file_write: bool = False
    allow_source_inspection: bool = False
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
class ScopedCIPatchProposalEngineResult:
    proposal_created: bool
    blocked: bool
    dry_run: bool
    success: bool
    partial: bool
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
    repair_plan: dict[str, object]
    repair_plan_steps: list[dict[str, object]]
    scoped_ci_patch_proposals: list[dict[str, object]]
    patch_proposal_summary: dict[str, object]
    proposal_hunks: list[dict[str, object]]
    proposal_files: list[str]
    proposal_operations: list[str]
    proposal_scope: list[str]
    candidate_target_areas: list[str]
    candidate_file_roots: list[str]
    blocked_target_areas: list[str]
    skipped_repair_steps: list[dict[str, object]]
    unsafe_repair_steps: list[dict[str, object]]
    safe_repair_steps: list[dict[str, object]]
    suggested_validation_commands: list[str]
    required_pre_patch_application_checks: list[str]
    required_followup_tests: list[str]
    max_patch_proposal_files: int
    max_patch_proposal_hunks: int
    max_hunks_per_file: int
    files_proposed_count: int
    hunks_proposed_count: int
    can_apply_patch: bool
    can_write_files: bool
    can_inspect_source: bool
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
