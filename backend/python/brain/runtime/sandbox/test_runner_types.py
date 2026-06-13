"""Types for the autonomous validation loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class AutonomousTestRunnerLoopRequest:
    commands: list[str] = field(default_factory=list)
    requested_by: str = "unknown"
    loop_mode: str = "disabled"
    runner_mode: str = "sandbox_readonly"
    command_mode: str = "sandbox_allowed"
    working_directory: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    purpose: Optional[str] = None
    stop_on_first_failure: bool = True
    max_commands: int = 10
    timeout_seconds_per_command: int = 60
    total_timeout_seconds: int = 600
    max_stdout_bytes_per_command: int = 20000
    max_stderr_bytes_per_command: int = 20000
    allow_failure_analysis: bool = True
    allow_repair_plan: bool = True
    allow_code_edit: bool = False
    allow_git_mutation: bool = False
    allow_network: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AutonomousTestRunnerLoopResult:
    executed: bool
    blocked: bool
    dry_run: bool
    success: bool
    failed: bool
    timed_out: bool
    partial: bool
    loop_mode: str
    runner_mode: str
    command_mode: str
    commands_requested: list[str]
    commands_planned: list[str]
    commands_executed: int
    commands_blocked: int
    command_results: list[dict[str, object]]
    failure_summary: Optional[str]
    failure_classification: Optional[str]
    recommended_next_action: str
    can_attempt_repair: bool
    repair_requires_new_phase: bool
    can_edit_code: bool
    can_mutate_git: bool
    can_open_pr: bool
    can_merge: bool
    requires_human_intervention: bool
    escalation_reason: Optional[str]
    started_at: str
    finished_at: str
    duration_ms: int
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
