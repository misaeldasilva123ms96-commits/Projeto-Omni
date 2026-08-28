"""Deny-by-default validation for future outbound external API requests."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlsplit

from brain.runtime.external.config import external_api_enabled
from brain.runtime.external.models import AuthenticationType, ExternalAPIDefinition


class ExternalAPIPolicyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExternalAPIPolicyDecision:
    allowed: bool
    reason: str


def _normalize_host(host: str) -> str:
    return str(host or "").strip().lower().rstrip(".")


def _validate_url(url: str, allowed_hosts: frozenset[str]) -> str:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise ExternalAPIPolicyError("https_required")
    if parsed.username is not None or parsed.password is not None:
        raise ExternalAPIPolicyError("embedded_credentials_denied")
    host = _normalize_host(parsed.hostname or "")
    if not host:
        raise ExternalAPIPolicyError("host_required")
    if host == "localhost" or host.endswith(".localhost"):
        raise ExternalAPIPolicyError("localhost_denied")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
        or address.is_multicast
    ):
        raise ExternalAPIPolicyError("non_public_ip_denied")
    normalized_allowed = {_normalize_host(item) for item in allowed_hosts}
    if host not in normalized_allowed:
        raise ExternalAPIPolicyError("host_not_allowlisted")
    return host


def validate_api_definition(definition: ExternalAPIDefinition) -> None:
    _validate_url(definition.base_url, definition.allowed_hosts)
    methods = {item.strip().upper() for item in definition.allowed_methods}
    if not methods or any(not item.isalpha() for item in methods):
        raise ExternalAPIPolicyError("invalid_allowed_methods")
    if definition.auth_type is AuthenticationType.UNKNOWN:
        raise ExternalAPIPolicyError("unknown_auth_denied")


class ExternalAPIPolicy:
    def __init__(self, registry: object) -> None:
        self._registry = registry

    def evaluate(
        self,
        *,
        api_id: str,
        endpoint: str,
        method: str,
        feature_enabled: bool | None = None,
    ) -> ExternalAPIPolicyDecision:
        if not (external_api_enabled() if feature_enabled is None else feature_enabled):
            return ExternalAPIPolicyDecision(False, "external_api_disabled")
        definition = self._registry.get(api_id)
        if definition is None:
            return ExternalAPIPolicyDecision(False, "unknown_api")
        if not definition.enabled:
            return ExternalAPIPolicyDecision(False, "api_disabled")
        if definition.auth_type is AuthenticationType.UNKNOWN:
            return ExternalAPIPolicyDecision(False, "unknown_auth_denied")
        normalized_method = str(method or "").strip().upper()
        if normalized_method not in {item.upper() for item in definition.allowed_methods}:
            return ExternalAPIPolicyDecision(False, "method_not_allowed")
        try:
            _validate_url(endpoint, definition.allowed_hosts)
        except ExternalAPIPolicyError as exc:
            return ExternalAPIPolicyDecision(False, str(exc))
        if urlsplit(endpoint).path not in definition.allowed_paths:
            return ExternalAPIPolicyDecision(False, "path_not_allowed")
        return ExternalAPIPolicyDecision(True, "allowed")
