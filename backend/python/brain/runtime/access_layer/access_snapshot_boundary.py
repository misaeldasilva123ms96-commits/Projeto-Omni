from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .public_access_snapshot import (
    PUBLIC_ACCESS_SNAPSHOT_VERSION,
    build_public_access_snapshot,
)


ACCESS_SNAPSHOT_BOUNDARY_VERSION = "access_snapshot_boundary_v1"

APPROVED_ACCESS_SNAPSHOT_KEYS = frozenset(
    {
        "snapshot_version",
        "plan_mode",
        "provider_mode",
        "subject_id",
        "usage_date",
        "tokens_in",
        "tokens_out",
        "tokens_total",
        "daily_token_limit",
        "quota_remaining",
        "quota_exceeded",
        "input_allowed",
        "output_allowed",
        "quota_allowed",
        "routing_allowed",
        "fallback_allowed",
        "selected_provider_family",
        "selected_adapter_id",
        "adapter_display_name",
        "adapter_capabilities",
        "decision_reason",
    }
)

APPROVED_ADAPTER_CAPABILITY_KEYS = frozenset(
    {
        "supports_streaming",
        "supports_tools",
        "supports_files",
        "supports_long_context",
        "supports_sensitive_tools",
        "is_experimental",
        "is_user_key_required",
        "is_managed",
        "is_internal",
    }
)

APPROVED_ACCESS_SNAPSHOT_ENVELOPE_KEYS = frozenset(
    {
        "ok",
        "access_snapshot",
        "denied",
        "reason",
        "snapshot_version",
        "boundary_version",
    }
)

_SAFE_REQUEST_KEYS = frozenset(
    {
        "plan_mode",
        "subject_id",
        "usage_date",
        "tokens_in",
        "tokens_out",
    }
)

_UNSAFE_PUBLIC_INPUT_KEYS = frozenset(
    {
        "adapter_id",
        "api_key",
        "billing_config",
        "credential",
        "daily_token_limit",
        "existing_daily_tokens",
        "internal_config",
        "max_context_tokens",
        "max_input_tokens",
        "max_output_tokens",
        "policy_overrides",
        "private_endpoint",
        "provider_family",
        "provider_mode",
        "provider_payload",
        "quota_remaining",
        "quota_exceeded",
        "raw_config",
        "raw_provider_config",
        "request_payload",
        "secret",
        "selected_adapter_id",
        "selected_provider_family",
        "token",
        "tokens_total",
    }
)

_UNSAFE_SUBJECT_FRAGMENTS = (
    "@",
    "api_key",
    "bearer ",
    "credential",
    "password",
    "secret",
    "sk-",
    "token",
)

_SAFE_CAPABILITIES = {
    "supports_streaming": False,
    "supports_tools": False,
    "supports_files": False,
    "supports_long_context": False,
    "supports_sensitive_tools": False,
    "is_experimental": False,
    "is_user_key_required": False,
    "is_managed": False,
    "is_internal": False,
}


def build_access_snapshot_response(
    public_input: Mapping[str, Any],
    *,
    existing_daily_tokens: int = 0,
) -> dict[str, Any]:
    """Build a public-safe access snapshot response envelope.

    The input mapping is public request-shaped data only. Trusted server-side
    values such as existing daily usage are accepted as keyword arguments.
    """

    normalized = normalize_access_snapshot_request(public_input)
    if not normalized["ok"]:
        return _fail_closed_response(str(normalized["reason"]))

    if not isinstance(existing_daily_tokens, int) or existing_daily_tokens < 0:
        return _fail_closed_response("invalid_token_usage")

    snapshot = build_public_access_snapshot(
        plan_mode=normalized["plan_mode"],
        subject_id=normalized["subject_id"],
        usage_date=normalized["usage_date"],
        tokens_in=normalized["tokens_in"],
        tokens_out=normalized["tokens_out"],
        existing_daily_tokens=existing_daily_tokens,
    )
    sanitized = sanitize_access_snapshot_output(snapshot)
    routing_allowed = bool(sanitized.get("routing_allowed", False))
    reason = "ok" if routing_allowed else str(sanitized.get("decision_reason") or "routing_denied")
    return _response_envelope(access_snapshot=sanitized, reason=reason)


