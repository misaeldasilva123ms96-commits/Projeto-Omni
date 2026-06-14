"""Types for controlled commit eligibility decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ControlledCommitGateRequest:
    post_patch_validation_result: Optional[dict[str, Any]] = None
    patch_apply_result: Optional[dict[str, Any]] = None
    patch_proposal_result: Optional[dict[str, Any]] = None
    repair_plan: Optional[dict[str, Any]] = None
    requested_by: str = "unknown"
    commit_gate_mode: str = "disabled"
    workspace_root: Optional[str] = None
    current_branch: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    changed_files: list[str] = field(default_factory=list)
    files_applied: list[str] = field(default_factory=list)
    files_blocked: list[str] = field(default_factory=list)
    validation_commands: list[str] = field(default_factory=list)
    validation_summary: Optional[str] = None
    commit_message_hint: Optional[str] = None
    require_post_patch_validation: bool = True
    require_patch_applied: bool = True
    require_non_main_branch: bool = True
    require_runtime_truth: bool = True
    require_clean_validation: bool = True
    allow_commit_execution: bool = False
    allow_git_mutation: bool = False
    allow_push: bool = False
    allow_pr_creation: bool = False
    allow_merge: bool = False
    allow_protected_files: bool = False
    allow_ci_change: bool = False
    allow_governance_change: bool = False
    allow_security_change: bool = False
    allow_vault_write: bool = False
    allow_network: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledCommitGateResult:
    evaluated: bool
    blocked: bool
    dry_run: bool
    success: bool
    commit_eligible: bool
    commit_ready_metadata_only: bool
    commit_gate_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    current_branch: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    patch_was_applied: bool
    post_patch_validated: bool
    validation_passed: bool
    validation_failed: bool
    validation_timed_out: bool
    protected_files_detected: bool
    secrets_detected: bool
    git_mutation_detected: bool
    main_modification_detected: bool
    files_considered: list[str]
    files_eligible_for_commit: list[str]
    files_blocked_from_commit: list[str]
    commit_plan: dict[str, object]
    proposed_commit_message: str
    validation_summary: Optional[str]
    required_pre_commit_checks: list[str]
    required_followup_tests: list[str]
    can_execute_commit: bool
    can_stage_files: bool
    can_push: bool
    can_open_pr: bool
    can_merge: bool
    can_edit_code: bool
    can_apply_patch: bool
    can_mutate_git: bool
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
