"""Post-patch validation orchestration for governed sandbox patches.

Phase 22 validates Phase 21 patch application evidence by delegating allowed
commands to the Phase 18 autonomous test runner loop. It does not execute
commands directly, edit files, apply patches, mutate Git, call providers, use
MCP, call agents, or write Vault notes.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .post_patch_validator_truth import (
    POST_PATCH_VALIDATION_EVIDENCE_VERSION,
    build_post_patch_validation_evidence,
)
from .post_patch_validator_types import (
    PostPatchValidationRequest,
    PostPatchValidationResult,
)
from .test_runner_loop import run_autonomous_test_loop
from .test_runner_types import AutonomousTestRunnerLoopRequest

VALIDATOR_MODES = frozenset({"disabled", "dry_run", "validate_patch", "blocked"})
DEFAULT_VALIDATOR_MODE = "disabled"
MAIN_BRANCH = "main"

_ALLOWED_COMMAND_PATTERNS = (
    re.compile(r"^python --version$"),
    re.compile(r"^node --version$"),
    re.compile(r"^npm --version$"),
    re.compile(r"^cargo --version$"),
    re.compile(r"^rustc --version$"),
    re.compile(r"^python -m pytest($| .+)"),
    re.compile(r"^pytest($| .+)"),
    re.compile(r"^npm test$"),
    re.compile(r"^npm run (test|build|lint|typecheck)$"),
    re.compile(r"^cargo (test|check|clippy)$"),
    re.compile(r"^cargo fmt --check$"),
    re.compile(r"^git diff --check$"),
    re.compile(r"^python -m json\.tool($| .+)"),
    re.compile(r"^python -m compileall($| .+)"),
)
_BLOCKED_COMMAND_MARKERS = (
    "git add",
    "git commit",
    "git push",
    "git checkout -b",
    "git switch -c",
    "git merge",
    "git rebase",
    "gh ",
    "curl",
    "wget",
    "ssh",
    "rm -rf",
    "cat .env",
    "printenv",
    " env",
)
_PROTECTED_PREFIXES = (
    "vault/08_ADR/",
    "docs/governance/",
    "docs/security/",
    ".github/workflows/",
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


def validate_post_patch(
    request_or_mapping: PostPatchValidationRequest | Mapping[str, Any] | Any,
    *,
    loop_runner: Callable[[AutonomousTestRunnerLoopRequest], Any] | None = None,
) -> PostPatchValidationResult:
    request = _coerce_request(request_or_mapping)
    loop_runner = loop_runner or run_autonomous_test_loop
    started = time.monotonic()
    started_at = _utc_now()
    validator_mode = str(request.validator_mode or DEFAULT_VALIDATOR_MODE).strip() or DEFAULT_VALIDATOR_MODE
    patch_result = _coerce_mapping(request.patch_apply_result)
    patch_truth = _coerce_mapping(patch_result.get("runtime_truth"))
    requested_by, requested_by_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, pr_redacted = _redact_optional(request.related_pr)
    workspace_root, workspace_redacted = _redact_optional(request.workspace_root or patch_result.get("workspace_root"))
    current_branch, current_redacted = _redact_optional(request.current_branch)
    target_branch, target_redacted = _redact_optional(request.target_branch)
    commands, commands_redacted = _redact_list(_validation_commands(request, patch_result))
    patch_evidence, patch_evidence_redacted = _redact_mapping(patch_truth)
    metadata_secret = _contains_credential_like(_metadata_text(request.metadata))
    loop_result: dict[str, object] | None = None
    secret_detected = any(
        (
            requested_by_redacted,
            phase_redacted,
            pr_redacted,
            workspace_redacted,
            current_redacted,
            target_redacted,
            commands_redacted,
            patch_evidence_redacted,
            metadata_secret,
        )
    )
    blocked_reason, classification = _blocked_reason(
        request=request,
        validator_mode=validator_mode,
        patch_result=patch_result,
        patch_truth=patch_truth,
        commands=commands,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        secret_detected=secret_detected,
    )
    if not blocked_reason and validator_mode == "validate_patch":
        loop_request = AutonomousTestRunnerLoopRequest(
            commands=commands[: max(1, int(request.max_commands or 10))],
            requested_by=request.requested_by,
            loop_mode=request.loop_mode,
            runner_mode=request.runner_mode,
            command_mode=request.command_mode,
            working_directory=request.workspace_root or patch_result.get("workspace_root"),
            target_branch=request.target_branch,
            base_branch=request.base_branch,
            related_phase=request.related_phase,
            related_pr=request.related_pr,
            purpose="post-patch validation",
            stop_on_first_failure=request.stop_on_first_failure,
            max_commands=request.max_commands,
            timeout_seconds_per_command=request.timeout_seconds_per_command,
            total_timeout_seconds=request.total_timeout_seconds,
            max_stdout_bytes_per_command=request.max_stdout_bytes_per_command,
            max_stderr_bytes_per_command=request.max_stderr_bytes_per_command,
            allow_failure_analysis=True,
            allow_repair_plan=True,
            allow_code_edit=False,
            allow_git_mutation=False,
            allow_network=False,
            metadata=request.metadata,
        )
        raw_loop_result = loop_runner(loop_request)
        loop_result = _coerce_result(raw_loop_result)
        loop_result, loop_redacted = _redact_mapping(loop_result)
        secret_detected = secret_detected or loop_redacted or _loop_secret_detected(loop_result)
        if secret_detected:
            blocked_reason = "Secret-like content was detected and redacted."
            classification = "secret_detected"

    finished_at = _utc_now()
    duration_ms = max(0, int((time.monotonic() - started) * 1000))
    dry_run = validator_mode == "dry_run" and not blocked_reason
    loop_success = bool(loop_result and loop_result.get("success") is True)
    loop_failed = bool(loop_result and loop_result.get("failed") is True)
    timed_out = bool(loop_result and loop_result.get("timed_out") is True)
    commands_executed = int(loop_result.get("commands_executed") or 0) if loop_result else 0
    commands_blocked = int(loop_result.get("commands_blocked") or 0) if loop_result else 0
    if loop_result and not blocked_reason:
        classification = _classification_from_loop(loop_result)
    validated = bool(loop_success and not blocked_reason)
    failed = bool(loop_failed or (classification not in {"validation_passed", "dry_run"} and not blocked_reason))
    blocked = bool(blocked_reason)
    partial = bool(loop_result and loop_result.get("partial") is True)
    success = bool(validated and not blocked)
    requires_repair = classification in {
        "tests_failed",
        "build_failed",
        "lint_failed",
        "typecheck_failed",
        "format_failed",
        "command_timed_out",
        "unknown_failure",
    }
    human_required = bool(blocked or secret_detected or classification in {
        "secret_detected",
        "protected_file_modified",
        "git_mutation_detected",
        "main_modification_detected",
        "command_blocked",
        "unsafe_command",
        "invalid_patch_apply_evidence",
    })
    ready_for_commit = bool(
        request.allow_commit_recommendation
        and validated
        and patch_result.get("applied") is True
        and patch_result.get("success") is True
        and not human_required
        and not secret_detected
    )
    next_action = _recommended_next_action(
        classification=classification,
        ready_for_commit=ready_for_commit,
        dry_run=dry_run,
        blocked=blocked,
        failed=failed,
        timed_out=timed_out,
    )
    child_events = _child_events(patch_truth, loop_result)
    runtime_truth = build_post_patch_validation_evidence(
        validator_mode=validator_mode,
        loop_mode=request.loop_mode,
        runner_mode=request.runner_mode,
        command_mode=request.command_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        patch_was_applied=bool(patch_result.get("applied") is True),
        patch_apply_event_type=patch_truth.get("event_type"),
        patch_apply_governance_decision=patch_truth.get("governance_decision"),
        patch_apply_files_applied_count=_count_from(patch_result, patch_truth, "files_applied"),
        patch_apply_hunks_applied_count=int(patch_result.get("hunks_applied") or patch_truth.get("hunks_applied_count") or 0),
        validation_commands_count=len(commands),
        commands_executed_count=commands_executed,
        commands_blocked_count=commands_blocked,
        validated=validated,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        failed=failed,
        timed_out=timed_out,
        partial=partial,
        ready_for_commit=ready_for_commit,
        ready_for_pr=False,
        requires_repair_cycle=requires_repair,
        command_executed=commands_executed > 0,
        secrets_detected=secret_detected,
        human_intervention_required=human_required,
        escalation_reason=blocked_reason or _escalation_reason(human_required, classification),
        child_runtime_truth_events=child_events,
    ).to_dict()
    return PostPatchValidationResult(
        validated=validated,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        failed=failed,
        timed_out=timed_out,
        partial=partial,
        validator_mode=validator_mode,
        loop_mode=request.loop_mode,
        runner_mode=request.runner_mode,
        command_mode=request.command_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        workspace_root=workspace_root,
        current_branch=current_branch,
        target_branch=target_branch,
        base_branch=request.base_branch,
        patch_was_applied=bool(patch_result.get("applied") is True),
        patch_apply_evidence=patch_evidence,
        validation_commands=commands,
        commands_executed=commands_executed,
        commands_blocked=commands_blocked,
        test_loop_result=loop_result,
        validation_summary=_validation_summary(classification, loop_result, blocked_reason),
        validation_classification=classification,
        recommended_next_action=next_action,
        ready_for_commit=ready_for_commit,
        ready_for_pr=False,
        requires_repair_cycle=requires_repair,
        requires_human_intervention=human_required,
        can_commit=False,
        can_push=False,
        can_open_pr=False,
        can_merge=False,
        can_edit_code=False,
        can_apply_patch=False,
        can_mutate_git=False,
        can_call_provider=False,
        can_call_agent=False,
        can_use_network=False,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        reason=_reason(validated=validated, dry_run=dry_run, blocked_reason=blocked_reason),
        blocked_reason=blocked_reason,
        escalation_reason=blocked_reason or _escalation_reason(human_required, classification),
        runtime_truth=runtime_truth,
        evidence_version=POST_PATCH_VALIDATION_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _coerce_request(value: PostPatchValidationRequest | Mapping[str, Any] | Any) -> PostPatchValidationRequest:
    if isinstance(value, PostPatchValidationRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Post-patch validation input must be a request, mapping, or object.")
    return PostPatchValidationRequest(
        patch_apply_result=_coerce_mapping(payload.get("patch_apply_result")),
        validation_commands=list(payload.get("validation_commands") or []),
        required_followup_tests=list(payload.get("required_followup_tests") or []),
        requested_by=str(payload.get("requested_by") or "unknown"),
        validator_mode=str(payload.get("validator_mode") or DEFAULT_VALIDATOR_MODE),
        loop_mode=str(payload.get("loop_mode") or "sandbox_readonly"),
        runner_mode=str(payload.get("runner_mode") or "sandbox_readonly"),
        command_mode=str(payload.get("command_mode") or "sandbox_allowed"),
        workspace_root=payload.get("workspace_root"),
        current_branch=payload.get("current_branch"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        stop_on_first_failure=bool(payload.get("stop_on_first_failure", True)),
        max_commands=int(payload.get("max_commands") or 10),
        timeout_seconds_per_command=int(payload.get("timeout_seconds_per_command") or 60),
        total_timeout_seconds=int(payload.get("total_timeout_seconds") or 600),
        max_stdout_bytes_per_command=int(payload.get("max_stdout_bytes_per_command") or 20000),
        max_stderr_bytes_per_command=int(payload.get("max_stderr_bytes_per_command") or 20000),
        require_patch_applied=bool(payload.get("require_patch_applied", True)),
        require_non_main_branch=bool(payload.get("require_non_main_branch", True)),
        require_runtime_truth=bool(payload.get("require_runtime_truth", True)),
        allow_commit_recommendation=bool(payload.get("allow_commit_recommendation", True)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
        allow_code_edit=bool(payload.get("allow_code_edit", False)),
        allow_patch_apply=bool(payload.get("allow_patch_apply", False)),
        allow_network=bool(payload.get("allow_network", False)),
        allow_provider_call=bool(payload.get("allow_provider_call", False)),
        allow_agent_call=bool(payload.get("allow_agent_call", False)),
        metadata=dict(payload.get("metadata") or {}),
    )


def _coerce_mapping(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    if hasattr(value, "__dataclass_fields__"):
        return dict(asdict(value))
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _coerce_result(value: object) -> dict[str, object]:
    return _coerce_mapping(value)


def _validation_commands(
    request: PostPatchValidationRequest,
    patch_result: Mapping[str, Any],
) -> list[str]:
    candidates = list(
        request.validation_commands
        or request.required_followup_tests
        or patch_result.get("validation_commands")
        or patch_result.get("required_followup_tests")
        or []
    )
    commands = []
    for item in candidates[: max(1, int(request.max_commands or 10))]:
        normalized = _normalize_command(item)
        if normalized:
            commands.append(normalized)
    return commands


def _blocked_reason(
    *,
    request: PostPatchValidationRequest,
    validator_mode: str,
    patch_result: Mapping[str, Any],
    patch_truth: Mapping[str, Any],
    commands: list[str],
    workspace_root: str | None,
    current_branch: str | None,
    target_branch: str | None,
    secret_detected: bool,
) -> tuple[str | None, str]:
    if secret_detected or patch_truth.get("secrets_detected") is True:
        return "Secret-like content was detected and redacted.", "secret_detected"
    if validator_mode not in VALIDATOR_MODES:
        return "Post-patch validator mode is unknown.", "unknown_failure"
    if validator_mode == "disabled":
        return "Post-patch validator is disabled by default.", "command_blocked"
    if validator_mode == "blocked":
        return "Post-patch validator mode blocks all validation.", "command_blocked"
    if any((request.allow_git_mutation, request.allow_code_edit, request.allow_patch_apply, request.allow_network, request.allow_provider_call, request.allow_agent_call)):
        return "Phase 22 cannot enable Git, code edit, patch apply, network, provider, or agent capabilities.", "command_blocked"
    if request.require_runtime_truth and not patch_truth:
        return "Patch apply Runtime Truth evidence is required.", "invalid_patch_apply_evidence"
    if patch_result.get("blocked") is True:
        return "Patch application result is blocked.", "invalid_patch_apply_evidence"
    if request.require_patch_applied and patch_result.get("applied") is not True:
        return "Patch application evidence does not show an applied patch.", "invalid_patch_apply_evidence"
    if patch_truth.get("command_executed") is True:
        return "Patch application evidence unexpectedly reports command execution.", "invalid_patch_apply_evidence"
    if patch_truth.get("git_mutated") is True:
        return "Patch application evidence reports Git mutation.", "git_mutation_detected"
    if patch_truth.get("main_modified") is True:
        return "Patch application evidence reports main branch modification.", "main_modification_detected"
    protected_file = _protected_file(patch_result.get("files_applied") or [])
    if protected_file:
        return "Patch application evidence includes a protected file.", "protected_file_modified"
    branch_block = _branch_block_reason(request, current_branch, target_branch)
    if branch_block:
        return branch_block, "main_modification_detected"
    workspace_block = _workspace_block_reason(workspace_root)
    if workspace_block:
        return workspace_block, "command_blocked"
    command_block = _command_block_reason(commands)
    if command_block:
        return command_block, "secret_detected" if _contains_credential_like(" ".join(commands)) else "command_blocked"
    if not commands and validator_mode != "dry_run":
        return "At least one safe validation command is required.", "command_blocked"
    if request.metadata.get("direct_main_edit") is True:
        return "direct main edit metadata is blocked.", "main_modification_detected"
    return None, "dry_run" if validator_mode == "dry_run" else "validation_passed"


def _branch_block_reason(
    request: PostPatchValidationRequest,
    current_branch: str | None,
    target_branch: str | None,
) -> str | None:
    if not request.require_non_main_branch:
        return None
    current = str(current_branch or "").strip().lower()
    target = str(target_branch or "").strip().lower()
    base = str(request.base_branch or "").strip().lower()
    if not current:
        return "current_branch metadata is required."
    if current == MAIN_BRANCH:
        return "current_branch must not be main."
    if current == base:
        return "current_branch must not equal base_branch."
    if target == MAIN_BRANCH:
        return "target_branch must not be main."
    if base != MAIN_BRANCH:
        return "base_branch must be main."
    return None


def _workspace_block_reason(workspace_root: str | None) -> str | None:
    if not workspace_root:
        return "workspace_root is required for post-patch validation."
    text = str(workspace_root).strip()
    if ".." in text.replace("\\", "/").split("/"):
        return "workspace_root must not contain path traversal."
    path = Path(text).expanduser()
    if path == Path(path.anchor):
        return "workspace_root must not be a filesystem root."
    return None


def _command_block_reason(commands: list[str]) -> str | None:
    for command in commands:
        lowered = command.lower()
        if _contains_credential_like(command):
            return "Secret-like content was detected and redacted."
        if any(marker in f" {lowered}" for marker in _BLOCKED_COMMAND_MARKERS):
            return "Validation command is blocked by post-patch policy."
        if not any(pattern.search(lowered) for pattern in _ALLOWED_COMMAND_PATTERNS):
            return "Validation command is outside the post-patch allowlist."
    return None


def _protected_file(paths: list[object]) -> str | None:
    for raw in paths:
        path = str(raw or "").replace("\\", "/")
        lowered = path.lower()
        if _contains_credential_like(path) or lowered.startswith(".git/"):
            return path
        if any(lowered.startswith(prefix.lower()) for prefix in _PROTECTED_PREFIXES):
            return path
        if any(marker in lowered for marker in ("production", "deploy", "billing", "secret", "credential", "private")):
            return path
    return None


def _classification_from_loop(loop_result: Mapping[str, object]) -> str:
    if loop_result.get("success") is True:
        return "validation_passed"
    if loop_result.get("timed_out") is True:
        return "command_timed_out"
    raw = str(loop_result.get("failure_classification") or "unknown_failure")
    if raw == "unsafe_command":
        return "unsafe_command"
    if raw == "command_blocked":
        return "command_blocked"
    if raw in {"tests_failed", "build_failed", "lint_failed", "typecheck_failed", "format_failed", "secret_detected"}:
        return raw
    return "unknown_failure"


def _recommended_next_action(
    *,
    classification: str,
    ready_for_commit: bool,
    dry_run: bool,
    blocked: bool,
    failed: bool,
    timed_out: bool,
) -> str:
    if dry_run:
        return "wait_for_manual_review"
    if ready_for_commit:
        return "ready_for_commit_phase"
    if classification in {"secret_detected", "protected_file_modified", "git_mutation_detected", "main_modification_detected", "unsafe_command"}:
        return "escalate_to_human"
    if blocked or classification in {"command_blocked", "invalid_patch_apply_evidence"}:
        return "blocked_by_policy"
    if timed_out:
        return "run_additional_validations"
    if failed:
        return "start_repair_cycle"
    return "no_action_needed"


def _child_events(
    patch_truth: Mapping[str, Any],
    loop_result: Mapping[str, object] | None,
) -> list[dict[str, object]]:
    events = []
    if patch_truth:
        events.append(dict(patch_truth))
    if loop_result and isinstance(loop_result.get("runtime_truth"), Mapping):
        events.append(dict(loop_result["runtime_truth"]))
    return events


def _count_from(
    patch_result: Mapping[str, Any],
    patch_truth: Mapping[str, Any],
    field: str,
) -> int:
    value = patch_result.get(field)
    if isinstance(value, list):
        return len(value)
    return int(patch_truth.get(f"{field}_count") or 0)


def _loop_secret_detected(loop_result: Mapping[str, object]) -> bool:
    if loop_result.get("redacted") is True:
        return True
    runtime_truth = loop_result.get("runtime_truth")
    return isinstance(runtime_truth, Mapping) and runtime_truth.get("secrets_detected") is True


def _validation_summary(
    classification: str,
    loop_result: Mapping[str, object] | None,
    blocked_reason: str | None,
) -> str | None:
    if blocked_reason:
        return blocked_reason
    if loop_result and loop_result.get("failure_summary"):
        return str(loop_result.get("failure_summary"))
    if classification == "validation_passed":
        return "Post-patch validation passed."
    if classification == "dry_run":
        return "Post-patch validation dry-run completed."
    return "Post-patch validation did not complete successfully."


def _escalation_reason(human_required: bool, classification: str) -> str | None:
    if not human_required:
        return None
    return f"Post-patch validation requires human intervention: {classification}."


def _reason(*, validated: bool, dry_run: bool, blocked_reason: str | None) -> str:
    if blocked_reason:
        return "Post-patch validator blocked this request."
    if dry_run:
        return "Post-patch validator verified evidence and commands without executing validations."
    if validated:
        return "Post-patch validator completed validations through the Phase 18 loop."
    return "Post-patch validator did not validate the patch."


def _normalize_command(command: object) -> str:
    return " ".join(str(command or "").strip().split())


def _redact_optional(value: object) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    return _redact_text(value)


def _redact_list(values: list[object]) -> tuple[list[str], bool]:
    redacted_values = []
    redacted = False
    for value in values:
        text, was_redacted = _redact_text(value)
        redacted_values.append(text)
        redacted = redacted or was_redacted
    return redacted_values, redacted


def _redact_mapping(value: Mapping[str, Any]) -> tuple[dict[str, object], bool]:
    redacted = False

    def redact_item(item: Any) -> Any:
        nonlocal redacted
        if isinstance(item, Mapping):
            return {str(key): redact_item(child) for key, child in item.items()}
        if isinstance(item, list):
            return [redact_item(child) for child in item]
        if isinstance(item, str):
            safe, was_redacted = _redact_text(item)
            redacted = redacted or was_redacted
            return safe
        return item

    return dict(redact_item(dict(value))), redacted


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
