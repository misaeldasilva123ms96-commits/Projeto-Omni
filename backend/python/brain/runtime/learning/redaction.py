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
    "raw_key",
    "raw_url",
    "execution_request",
    "tool_raw_result",
    "memory_raw",
    "memory_content",
)

_SAFE_IDENTIFIER_KEYS = {
    "artifact_id",
    "goal_id",
    "request_id",
    "run_id",
    "session_id",
    "trace_id",
}

_SUPABASE_URL_RE = re.compile(r"https://[a-z0-9-]+\.supabase\.co(?:/[^\s\"'`{}[\],;]*)?", re.IGNORECASE)
_SUPABASE_KEY_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_JWT_RE = _SUPABASE_KEY_RE
_OPENAI_KEY_RE = re.compile(r"\bsk-(?:proj-|ant-|groq-)?[A-Za-z0-9_-]{8,}\b")
_COMMON_PROVIDER_KEY_RE = re.compile(
    r"\b(?:AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AIza[0-9A-Za-z_-]{20,}|sk_live_[0-9A-Za-z]{16,}|rk_live_[0-9A-Za-z]{16,})\b"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")
_BASIC_AUTH_RE = re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/=]{12,}")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_BR_PHONE_RE = re.compile(
    r"(?<![A-Za-z0-9_-])"
    r"(?:"
    r"\+55\s*+\(?\d{2}\)?\s*+9?\s*+\d{4}[-.\s]?\d{4}"
    r"|"
    r"\(?\d{2}\)?\s*+9\s*+\d{4}[-.\s]?\d{4}"
    r"|"
    r"\d{5}[-.\s]\d{4}"
    r")"
    r"(?![A-Za-z0-9_-])"
)
_CPF_RE = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passphrase|token|secret|api[_-]?key|access[_-]?key|client[_-]?secret)\s*[:=]\s*([\"']?)([^\s,;}\]]+)\2"
)
_URL_CREDENTIAL_RE = re.compile(r"(?i)(https?://)([^\s/@:]+):([^\s/@]+)@")
_UNIX_PATH_RE = re.compile(r"(?<!\w)/(?:home|root|tmp|var|usr|etc)(?:/[^\s\"'`{}[\],;:]+)+")
_WINDOWS_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:\\(?:Users|Windows|Program Files|Program Files \(x86\))(?:\\[^\s\"'`{}[\],;:]+)+)"
)


def _dangerous_key(key: Any) -> bool:
    normalized = str(key or "").strip().lower()
    if normalized in _SAFE_IDENTIFIER_KEYS:
        return False
    return any(fragment in normalized for fragment in _DANGEROUS_KEY_FRAGMENTS)


def _redact_private_keys(text: str) -> str:
    """Redact PEM private-key blocks with a bounded, linear scan."""
    begin_prefix = "-----BEGIN"
    header_suffix = " PRIVATE KEY-----"
    cursor = 0
    chunks: list[str] = []
    while True:
        begin = text.find(begin_prefix, cursor)
        if begin < 0:
            chunks.append(text[cursor:])
            return "".join(chunks)

        label_start = begin + len(begin_prefix)
        # PEM labels are short. Bounding this lookup prevents repeated markers
        # in uncontrolled input from causing polynomial backtracking behavior.
        header_end = text.find(header_suffix, label_start, min(len(text), label_start + 40))
        if header_end < 0:
            chunks.append(text[cursor : label_start])
            cursor = label_start
            continue

        label = text[label_start:header_end]
        if label and (not label.startswith(" ") or not label[1:].isalnum() or not label[1:].isupper()):
            chunks.append(text[cursor : label_start])
            cursor = label_start
            continue

        end_marker = f"-----END{label} PRIVATE KEY-----"
        block_end = text.find(end_marker, header_end + len(header_suffix))
        chunks.append(text[cursor:begin])
        chunks.append("[REDACTED_PRIVATE_KEY]")
        if block_end < 0:
            return "".join(chunks)
        cursor = block_end + len(end_marker)


def redact_sensitive_text(value: Any) -> str:
    text = str(value or "")
    text = _SUPABASE_URL_RE.sub("[REDACTED_SUPABASE_URL]", text)
    text = _JWT_RE.sub("[REDACTED_JWT]", text)
    text = _OPENAI_KEY_RE.sub("[REDACTED_API_KEY]", text)
    text = _COMMON_PROVIDER_KEY_RE.sub("[REDACTED_API_KEY]", text)
    text = _BEARER_RE.sub("Bearer [REDACTED_TOKEN]", text)
    text = _BASIC_AUTH_RE.sub("Basic [REDACTED_TOKEN]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _BR_PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = _CPF_RE.sub("[REDACTED_CPF]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[REDACTED_SECRET]", text)
    text = _redact_private_keys(text)
    text = _URL_CREDENTIAL_RE.sub(r"\1[REDACTED_CREDENTIALS]@", text)
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
