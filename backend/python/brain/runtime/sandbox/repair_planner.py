"""Autonomous repair planning for governed sandbox validation failures.

Phase 19 transforms validation failures into structured repair metadata only.
It does not execute commands, edit files, apply patches, mutate Git, call
providers, call agents, use MCP, create pull requests, or write Vault notes.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping

from .repair_planner_truth import (
    REPAIR_PLANNER_EVIDENCE_VERSION,
    build_repair_planner_evidence,
)
from .repair_planner_types import (
    AutonomousRepairPlannerRequest,
    AutonomousRepairPlannerResult,
)

PLANNER_MODES = frozenset({"disabled", "dry_run", "plan_only", "blocked"})
DEFAULT_PLANNER_MODE = "disabled"
MAIN_BRANCH = "main"

_ALIASES = {
    "test_failed": "tests_failed",
    "pytest_failed": "tests_failed",
    "npm_build_failed": "build_failed",
    "eslint_failed": "lint_failed",
    "tsc_failed": "typecheck_failed",
    "cargo_fmt_failed": "format_failed",
    "timeout": "command_timed_out",
    "blocked": "command_blocked",
}
_CATEGORY = {
    "tests_failed": "test_repair",
    "build_failed": "build_repair",
    "lint_failed": "lint_repair",
    "typecheck_failed": "type_repair",
    "format_failed": "formatting_repair",
    "command_not_found": "environment_or_tooling",
    "command_timed_out": "timeout_or_performance",
    "invalid_command": "command_plan_issue",
    "command_blocked": "policy_blocked",
    "unsafe_command": "policy_blocked",
    "secret_detected": "security_escalation",
    "unknown_failure": "investigation_required",
}
_COMPLEXITY = {
    "format_failed": "low",
    "lint_failed": "medium",
    "typecheck_failed": "medium",
    "tests_failed": "medium",
    "build_failed": "high",
    "command_not_found": "medium",
    "command_timed_out": "high",
    "invalid_command": "medium",
    "unknown_failure": "high",
    "command_blocked": "critical",
    "unsafe_command": "critical",
    "secret_detected": "critical",
}
_VALIDATION_COMMANDS = {
    "tests_failed": ["python -m pytest tests"],
    "build_failed": ["npm run build"],
    "lint_failed": ["npm run lint"],
    "typecheck_failed": ["npm run typecheck"],
    "format_failed": ["cargo fmt --check", "git diff --check"],
    "command_not_found": ["python --version"],
    "command_timed_out": ["python -m pytest tests"],
    "invalid_command": ["git diff --check"],
    "unknown_failure": ["git diff --check"],
}
_ALLOWED_PREFIXES = (
    "backend/python/",
    "backend/rust/",
    "frontend/",
    "tests/",
    "docs/",
    "sandbox/local/",
    "vault/templates/",
)
_HIGH_RISK_PREFIXES = (
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


def plan_autonomous_repair(
    request_or_mapping: AutonomousRepairPlannerRequest | Mapping[str, Any] | Any,
) -> AutonomousRepairPlannerResult:
    request = _coerce_request(request_or_mapping)
    loop = _coerce_mapping(request.test_loop_result)
    planner_mode = str(request.planner_mode or DEFAULT_PLANNER_MODE).strip() or DEFAULT_PLANNER_MODE
    requested_by, requested_by_redacted = _redact_text(request.requested_by)
    related_phase, phase_redacted = _redact_optional(request.related_phase)
    related_pr, pr_redacted = _redact_optional(request.related_pr)
    target_branch, branch_redacted = _redact_optional(request.target_branch)
    summary_source = request.failure_summary or loop.get("failure_summary")
    failure_summary, summary_redacted = _redact_optional(summary_source)
    command_results = list(request.command_results or loop.get("command_results") or [])
    raw_classification = (
        request.failure_classification
        or loop.get("failure_classification")
        or ("command_timed_out" if loop.get("timed_out") else None)
        or ("unknown_failure" if loop.get("failed") else None)
    )
    normalized = _normalize_failure(raw_classification, bool(loop.get("success")))
    metadata_text = _metadata_text(request.metadata)
    file_scope = _file_scope(request, command_results)
    files_changed, files_changed_redacted = _redact_list(request.files_changed)
    allowed_files, allowed_redacted = _redact_list(request.allowed_files)
    blocked_files, blocked_redacted = _redact_list(request.blocked_files)
    suspected_files, suspected_redacted = _redact_list(
        _suspected_files(file_scope, files_changed, request.max_files_to_touch)
    )
    secret_detected = any(
        (
            requested_by_redacted,
            phase_redacted,
            pr_redacted,
            branch_redacted,
            summary_redacted,
            files_changed_redacted,
            allowed_redacted,
            blocked_redacted,
            suspected_redacted,
            _contains_credential_like(metadata_text),
            _command_results_secret(command_results),
        )
    )
    if secret_detected:
        normalized = "secret_detected"

    repair_category = _CATEGORY.get(normalized, "investigation_required")
    complexity = _COMPLEXITY.get(normalized, "high")
    risk_level = _risk_level(normalized, complexity)
    affected_areas = _affected_areas(suspected_files, command_results)
    proposed_steps = _proposed_steps(normalized, repair_category, risk_level, request.max_repair_steps)
    validation_commands = _validation_commands(normalized)
    followup_tests = list(validation_commands)
    human_required, escalation_reason = _human_escalation(
        request=request,
        normalized=normalized,
        suspected_files=suspected_files,
        allowed_files=allowed_files,
        metadata_text=metadata_text,
        target_branch=target_branch,
    )
    blocked_reason = _blocked_reason(
        planner_mode=planner_mode,
        secret_detected=secret_detected,
        human_required=human_required,
        request=request,
    )
    no_repair_needed = bool(loop.get("success")) and normalized == "no_failure"
    planned = planner_mode in {"dry_run", "plan_only"} and not blocked_reason and not no_repair_needed
    dry_run = planner_mode == "dry_run" and not blocked_reason
    blocked = bool(blocked_reason)
    success = bool((planned or no_repair_needed) and not blocked)
    reason = _reason(
        planned=planned,
        no_repair_needed=no_repair_needed,
        blocked_reason=blocked_reason,
        dry_run=dry_run,
    )
    if no_repair_needed:
        proposed_steps = []
        validation_commands = []
        followup_tests = []
        repair_category = "no_repair_needed"
        complexity = "low"
        risk_level = "low"

    runtime_truth = build_repair_planner_evidence(
        planner_mode=planner_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        target_branch=target_branch,
        base_branch=request.base_branch,
        failure_classification=raw_classification,
        normalized_failure_classification=normalized,
        repair_category=repair_category,
        repair_complexity=complexity,
        risk_level=risk_level,
        planned=planned,
        blocked=blocked,
        dry_run=dry_run,
        proposed_steps_count=len(proposed_steps),
        suspected_files_count=len(suspected_files),
        validation_commands_count=len(validation_commands),
        secrets_detected=secret_detected,
        human_intervention_required=human_required or blocked,
        escalation_reason=escalation_reason or blocked_reason,
    ).to_dict()
    return AutonomousRepairPlannerResult(
        planned=planned,
        blocked=blocked,
        dry_run=dry_run,
        success=success,
        planner_mode=planner_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        target_branch=target_branch,
        base_branch=request.base_branch,
        failure_summary=failure_summary,
        failure_classification=raw_classification,
        normalized_failure_classification=normalized,
        repair_category=repair_category,
        repair_complexity=complexity,
        risk_level=risk_level,
        affected_areas=affected_areas,
        suspected_files=suspected_files,
        allowed_files=allowed_files,
        blocked_files=blocked_files,
        proposed_steps=proposed_steps,
        validation_commands=validation_commands,
        required_followup_tests=followup_tests,
        can_attempt_autonomous_repair=False,
        repair_requires_human=human_required or blocked,
        repair_requires_new_phase=True,
        can_edit_code=False,
        can_mutate_git=False,
        can_call_provider=False,
        can_call_agent=False,
        can_use_network=False,
        can_open_pr=False,
        can_merge=False,
        reason=reason,
        blocked_reason=blocked_reason,
        escalation_reason=escalation_reason or blocked_reason,
        runtime_truth=runtime_truth,
        evidence_version=REPAIR_PLANNER_EVIDENCE_VERSION,
        redacted=secret_detected,
    )


def _coerce_request(value: AutonomousRepairPlannerRequest | Mapping[str, Any] | Any) -> AutonomousRepairPlannerRequest:
    if isinstance(value, AutonomousRepairPlannerRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Repair planner input must be a request, mapping, or object.")
    return AutonomousRepairPlannerRequest(
        test_loop_result=_coerce_mapping(payload.get("test_loop_result")),
        failure_summary=payload.get("failure_summary"),
        failure_classification=payload.get("failure_classification"),
        command_results=list(payload.get("command_results") or []),
        requested_by=str(payload.get("requested_by") or "unknown"),
        planner_mode=str(payload.get("planner_mode") or DEFAULT_PLANNER_MODE),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        task_type=payload.get("task_type"),
        files_changed=list(payload.get("files_changed") or []),
        allowed_files=list(payload.get("allowed_files") or []),
        blocked_files=list(payload.get("blocked_files") or []),
        max_files_to_touch=int(payload.get("max_files_to_touch") or 5),
        max_repair_steps=int(payload.get("max_repair_steps") or 10),
        allow_code_edit=bool(payload.get("allow_code_edit", False)),
        allow_git_mutation=bool(payload.get("allow_git_mutation", False)),
        allow_test_execution=bool(payload.get("allow_test_execution", False)),
        allow_provider_call=bool(payload.get("allow_provider_call", False)),
        allow_agent_call=bool(payload.get("allow_agent_call", False)),
        allow_network=bool(payload.get("allow_network", False)),
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


def _normalize_failure(value: object, success: bool) -> str:
    if success:
        return "no_failure"
    text = str(value or "unknown_failure").strip() or "unknown_failure"
    text = _ALIASES.get(text, text)
    return text if text in _CATEGORY else "unknown_failure"


def _file_scope(
    request: AutonomousRepairPlannerRequest,
    command_results: list[dict[str, Any]],
) -> list[str]:
    files = list(request.files_changed or request.allowed_files)
    for result in command_results:
        command = str(result.get("command") or "")
        files.extend(_paths_from_command(command))
    return files


def _paths_from_command(command: str) -> list[str]:
    parts = command.replace('"', " ").replace("'", " ").split()
    return [part for part in parts if "/" in part and not part.startswith("-")]


def _suspected_files(files: list[str], fallback: list[str], limit: int) -> list[str]:
    candidates = files or fallback
    safe: list[str] = []
    for path in candidates:
        normalized = _normalize_path(path)
        if not normalized or normalized in safe:
            continue
        safe.append(normalized)
        if len(safe) >= max(1, int(limit or 5)):
            break
    return safe


def _normalize_path(path: object) -> str | None:
    text = str(path or "").replace("\\", "/").strip()
    if not text or ".." in text.split("/") or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return None
    safe_text, _ = _redact_text(text)
    return safe_text


def _affected_areas(files: list[str], command_results: list[dict[str, Any]]) -> list[str]:
    areas = set()
    for path in files:
        if path.startswith("backend/"):
            areas.add("backend")
        elif path.startswith("frontend/"):
            areas.add("frontend")
        elif path.startswith("tests/"):
            areas.add("tests")
        elif path.startswith("docs/"):
            areas.add("docs")
        elif path.startswith("sandbox/"):
            areas.add("sandbox")
        elif path.startswith("vault/"):
            areas.add("vault")
    for result in command_results:
        command = str(result.get("command") or "")
        if "npm" in command:
            areas.add("frontend")
        if "pytest" in command or "python" in command:
            areas.add("backend")
        if "cargo" in command:
            areas.add("rust")
    return sorted(areas or {"unknown"})


def _proposed_steps(normalized: str, category: str, risk_level: str, limit: int) -> list[dict[str, object]]:
    if normalized == "no_failure":
        return []
    if normalized in {"secret_detected", "unsafe_command", "command_blocked"}:
        base = [
            ("Escalate blocked repair", "Escalate the policy or security failure for human review."),
            ("Preserve evidence", "Use the Runtime Truth evidence as the source for the review."),
        ]
    else:
        base = [
            ("Review failure evidence", "Inspect the validation summary and failed command metadata."),
            ("Identify minimal repair scope", "Select the smallest safe file scope for a future repair phase."),
            ("Prepare future repair change", "Draft a later governed repair step without editing files now."),
            ("Run validation after repair", "Use safe validation commands after a future repair phase."),
        ]
    steps = []
    for index, (title, description) in enumerate(base[: max(1, int(limit or 10))], start=1):
        steps.append(
            {
                "step_id": f"repair-step-{index}",
                "title": title,
                "description": description,
                "target_area": category,
                "expected_effect": "repair planning metadata only",
                "risk_level": risk_level,
                "requires_human": normalized in {"secret_detected", "unsafe_command", "command_blocked"},
                "allowed_in_future_autonomous_repair": normalized not in {"secret_detected", "unsafe_command", "command_blocked"},
            }
        )
    return steps


def _validation_commands(normalized: str) -> list[str]:
    return list(_VALIDATION_COMMANDS.get(normalized, ["git diff --check"]))


def _human_escalation(
    *,
    request: AutonomousRepairPlannerRequest,
    normalized: str,
    suspected_files: list[str],
    allowed_files: list[str],
    metadata_text: str,
    target_branch: str | None,
) -> tuple[bool, str | None]:
    reasons: list[str] = []
    if normalized in {"secret_detected", "unsafe_command", "command_blocked"}:
        reasons.append("Policy, unsafe command, or secret failure requires human intervention.")
    if _is_main(target_branch):
        reasons.append("Future edits targeting main require human intervention.")
    if normalized not in {"no_failure", "command_blocked", "unsafe_command", "secret_detected"} and not allowed_files:
        reasons.append("Repair planning needs an explicit allowed file scope before future edits.")
    for path in suspected_files + list(request.files_changed) + allowed_files + list(request.blocked_files):
        if _path_requires_human(path):
            reasons.append("Governance, security, CI, secret, production, or billing file scope requires human intervention.")
            break
    lowered_metadata = metadata_text.lower()
    for marker in ("ci_threshold", "skip tests", "skip_tests", "disable_security", "production", "deploy", "billing", "destructive"):
        if marker in lowered_metadata:
            reasons.append("Metadata indicates a governed exception trigger.")
            break
    return bool(reasons), "; ".join(reasons) if reasons else None


def _blocked_reason(
    *,
    planner_mode: str,
    secret_detected: bool,
    human_required: bool,
    request: AutonomousRepairPlannerRequest,
) -> str | None:
    if secret_detected:
        return "Secret-like content was detected and redacted."
    if planner_mode not in PLANNER_MODES:
        return "Repair planner mode is unknown."
    if planner_mode == "disabled":
        return "Repair planner is disabled by default."
    if planner_mode == "blocked":
        return "Repair planner mode blocks all planning."
    if any((request.allow_code_edit, request.allow_git_mutation, request.allow_provider_call, request.allow_agent_call, request.allow_network)):
        return "Phase 19 cannot enable edit, Git, provider, agent, or network capabilities."
    return None


def _reason(*, planned: bool, no_repair_needed: bool, blocked_reason: str | None, dry_run: bool) -> str:
    if blocked_reason:
        return "Repair planner blocked this request."
    if no_repair_needed:
        return "Validation passed; no repair plan is needed."
    if dry_run:
        return "Repair planner classified the failure in dry-run mode."
    if planned:
        return "Repair planner generated structured repair metadata only."
    return "Repair planner did not create a plan."


def _risk_level(normalized: str, complexity: str) -> str:
    if normalized in {"secret_detected", "unsafe_command", "command_blocked"}:
        return "critical"
    if complexity == "high":
        return "high"
    if complexity == "medium":
        return "medium"
    return "low"


def _is_main(branch: str | None) -> bool:
    return str(branch or "").strip().lower() == MAIN_BRANCH


def _path_requires_human(path: str) -> bool:
    lowered = str(path or "").replace("\\", "/").lower()
    if _contains_credential_like(lowered):
        return True
    if any(lowered.startswith(prefix.lower()) for prefix in _HIGH_RISK_PREFIXES):
        return True
    if any(marker in lowered for marker in ("production", "deploy", "billing", "secret", "credential", "private")):
        return True
    return not any(lowered.startswith(prefix.lower()) for prefix in _ALLOWED_PREFIXES)


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


def _command_results_secret(command_results: list[dict[str, Any]]) -> bool:
    for result in command_results:
        runtime_truth = result.get("runtime_truth")
        if isinstance(runtime_truth, Mapping) and runtime_truth.get("secrets_detected") is True:
            return True
        for field in ("command", "stdout", "stderr", "failure_summary", "blocked_reason"):
            if _contains_credential_like(result.get(field)):
                return True
    return False
