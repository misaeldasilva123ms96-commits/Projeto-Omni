from __future__ import annotations

from enum import StrEnum
from typing import Any


class OmniErrorCode(StrEnum):
    SHELL_TOOL_BLOCKED = "SHELL_TOOL_BLOCKED"
    TOOL_BLOCKED_PUBLIC_DEMO = "TOOL_BLOCKED_PUBLIC_DEMO"
    TOOL_BLOCKED_BY_GOVERNANCE = "TOOL_BLOCKED_BY_GOVERNANCE"
    TOOL_APPROVAL_REQUIRED = "TOOL_APPROVAL_REQUIRED"
    SPECIALIST_FAILED = "SPECIALIST_FAILED"
    MATCHER_SHORTCUT_USED = "MATCHER_SHORTCUT_USED"
    RULE_BASED_INTENT_USED = "RULE_BASED_INTENT_USED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    NODE_EMPTY_RESPONSE = "NODE_EMPTY_RESPONSE"
    NODE_RUNNER_FAILED = "NODE_RUNNER_FAILED"
    PYTHON_ORCHESTRATOR_FAILED = "PYTHON_ORCHESTRATOR_FAILED"
    MEMORY_STORE_UNAVAILABLE = "MEMORY_STORE_UNAVAILABLE"
    SUPABASE_NOT_CONFIGURED = "SUPABASE_NOT_CONFIGURED"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR_REDACTED = "INTERNAL_ERROR_REDACTED"


ERROR_MESSAGES: dict[str, str] = {
    OmniErrorCode.SHELL_TOOL_BLOCKED: "Shell execution is disabled by policy.",
    OmniErrorCode.TOOL_BLOCKED_PUBLIC_DEMO: "Tool execution is blocked in public demo mode.",
    OmniErrorCode.TOOL_BLOCKED_BY_GOVERNANCE: "Tool execution was blocked by governance policy.",
    OmniErrorCode.TOOL_APPROVAL_REQUIRED: "Tool execution requires explicit approval before running.",
    OmniErrorCode.SPECIALIST_FAILED: "Specialist execution failed. Using fallback.",
    OmniErrorCode.MATCHER_SHORTCUT_USED: "Responded using a local pattern matcher. No AI provider was used.",
    OmniErrorCode.RULE_BASED_INTENT_USED: "Intent was classified by deterministic rules.",
    OmniErrorCode.PROVIDER_UNAVAILABLE: "No usable AI provider was available for this request.",
    OmniErrorCode.NODE_EMPTY_RESPONSE: "Node runtime returned an empty response.",
    OmniErrorCode.NODE_RUNNER_FAILED: "Node runtime did not complete successfully.",
    OmniErrorCode.PYTHON_ORCHESTRATOR_FAILED: "Python orchestrator could not complete the request.",
    OmniErrorCode.MEMORY_STORE_UNAVAILABLE: "Memory store is unavailable for this request.",
    OmniErrorCode.SUPABASE_NOT_CONFIGURED: "Supabase is not configured for this environment.",
    OmniErrorCode.TIMEOUT: "The operation timed out.",
    OmniErrorCode.INTERNAL_ERROR_REDACTED: "An internal runtime error occurred and details were redacted.",
}

ERROR_SEVERITY: dict[str, str] = {
    OmniErrorCode.SHELL_TOOL_BLOCKED: "blocked",
    OmniErrorCode.TOOL_BLOCKED_PUBLIC_DEMO: "blocked",
    OmniErrorCode.TOOL_BLOCKED_BY_GOVERNANCE: "blocked",
    OmniErrorCode.TOOL_APPROVAL_REQUIRED: "blocked",
    OmniErrorCode.SPECIALIST_FAILED: "degraded",
    OmniErrorCode.MATCHER_SHORTCUT_USED: "info",
    OmniErrorCode.RULE_BASED_INTENT_USED: "info",
    OmniErrorCode.PROVIDER_UNAVAILABLE: "degraded",
    OmniErrorCode.NODE_EMPTY_RESPONSE: "degraded",
    OmniErrorCode.NODE_RUNNER_FAILED: "degraded",
    OmniErrorCode.PYTHON_ORCHESTRATOR_FAILED: "error",
    OmniErrorCode.MEMORY_STORE_UNAVAILABLE: "degraded",
    OmniErrorCode.SUPABASE_NOT_CONFIGURED: "info",
    OmniErrorCode.TIMEOUT: "error",
    OmniErrorCode.INTERNAL_ERROR_REDACTED: "critical",
}

ERROR_RETRYABLE: dict[str, bool] = {
    OmniErrorCode.SHELL_TOOL_BLOCKED: False,
    OmniErrorCode.TOOL_BLOCKED_PUBLIC_DEMO: False,
    OmniErrorCode.TOOL_BLOCKED_BY_GOVERNANCE: False,
    OmniErrorCode.TOOL_APPROVAL_REQUIRED: False,
    OmniErrorCode.SPECIALIST_FAILED: True,
    OmniErrorCode.MATCHER_SHORTCUT_USED: False,
    OmniErrorCode.RULE_BASED_INTENT_USED: False,
    OmniErrorCode.PROVIDER_UNAVAILABLE: True,
    OmniErrorCode.NODE_EMPTY_RESPONSE: True,
    OmniErrorCode.NODE_RUNNER_FAILED: True,
    OmniErrorCode.PYTHON_ORCHESTRATOR_FAILED: True,
    OmniErrorCode.MEMORY_STORE_UNAVAILABLE: True,
    OmniErrorCode.SUPABASE_NOT_CONFIGURED: False,
    OmniErrorCode.TIMEOUT: True,
    OmniErrorCode.INTERNAL_ERROR_REDACTED: False,
}


def _normalize_code(code: Any) -> str:
    value = str(code or "").strip()
    if value in ERROR_MESSAGES:
        return value
    return OmniErrorCode.INTERNAL_ERROR_REDACTED.value


def build_public_error(code: Any, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = _normalize_code(code)
    payload = {
        "error_public_code": normalized,
        "error_public_message": ERROR_MESSAGES[normalized],
        "severity": ERROR_SEVERITY[normalized],
        "retryable": bool(ERROR_RETRYABLE[normalized]),
        "internal_error_redacted": True,
    }
    if isinstance(overrides, dict):
        for key in ("error_public_message", "severity", "retryable"):
            if key in overrides:
                payload[key] = overrides[key]
    return payload


def normalize_public_error(error_or_code: Any) -> dict[str, Any]:
    if isinstance(error_or_code, dict):
        return build_public_error(error_or_code.get("error_public_code") or error_or_code.get("code"))
    return build_public_error(error_or_code)


__all__ = [
    "ERROR_MESSAGES",
    "ERROR_RETRYABLE",
    "ERROR_SEVERITY",
    "OmniErrorCode",
    "build_public_error",
    "normalize_public_error",
]
