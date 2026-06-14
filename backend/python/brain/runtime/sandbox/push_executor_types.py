"""Types for controlled push execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ControlledPushExecutorRequest:
    push_gate_result: Optional[dict[str, Any]] = None
    commit_executor_result: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    executor_mode: str = "disabled"
    workspace_root: Optional[str] = None
    current_branch: Optional[str] = None
    verified_current_branch: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    remote_name: str = "origin"
    remote_branch: Optional[str] = None
    proposed_push_ref: Optional[str] = None
    commit_sha: Optional[str] = None
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    require_push_gate_eligible: bool = True
    require_commit_executed: bool = True
    require_non_main_branch: bool = True
    require_runtime_truth: bool = True
    require_clean_evidence: bool = True
    require_remote_origin: bool = True
    allow_push_execution: bool = True
    allow_force_push: bool = False
    allow_main_push: bool = False
    allow_protected_branch_push: bool = False
    allow_pr_creation: bool = False
    allow_merge: bool = False
    allow_rebase: bool = False
    allow_branch_create: bool = False
    allow_checkout: bool = False
    allow_file_write: bool = False
    allow_code_edit: bool = False
    allow_patch_apply: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledPushExecutorResult:
    pushed: bool
    blocked: bool
    dry_run: bool
    success: bool
    partial: bool
    executor_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    current_branch: Optional[str]
    verified_current_branch: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    remote_name: str
    remote_branch: Optional[str]
    proposed_push_ref: Optional[str]
    final_push_ref: Optional[str]
    push_gate_eligible: bool
    commit_was_executed: bool
    commit_sha: Optional[str]
    pre_push_head: Optional[str]
    post_push_head: Optional[str]
    git_operations_attempted: list[str]
    git_operations_completed: list[str]
    git_operations_blocked: list[str]
    status_before: str
    status_after: str
    push_stdout_summary: str
    push_stderr_summary: str
    pushed_ref: Optional[str]
    pushed_remote: Optional[str]
    can_open_pr: bool
    can_merge: bool
    can_rebase: bool
    can_force_push: bool
    can_push_main: bool
    can_create_branch: bool
    can_checkout: bool
    can_edit_code: bool
    can_apply_patch: bool
    can_call_provider: bool
    can_call_agent: bool
    requires_pr_phase: bool
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
