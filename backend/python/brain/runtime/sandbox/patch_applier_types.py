"""Types for controlled branch patch application."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ControlledPatchApplierRequest:
    patch_proposal: Optional[dict[str, Any]] = None
    patch_proposals: list[dict[str, Any]] = field(default_factory=list)
    requested_by: str = "unknown"
    applier_mode: str = "disabled"
    workspace_root: Optional[str] = None
    current_branch: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    allowed_files: list[str] = field(default_factory=list)
    blocked_files: list[str] = field(default_factory=list)
    max_files_to_apply: int = 5
    max_hunks_per_file: int = 8
    max_total_hunks: int = 20
    max_file_bytes: int = 500000
    require_non_main_branch: bool = True
    require_runtime_truth: bool = True
    require_validation_commands: bool = True
    allow_file_create: bool = False
    allow_file_delete: bool = False
    allow_file_rename: bool = False
    allow_chmod: bool = False
    allow_dependency_change: bool = False
    allow_ci_change: bool = False
    allow_governance_change: bool = False
    allow_security_change: bool = False
    allow_vault_write: bool = False
    allow_git_mutation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledPatchApplierResult:
    applied: bool
    blocked: bool
    dry_run: bool
    success: bool
    partial: bool
    applier_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    current_branch: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    files_requested: list[str]
    files_considered: list[str]
    files_applied: list[str]
    files_blocked: list[str]
    hunks_requested: int
    hunks_applied: int
    hunks_blocked: int
    applied_changes: list[dict[str, object]]
    blocked_changes: list[dict[str, object]]
    validation_commands: list[str]
    required_followup_tests: list[str]
    pre_apply_hashes: dict[str, Optional[str]]
    post_apply_hashes: dict[str, Optional[str]]
    can_commit: bool
    can_push: bool
    can_open_pr: bool
    can_merge: bool
    can_execute_tests: bool
    requires_followup_validation: bool
    requires_human_intervention: bool
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
