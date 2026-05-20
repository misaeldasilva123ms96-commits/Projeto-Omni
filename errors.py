"""
Centralized public error codes for the Python runtime — Phase 8 (Roadmap Oficial v2.1).

Rules:
- All public-facing error codes are defined here.
- Never include internal details in error_public_message.
- severity: 'fatal' | 'degraded' | 'warning' | 'info'
- retryable: True if the client may retry the same request.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PublicErrorSpec:
    code: str
    message: str
    severity: str
    retryable: bool


ERRORS: dict[str, PublicErrorSpec] = {
    "SHELL_TOOL_BLOCKED": PublicErrorSpec("SHELL_TOOL_BLOCKED", "Shell execution is disabled by policy.", "warning", False),
    "TOOL_BLOCKED_PUBLIC_DEMO": PublicErrorSpec("TOOL_BLOCKED_PUBLIC_DEMO", "This tool is not available in public demo mode.", "warning", False),
    "TOOL_BLOCKED_BY_GOVERNANCE": PublicErrorSpec("TOOL_BLOCKED_BY_GOVERNANCE", "Tool execution was blocked by governance policy.", "warning", False),
    "TOOL_APPROVAL_REQUIRED": PublicErrorSpec("TOOL_APPROVAL_REQUIRED", "This operation requires explicit approval before execution.", "warning", False),
    "SPECIALIST_FAILED": PublicErrorSpec("SPECIALIST_FAILED", "Specialist execution failed. Using fallback.", "degraded", True),
    "PROVIDER_UNAVAILABLE": PublicErrorSpec("PROVIDER_UNAVAILABLE", "No AI provider is available at this time.", "degraded", True),
    "NODE_EMPTY_RESPONSE": PublicErrorSpec("NODE_EMPTY_RESPONSE", "The Node runtime did not return a usable response.", "degraded", True),
    "NODE_RUNNER_FAILED": PublicErrorSpec("NODE_RUNNER_FAILED", "The Node runtime failed to process the request.", "degraded", True),
    "PYTHON_ORCHESTRATOR_FAILED": PublicErrorSpec("PYTHON_ORCHESTRATOR_FAILED", "The Python orchestrator failed to process the request.", "degraded", True),
    "MATCHER_SHORTCUT_USED": PublicErrorSpec("MATCHER_SHORTCUT_USED", "Responded using a local pattern matcher. No AI provider was used.", "info", False),
    "RULE_BASED_INTENT_USED": PublicErrorSpec("RULE_BASED_INTENT_USED", "Intent was classified by rule-based heuristics, not an AI model.", "info", False),
    "MEMORY_STORE_UNAVAILABLE": PublicErrorSpec("MEMORY_STORE_UNAVAILABLE", "Memory store is unavailable. Responses may lack context.", "degraded", True),
    "SUPABASE_NOT_CONFIGURED": PublicErrorSpec("SUPABASE_NOT_CONFIGURED", "Supabase is not configured. Persistence features are unavailable.", "info", False),
    "TIMEOUT": PublicErrorSpec("TIMEOUT", "The operation timed out.", "degraded", True),
    "INTERNAL_ERROR_REDACTED": PublicErrorSpec("INTERNAL_ERROR_REDACTED", "An internal error occurred. Details have been redacted for security.", "fatal", False),
    "INPUT_TOO_LONG": PublicErrorSpec("INPUT_TOO_LONG", "The message exceeds the maximum allowed length.", "warning", False),
    "INPUT_INVALID": PublicErrorSpec("INPUT_INVALID", "The input contains invalid characters or format.", "warning", False),
    "RATE_LIMITED": PublicErrorSpec("RATE_LIMITED", "Too many requests. Please wait before sending another message.", "warning", True),
}


def build_public_error(code: str, **overrides: Any) -> dict[str, Any]:
    """Build a standardized public error response dict."""
    spec = ERRORS.get(code, ERRORS["INTERNAL_ERROR_REDACTED"])
    return {
        "ok": False,
        "error_public_code": spec.code,
        "error_public_message": overrides.get("message", spec.message),
        "severity": overrides.get("severity", spec.severity),
        "retryable": overrides.get("retryable", spec.retryable),
        "internal_error_redacted": True,
    }


__all__ = ["ERRORS", "PublicErrorSpec", "build_public_error"]
