"""Typed declarations for governed external API candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping

_API_ID = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
_DICTIONARY_PATH = re.compile(r"^/api/v2/entries/en/[A-Za-z]+(?:['-][A-Za-z]+)*$")


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


class SafePathTemplate(StrEnum):
    """Closed, maintainer-owned path authorities; never caller-defined patterns."""

    FREE_DICTIONARY_ENGLISH_WORD = "free_dictionary_english_word"

    def matches(self, path: str) -> bool:
        if self is SafePathTemplate.FREE_DICTIONARY_ENGLISH_WORD:
            return _DICTIONARY_PATH.fullmatch(path) is not None
        return False


@dataclass(frozen=True, slots=True)
class ExternalAPIDefinition:
    api_id: str
    name: str
    description: str
    base_url: str
    allowed_hosts: frozenset[str]
    allowed_methods: frozenset[str]
    allowed_paths: frozenset[str]
    allowed_path_templates: frozenset[SafePathTemplate] = field(default_factory=frozenset)
    auth_type: AuthenticationType = AuthenticationType.NONE
    requires_network: bool = True
    risk_level: RiskLevel = RiskLevel.MEDIUM
    estimated_cost: str = "unknown"
    latency_class: LatencyClass = LatencyClass.VARIABLE
    timeout_seconds: float = 10.0
    max_response_bytes: int = 1_000_000
    redirect_policy: RedirectPolicy = RedirectPolicy.DENY
    cache_ttl_seconds: int | None = None
    max_attempts: int = 2
    rate_limit_requests: int = 30
    rate_limit_window_seconds: float = 60.0
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
        if (
            not self.allowed_hosts
            or not self.allowed_methods
            or not (self.allowed_paths or self.allowed_path_templates)
        ):
            raise ValueError("allowed hosts, methods, and paths must not be empty")
        if any(
            not isinstance(item, str) or not item.strip()
            for item in self.allowed_hosts | self.allowed_methods | self.allowed_paths
        ):
            raise ValueError("allowed hosts, methods, and paths must be non-empty strings")
        if any(not path.startswith("/") or path.startswith("//") for path in self.allowed_paths):
            raise ValueError("allowed paths must be absolute-path references")
        if self.timeout_seconds <= 0 or self.max_response_bytes <= 0:
            raise ValueError("timeout and response limit must be positive")
        if self.cache_ttl_seconds is not None and self.cache_ttl_seconds < 0:
            raise ValueError("cache TTL must be non-negative")
        if not 1 <= self.max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        if self.rate_limit_requests <= 0 or self.rate_limit_window_seconds <= 0:
            raise ValueError("rate limit values must be positive")


@dataclass(frozen=True, slots=True)
class ExternalAPIRequest:
    api_id: str
    method: str
    path: str
    query: Mapping[str, str | int | float | tuple[str, ...]] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.api_id.strip() or not self.method.strip():
            raise ValueError("api_id and method are required")
        if not self.path.startswith("/") or self.path.startswith("//") or "://" in self.path:
            raise ValueError("path must be an absolute-path reference without a host")
        allowed_headers = {"accept", "user-agent"}
        if any(str(name).strip().lower() not in allowed_headers for name in self.headers):
            raise ValueError("request contains a non-allowlisted header")
        if any(
            "\r" in str(value) or "\n" in str(value) or "\x00" in str(value)
            for value in self.headers.values()
        ):
            raise ValueError("request contains an unsafe header value")


@dataclass(frozen=True, slots=True)
class ExternalAPIResponse:
    status_code: int
    data: object
    provenance: Mapping[str, object]
