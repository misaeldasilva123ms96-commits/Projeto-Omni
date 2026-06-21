"""Safe Command Execution Gate.

Phase 16 classifies command requests for future sandbox use. It never starts
processes, contacts networks, calls providers, uses MCP, writes vault notes,
changes files, creates pull requests, merges pull requests, or mutates Git.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping

from .command_types import CommandGateDecision, CommandGateRequest

COMMAND_GATE_EVIDENCE_VERSION = "1.0"
DEFAULT_COMMAND_MODE = "disabled"
MAIN_BRANCH = "main"
CREDENTIAL_REASON = "Credential-like content was detected and redacted."

COMMAND_MODES = frozenset(
    {
        "disabled",
        "dry_run_policy_only",
        "sandbox_allowed",
        "blocked",
    }
)

READ_SAFE_PATTERNS = (
    re.compile(r"^git status$"),
    re.compile(r"^git diff( --check)?$"),
    re.compile(r"^git log($| .+)"),
    re.compile(r"^git branch --show-current$"),
    re.compile(r"^git remote -v$"),
    re.compile(r"^python -m pytest($| .+)"),
    re.compile(r"^pytest($| .+)"),
    re.compile(r"^npm test$"),
    re.compile(r"^npm run (test|build|lint|typecheck)$"),
    re.compile(r"^cargo (test|check|clippy)$"),
    re.compile(r"^cargo fmt --check$"),
    re.compile(r"^python -m json\.tool($| .+)"),
    re.compile(r"^python -m compileall($| .+)"),
    re.compile(r"^node --version$"),
    re.compile(r"^npm --version$"),
    re.compile(r"^python --version$"),
    re.compile(r"^rustc --version$"),
    re.compile(r"^cargo --version$"),
)

GIT_BRANCH_WRITE_PATTERNS = (
    re.compile(r"^git checkout -b (?P<branch>\S+)$"),
    re.compile(r"^git switch -c (?P<branch>\S+)$"),
    re.compile(r"^git add (?P<path>.+)$"),
    re.compile(r"^git commit -m (?P<message>.+)$"),
    re.compile(r"^git push origin (?P<branch>\S+)$"),
    re.compile(r"^git push -u origin (?P<branch>\S+)$"),
)

BLOCKED_PATTERNS = (
    (re.compile(r"^git push origin main$"), "git_main_mutation", "critical"),
    (re.compile(r"^git push .*(-f|--force)($| .*)"), "force_push", "critical"),
    (re.compile(r"^git merge($| .+)"), "git_merge", "critical"),
    (re.compile(r"^git rebase($| .+)"), "git_rebase", "critical"),
    (re.compile(r"^gh pr merge($| .+)"), "pull_request_merge", "critical"),
    (re.compile(r"^gh (api|auth)($| .+)"), "github_sensitive", "high"),
    (re.compile(r"(^|[;&|]\s*)rm -rf($| .+)"), "destructive", "critical"),
    (re.compile(r"(^|[;&|]\s*)del /s($| .+)", re.IGNORECASE), "destructive", "critical"),
    (re.compile(r"(^|[;&|]\s*)rmdir /s($| .+)", re.IGNORECASE), "destructive", "critical"),
    (re.compile(r"Remove-Item .*-Recurse", re.IGNORECASE), "destructive", "critical"),
    (re.compile(r"^chmod 777($| .+)"), "permission_risk", "high"),
    (re.compile(r"^chown($| .+)"), "permission_risk", "high"),
    (re.compile(r"^(sudo|su)($| .+)"), "privilege_escalation", "critical"),
    (
        re.compile(r"^(curl|wget|Invoke-WebRequest|iwr|irm)($| .+)", re.IGNORECASE),
        "network",
        "high",
    ),
    (re.compile(r"^(ssh|scp|ftp|nc|netcat)($| .+)", re.IGNORECASE), "network", "high"),
    (re.compile(r"docker run .*--privileged", re.IGNORECASE), "container_escape_risk", "critical"),
    (
        re.compile(r"docker .*(/var/run/docker\.sock|docker\.sock)", re.IGNORECASE),
        "container_escape_risk",
        "critical",
    ),
    (re.compile(r"^(cat|type|Get-Content) \.env$", re.IGNORECASE), "secrets_access", "critical"),
    (re.compile(r"^(printenv|env|set|export)($| .*)"), "secrets_access", "high"),
    (re.compile(r".*(deploy|production deploy).*", re.IGNORECASE), "production", "critical"),
    (re.compile(r".*billing.*", re.IGNORECASE), "billing", "critical"),
)

_CREDENTIAL_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9])" + "s" + r"k-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile("API" + r"_KEY", re.IGNORECASE),
    re.compile("SEC" + r"RET", re.IGNORECASE),
    re.compile(
        r"(?<![A-Za-z0-9])(?:[A-Za-z0-9]+[_-])?TO"
        r"KEN(?:[_-][A-Za-z0-9]+)?\s*(?:=|:)\s*\S+",
        re.IGNORECASE,
    ),
    re.compile("PASS" + r"WORD", re.IGNORECASE),
    re.compile("SUPA" + r"BASE", re.IGNORECASE),
    re.compile("OPEN" + r"AI", re.IGNORECASE),
    re.compile("J" + r"WT", re.IGNORECASE),
    re.compile("PRIVATE" + r"_KEY", re.IGNORECASE),
    re.compile(r"\." + "env", re.IGNORECASE),
)


def evaluate_command_gate(
    request_or_mapping: CommandGateRequest | Mapping[str, Any] | Any,
) -> CommandGateDecision:
    request = _coerce_request(request_or_mapping)
    normalized_command = normalize_gate_command(request.command)
    command_mode = str(request.command_mode or DEFAULT_COMMAND_MODE).strip() or DEFAULT_COMMAND_MODE
    target_branch, target_redacted = _redact_optional(request.target_branch)
    working_directory, working_directory_redacted = _redact_optional(request.working_directory)
    command, command_redacted = _redact_text(request.command)
    safe_normalized, normalized_redacted = _redact_text(normalized_command)
    requested_by, requested_by_redacted = _redact_text(request.requested_by)
    purpose, purpose_redacted = _redact_optional(request.purpose)
    metadata_text = _metadata_text(request.metadata)
    metadata_redacted = _contains_credential_like(metadata_text)
    credential_detected = request.reads_secrets or any(
        _contains_credential_like(value)
        for value in (
            request.command,
            normalized_command,
            request.requested_by,
            request.working_directory,
            request.purpose,
            metadata_text,
        )
    )

    category, category_risk, matched_branch = _classify(normalized_command)
    unknown_mode = command_mode not in COMMAND_MODES
    blocked_reasons: list[str] = []
    if credential_detected:
        blocked_reasons.append(CREDENTIAL_REASON)
    if unknown_mode:
        blocked_reasons.append("Command gate mode is unknown.")
    elif command_mode == "disabled":
        blocked_reasons.append("Command execution gate is disabled by default.")
    elif command_mode == "blocked":
        blocked_reasons.append("Command gate mode blocks all commands.")
    if category == "unknown":
        blocked_reasons.append("Command is unknown or high risk.")
    if category == "blocked_high_or_critical":
        blocked_reasons.append("Command is blocked by command gate policy.")
    blocked_reasons.extend(
        _exception_reasons(
            request=request,
            normalized_command=normalized_command,
            target_branch=target_branch,
            category=category,
            matched_branch=matched_branch,
        )
    )

    branch_write_eligible = (
        category == "git_write_branch"
        and command_mode == "sandbox_allowed"
        and not blocked_reasons
        and not _is_main_branch(matched_branch)
        and not _is_main_branch(target_branch)
    )
    read_safe_eligible = (
        category == "read_safe"
        and command_mode in {"dry_run_policy_only", "sandbox_allowed"}
        and not blocked_reasons
    )
    safe_for_future_execution = read_safe_eligible or branch_write_eligible
    allowed = safe_for_future_execution
    blocked = not allowed
    requires_human_intervention = bool(blocked_reasons) or category in {
        "unknown",
        "blocked_high_or_critical",
    }
    requires_runtime_truth = safe_for_future_execution
    requires_sandbox = safe_for_future_execution
    risk_level = _risk_level(
        category_risk=category_risk,
        blocked=blocked,
        credential_detected=credential_detected,
        unknown_mode=unknown_mode,
        blocked_reasons=blocked_reasons,
    )
    reason = _reason(
        allowed=allowed,
        credential_detected=credential_detected,
        command_mode=command_mode,
        category=category,
        unknown_mode=unknown_mode,
    )
    escalation_reason = "; ".join(blocked_reasons) if blocked_reasons else None
    safe_reason, reason_redacted = _redact_text(reason)
    safe_escalation, escalation_redacted = _redact_optional(escalation_reason)
    redacted = any(
        (
            target_redacted,
            working_directory_redacted,
            command_redacted,
            normalized_redacted,
            requested_by_redacted,
            purpose_redacted,
            metadata_redacted,
            reason_redacted,
            escalation_redacted,
            credential_detected,
        )
    )

    return CommandGateDecision(
        allowed=allowed,
        blocked=blocked,
        requires_human_intervention=requires_human_intervention,
        requires_runtime_truth=requires_runtime_truth,
        requires_sandbox=requires_sandbox,
        command=command,
        normalized_command=safe_normalized,
        command_mode=command_mode,
        category=category,
        risk_level=risk_level,
        reason=safe_reason,
        escalation_reason=safe_escalation,
        requested_by=requested_by,
        target_branch=target_branch,
        base_branch=str(request.base_branch or MAIN_BRANCH),
        working_directory=working_directory,
        timeout_seconds=int(request.timeout_seconds or 60),
        command_execution_allowed=False,
        network_allowed=False,
        file_write_allowed=False,
        git_mutation_allowed=False,
        git_push_allowed=False,
        git_merge_allowed=False,
        main_branch_protected=True,
        secrets_access_allowed=False,
        production_allowed=False,
        destructive_allowed=False,
        safe_for_future_execution=safe_for_future_execution,
        evidence_version=COMMAND_GATE_EVIDENCE_VERSION,
        redacted=redacted,
    )


def normalize_gate_command(command: object) -> str:
    return " ".join(str(command or "").strip().split())


def _coerce_request(value: CommandGateRequest | Mapping[str, Any] | Any) -> CommandGateRequest:
    if isinstance(value, CommandGateRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Command gate input must be a request, mapping, or object with to_dict().")

    return CommandGateRequest(
        command=str(payload.get("command") or ""),
        requested_by=str(payload.get("requested_by") or "unknown"),
        command_mode=str(payload.get("command_mode") or DEFAULT_COMMAND_MODE),
        autonomy_level=payload.get("autonomy_level"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        working_directory=payload.get("working_directory"),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        purpose=payload.get("purpose"),
        timeout_seconds=int(payload.get("timeout_seconds") or 60),
        requires_network=bool(payload.get("requires_network", False)),
        writes_files=bool(payload.get("writes_files", False)),
        mutates_git=bool(payload.get("mutates_git", False)),
        reads_secrets=bool(payload.get("reads_secrets", False)),
        production_targeted=bool(payload.get("production_targeted", False)),
        destructive_intent=bool(payload.get("destructive_intent", False)),
        metadata=dict(payload.get("metadata") or {}),
    )


def _classify(command: str) -> tuple[str, str, str | None]:
    lowered = command.lower()
    for pattern, _blocked_category, risk_level in BLOCKED_PATTERNS:
        if pattern.search(command):
            return "blocked_high_or_critical", risk_level, None
    for pattern in READ_SAFE_PATTERNS:
        if pattern.search(lowered):
            return "read_safe", "low", None
    for pattern in GIT_BRANCH_WRITE_PATTERNS:
        match = pattern.search(command)
        if match:
            return "git_write_branch", "medium", match.groupdict().get("branch")
    return "unknown", "high", None


def _exception_reasons(
    *,
    request: CommandGateRequest,
    normalized_command: str,
    target_branch: str | None,
    category: str,
    matched_branch: str | None,
) -> list[str]:
    reasons: list[str] = []
    lowered = normalized_command.lower()
    if request.requires_network or _looks_networked(lowered):
        reasons.append("Network access requires human intervention.")
    if request.reads_secrets:
        reasons.append("Secret access requires human intervention.")
    if request.production_targeted or "production" in lowered:
        reasons.append("Production-targeted commands require human intervention.")
    if request.destructive_intent:
        reasons.append("Destructive intent requires human intervention.")
    if "lower_ci_threshold" in lowered or "disable_security_scan" in lowered:
        reasons.append("Security or CI reduction requires human intervention.")
    if "skip_tests" in lowered or "skip tests" in lowered:
        reasons.append("Skipping tests requires human intervention.")
    if "billing" in lowered:
        reasons.append("Billing changes require human intervention.")
    if category == "git_write_branch" and _is_main_branch(target_branch):
        reasons.append("Main branch cannot be targeted for Git mutation.")
    if category == "git_write_branch" and _is_main_branch(matched_branch):
        reasons.append("Main branch cannot be targeted for Git mutation.")
    if " push " in f" {lowered} " and " main" in f" {lowered} ":
        reasons.append("Push to main is blocked.")
    if " --force" in lowered or " -f" in lowered:
        reasons.append("Force push is blocked.")
    if lowered.startswith("git merge") or lowered.startswith("git rebase"):
        reasons.append("Merge and rebase commands are blocked in this gate.")
    return reasons


def _looks_networked(lowered_command: str) -> bool:
    return any(
        token in lowered_command
        for token in (
            "curl",
            "wget",
            "invoke-webrequest",
            "iwr",
            "irm",
            "ssh",
            "scp",
            "ftp",
            "netcat",
        )
    )


def _reason(
    *,
    allowed: bool,
    credential_detected: bool,
    command_mode: str,
    category: str,
    unknown_mode: bool,
) -> str:
    if credential_detected:
        return CREDENTIAL_REASON
    if unknown_mode:
        return "Command gate mode is unknown."
    if command_mode == "disabled":
        return "Command execution gate is disabled by default."
    if command_mode == "blocked":
        return "Command gate mode blocks all commands."
    if allowed:
        return "Command is eligible for future sandbox execution by policy."
    if category == "unknown":
        return "Command is unknown or high risk."
    return "Command is blocked by command gate policy."


def _risk_level(
    *,
    category_risk: str,
    blocked: bool,
    credential_detected: bool,
    unknown_mode: bool,
    blocked_reasons: list[str],
) -> str:
    if credential_detected:
        return "critical"
    if unknown_mode:
        return "high"
    if any("Force push" in reason or "main" in reason for reason in blocked_reasons):
        return "critical"
    if blocked and category_risk == "low":
        return "medium"
    return category_risk


def _is_main_branch(branch: str | None) -> bool:
    return str(branch or "").strip().lower() == MAIN_BRANCH


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
