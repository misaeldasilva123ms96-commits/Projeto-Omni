"""Types for PR creation eligibility decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class PRCreationGateRequest:
    push_executor_result: Optional[dict[str, Any]] = None
    push_gate_result: Optional[dict[str, Any]] = None
    commit_executor_result: Optional[dict[str, Any]] = None
    commit_gate_result: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    pr_gate_mode: str = "disabled"
    workspace_root: Optional[str] = None
    repository_full_name: Optional[str] = None
    source_branch: Optional[str] = None
    head_branch: Optional[str] = None
    base_branch: str = "main"
    current_branch: Optional[str] = None
    remote_name: str = "origin"
    remote_branch: Optional[str] = None
    pushed_ref: Optional[str] = None
    pushed_remote: Optional[str] = None
    commit_sha: Optional[str] = None
    pr_title_hint: Optional[str] = None
    pr_body_hint: Optional[str] = None
    labels: list[str] = field(default_factory=list)
    reviewers: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    require_push_executed: bool = True
    require_non_main_source_branch: bool = True
    require_base_main: bool = True
    require_runtime_truth: bool = True
    require_clean_push_evidence: bool = True
    require_commit_sha: bool = True
    allow_pr_creation: bool = False
    allow_draft_pr: bool = True
    allow_ready_pr: bool = True
    allow_auto_merge: bool = False
    allow_merge: bool = False
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
class PRCreationGateResult:
    evaluated: bool
    blocked: bool
    dry_run: bool
    success: bool
    pr_eligible: bool
    pr_ready_metadata_only: bool
    pr_gate_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    repository_full_name: Optional[str]
    source_branch: Optional[str]
    head_branch: Optional[str]
    base_branch: str
    current_branch: Optional[str]
    remote_name: str
    remote_branch: Optional[str]
    pushed_ref: Optional[str]
    pushed_remote: Optional[str]
    commit_sha: Optional[str]
    push_was_executed: bool
    push_evidence_clean: bool
    branch_safe: bool
    base_safe: bool
    repository_safe: bool
    title_safe: bool
    body_safe: bool
    labels_safe: bool
    reviewers_safe: bool
    assignees_safe: bool
    secrets_detected: bool
    protected_branch_detected: bool
    main_source_branch_detected: bool
    unsafe_repository_detected: bool
    duplicate_pr_risk: bool
    pr_plan: dict[str, object]
    proposed_pr_title: Optional[str]
    proposed_pr_body: Optional[str]
    proposed_pr_draft: bool
    proposed_labels: list[str]
    proposed_reviewers: list[str]
    proposed_assignees: list[str]
    required_pre_pr_checks: list[str]
    can_create_pr: bool
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
    requires_pr_executor_phase: bool
    requires_ci_monitor_phase: bool
    requires_human_intervention: bool
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
