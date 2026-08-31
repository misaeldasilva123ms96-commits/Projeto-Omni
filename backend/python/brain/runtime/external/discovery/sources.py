"""Closed discovery-source declarations, isolated from executable providers."""

from brain.runtime.external.models import ExternalAPIDefinition, RedirectPolicy
from brain.runtime.external.registry import ExternalAPIRegistry

APIS_GURU_ID = "discovery_apis_guru"
PUBLIC_APIS_ID = "discovery_public_apis"


def apis_guru_definition() -> ExternalAPIDefinition:
    return ExternalAPIDefinition(
        api_id=APIS_GURU_ID,
        name="APIs.guru discovery catalog",
        description="Untrusted discovery-only API directory metadata",
        base_url="https://api.apis.guru",
        allowed_hosts=frozenset({"api.apis.guru"}),
        allowed_methods=frozenset({"GET"}),
        allowed_paths=frozenset({"/v2/list.json"}),
        max_response_bytes=16 * 1024 * 1024,
        redirect_policy=RedirectPolicy.DENY,
        cache_ttl_seconds=86_400,
        max_attempts=2,
        rate_limit_requests=2,
        rate_limit_window_seconds=60,
        enabled=True,
        provenance="APIs.guru community catalog; discovery metadata only",
    )


def public_apis_definition() -> ExternalAPIDefinition:
    return ExternalAPIDefinition(
        api_id=PUBLIC_APIS_ID,
        name="public-apis discovery catalog",
        description="Untrusted discovery-only README catalog metadata",
        base_url="https://api.github.com",
        allowed_hosts=frozenset({"api.github.com"}),
        allowed_methods=frozenset({"GET"}),
        allowed_paths=frozenset({"/repos/public-apis/public-apis/contents/README.md"}),
        max_response_bytes=4 * 1024 * 1024,
        redirect_policy=RedirectPolicy.DENY,
        cache_ttl_seconds=86_400,
        max_attempts=1,
        rate_limit_requests=1,
        rate_limit_window_seconds=60,
        enabled=True,
        provenance="public-apis repository catalog; discovery metadata only",
    )


def build_discovery_source_registry() -> ExternalAPIRegistry:
    registry = ExternalAPIRegistry()
    registry.register(apis_guru_definition())
    registry.register(public_apis_definition())
    return registry
