from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .plan_policy import PlanMode
from .provider_registry import (
    UnknownProviderFamilyError,
    build_public_provider_adapter_snapshot,
    validate_router_decision_adapter,
)
from .provider_router import ProviderRoutingDecision, build_provider_routing_decision
from .token_quota import calculate_quota_remaining, calculate_tokens_total


PUBLIC_ACCESS_SNAPSHOT_VERSION = "public_access_snapshot_v1"

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


@dataclass(frozen=True, slots=True)
class PublicAccessSnapshot:
    plan_mode: str
    provider_mode: str
    subject_id: str
    usage_date: str
    tokens_in: int
    tokens_out: int
    tokens_total: int
    daily_token_limit: int | None
    quota_remaining: int | None
    quota_exceeded: bool
    input_allowed: bool
    output_allowed: bool
    quota_allowed: bool
    routing_allowed: bool
    fallback_allowed: bool
    selected_provider_family: str
    selected_adapter_id: str
    adapter_display_name: str
    adapter_capabilities: dict[str, bool] = field(default_factory=dict)
    decision_reason: str = "routing_denied"

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "snapshot_version": PUBLIC_ACCESS_SNAPSHOT_VERSION,
            "plan_mode": self.plan_mode,
            "provider_mode": self.provider_mode,
            "subject_id": self.subject_id,
            "usage_date": self.usage_date,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "tokens_total": self.tokens_total,
            "daily_token_limit": self.daily_token_limit,
            "quota_remaining": self.quota_remaining,
            "quota_exceeded": self.quota_exceeded,
            "input_allowed": self.input_allowed,
            "output_allowed": self.output_allowed,
            "quota_allowed": self.quota_allowed,
            "routing_allowed": self.routing_allowed,
            "fallback_allowed": self.fallback_allowed,
            "selected_provider_family": self.selected_provider_family,
            "selected_adapter_id": self.selected_adapter_id,
            "adapter_display_name": self.adapter_display_name,
            "adapter_capabilities": _safe_capabilities(self.adapter_capabilities),
            "decision_reason": self.decision_reason,
        }


