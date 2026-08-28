"""Typed declarations for governed external API candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_API_ID = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")


class AuthenticationType(StrEnum):
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH = "oauth"
    UNKNOWN = "unknown"


class RedirectPolicy(StrEnum):
    DENY = "deny"
    SAME_HOST = "same_host"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LatencyClass(StrEnum):
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    VARIABLE = "variable"


@dataclass(frozen=True, slots=True)
class ExternalAPIDefinition:
    api_id: str
    name: str
    description: str
    base_url: str
    allowed_hosts: frozenset[str]
    allowed_methods: frozenset[str]
    auth_type: AuthenticationType = AuthenticationType.NONE
    requires_network: bool = True
    risk_level: RiskLevel = RiskLevel.MEDIUM
    estimated_cost: str = "unknown"
    latency_class: LatencyClass = LatencyClass.VARIABLE
    timeout_seconds: float = 10.0
    max_response_bytes: int = 1_000_000
    redirect_policy: RedirectPolicy = RedirectPolicy.DENY
    cache_ttl_seconds: int | None = None
    enabled: bool = False
    provenance: str = "maintainer_reviewed"

    def __post_init__(self) -> None:
        if not isinstance(self.auth_type, AuthenticationType):
            raise ValueError("auth_type must be an AuthenticationType")
        if not isinstance(self.risk_level, RiskLevel):
            raise ValueError("risk_level must be a RiskLevel")
        if not isinstance(self.latency_class, LatencyClass):
            raise ValueError("latency_class must be a LatencyClass")
        if not isinstance(self.redirect_policy, RedirectPolicy):
            raise ValueError("redirect_policy must be a RedirectPolicy")
        if not _API_ID.fullmatch(self.api_id):
            raise ValueError("api_id must be a stable lowercase identifier")
        if not self.name.strip() or not self.description.strip() or not self.base_url.strip():
            raise ValueError("name, description, and base_url are required")
        if not self.allowed_hosts or not self.allowed_methods:
            raise ValueError("allowed_hosts and allowed_methods must not be empty")
        if any(not isinstance(item, str) or not item.strip() for item in self.allowed_hosts | self.allowed_methods):
            raise ValueError("allowed hosts and methods must be non-empty strings")
        if self.timeout_seconds <= 0 or self.max_response_bytes <= 0:
            raise ValueError("timeout and response limit must be positive")
        if self.cache_ttl_seconds is not None and self.cache_ttl_seconds < 0:
            raise ValueError("cache TTL must be non-negative")
