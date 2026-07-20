"""Types for the governed sandbox command runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class SandboxCommandRunnerRequest:
    command: str
    requested_by: str = "unknown"
    runner_mode: str = "disabled"
    command_mode: str = "sandbox_allowed"
    workspace_root: Optional[str] = None
    working_directory: Optional[str] = None
    timeout_seconds: int = 60
    max_stdout_bytes: int = 20000
    max_stderr_bytes: int = 20000
    target_branch: Optional[str] = None
    base_branch: str = "main"
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    purpose: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxCommandRunnerResult:
    executed: bool
    blocked: bool
    dry_run: bool
    timed_out: bool
    exit_code: Optional[int]
    command: str
    normalized_command: str
    argv: list[str]
    runner_mode: str
    command_mode: str
    category: str
    risk_level: str
    reason: str
    blocked_reason: Optional[str]
    escalation_reason: Optional[str]
    working_directory: Optional[str]
    timeout_seconds: int
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    stdout_bytes: int
    stderr_bytes: int
    started_at: str
    finished_at: str
    duration_ms: int
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    gate_allowed: bool
    gate_blocked: bool
    gate_requires_runtime_truth: bool
    gate_requires_sandbox: bool
    runtime_truth: dict[str, object]
    evidence_version: str
    redacted: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