def build_public_access_snapshot(
    *,
    plan_mode: str | PlanMode,
    subject_id: str,
    usage_date: str,
    tokens_in: int,
    tokens_out: int,
    existing_daily_tokens: int = 0,
    policy_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_subject_id = str(subject_id or "")
    safe_usage_date = str(usage_date or "")
    safe_plan_mode = _public_plan_mode(plan_mode)

    try:
        _validate_existing_daily_tokens(existing_daily_tokens)
        tokens_total = calculate_tokens_total(tokens_in, tokens_out)
    except ValueError:
        return _fail_closed_snapshot(
            plan_mode=safe_plan_mode,
            subject_id=safe_subject_id,
            usage_date=safe_usage_date,
            tokens_in=_safe_non_negative_int(tokens_in),
            tokens_out=_safe_non_negative_int(tokens_out),
            tokens_total=0,
            decision_reason="invalid_token_usage",
        )

    try:
        decision = build_provider_routing_decision(
            plan_mode=plan_mode,
            subject_id=safe_subject_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            usage_date=safe_usage_date,
            policy_overrides=policy_overrides,
        )
    except ValueError:
        return _fail_closed_snapshot(
            plan_mode=safe_plan_mode,
            subject_id=safe_subject_id,
            usage_date=safe_usage_date,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tokens_total=tokens_total,
            decision_reason="invalid_plan_or_policy",
        )

    quota_snapshot = dict(decision.public_safe_snapshot)
    daily_token_limit = quota_snapshot.get("daily_token_limit")
    daily_usage_total = existing_daily_tokens + tokens_total
    quota_remaining = calculate_quota_remaining(
        daily_token_limit=daily_token_limit,
        tokens_total=daily_usage_total,
    )
    quota_exceeded = (
        False if daily_token_limit is None else daily_usage_total > int(daily_token_limit)
    )
    quota_allowed = not quota_exceeded
    input_allowed = bool(decision.input_allowed)
    output_allowed = bool(decision.output_allowed)
    routing_allowed = bool(decision.routing_allowed and quota_allowed)

    try:
        registry_valid = validate_router_decision_adapter(decision)
        adapter = build_public_provider_adapter_snapshot(decision.selected_provider_family)
    except (UnknownProviderFamilyError, ValueError):
        registry_valid = False
        adapter = {}

    if not registry_valid:
        return _fail_closed_from_decision(
            decision=decision,
            quota_remaining=quota_remaining,
            quota_exceeded=quota_exceeded,
            quota_allowed=quota_allowed,
            decision_reason="provider_registry_mismatch",
        )

    final_reason = _decision_reason(
        base_reason=str(decision.decision_reason or ""),
        quota_allowed=quota_allowed,
        input_allowed=input_allowed,
        output_allowed=output_allowed,
        routing_allowed=routing_allowed,
    )
    return PublicAccessSnapshot(
        plan_mode=decision.plan_mode.value,
        provider_mode=decision.provider_mode.value,
        subject_id=safe_subject_id,
        usage_date=safe_usage_date,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tokens_total=tokens_total,
        daily_token_limit=daily_token_limit,
        quota_remaining=quota_remaining,
        quota_exceeded=quota_exceeded,
        input_allowed=input_allowed,
        output_allowed=output_allowed,
        quota_allowed=quota_allowed,
        routing_allowed=routing_allowed,
        fallback_allowed=not routing_allowed,
        selected_provider_family=str(decision.selected_provider_family or ""),
        selected_adapter_id=str(adapter.get("adapter_id") or ""),
        adapter_display_name=str(adapter.get("display_name") or ""),
        adapter_capabilities=_adapter_capabilities(adapter),
        decision_reason=final_reason,
    ).as_public_dict()


def _fail_closed_from_decision(
    *,
    decision: ProviderRoutingDecision,
    quota_remaining: int | None,
    quota_exceeded: bool,
    quota_allowed: bool,
    decision_reason: str,
) -> dict[str, Any]:
    quota_snapshot = dict(decision.public_safe_snapshot)
    return PublicAccessSnapshot(
        plan_mode=decision.plan_mode.value,
        provider_mode=decision.provider_mode.value,
        subject_id=str(quota_snapshot.get("subject_id") or ""),
        usage_date=str(quota_snapshot.get("usage_date") or ""),
        tokens_in=int(quota_snapshot.get("tokens_in") or 0),
        tokens_out=int(quota_snapshot.get("tokens_out") or 0),
        tokens_total=int(quota_snapshot.get("tokens_total") or 0),
        daily_token_limit=quota_snapshot.get("daily_token_limit"),
        quota_remaining=quota_remaining,
        quota_exceeded=quota_exceeded,
        input_allowed=bool(decision.input_allowed),
        output_allowed=bool(decision.output_allowed),
        quota_allowed=quota_allowed,
        routing_allowed=False,
        fallback_allowed=True,
        selected_provider_family=str(decision.selected_provider_family or ""),
        selected_adapter_id="",
        adapter_display_name="",
        adapter_capabilities=_SAFE_CAPABILITIES,
        decision_reason=decision_reason,
    ).as_public_dict()


def _fail_closed_snapshot(
    *,
    plan_mode: str,
    subject_id: str,
    usage_date: str,
    tokens_in: int,
    tokens_out: int,
    tokens_total: int,
    decision_reason: str,
) -> dict[str, Any]:
    return PublicAccessSnapshot(
        plan_mode=plan_mode,
        provider_mode="",
        subject_id=subject_id,
        usage_date=usage_date,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tokens_total=tokens_total,
        daily_token_limit=None,
        quota_remaining=None,
        quota_exceeded=False,
        input_allowed=False,
        output_allowed=False,
        quota_allowed=False,
        routing_allowed=False,
        fallback_allowed=True,
        selected_provider_family="",
        selected_adapter_id="",
        adapter_display_name="",
        adapter_capabilities=_SAFE_CAPABILITIES,
        decision_reason=decision_reason,
    ).as_public_dict()


def _adapter_capabilities(adapter: dict[str, Any]) -> dict[str, bool]:
    return _safe_capabilities(
        {
            "supports_streaming": bool(adapter.get("supports_streaming", False)),
            "supports_tools": bool(adapter.get("supports_tools", False)),
            "supports_files": bool(adapter.get("supports_files", False)),
            "supports_long_context": bool(adapter.get("supports_long_context", False)),
            "supports_sensitive_tools": bool(adapter.get("supports_sensitive_tools", False)),
            "is_experimental": bool(adapter.get("is_experimental", False)),
            "is_user_key_required": bool(adapter.get("is_user_key_required", False)),
            "is_managed": bool(adapter.get("is_managed", False)),
            "is_internal": bool(adapter.get("is_internal", False)),
        }
    )


def _safe_capabilities(values: dict[str, Any]) -> dict[str, bool]:
    return {key: bool(values.get(key, False)) for key in _SAFE_CAPABILITIES}


def _decision_reason(
    *,
    base_reason: str,
    quota_allowed: bool,
    input_allowed: bool,
    output_allowed: bool,
    routing_allowed: bool,
) -> str:
    if not quota_allowed:
        return "quota_exceeded"
    if not input_allowed:
        return "input_limit_exceeded"
    if not output_allowed:
        return "output_limit_exceeded"
    if not routing_allowed:
        return "routing_denied"
    return base_reason or "routing_allowed"


def _public_plan_mode(plan_mode: str | PlanMode) -> str:
    if isinstance(plan_mode, PlanMode):
        return plan_mode.value
    return str(plan_mode or "").strip().lower()


def _validate_existing_daily_tokens(value: int) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError("existing_daily_tokens must be a non-negative integer")


def _safe_non_negative_int(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else 0
