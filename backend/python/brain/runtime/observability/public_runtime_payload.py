"""Public-safe runtime payload view for API/frontend boundaries."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any

DANGEROUS_KEY_FRAGMENTS = (
    "stack",
    "trace",
    "traceback",
    "raw_error",
    "stderr",
    "stdout",
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

PUBLIC_INSPECTION_KEYS = {
    "runtime_mode",
    "runtime_truth",
    "runtime_reason",
    "intent",
    "intent_source",
    "classifier_version",
    "matcher_used",
    "llm_provider_attempted",
    "llm_provider_succeeded",
    "tool_invoked",
    "tool_executed",
    "cognitive_chain",
    "source_of_truth",
    "final_verdict",
    "fallback_triggered",
    "provider_actual",
    "provider_public_name",
    "provider_failed",
    "tool_status",
    "tool_public_name",
    "latency_ms",
    "request_id",
    "warnings_public",
    "error_public_code",
    "error_public_message",
    "severity",
    "retryable",
    "internal_error_redacted",
    "public_summary",
}

_UNIX_PATH_RE = re.compile(r"(?<!\w)/(?:home|root|tmp|var|usr|etc)(?:/[^\s\"'`{}[\],;:]+)+")
_WINDOWS_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:\\(?:Users|Windows|Program Files|Program Files \(x86\))(?:\\[^\s\"'`{}[\],;:]+)+)"
)
_OPENAI_KEY_RE = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_SUPABASE_URL_RE = re.compile(r"https://[a-z0-9-]+\.supabase\.co(?:/[^\s\"'`{}[\],;]*)?", re.IGNORECASE)


def _dangerous_key(key: Any) -> bool:
    normalized = str(key or "").strip().lower()
    return any(fragment in normalized for fragment in DANGEROUS_KEY_FRAGMENTS)


def _redact_string(value: str) -> str:
    redacted = _UNIX_PATH_RE.sub("[redacted_location]", value)
    redacted = _WINDOWS_PATH_RE.sub("[redacted_location]", redacted)
    redacted = _OPENAI_KEY_RE.sub("[redacted_secret]", redacted)
    redacted = _BEARER_RE.sub("Bearer [redacted_secret]", redacted)
    redacted = _JWT_RE.sub("[redacted_jwt]", redacted)
    redacted = _SUPABASE_URL_RE.sub("[redacted_supabase_url]", redacted)
    return redacted


def _sanitize_recursive(value: Any) -> Any:
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if _dangerous_key(key):
                continue
            clean[str(key)] = _sanitize_recursive(item)
        return clean
    if isinstance(value, list):
        return [_sanitize_recursive(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_recursive(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _redact_string(str(value))


def build_public_summary(runtime_mode: Any) -> str:
    mode = str(runtime_mode or "").strip()
    if mode == "MATCHER_SHORTCUT":
        return "Responded using a local pattern matcher. No AI provider was used."
    if mode == "SAFE_FALLBACK":
        return "System operated in safe fallback mode due to runtime constraints."
    if mode == "FULL_COGNITIVE_RUNTIME":
        return "Full cognitive execution with provider and tool verification."
    if mode == "TOOL_EXECUTED":
        return "A real tool/action executed successfully."
    if mode == "TOOL_BLOCKED":
        return "A requested tool/action was blocked by policy."
    if mode == "PROVIDER_UNAVAILABLE":
        return "No usable LLM provider completed this turn."
    if mode == "NODE_FALLBACK":
        return "Node runtime did not produce a usable execution result."
    if mode == "MEMORY_ONLY_RESPONSE":
        return "Responded from memory/context without provider execution."
    return f"Execution completed in {mode or 'unknown'} mode."


def build_public_cognitive_runtime_inspection(inspection: Any) -> dict[str, Any]:
    if not isinstance(inspection, Mapping):
        return {
            "runtime_mode": "SAFE_FALLBACK",
            "runtime_reason": "invalid_runtime_inspection",
            "fallback_triggered": True,
            "internal_error_redacted": True,
            "public_summary": build_public_summary("SAFE_FALLBACK"),
        }

    source = copy.deepcopy(dict(inspection))
    signals = source.get("signals") if isinstance(source.get("signals"), Mapping) else {}
    public: dict[str, Any] = {}

    for key in PUBLIC_INSPECTION_KEYS:
        if key in source:
            public[key] = _sanitize_recursive(source.get(key))
        elif isinstance(signals, Mapping) and key in signals:
            public[key] = _sanitize_recursive(signals.get(key))

    if "runtime_mode" not in public:
        public["runtime_mode"] = _sanitize_recursive(source.get("runtime_mode", "UNKNOWN"))
    if "runtime_truth" in public and isinstance(public["runtime_truth"], Mapping):
        truth = dict(public["runtime_truth"])
        truth_mode = str(truth.get("runtime_mode") or "").strip()
        truth["public_summary"] = str(truth.get("public_summary") or build_public_summary(truth_mode))
        public["runtime_truth"] = _sanitize_recursive(truth)
    if "runtime_reason" not in public:
        public["runtime_reason"] = _sanitize_recursive(source.get("runtime_reason", ""))
    if "fallback_triggered" not in public and isinstance(signals, Mapping):
        public["fallback_triggered"] = bool(signals.get("fallback_triggered", False))
    if "provider_actual" not in public and isinstance(signals, Mapping):
        provider = signals.get("provider_actual") or signals.get("provider_public_name")
        if provider:
            public["provider_actual"] = _sanitize_recursive(provider)
    if "provider_failed" not in public and isinstance(signals, Mapping):
        public["provider_failed"] = bool(signals.get("provider_failed", False))
    if "tool_status" not in public and isinstance(signals, Mapping):
        if signals.get("tool_succeeded"):
            public["tool_status"] = "succeeded"
        elif signals.get("tool_failed"):
            public["tool_status"] = "failed"
        elif signals.get("tool_attempted"):
            public["tool_status"] = "attempted"
    if "latency_ms" not in public and isinstance(signals, Mapping) and "duration_ms" in signals:
        public["latency_ms"] = _sanitize_recursive(signals.get("duration_ms"))
    public["public_summary"] = build_public_summary(
        (public.get("runtime_truth") or {}).get("runtime_mode")
        if isinstance(public.get("runtime_truth"), Mapping)
        else public.get("runtime_mode")
    )
    return public


def sanitize_public_runtime_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "response": "",
            "error_public_code": "INVALID_PUBLIC_PAYLOAD",
            "error_public_message": "Backend produced an invalid public payload.",
            "internal_error_redacted": True,
        }

    cloned = copy.deepcopy(dict(payload))
    if isinstance(cloned.get("cognitive_runtime_inspection"), Mapping):
        cloned["cognitive_runtime_inspection"] = build_public_cognitive_runtime_inspection(
            cloned.get("cognitive_runtime_inspection")
        )
    return _sanitize_recursive(cloned)


__all__ = [
    "build_public_cognitive_runtime_inspection",
    "build_public_summary",
    "sanitize_public_runtime_payload",
]
