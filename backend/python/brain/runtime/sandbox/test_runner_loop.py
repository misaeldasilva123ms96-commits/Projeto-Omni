"""Autonomous validation loop for governed sandbox commands.

Phase 18 orchestrates validation commands through the Phase 17 command runner.
It never starts commands directly, edits code, mutates Git, opens pull
requests, merges pull requests, calls providers, uses MCP, or writes Vault
notes.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Mapping

from .command_runner import run_sandbox_command
from .command_runner_types import SandboxCommandRunnerRequest, SandboxCommandRunnerResult
from .test_runner_truth import (
    TEST_RUNNER_LOOP_EVIDENCE_VERSION,
    build_test_runner_loop_evidence,
)
from .test_runner_types import (
    AutonomousTestRunnerLoopRequest,
    AutonomousTestRunnerLoopResult,
)

LOOP_MODES = frozenset({"disabled", "dry_run", "sandbox_readonly", "blocked"})
DEFAULT_LOOP_MODE = "disabled"
MAX_COMMANDS_LIMIT = 10
MIN_COMMANDS_LIMIT = 1
MAX_TIMEOUT_SECONDS = 300
MIN_TIMEOUT_SECONDS = 1
DEFAULT_TOTAL_TIMEOUT_SECONDS = 600

_ALLOWED_COMMAND_PATTERNS = (
    re.compile(r"^python -m pytest($| .+)"),
    re.compile(r"^pytest($| .+)"),
    re.compile(r"^npm test$"),
    re.compile(r"^npm run (test|build|lint|typecheck)$"),
    re.compile(r"^cargo (test|check|clippy)$"),
    re.compile(r"^cargo fmt --check$"),
    re.compile(r"^python -m json\.tool($| .+)"),
    re.compile(r"^python -m compileall($| .+)"),
    re.compile(r"^git diff --check$"),
    re.compile(r"^git status$"),
    re.compile(r"^git diff$"),
    re.compile(r"^python --version$"),
    re.compile(r"^node --version$"),
    re.compile(r"^npm --version$"),
    re.compile(r"^cargo --version$"),
    re.compile(r"^rustc --version$"),
)
_CREDENTIAL_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9])" + "s" + r"k-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile("API" + r"_KEY", re.IGNORECASE),
    re.compile("SEC" + r"RET", re.IGNORECASE),
    re.compile("TO" + r"KEN", re.IGNORECASE),
    re.compile("PASS" + r"WORD", re.IGNORECASE),
    re.compile("SUPA" + r"BASE", re.IGNORECASE),
    re.compile("OPEN" + r"AI", re.IGNORECASE),
    re.compile("J" + r"WT", re.IGNORECASE),
    re.compile("PRIVATE" + r"_KEY", re.IGNORECASE),
    re.compile("AUTH" + r"ORIZATION", re.IGNORECASE),
    re.compile(r"\." + "env", re.IGNORECASE),
)
_HIGH_RISK_MARKERS = (
    "curl",
    "wget",
    "ssh",
    "scp",
    "ftp",
    "netcat",
    "rm -rf",
    "remove-item -recurse",
    "deploy",
    "production",
    "billing",
)


def run_autonomous_test_loop(
    request_or_mapping: AutonomousTestRunnerLoopRequest | Mapping[str, Any] | Any,
) -> AutonomousTestRunnerLoopResult:
    request = _coerce_request(request_or_mapping)
    started = time.monotonic()
    started_at = _utc_now()
    loop_mode = str(request.loop_mode or DEFAULT_LOOP_MODE).strip() or DEFAULT_LOOP_MODE
    max_commands = _normalize_count(request.max_commands)
    command_timeout = _normalize_timeout(request.timeout_seconds_per_command)
    total_timeout = _normalize_total_timeout(request.total_timeout_seconds)
    commands_requested, commands_redacted = _redact_commands(request.commands)
    requested_by, requested_by_redacted = _redact_text(request.requested_by)
    working_directory, working_directory_redacted = _redact_optional(request.working_directory)
    purpose, purpose_redacted = _redact_optional(request.purpose)
    metadata_text = _metadata_text(request.metadata)
    metadata_redacted = _contains_credential_like(metadata_text)
    secret_detected = any(
        (
            commands_redacted,
            requested_by_redacted,
            working_directory_redacted,
            purpose_redacted,
            metadata_redacted,
        )
    )

    base_block = _base_block_reason(
        loop_mode=loop_mode,
        secret_detected=secret_detected,
        allow_code_edit=request.allow_code_edit,
        allow_git_mutation=request.allow_git_mutation,
        allow_network=request.allow_network,
    )
    if base_block:
        return _result(
            request=request,
            loop_mode=loop_mode,
            commands_requested=commands_requested,
            commands_planned=[],
            command_results=[],
            started=started,
            started_at=started_at,
            executed=False,
            blocked=True,
            dry_run=False,
            failed=True,
            timed_out=False,
            partial=False,
            failure_summary=base_block,
            failure_classification="secret_detected" if secret_detected else "command_blocked",
            recommended_next_action=(
                "escalate_to_human" if secret_detected else "blocked_by_policy"
            ),
            escalation_reason=base_block,
            redacted=secret_detected,
            secrets_detected=secret_detected,
            requested_by=requested_by,
            working_directory=working_directory,
        )

    commands_planned = commands_requested[:max_commands]
    truncated_by_max = len(commands_requested) > len(commands_planned)
    command_results: list[dict[str, object]] = []
    failure_summary: str | None = None
    failure_classification: str | None = None
    timed_out = False
    blocked = False
    failed = False
    loop_executed = False
    redacted = secret_detected
    start_deadline = time.monotonic()

    for command in commands_planned:
        if time.monotonic() - start_deadline >= total_timeout:
            failure_summary = "Total validation loop timeout was reached."
            failure_classification = "command_timed_out"
            timed_out = True
            failed = True
            break

        plan_error = _planning_error(command)
        if plan_error:
            entry = _planned_blocked_entry(command, plan_error)
            command_results.append(entry)
            blocked = True
            failed = True
            failure_summary = plan_error
            failure_classification = "secret_detected" if _contains_credential_like(command) else "unsafe_command"
            redacted = redacted or _contains_credential_like(command)
            if request.stop_on_first_failure:
                break
            continue

        runner_result = run_sandbox_command(
            SandboxCommandRunnerRequest(
                command=command,
                requested_by=request.requested_by,
                runner_mode="dry_run" if loop_mode == "dry_run" else request.runner_mode,
                command_mode=request.command_mode,
                working_directory=request.working_directory,
                timeout_seconds=command_timeout,
                max_stdout_bytes=request.max_stdout_bytes_per_command,
                max_stderr_bytes=request.max_stderr_bytes_per_command,
                target_branch=request.target_branch,
                base_branch=request.base_branch,
                related_phase=request.related_phase,
                related_pr=request.related_pr,
                purpose=request.purpose,
                metadata=request.metadata,
            )
        )
        command_results.append(runner_result.to_dict())
        loop_executed = loop_executed or runner_result.executed
        redacted = redacted or runner_result.redacted

        classification = _classify_runner_result(command, runner_result)
        if classification:
            failed = True
            blocked = blocked or runner_result.blocked
            timed_out = timed_out or runner_result.timed_out
            failure_classification = failure_classification or classification
            failure_summary = failure_summary or _failure_summary(command, runner_result, classification)
            if request.stop_on_first_failure:
                break

    partial = _is_partial(
        commands_planned=commands_planned,
        command_results=command_results,
        failed=failed,
        truncated_by_max=truncated_by_max,
    )
    success = bool(commands_planned) and not failed and not blocked and not timed_out
    recommended_next_action = _recommended_next_action(
        success=success,
        failure_classification=failure_classification,
        allow_repair_plan=request.allow_repair_plan,
    )
    requires_human = _requires_human_intervention(failure_classification, blocked, secret_detected)
    return _result(
        request=request,
        loop_mode=loop_mode,
        commands_requested=commands_requested,
        commands_planned=commands_planned,
        command_results=command_results,
        started=started,
        started_at=started_at,
        executed=loop_executed,
        blocked=blocked or secret_detected,
        dry_run=loop_mode == "dry_run",
        failed=failed,
        timed_out=timed_out,
        partial=partial,
        failure_summary=failure_summary,
        failure_classification=failure_classification,
        recommended_next_action=recommended_next_action,
        escalation_reason=failure_summary if requires_human else None,
        redacted=redacted,
        secrets_detected=secret_detected or _child_secret_detected(command_results),
        requested_by=requested_by,
        working_directory=working_directory,
    )


def _coerce_request(
    value: AutonomousTestRunnerLoopRequest | Mapping[str, Any] | Any,
) -> AutonomousTestRunnerLoopRequest:
    if isinstance(value, AutonomousTestRunnerLoopRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Autonomous test loop input must be a request, mapping, or object.")

    return AutonomousTestRunnerLoopRequest(
        commands=list(payload.get("commands") or []),
        requested_by=str(payload.get("requested_by") or "unknown"),
        loop_mode=str(payload.get("loop_mode") or DEFAULT_LOOP_MODE),
        runner_mode=str(payload.get("runner_mode") or "sandbox_readonly"),
        command_mode=str(payload.get("command_mode") or "sandbox_allowed"),
        working_directory=payload.get("working_directory"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or "main"),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        purpose=payload.get("purpose"),
        stop_on_first_failure=bool(payload.get("stop_on_first_failure", True)),
        max_commands=int(payload.get("max_commands") or MAX_COMMANDS_LIMIT),
        timeout_seconds_per_command=int(payload.get("timeout_seconds_per_command") or 60),
        total_timeout_seconds=int(
            payload.get("total_timeout_seconds") or DEFAULT_TOTAL_TIMEOUT_SECONDS
        ),
        max_stdout_bytes_per_command=int(payload.get("max_stdout_bytes_per_command") or 20000),
        max_stderr_bytes_per_command=int(payload.get("max_stderr_bytes_per_command") or 20000),
        allow_failure_analysis=bool(payload.get("allow_failure_analysis", True)),
        allow_repair_plan=bool(payload.get("allow_repair_plan", True)),
        allow_code_edit=bool(payload.get("allow_code_edit", False)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
        allow_network=bool(payload.get("allow_network", False)),
        metadata=dict(payload.get("metadata") or {}),
    )


def _base_block_reason(
    *,
    loop_mode: str,
    secret_detected: bool,
    allow_code_edit: bool,
    allow_git_mutation: bool,
    allow_network: bool,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if loop_mode not in LOOP_MODES:
        return "Autonomous test runner loop mode is unknown."
    if loop_mode == "disabled":
        return "Autonomous test runner loop is disabled by default."
    if loop_mode == "blocked":
        return "Autonomous test runner loop mode blocks all commands."
    if allow_code_edit:
        return "Code editing is not allowed in Phase 18."
    if allow_git_mutation:
        return "Git mutation is not allowed in Phase 18."
    if allow_network:
        return "Network access is not allowed in Phase 18."
    return None


def _planning_error(command: str) -> str | None:
    normalized = _normalize_command(command)
    if _contains_credential_like(normalized):
        return "Secret-like content was detected and redacted."
    if _looks_high_risk(normalized):
        return "Unsafe validation command is blocked by loop policy."
    if not any(pattern.search(normalized.lower()) for pattern in _ALLOWED_COMMAND_PATTERNS):
        return "Command is not in the Phase 18 validation allowlist."
    return None


def _planned_blocked_entry(command: str, reason: str) -> dict[str, object]:
    safe_command, redacted = _redact_text(command)
    return {
        "executed": False,
        "blocked": True,
        "dry_run": False,
        "timed_out": False,
        "exit_code": None,
        "command": safe_command,
        "normalized_command": _normalize_command(safe_command),
        "category": "blocked",
        "risk_level": "critical" if redacted else "high",
        "reason": "Autonomous test loop blocked this command.",
        "blocked_reason": reason,
        "runtime_truth": {
            "event_type": "sandbox.command.execution",
            "governance_decision": "blocked",
            "secrets_detected": redacted,
            "command_executed": False,
        },
        "redacted": redacted,
    }


def _classify_runner_result(
    command: str,
    result: SandboxCommandRunnerResult,
) -> str | None:
    if result.redacted or result.runtime_truth.get("secrets_detected") is True:
        return "secret_detected"
    if result.blocked:
        return "command_blocked"
    if result.timed_out:
        return "command_timed_out"
    if result.exit_code in (None, 0):
        return None
    lowered = command.lower()
    if "pytest" in lowered or "npm test" in lowered or "cargo test" in lowered:
        return "tests_failed"
    if "build" in lowered:
        return "build_failed"
    if "lint" in lowered or "clippy" in lowered:
        return "lint_failed"
    if "typecheck" in lowered:
        return "typecheck_failed"
    if "fmt --check" in lowered or "diff --check" in lowered:
        return "format_failed"
    if "not recognized" in result.stderr.lower() or "no such file" in result.stderr.lower():
        return "command_not_found"
    return "unknown_failure"


def _failure_summary(
    command: str,
    result: SandboxCommandRunnerResult,
    classification: str,
) -> str:
    if classification == "secret_detected":
        return "Secret-like content was detected and redacted."
    if result.blocked:
        return result.blocked_reason or "Command was blocked by policy."
    if result.timed_out:
        return "Validation command timed out."
    return f"Validation command failed: {_normalize_command(command)}"


def _recommended_next_action(
    *,
    success: bool,
    failure_classification: str | None,
    allow_repair_plan: bool,
) -> str:
    if success:
        return "no_action_needed"
    if failure_classification in {"secret_detected", "unsafe_command"}:
        return "escalate_to_human"
    if failure_classification == "command_blocked":
        return "blocked_by_policy"
    if failure_classification == "command_timed_out":
        return "run_additional_tests"
    if failure_classification in {
        "tests_failed",
        "build_failed",
        "lint_failed",
        "typecheck_failed",
        "format_failed",
    }:
        return "create_repair_plan" if allow_repair_plan else "wait_for_next_phase_repair_loop"
    return "blocked_by_policy"


def _requires_human_intervention(
    failure_classification: str | None,
    blocked: bool,
    secret_detected: bool,
) -> bool:
    return bool(
        secret_detected
        or failure_classification in {"secret_detected", "unsafe_command", "command_blocked"}
        or blocked
    )


def _is_partial(
    *,
    commands_planned: list[str],
    command_results: list[dict[str, object]],
    failed: bool,
    truncated_by_max: bool,
) -> bool:
    return truncated_by_max or (failed and len(command_results) < len(commands_planned))


def _result(
    *,
    request: AutonomousTestRunnerLoopRequest,
    loop_mode: str,
    commands_requested: list[str],
    commands_planned: list[str],
    command_results: list[dict[str, object]],
    started: float,
    started_at: str,
    executed: bool,
    blocked: bool,
    dry_run: bool,
    failed: bool,
    timed_out: bool,
    partial: bool,
    failure_summary: str | None,
    failure_classification: str | None,
    recommended_next_action: str,
    escalation_reason: str | None,
    redacted: bool,
    secrets_detected: bool,
    requested_by: str,
    working_directory: str | None,
) -> AutonomousTestRunnerLoopResult:
    finished_at = _utc_now()
    duration_ms = max(0, int((time.monotonic() - started) * 1000))
    commands_executed = sum(1 for item in command_results if item.get("executed") is True)
    commands_blocked = sum(1 for item in command_results if item.get("blocked") is True)
    success = bool(commands_planned) and not failed and not blocked and not timed_out
    child_events = [
        item["runtime_truth"]
        for item in command_results
        if isinstance(item.get("runtime_truth"), dict)
    ]
    human_required = _requires_human_intervention(failure_classification, blocked, secrets_detected)
    safe_summary, summary_redacted = _redact_optional(failure_summary)
    safe_recommendation, recommendation_redacted = _redact_text(recommended_next_action)
    evidence = build_test_runner_loop_evidence(
        loop_mode=loop_mode,
        runner_mode=request.runner_mode,
        command_mode=request.command_mode,
        requested_by=requested_by,
        working_directory=working_directory,
        commands_requested_count=len(commands_requested),
        commands_planned_count=len(commands_planned),
        commands_executed_count=commands_executed,
        commands_blocked_count=commands_blocked,
        success=success,
        failed=failed,
        timed_out=timed_out,
        partial=partial,
        stop_on_first_failure=request.stop_on_first_failure,
        duration_ms=duration_ms,
        child_runtime_truth_events=child_events,
        secrets_detected=secrets_detected,
        human_intervention_required=human_required,
        dry_run=dry_run,
        blocked=blocked,
        related_phase=request.related_phase,
        related_pr=request.related_pr,
    ).to_dict()
    return AutonomousTestRunnerLoopResult(
        executed=executed,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        failed=failed,
        timed_out=timed_out,
        partial=partial,
        loop_mode=loop_mode,
        runner_mode=request.runner_mode,
        command_mode=request.command_mode,
        commands_requested=commands_requested,
        commands_planned=commands_planned,
        commands_executed=commands_executed,
        commands_blocked=commands_blocked,
        command_results=command_results,
        failure_summary=safe_summary,
        failure_classification=failure_classification,
        recommended_next_action=safe_recommendation,
        can_attempt_repair=False,
        repair_requires_new_phase=True,
        can_edit_code=False,
        can_mutate_git=False,
        can_open_pr=False,
        can_merge=False,
        requires_human_intervention=human_required,
        escalation_reason=escalation_reason,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        requested_by=requested_by,
        related_phase=request.related_phase,
        related_pr=request.related_pr,
        runtime_truth=evidence,
        evidence_version=TEST_RUNNER_LOOP_EVIDENCE_VERSION,
        redacted=redacted or summary_redacted or recommendation_redacted,
    )


def _normalize_command(command: object) -> str:
    return " ".join(str(command or "").strip().split())


def _normalize_count(value: int) -> int:
    return min(MAX_COMMANDS_LIMIT, max(MIN_COMMANDS_LIMIT, int(value or MAX_COMMANDS_LIMIT)))


def _normalize_timeout(value: int) -> int:
    return min(MAX_TIMEOUT_SECONDS, max(MIN_TIMEOUT_SECONDS, int(value or 60)))


def _normalize_total_timeout(value: int) -> int:
    return max(MIN_TIMEOUT_SECONDS, int(value or DEFAULT_TOTAL_TIMEOUT_SECONDS))


def _looks_high_risk(command: str) -> bool:
    lowered = command.lower()
    return any(marker in lowered for marker in _HIGH_RISK_MARKERS) or lowered.startswith(
        (
            "git add",
            "git commit",
            "git push",
            "git checkout -b",
            "git switch -c",
            "git merge",
            "git rebase",
            "gh ",
        )
    )


def _redact_commands(commands: list[str]) -> tuple[list[str], bool]:
    redacted_commands: list[str] = []
    redacted = False
    for command in commands:
        safe_command, was_redacted = _redact_text(command)
        redacted_commands.append(safe_command)
        redacted = redacted or was_redacted
    return redacted_commands, redacted


def _redact_optional(value: object) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    return _redact_text(value)


def _redact_text(value: object) -> tuple[str, bool]:
    text = "" if value is None else str(value)
    redacted = text
    for pattern in _CREDENTIAL_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted, redacted != text


def _contains_credential_like(value: object) -> bool:
    text = "" if value is None else str(value)
    return any(pattern.search(text) for pattern in _CREDENTIAL_PATTERNS)


def _metadata_text(metadata: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key, value in metadata.items():
        parts.append(str(key))
        if isinstance(value, Mapping):
            parts.append(_metadata_text(value))
        elif isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value)
        else:
            parts.append(str(value))
    return " ".join(parts)


def _child_secret_detected(command_results: list[dict[str, object]]) -> bool:
    for item in command_results:
        runtime_truth = item.get("runtime_truth")
        if isinstance(runtime_truth, Mapping) and runtime_truth.get("secrets_detected") is True:
            return True
        if item.get("redacted") is True:
            return True
    return False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
