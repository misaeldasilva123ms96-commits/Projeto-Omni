"""Runtime Truth evidence for autonomous validation loops."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

TEST_RUNNER_LOOP_EVIDENCE_VERSION = "1.0"
TEST_RUNNER_LOOP_EVENT_TYPE = "sandbox.test_runner.loop"


@dataclass(frozen=True)
class AutonomousTestRunnerLoopEvidence:
    event_type: str
    evidence_version: str
    loop_mode: str
    runner_mode: str
    command_mode: str
    requested_by: str
    working_directory: Optional[str]
    commands_requested_count: int
    commands_planned_count: int
    commands_executed_count: int
    commands_blocked_count: int
    success: bool
    failed: bool
    timed_out: bool
    partial: bool
    stop_on_first_failure: bool
    duration_ms: int
    child_runtime_truth_events: list[dict[str, object]]
    network_used: bool
    provider_called: bool
    mcp_used: bool
    vault_written: bool
    git_mutated: bool
    main_modified: bool
    code_edited: bool
    pr_created: bool
    pr_merged: bool
    secrets_detected: bool
    governance_decision: str
    human_intervention_required: bool
    related_phase: Optional[str]
    related_pr: Optional[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_test_runner_loop_evidence(
    *,
    loop_mode: str,
    runner_mode: str,
    command_mode: str,
    requested_by: str,
    working_directory: str | None,
    commands_requested_count: int,
    commands_planned_count: int,
    commands_executed_count: int,
    commands_blocked_count: int,
    success: bool,
    failed: bool,
    timed_out: bool,
    partial: bool,
    stop_on_first_failure: bool,
    duration_ms: int,
    child_runtime_truth_events: list[dict[str, object]],
    secrets_detected: bool,
    human_intervention_required: bool,
    dry_run: bool,
    blocked: bool,
    related_phase: str | None,
    related_pr: str | None,
) -> AutonomousTestRunnerLoopEvidence:
    return AutonomousTestRunnerLoopEvidence(
        event_type=TEST_RUNNER_LOOP_EVENT_TYPE,
        evidence_version=TEST_RUNNER_LOOP_EVIDENCE_VERSION,
        loop_mode=loop_mode,
        runner_mode=runner_mode,
        command_mode=command_mode,
        requested_by=requested_by,
        working_directory=working_directory,
        commands_requested_count=commands_requested_count,
        commands_planned_count=commands_planned_count,
        commands_executed_count=commands_executed_count,
        commands_blocked_count=commands_blocked_count,
        success=success,
        failed=failed,
        timed_out=timed_out,
        partial=partial,
        stop_on_first_failure=stop_on_first_failure,
        duration_ms=duration_ms,
        child_runtime_truth_events=child_runtime_truth_events,
        network_used=False,
        provider_called=False,
        mcp_used=False,
        vault_written=False,
        git_mutated=False,
        main_modified=False,
        code_edited=False,
        pr_created=False,
        pr_merged=False,
        secrets_detected=secrets_detected,
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            success=success,
            failed=failed,
            timed_out=timed_out,
            partial=partial,
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
    success: bool,
    failed: bool,
    timed_out: bool,
    partial: bool,
    secrets_detected: bool,
) -> str:
    if blocked or secrets_detected:
        return "blocked"
    if dry_run:
        return "dry_run"
    if timed_out:
        return "timed_out"
    if partial and failed:
        return "partial_failed"
    if failed:
        return "validation_failed"
    if success:
        return "validation_passed"
    return "blocked"
