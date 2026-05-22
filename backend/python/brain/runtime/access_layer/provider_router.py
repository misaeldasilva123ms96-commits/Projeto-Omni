from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .plan_policy import PlanMode, ProviderMode, resolve_plan_policy
from .token_quota import TokenQuotaSnapshot, build_token_quota_snapshot


PROVIDER_ROUTER_VERSION = "provider_router_v1"

PROVIDER_FAMILY_BY_MODE: dict[tuple[PlanMode, ProviderMode], str] = {
    (PlanMode.FREE, ProviderMode.EXPERIMENTAL_FREE): "experimental_free_provider",
    (PlanMode.BYOK, ProviderMode.USER_KEY): "user_supplied_provider",
    (PlanMode.PRO, ProviderMode.MANAGED): "managed_provider",
    (PlanMode.INTERNAL, ProviderMode.INTERNAL): "internal_provider",
}


@dataclass(frozen=True, slots=True)
class ProviderRoutingDecision:
    plan_mode: PlanMode
    provider_mode: ProviderMode
    selected_provider_family: str
    quota_allowed: bool
    quota_exceeded: bool
    input_allowed: bool
    output_allowed: bool
    routing_allowed: bool
    fallback_allowed: bool
    decision_reason: str
    public_safe_snapshot: dict[str, Any]

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "router_version": PROVIDER_ROUTER_VERSION,
            "plan_mode": self.plan_mode.value,
            "provider_mode": self.provider_mode.value,
            "selected_provider_family": self.selected_provider_family,
            "quota_allowed": self.quota_allowed,
            "quota_exceeded": self.quota_exceeded,
            "input_allowed": self.input_allowed,
            "output_allowed": self.output_allowed,
            "routing_allowed": self.routing_allowed,
            "fallback_allowed": self.fallback_allowed,
            "decision_reason": self.decision_reason,
            "public_safe_snapshot": dict(self.public_safe_snapshot),
        }


def build_provider_routing_decision(
    *,
    plan_mode: str | PlanMode,
    subject_id: str,
    tokens_in: int,
    tokens_out: int,
    usage_date: str,
    policy_overrides: dict[str, Any] | None = None,
) -> ProviderRoutingDecision:
    policy = resolve_plan_policy(plan_mode, overrides=policy_overrides)
    quota = build_token_quota_snapshot(
        plan_mode=policy.plan_mode,
        subject_id=subject_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        usage_date=usage_date,
        policy_overrides=policy_overrides,
    )
    provider_family = PROVIDER_FAMILY_BY_MODE[(policy.plan_mode, policy.provider_mode)]
    quota_allowed = not quota.quota_exceeded
    input_allowed = not quota.input_limit_exceeded
    output_allowed = not quota.output_limit_exceeded
    routing_allowed = quota_allowed and input_allowed and output_allowed
    return ProviderRoutingDecision(
        plan_mode=policy.plan_mode,
        provider_mode=policy.provider_mode,
        selected_provider_family=provider_family,
        quota_allowed=quota_allowed,
        quota_exceeded=quota.quota_exceeded,
        input_allowed=input_allowed,
        output_allowed=output_allowed,
        routing_allowed=routing_allowed,
        fallback_allowed=not routing_allowed,
        decision_reason=_decision_reason(
            quota_allowed=quota_allowed,
            input_allowed=input_allowed,
            output_allowed=output_allowed,
        ),
        public_safe_snapshot=_public_quota_snapshot(quota),
    )


def build_public_provider_routing_decision(
    *,
    plan_mode: str | PlanMode,
    subject_id: str,
    tokens_in: int,
    tokens_out: int,
    usage_date: str,
    policy_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_provider_routing_decision(
        plan_mode=plan_mode,
        subject_id=subject_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        usage_date=usage_date,
        policy_overrides=policy_overrides,
    ).as_public_dict()


def _decision_reason(
    *,
    quota_allowed: bool,
    input_allowed: bool,
    output_allowed: bool,
) -> str:
    if not quota_allowed:
        return "quota_exceeded"
    if not input_allowed:
        return "input_limit_exceeded"
    if not output_allowed:
        return "output_limit_exceeded"
    return "routing_allowed"


def _public_quota_snapshot(quota: TokenQuotaSnapshot) -> dict[str, Any]:
    return quota.as_public_dict()
