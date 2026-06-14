"""Types for the autonomous repair planner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class AutonomousRepairPlannerRequest:
    test_loop_result: Optional[dict[str, Any]] = None
    failure_summary: Optional[str] = None
    failure_classification: Optional[str] = None
    command_results: list[dict[str, Any]] = field(default_factory=list)
    requested_by: str = "unknown"
    planner_mode: str = "disabled"
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    task_type: Optional[str] = None
    files_changed: list[str] = field(default_factory=list)
    allowed_files: list[str] = field(default_factory=list)
    blocked_files: list[str] = field(default_factory=list)
    max_files_to_touch: int = 5
    max_repair_steps: int = 10
    allow_code_edit: bool = False
    allow_git_mutation: bool = False
    allow_test_execution: bool = False
    allow_provider_call: bool = False
    allow_agent_call: bool = False
    allow_network: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AutonomousRepairPlannerResult:
    planned: bool
    blocked: bool
    dry_run: bool
    success: bool
    planner_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    failure_summary: Optional[str]
    failure_classification: Optional[str]
    normalized_failure_classification: str
    repair_category: str
    repair_complexity: str
    risk_level: str
    affected_areas: list[str]
    suspected_files: list[str]
    allowed_files: list[str]
    blocked_files: list[str]
    proposed_steps: list[dict[str, object]]
    validation_commands: list[str]
    required_followup_tests: list[str]
    can_attempt_autonomous_repair: bool
    repair_requires_human: bool
    repair_requires_new_phase: bool
    can_edit_code: bool
    can_mutate_git: bool
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
