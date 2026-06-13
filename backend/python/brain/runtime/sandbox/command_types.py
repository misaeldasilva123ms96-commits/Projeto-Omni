"""Types for the Safe Command Execution Gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class CommandGateRequest:
    command: str
    requested_by: str = "unknown"
    command_mode: str = "disabled"
    autonomy_level: Optional[str] = None
    target_branch: Optional[str] = None
    base_branch: str = "main"
    working_directory: Optional[str] = None
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    purpose: Optional[str] = None
    timeout_seconds: int = 60
    requires_network: bool = False
    writes_files: bool = False
    mutates_git: bool = False
    reads_secrets: bool = False
    production_targeted: bool = False
    destructive_intent: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CommandGateDecision:
    allowed: bool
    blocked: bool
    requires_human_intervention: bool
    requires_runtime_truth: bool
    requires_sandbox: bool
    command: str
    normalized_command: str
    command_mode: str
    category: str
    risk_level: str
    reason: str
    escalation_reason: Optional[str]
    requested_by: str
    target_branch: Optional[str]
    base_branch: str
    working_directory: Optional[str]
    timeout_seconds: int
    command_execution_allowed: bool
    network_allowed: bool
    file_write_allowed: bool
    git_mutation_allowed: bool
    git_push_allowed: bool
    git_merge_allowed: bool
    main_branch_protected: bool
    secrets_access_allowed: bool
    production_allowed: bool
    destructive_allowed: bool
    safe_for_future_execution: bool
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