def normalize_access_snapshot_request(public_input: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(public_input, Mapping):
        return {"ok": False, "reason": "invalid_request"}

    unsafe_keys = reject_unsafe_public_input(public_input)
    if unsafe_keys:
        return {"ok": False, "reason": "unsafe_public_input"}

    if not _SAFE_REQUEST_KEYS.issuperset(public_input.keys()):
        return {"ok": False, "reason": "unsafe_public_input"}

    try:
        plan_mode = str(public_input["plan_mode"] or "").strip().lower()
        subject_id = str(public_input["subject_id"] or "")
        usage_date = str(public_input["usage_date"] or "")
        raw_tokens_in = public_input["tokens_in"]
        raw_tokens_out = public_input["tokens_out"]
    except KeyError:
        return {"ok": False, "reason": "invalid_request"}

    try:
        tokens_in = _coerce_non_negative_int(raw_tokens_in)
        tokens_out = _coerce_non_negative_int(raw_tokens_out)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "invalid_token_usage"}

    if not plan_mode or not usage_date:
        return {"ok": False, "reason": "invalid_request"}

    if not _is_public_opaque_subject_id(subject_id):
        return {"ok": False, "reason": "unsafe_subject_id"}

    return {
        "ok": True,
        "plan_mode": plan_mode,
        "subject_id": subject_id,
        "usage_date": usage_date,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


def reject_unsafe_public_input(public_input: Mapping[str, Any]) -> tuple[str, ...]:
    if not isinstance(public_input, Mapping):
        return ("request",)

    unsafe = []
    for key in public_input:
        normalized_key = str(key or "").strip().lower()
        if normalized_key in _UNSAFE_PUBLIC_INPUT_KEYS:
            unsafe.append(normalized_key)
    return tuple(sorted(unsafe))


def validate_public_access_snapshot_keys(snapshot: Mapping[str, Any]) -> bool:
    if set(snapshot.keys()) != APPROVED_ACCESS_SNAPSHOT_KEYS:
        return False
    capabilities = snapshot.get("adapter_capabilities")
    return isinstance(capabilities, Mapping) and set(capabilities.keys()) == APPROVED_ADAPTER_CAPABILITY_KEYS


def sanitize_access_snapshot_output(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping) or not validate_public_access_snapshot_keys(snapshot):
        return _fail_closed_snapshot("snapshot_validation_failed")

    sanitized = {key: snapshot[key] for key in APPROVED_ACCESS_SNAPSHOT_KEYS}
    sanitized["adapter_capabilities"] = {
        key: bool(snapshot["adapter_capabilities"].get(key, False))
        for key in APPROVED_ADAPTER_CAPABILITY_KEYS
    }
    return sanitized


def _response_envelope(*, access_snapshot: dict[str, Any], reason: str) -> dict[str, Any]:
    routing_allowed = bool(access_snapshot.get("routing_allowed", False))
    return {
        "ok": routing_allowed,
        "access_snapshot": access_snapshot,
        "denied": not routing_allowed,
        "reason": "ok" if routing_allowed else reason,
        "snapshot_version": str(access_snapshot.get("snapshot_version") or PUBLIC_ACCESS_SNAPSHOT_VERSION),
        "boundary_version": ACCESS_SNAPSHOT_BOUNDARY_VERSION,
    }


def _fail_closed_response(reason: str) -> dict[str, Any]:
    return _response_envelope(access_snapshot=_fail_closed_snapshot(reason), reason=reason)


def _fail_closed_snapshot(reason: str) -> dict[str, Any]:
    return {
        "snapshot_version": PUBLIC_ACCESS_SNAPSHOT_VERSION,
        "plan_mode": "",
        "provider_mode": "",
        "subject_id": "",
        "usage_date": "",
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens_total": 0,
        "daily_token_limit": None,
        "quota_remaining": None,
        "quota_exceeded": False,
        "input_allowed": False,
        "output_allowed": False,
        "quota_allowed": False,
        "routing_allowed": False,
        "fallback_allowed": True,
        "selected_provider_family": "",
        "selected_adapter_id": "",
        "adapter_display_name": "",
        "adapter_capabilities": dict(_SAFE_CAPABILITIES),
        "decision_reason": reason,
    }


def _coerce_non_negative_int(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("token values must be non-negative integers")
    return value


def _is_public_opaque_subject_id(value: str) -> bool:
    if not value or len(value) > 128 or any(character.isspace() for character in value):
        return False

    lowered = value.lower()
    return not any(fragment in lowered for fragment in _UNSAFE_SUBJECT_FRAGMENTS)
