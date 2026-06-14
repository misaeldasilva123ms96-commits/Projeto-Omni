"""Types for scoped patch proposal planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ScopedPatchProposalRequest:
    repair_plan: Optional[dict[str, Any]] = None
    repair_category: Optional[str] = None
    failure_classification: Optional[str] = None
    requested_by: str = "unknown"
    proposal_mode: str = "disabled"
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    allowed_files: list[str] = field(default_factory=list)
    blocked_files: list[str] = field(default_factory=list)
    suspected_files: list[str] = field(default_factory=list)
    proposed_steps: list[dict[str, Any]] = field(default_factory=list)
    validation_commands: list[str] = field(default_factory=list)
    file_contexts: dict[str, str] = field(default_factory=dict)
    max_files_to_patch: int = 5
    max_patch_hunks_per_file: int = 8
    max_total_patch_hunks: int = 20
    allow_code_edit: bool = False
    allow_patch_apply: bool = False
    allow_file_write: bool = False
    allow_git_mutation: bool = False
    allow_command_execution: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    allow_network: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ScopedPatchProposalResult:
    proposed: bool
    blocked: bool
    dry_run: bool
    success: bool
    proposal_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    repair_category: str
    failure_classification: Optional[str]
    patch_scope: str
    patch_complexity: str
    risk_level: str
    files_considered: list[str]
    files_proposed: list[str]
    files_blocked: list[str]
    patch_proposals: list[dict[str, object]]
    validation_commands: list[str]
    required_followup_tests: list[str]
    can_apply_patch: bool
    patch_requires_human: bool
    patch_requires_new_phase: bool
    can_edit_code: bool
    can_write_files: bool
    can_mutate_git: bool
    can_execute_commands: bool
    can_call_provider: bool
    can_call_agent: bool
    can_use_network: bool
    can_open_pr: bool
    can_merge: bool
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
