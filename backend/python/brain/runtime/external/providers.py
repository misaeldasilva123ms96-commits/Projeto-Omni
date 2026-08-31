"""Maintainer-controlled external provider declarations."""

from __future__ import annotations

from brain.runtime.external.models import (
    AuthenticationType,
    ExternalAPIDefinition,
    LatencyClass,
    RedirectPolicy,
    RiskLevel,
    SafePathTemplate,
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


def nominatim_definition() -> ExternalAPIDefinition:
    return ExternalAPIDefinition(
        api_id="nominatim",
        name="Nominatim / OpenStreetMap",
        description="Opt-in development/evaluation settlement geocoding pilot",
        base_url="https://nominatim.openstreetmap.org",
        allowed_hosts=frozenset({"nominatim.openstreetmap.org"}),
        allowed_methods=frozenset({"GET"}),
        allowed_paths=frozenset({"/search"}),
        auth_type=AuthenticationType.NONE,
        risk_level=RiskLevel.LOW,
        estimated_cost="free/public-pilot",
        latency_class=LatencyClass.VARIABLE,
        timeout_seconds=8.0,
        max_response_bytes=128_000,
        redirect_policy=RedirectPolicy.DENY,
        cache_ttl_seconds=86_400,
        max_attempts=1,
        rate_limit_requests=1,
        rate_limit_window_seconds=1.1,
        enabled=True,
        provenance=(
            "Geocoding by Nominatim; data © OpenStreetMap contributors, ODbL 1.0; "
            "development/evaluation pilot"
        ),
    )


def build_external_api_registry() -> ExternalAPIRegistry:
    registry = ExternalAPIRegistry()
    registry.register(open_meteo_definition())
    registry.register(nominatim_definition())
    registry.register(frankfurter_definition())
    registry.register(free_dictionary_definition())
    registry.register(urlhaus_definition())
    return registry


def frankfurter_definition() -> ExternalAPIDefinition:
    return ExternalAPIDefinition(
        api_id="frankfurter",
        name="Frankfurter",
        description="Informational currency rates v2",
        base_url="https://api.frankfurter.dev",
        allowed_hosts=frozenset({"api.frankfurter.dev"}),
        allowed_methods=frozenset({"GET"}),
        allowed_paths=frozenset({"/v2/rates"}),
        risk_level=RiskLevel.LOW,
        estimated_cost="free/public",
        timeout_seconds=8.0,
        max_response_bytes=64_000,
        redirect_policy=RedirectPolicy.DENY,
        cache_ttl_seconds=1800,
        max_attempts=2,
        rate_limit_requests=30,
        rate_limit_window_seconds=60.0,
        enabled=True,
        provenance="Rates by Frankfurter; informational and may blend underlying sources",
    )


def free_dictionary_definition() -> ExternalAPIDefinition:
    return ExternalAPIDefinition(
        api_id="free_dictionary",
        name="Free Dictionary API",
        description="Community/experimental English dictionary pilot",
        base_url="https://api.dictionaryapi.dev",
        allowed_hosts=frozenset({"api.dictionaryapi.dev"}),
        allowed_methods=frozenset({"GET"}),
        allowed_paths=frozenset(),
        allowed_path_templates=frozenset({SafePathTemplate.FREE_DICTIONARY_ENGLISH_WORD}),
        risk_level=RiskLevel.LOW,
        estimated_cost="free/community-pilot",
        timeout_seconds=8.0,
        max_response_bytes=256_000,
        redirect_policy=RedirectPolicy.DENY,
        cache_ttl_seconds=604800,
        max_attempts=1,
        rate_limit_requests=10,
        rate_limit_window_seconds=60.0,
        enabled=True,
        provenance="Definitions by Free Dictionary API; community pilot without SLA",
    )


def urlhaus_definition() -> ExternalAPIDefinition:
    return ExternalAPIDefinition(
        api_id="urlhaus",
        name="URLhaus",
        description="Read-only community malware URL reputation pilot",
        base_url="https://urlhaus-api.abuse.ch",
        allowed_hosts=frozenset({"urlhaus-api.abuse.ch"}),
        allowed_methods=frozenset({"POST"}),
        allowed_paths=frozenset({"/v1/url/"}),
        auth_type=AuthenticationType.API_KEY,
        credential_id="urlhaus_auth_key",
        auth_header_name="Auth-Key",
        allowed_form_fields=frozenset({"url"}),
        risk_level=RiskLevel.MEDIUM,
        estimated_cost="community/fair-use-pilot",
        latency_class=LatencyClass.VARIABLE,
        timeout_seconds=8.0,
        max_response_bytes=256_000,
        max_request_body_bytes=4096,
        redirect_policy=RedirectPolicy.DENY,
        cache_ttl_seconds=1800,
        max_attempts=1,
        rate_limit_requests=10,
        rate_limit_window_seconds=60.0,
        enabled=True,
        provenance="URLhaus by abuse.ch/Spamhaus; community fair-use pilot",
    )
