"""Text-only command classifier for the local governed sandbox.

This module must never execute command text. It only normalizes and classifies
commands against the documented Phase 3 allowlist and denylist.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from .policy_types import PolicyDecision, PolicyInput

UNKNOWN_COMMAND_REASON = "Command is not explicitly allowed by sandbox policy."

ALLOW_CATEGORY_MAP = {
    "git-inspection": "read_safe",
    "static-validation": "validation_safe",
    "test": "validation_requires_approval",
    "security-validation": "validation_requires_approval",
    "runtime-validation": "validation_requires_approval",
}

DENY_CATEGORY_MAP = {
    "git-main-mutation": "git_sensitive",
    "git-history-mutation": "git_sensitive",
    "pull-request-mutation": "git_sensitive",
    "destructive-git": "destructive",
    "destructive-filesystem": "destructive",
    "secret-exposure": "secrets_access",
    "external-publication": "external_publish",
    "destructive-docker": "destructive",
    "remote-access": "network",
    "remote-transfer": "network",
    "network-secret-exposure": "network",
    "host-secret-access": "secrets_access",
}

SENSITIVE_ACCESS_PATTERNS = (
    "private_key",
    "api_key",
    "token",
    "secret",
    "password",
    "jwt",
    "~/.ssh",
)


def normalize_command(command: str) -> str:
    """Conservatively normalize command text without parsing or expansion."""
    return " ".join(str(command or "").strip().split())


def classify_command(
    command: str,
    cwd: Optional[str] = None,
    requested_by: str = "unknown",
    sandbox_mode: str = "local",
) -> PolicyDecision:
    """Classify command text against sandbox policy rules without executing it."""
    policy_input = PolicyInput(
        command=command,
        cwd=cwd,
        requested_by=requested_by or "unknown",
        sandbox_mode=sandbox_mode or "local",
    )
    normalized = normalize_command(policy_input.command)
    lowered = normalized.lower()

    deny_match = _find_deny_match(lowered)
    if deny_match is not None:
        category = DENY_CATEGORY_MAP.get(str(deny_match.get("category", "")), "blocked")
        return PolicyDecision(
            allowed=False,
            blocked=True,
            requires_approval=True,
            category=category,
            risk_level=str(deny_match.get("risk_level", "critical")),
            reason=str(deny_match.get("reason", "Command is blocked by sandbox policy.")),
            matched_rule=str(deny_match.get("pattern", "")),
            normalized_command=normalized,
            sandbox_mode=policy_input.sandbox_mode,
        )

    allow_match = _find_allow_match(lowered)
    if allow_match is not None:
        requires_approval = bool(allow_match.get("requires_approval", False))
        category = ALLOW_CATEGORY_MAP.get(str(allow_match.get("category", "")), "validation_safe")
        return PolicyDecision(
            allowed=not requires_approval,
            blocked=False,
            requires_approval=requires_approval,
            category=category,
            risk_level=str(allow_match.get("risk_level", "low")),
            reason=str(allow_match.get("reason", "Command is explicitly allowed by sandbox policy.")),
            matched_rule=str(allow_match.get("command", "")),
            normalized_command=normalized,
            sandbox_mode=policy_input.sandbox_mode,
        )

    return PolicyDecision(
        allowed=False,
        blocked=True,
        requires_approval=True,
        category="unknown",
        risk_level="high",
        reason=UNKNOWN_COMMAND_REASON,
        matched_rule=None,
        normalized_command=normalized,
        sandbox_mode=policy_input.sandbox_mode,
    )


def _find_allow_match(lowered_command: str) -> Optional[Mapping[str, Any]]:
    for rule in _load_allowlist():
        rule_command = normalize_command(str(rule.get("command", ""))).lower()
        if lowered_command == rule_command:
            return rule
    return None


def _find_deny_match(lowered_command: str) -> Optional[Mapping[str, Any]]:
    for rule in _load_denylist():
        pattern = normalize_command(str(rule.get("pattern", ""))).lower()
        if not pattern:
            continue
        if _matches_blocked_pattern(lowered_command, pattern):
            return rule

    for sensitive_pattern in SENSITIVE_ACCESS_PATTERNS:
        if sensitive_pattern in lowered_command:
            return {
                "pattern": sensitive_pattern.upper(),
                "category": "secret-exposure",
                "risk_level": "critical",
                "reason": "Command references secret-like material blocked by sandbox policy.",
            }
    return None


def _matches_blocked_pattern(lowered_command: str, pattern: str) -> bool:
    if pattern in {"env", "ssh", "scp"}:
        return bool(re.search(rf"(^|[;&|()\s]){re.escape(pattern)}($|[;&|()\s])", lowered_command))
    return pattern in lowered_command


@lru_cache(maxsize=1)
def _load_allowlist() -> tuple[Mapping[str, Any], ...]:
    return tuple(_read_json_rules("allowlist.commands.json"))


@lru_cache(maxsize=1)
def _load_denylist() -> tuple[Mapping[str, Any], ...]:
    return tuple(_read_json_rules("denylist.commands.json"))


def _read_json_rules(filename: str) -> Iterable[Mapping[str, Any]]:
    path = _project_root() / "sandbox" / "local" / filename
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Sandbox policy file must contain a JSON array: {path}")
    for item in payload:
        if isinstance(item, dict):
            yield item


def _project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "sandbox" / "local").is_dir() and (parent / "backend").is_dir():
            return parent
    raise RuntimeError("Could not locate Projeto Omni repository root.")
