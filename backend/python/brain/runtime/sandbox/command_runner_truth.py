"""Runtime Truth evidence for governed sandbox command execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

COMMAND_RUNNER_EVIDENCE_VERSION = "1.0"
COMMAND_RUNNER_EVENT_TYPE = "sandbox.command.execution"


@dataclass(frozen=True)
class SandboxCommandExecutionEvidence:
    event_type: str
    evidence_version: str
    command: str
    normalized_command: str
    category: str
    runner_mode: str
    command_mode: str
    requested_by: str
    working_directory: Optional[str]
    gate_allowed: bool
    gate_blocked: bool
    gate_reason: str
    gate_risk_level: str
    execution_attempted: bool
    command_executed: bool
    blocked: bool
    timed_out: bool
    exit_code: Optional[int]
    duration_ms: int
    stdout_truncated: bool
    stderr_truncated: bool
    network_used: bool
    provider_called: bool
    mcp_used: bool
    vault_written: bool
    git_mutated: bool
    main_modified: bool
    secrets_detected: bool
    governance_decision: str
    human_intervention_required: bool
    related_phase: Optional[str]
    related_pr: Optional[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_command_runner_evidence(
    *,
    command: str,
    normalized_command: str,
    category: str,
    runner_mode: str,
    command_mode: str,
    requested_by: str,
    working_directory: str | None,
    gate_allowed: bool,
    gate_blocked: bool,
    gate_reason: str,
    gate_risk_level: str,
    execution_attempted: bool,
    command_executed: bool,
    blocked: bool,
    dry_run: bool,
    timed_out: bool,
    exit_code: int | None,
    duration_ms: int,
    stdout_truncated: bool,
    stderr_truncated: bool,
    secrets_detected: bool,
    human_intervention_required: bool,
    related_phase: str | None,
    related_pr: str | None,
) -> SandboxCommandExecutionEvidence:
    return SandboxCommandExecutionEvidence(
        event_type=COMMAND_RUNNER_EVENT_TYPE,
        evidence_version=COMMAND_RUNNER_EVIDENCE_VERSION,
        command=command,
        normalized_command=normalized_command,
        category=category,
        runner_mode=runner_mode,
        command_mode=command_mode,
        requested_by=requested_by,
        working_directory=working_directory,
        gate_allowed=gate_allowed,
        gate_blocked=gate_blocked,
        gate_reason=gate_reason,
        gate_risk_level=gate_risk_level,
        execution_attempted=execution_attempted,
        command_executed=command_executed,
        blocked=blocked,
        timed_out=timed_out,
        exit_code=exit_code,
        duration_ms=duration_ms,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        network_used=False,
        provider_called=False,
        mcp_used=False,
        vault_written=False,
        git_mutated=False,
        main_modified=False,
        secrets_detected=secrets_detected,
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            timed_out=timed_out,
            exit_code=exit_code,
            secrets_detected=secrets_detected,
        ),
        human_intervention_required=human_intervention_required,
        related_phase=related_phase,
        related_pr=related_pr,
    )


def _governance_decision(
    *,
    blocked: bool,
    dry_run: bool,
    timed_out: bool,
    exit_code: int | None,
    secrets_detected: bool,
) -> str:
    if blocked or secrets_detected:
        return "blocked"
    if dry_run:
        return "dry_run"
    if timed_out:
        return "timed_out"
    if exit_code == 0:
        return "executed_success"
    return "executed_failed"
