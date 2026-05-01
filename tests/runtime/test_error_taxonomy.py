from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.error_taxonomy import (  # noqa: E402
    ERROR_MESSAGES,
    ERROR_RETRYABLE,
    ERROR_SEVERITY,
    OmniErrorCode,
    build_public_error,
    normalize_public_error,
)
from brain.runtime.observability.public_runtime_payload import sanitize_public_runtime_payload  # noqa: E402


def test_every_required_error_code_has_public_metadata() -> None:
    required = {
        "SHELL_TOOL_BLOCKED",
        "TOOL_BLOCKED_PUBLIC_DEMO",
        "TOOL_BLOCKED_BY_GOVERNANCE",
        "TOOL_APPROVAL_REQUIRED",
        "SPECIALIST_FAILED",
        "MATCHER_SHORTCUT_USED",
        "RULE_BASED_INTENT_USED",
        "PROVIDER_UNAVAILABLE",
        "NODE_EMPTY_RESPONSE",
        "NODE_RUNNER_FAILED",
        "PYTHON_ORCHESTRATOR_FAILED",
        "MEMORY_STORE_UNAVAILABLE",
        "SUPABASE_NOT_CONFIGURED",
        "TIMEOUT",
        "INTERNAL_ERROR_REDACTED",
        "INPUT_VALIDATION_FAILED",
        "PAYLOAD_TOO_LARGE",
        "RATE_LIMITED",
        "INVALID_CONTENT_TYPE",
        "INVALID_JSON",
    }

    assert required == {item.value for item in OmniErrorCode}
    for code in required:
        assert ERROR_MESSAGES[code]
        assert ERROR_SEVERITY[code] in {"info", "degraded", "blocked", "error", "critical"}
        assert isinstance(ERROR_RETRYABLE[code], bool)


def test_build_and_normalize_public_error_shape() -> None:
    error = build_public_error(OmniErrorCode.SHELL_TOOL_BLOCKED)

    assert error == {
        "error_public_code": "SHELL_TOOL_BLOCKED",
        "error_public_message": "Shell execution is disabled by policy.",
        "severity": "blocked",
        "retryable": False,
        "internal_error_redacted": True,
    }
    assert normalize_public_error({"error_public_code": "TOOL_APPROVAL_REQUIRED"})["severity"] == "blocked"
    assert normalize_public_error("TIMEOUT")["retryable"] is True


def test_unknown_internal_error_is_redacted_and_safe() -> None:
    error = normalize_public_error({"code": "DOES_NOT_EXIST", "message": "/home/render/.env sk-proj-secret"})

    assert error["error_public_code"] == "INTERNAL_ERROR_REDACTED"
    assert error["internal_error_redacted"] is True
    serialized = repr(error)
    assert "/home/render" not in serialized
    assert "sk-proj" not in serialized
    assert "DOES_NOT_EXIST" not in serialized


def test_major_error_code_mappings() -> None:
    expectations = {
        "TOOL_BLOCKED_PUBLIC_DEMO": ("blocked", False),
        "TOOL_BLOCKED_BY_GOVERNANCE": ("blocked", False),
        "TOOL_APPROVAL_REQUIRED": ("blocked", False),
        "SPECIALIST_FAILED": ("degraded", True),
        "PROVIDER_UNAVAILABLE": ("degraded", True),
        "NODE_EMPTY_RESPONSE": ("degraded", True),
        "TIMEOUT": ("error", True),
        "INPUT_VALIDATION_FAILED": ("blocked", False),
        "PAYLOAD_TOO_LARGE": ("blocked", False),
        "RATE_LIMITED": ("blocked", True),
        "INVALID_CONTENT_TYPE": ("blocked", False),
        "INVALID_JSON": ("blocked", False),
    }

    for code, (severity, retryable) in expectations.items():
        error = build_public_error(code)
        assert error["severity"] == severity
        assert error["retryable"] is retryable


def test_sanitizer_preserves_standard_public_error_fields_and_removes_raw() -> None:
    payload = {
        "response": "x",
        **build_public_error("NODE_RUNNER_FAILED"),
        "stack": "raw stack",
        "stderr": "raw stderr",
        "env": {"TOKEN": "secret"},
        "raw_payload": {"body": "secret"},
    }

    sanitized = sanitize_public_runtime_payload(payload)
    assert sanitized["error_public_code"] == "NODE_RUNNER_FAILED"
    assert sanitized["severity"] == "degraded"
    assert sanitized["retryable"] is True
    assert "stack" not in repr(sanitized)
    assert "stderr" not in repr(sanitized)
    assert "TOKEN" not in repr(sanitized)
    assert "raw_payload" not in repr(sanitized)
