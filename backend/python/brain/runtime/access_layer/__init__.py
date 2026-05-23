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
from .provider_registry import (
    PROVIDER_REGISTRY_VERSION,
    ProviderAdapterMetadata,
    UnknownProviderFamilyError,
    build_public_provider_adapter_snapshot,
    get_provider_adapter,
    list_provider_adapters,
    list_public_provider_adapters,
    validate_router_decision_adapter,
)
from .public_access_snapshot import (
    PUBLIC_ACCESS_SNAPSHOT_VERSION,
    PublicAccessSnapshot,
    build_public_access_snapshot,
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
    "PROVIDER_REGISTRY_VERSION",
    "PROVIDER_ROUTER_VERSION",
    "TOKEN_QUOTA_VERSION",
    "PLAN_POLICY_VERSION",
    "PUBLIC_ACCESS_SNAPSHOT_VERSION",
    "InvalidTokenQuotaError",
    "PlanMode",
    "PlanPolicy",
    "ProviderMode",
    "ProviderAdapterMetadata",
    "ProviderRoutingDecision",
    "PublicAccessSnapshot",
    "TokenQuotaSnapshot",
    "ToolAccessMode",
    "UnknownProviderFamilyError",
    "build_public_provider_adapter_snapshot",
    "build_provider_routing_decision",
    "build_public_quota_snapshot",
    "build_public_plan_policy",
    "build_public_provider_routing_decision",
    "build_public_access_snapshot",
    "build_token_quota_snapshot",
    "calculate_quota_remaining",
    "calculate_tokens_total",
    "get_provider_adapter",
    "is_quota_exceeded",
    "list_provider_adapters",
    "list_public_provider_adapters",
    "resolve_plan_policy",
    "validate_router_decision_adapter",
    "validate_max_input_tokens",
    "validate_max_output_tokens",
]
