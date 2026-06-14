"""Types for controlled commit execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ControlledCommitExecutorRequest:
    commit_gate_result: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    executor_mode: str = "disabled"
    workspace_root: Optional[str] = None
    current_branch: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    files_to_commit: list[str] = field(default_factory=list)
    proposed_commit_message: Optional[str] = None
    commit_message_hint: Optional[str] = None
    require_commit_gate_eligible: bool = True
    require_non_main_branch: bool = True
    require_runtime_truth: bool = True
    require_validation_passed: bool = True
    require_patch_applied: bool = True
    require_clean_evidence: bool = True
    max_files_to_stage: int = 20
    max_commit_message_chars: int = 120
    allow_git_add: bool = True
    allow_git_commit: bool = True
    allow_push: bool = False
    allow_pr_creation: bool = False
    allow_merge: bool = False
    allow_rebase: bool = False
    allow_branch_create: bool = False
    allow_checkout: bool = False
    allow_file_write: bool = False
    allow_code_edit: bool = False
    allow_patch_apply: bool = False
    allow_network: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledCommitExecutorResult:
    committed: bool
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
    commit_gate_eligible: bool
    files_requested: list[str]
    files_considered: list[str]
    files_staged: list[str]
    files_blocked: list[str]
    proposed_commit_message: Optional[str]
    final_commit_message: Optional[str]
    pre_commit_head: Optional[str]
    post_commit_head: Optional[str]
    commit_sha: Optional[str]
    git_operations_attempted: list[str]
    git_operations_completed: list[str]
    git_operations_blocked: list[str]
    status_before: str
    status_after: str
    can_push: bool
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
    requires_push_phase: bool
    requires_pr_phase: bool
    requires_human_intervention: bool
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
