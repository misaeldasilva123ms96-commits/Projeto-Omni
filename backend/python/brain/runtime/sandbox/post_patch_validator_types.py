"""Types for post-patch validation orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class PostPatchValidationRequest:
    patch_apply_result: Optional[dict[str, Any]] = None
    validation_commands: list[str] = field(default_factory=list)
    required_followup_tests: list[str] = field(default_factory=list)
    requested_by: str = "unknown"
    validator_mode: str = "disabled"
    loop_mode: str = "sandbox_readonly"
    runner_mode: str = "sandbox_readonly"
    command_mode: str = "sandbox_allowed"
    workspace_root: Optional[str] = None
    current_branch: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    stop_on_first_failure: bool = True
    max_commands: int = 10
    timeout_seconds_per_command: int = 60
    total_timeout_seconds: int = 600
    max_stdout_bytes_per_command: int = 20000
    max_stderr_bytes_per_command: int = 20000
    require_patch_applied: bool = True
    require_non_main_branch: bool = True
    require_runtime_truth: bool = True
    allow_commit_recommendation: bool = True
    allow_git_mutation: bool = False
    allow_code_edit: bool = False
    allow_patch_apply: bool = False
    allow_network: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PostPatchValidationResult:
    validated: bool
    blocked: bool
    dry_run: bool
    success: bool
    failed: bool
    timed_out: bool
    partial: bool
    validator_mode: str
    loop_mode: str
    runner_mode: str
    command_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    workspace_root: Optional[str]
    current_branch: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    patch_was_applied: bool
    patch_apply_evidence: dict[str, object]
    validation_commands: list[str]
    commands_executed: int
    commands_blocked: int
    test_loop_result: Optional[dict[str, object]]
    validation_summary: Optional[str]
    validation_classification: str
    recommended_next_action: str
    ready_for_commit: bool
    ready_for_pr: bool
    requires_repair_cycle: bool
    requires_human_intervention: bool
    can_commit: bool
    can_push: bool
    can_open_pr: bool
    can_merge: bool
    can_edit_code: bool
    can_apply_patch: bool
    can_mutate_git: bool
    can_call_provider: bool
    can_call_agent: bool
    can_use_network: bool
    started_at: str
    finished_at: str
    duration_ms: int
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
