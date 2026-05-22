"""Access Layer foundation contracts."""

from .plan_policy import (
    PLAN_POLICY_VERSION,
    PlanMode,
    PlanPolicy,
    ProviderMode,
    ToolAccessMode,
    build_public_plan_policy,
    resolve_plan_policy,
)
from .provider_router import (
    PROVIDER_ROUTER_VERSION,
    ProviderRoutingDecision,
    build_provider_routing_decision,
    build_public_provider_routing_decision,
)
from .token_quota import (
    TOKEN_QUOTA_VERSION,
    InvalidTokenQuotaError,
    TokenQuotaSnapshot,
    build_public_quota_snapshot,
    build_token_quota_snapshot,
    calculate_quota_remaining,
    calculate_tokens_total,
    is_quota_exceeded,
    validate_max_input_tokens,
    validate_max_output_tokens,
)

__all__ = [
    "PROVIDER_ROUTER_VERSION",
    "TOKEN_QUOTA_VERSION",
    "PLAN_POLICY_VERSION",
    "InvalidTokenQuotaError",
    "PlanMode",
    "PlanPolicy",
    "ProviderMode",
    "ProviderRoutingDecision",
    "TokenQuotaSnapshot",
    "ToolAccessMode",
    "build_provider_routing_decision",
    "build_public_quota_snapshot",
    "build_public_plan_policy",
    "build_public_provider_routing_decision",
    "build_token_quota_snapshot",
    "calculate_quota_remaining",
    "calculate_tokens_total",
    "is_quota_exceeded",
    "resolve_plan_policy",
    "validate_max_input_tokens",
    "validate_max_output_tokens",
]
