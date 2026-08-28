"""Maintainer-controlled external provider declarations."""

from __future__ import annotations

from brain.runtime.external.models import (
    AuthenticationType,
    ExternalAPIDefinition,
    LatencyClass,
    RedirectPolicy,
    RiskLevel,
)
from brain.runtime.external.registry import ExternalAPIRegistry


def open_meteo_definition() -> ExternalAPIDefinition:
    return ExternalAPIDefinition(
        api_id="open_meteo",
        name="Open-Meteo",
        description="Development/evaluation/non-commercial weather forecast pilot",
        base_url="https://api.open-meteo.com",
        allowed_hosts=frozenset({"api.open-meteo.com"}),
        allowed_methods=frozenset({"GET"}),
        allowed_paths=frozenset({"/v1/forecast"}),
        auth_type=AuthenticationType.NONE,
        risk_level=RiskLevel.LOW,
        estimated_cost="free/non-commercial-pilot",
        latency_class=LatencyClass.VARIABLE,
        timeout_seconds=8.0,
        max_response_bytes=256_000,
        redirect_policy=RedirectPolicy.DENY,
        cache_ttl_seconds=300,
        max_attempts=2,
        rate_limit_requests=30,
        rate_limit_window_seconds=60.0,
        enabled=True,
        provenance="Weather data by Open-Meteo.com; attribution required; non-commercial pilot",
    )


def build_external_api_registry() -> ExternalAPIRegistry:
    registry = ExternalAPIRegistry()
    registry.register(open_meteo_definition())
    return registry
