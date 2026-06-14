"""Types for controlled push eligibility decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ControlledPushGateRequest:
    commit_executor_result: Optional[dict[str, Any]] = None
    commit_gate_result: Optional[dict[str, Any]] = None
    post_patch_validation_result: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    push_gate_mode: str = "disabled"
    workspace_root: Optional[str] = None
    current_branch: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    remote_name: str = "origin"
    remote_branch: Optional[str] = None
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    commit_sha: Optional[str] = None
    pre_commit_head: Optional[str] = None
    post_commit_head: Optional[str] = None
    files_committed: list[str] = field(default_factory=list)
    proposed_push_ref: Optional[str] = None
    require_commit_executed: bool = True
    require_non_main_branch: bool = True
    require_runtime_truth: bool = True
    require_clean_commit_evidence: bool = True
    require_no_uncommitted_changes: bool = False
    allow_push_execution: bool = False
    allow_force_push: bool = False
    allow_main_push: bool = False
    allow_protected_branch_push: bool = False
    allow_git_mutation: bool = False
    allow_pr_creation: bool = False
    allow_merge: bool = False
    allow_rebase: bool = False
    allow_branch_create: bool = False
    allow_checkout: bool = False
    allow_network: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledPushGateResult:
    evaluated: bool
    blocked: bool
    dry_run: bool
    success: bool
    push_eligible: bool
    push_ready_metadata_only: bool
    push_gate_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    current_branch: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    remote_name: str
    remote_branch: Optional[str]
    proposed_push_ref: Optional[str]
    commit_was_executed: bool
    commit_sha: Optional[str]
    pre_commit_head: Optional[str]
    post_commit_head: Optional[str]
    commit_evidence_clean: bool
    branch_safe: bool
    remote_safe: bool
    protected_branch_detected: bool
    force_push_detected: bool
    main_push_detected: bool
    secrets_detected: bool
    git_mutation_issue_detected: bool
    files_considered: list[str]
    files_blocked: list[str]
    push_plan: dict[str, object]
    required_pre_push_checks: list[str]
    can_execute_push: bool
    can_force_push: bool
    can_push_main: bool
    can_open_pr: bool
    can_merge: bool
    can_rebase: bool
    can_create_branch: bool
    can_checkout: bool
    can_edit_code: bool
    can_apply_patch: bool
    can_call_provider: bool
    can_call_agent: bool
    can_use_network: bool
    requires_human_intervention: bool
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
