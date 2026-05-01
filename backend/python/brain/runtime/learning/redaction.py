from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any

REDACTED_INTERNAL_PAYLOAD = "[REDACTED_INTERNAL_PAYLOAD]"

_DANGEROUS_KEY_FRAGMENTS = (
    "stack",
    "trace",
    "traceback",
    "raw_error",
    "stdout",
    "stderr",
    "command",
    "args",
    "argv",
    "env",
    "api_key",
    "token",
    "jwt",
    "secret",
    "password",
    "authorization",
    "bearer",
    "provider_raw",
    "raw_provider",
    "raw_response",
    "raw_payload",
    "execution_request",
    "tool_raw_result",
    "memory_raw",
    "memory_content",
)

_SUPABASE_URL_RE = re.compile(r"https://[a-z0-9-]+\.supabase\.co(?:/[^\s\"'`{}[\],;]*)?", re.IGNORECASE)
_SUPABASE_KEY_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_JWT_RE = _SUPABASE_KEY_RE
_OPENAI_KEY_RE = re.compile(r"\bsk-(?:proj-|ant-|groq-)?[A-Za-z0-9_-]{8,}\b")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_BR_PHONE_RE = re.compile(r"(?<!\d)(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?(?:9\s*)?\d{4}[-.\s]?\d{4}(?!\d)")
_CPF_RE = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|token|secret|api_key)\s*=\s*([^\s,;}\]]+)"
)
_UNIX_PATH_RE = re.compile(r"(?<!\w)/(?:home|root|tmp|var|usr|etc)(?:/[^\s\"'`{}[\],;:]+)+")
_WINDOWS_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:\\(?:Users|Windows|Program Files|Program Files \(x86\))(?:\\[^\s\"'`{}[\],;:]+)+)"
)


def _dangerous_key(key: Any) -> bool:
    normalized = str(key or "").strip().lower()
    return any(fragment in normalized for fragment in _DANGEROUS_KEY_FRAGMENTS)


def redact_sensitive_text(value: Any) -> str:
    text = str(value or "")
    text = _SUPABASE_URL_RE.sub("[REDACTED_SUPABASE_URL]", text)
    text = _JWT_RE.sub("[REDACTED_JWT]", text)
    text = _OPENAI_KEY_RE.sub("[REDACTED_API_KEY]", text)
    text = _BEARER_RE.sub("Bearer [REDACTED_TOKEN]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _BR_PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = _CPF_RE.sub("[REDACTED_CPF]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[REDACTED_SECRET]", text)
    text = _UNIX_PATH_RE.sub("[REDACTED_PATH]", text)
    text = _WINDOWS_PATH_RE.sub("[REDACTED_PATH]", text)
    return text


def redact_sensitive_payload(payload: Any) -> Any:
    cloned = copy.deepcopy(payload)
    return _redact_recursive(cloned)


def redact_learning_record(record: Any) -> Any:
    return redact_sensitive_payload(record)


def _redact_recursive(value: Any) -> Any:
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = str(key)
            if _dangerous_key(safe_key):
                out[safe_key] = REDACTED_INTERNAL_PAYLOAD
            else:
                out[safe_key] = _redact_recursive(item)
        return out
    if isinstance(value, list):
        return [_redact_recursive(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_recursive(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return redact_sensitive_text(value)


__all__ = [
    "REDACTED_INTERNAL_PAYLOAD",
    "redact_learning_record",
    "redact_sensitive_payload",
    "redact_sensitive_text",
]
