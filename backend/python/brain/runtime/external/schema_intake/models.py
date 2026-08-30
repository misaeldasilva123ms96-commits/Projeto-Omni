"""Immutable review-only contracts produced by structural schema intake."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ReferenceAudit:
    internal_refs: int = 0
    external_refs: int = 0
    relative_external_refs: int = 0
    absolute_external_refs: int = 0
    unusual_scheme_refs: int = 0
    reference_cycle_resolution: str = "not_performed"


@dataclass(frozen=True, slots=True)
class DeclaredServer:
    scheme: str | None
    hostname: str | None
    port: int | None
    base_path: str
    templated: bool


@dataclass(frozen=True, slots=True)
class SecuritySchemeSummary:
    name: str
    scheme_type: str
    location: str | None = None
    http_scheme: str | None = None
    oauth_flows: tuple[str, ...] = field(default_factory=tuple)
    scope_count: int = 0


@dataclass(frozen=True, slots=True)
class OperationSummary:
    method: str
    path: str
    operation_id: str | None
    summary: str
    deprecated: bool
    parameter_locations: tuple[str, ...]
    request_content_types: tuple[str, ...]
    response_content_types: tuple[str, ...]
    security_override_present: bool
    security_mode: str
    security_requirement_count: int
    anonymous_security_option_present: bool
    mutating_signal: bool


@dataclass(frozen=True, slots=True)
class ProviderDesignProposal:
    proposal_id: str
    proposal_format_version: str
    candidate_id: str
    source_record_id: str
    canonical_schema_sha256: str
    canonical_schema_bytes: int
    catalog_openapi_version: str | None
    detected_openapi_version: str
    title: str
    api_version: str | None
    license_name: str | None
    license_identifier: str | None
    license_url_present: bool
    terms_of_service_present: bool
    declared_servers: tuple[DeclaredServer, ...]
    operation_count: int
    method_counts: tuple[tuple[str, int], ...]
    operations: tuple[OperationSummary, ...]
    operation_details_truncated: bool
    security_schemes: tuple[SecuritySchemeSummary, ...]
    global_security_present: bool
    global_security_requirement_count: int
    reference_audit: ReferenceAudit
    external_resource_counts: tuple[tuple[str, int], ...]
    callback_count: int
    webhook_count: int
    risk_signals: tuple[str, ...]
    issues: tuple[str, ...]
    review_blockers: tuple[str, ...]
    proposal_state: str = field(default="manual_review_required", init=False)
    maintainer_review_required: bool = field(default=True, init=False)
    terms_review_required: bool = field(default=True, init=False)
    security_review_required: bool = field(default=True, init=False)
    privacy_review_required: bool = field(default=True, init=False)
    cost_review_required: bool = field(default=True, init=False)
    rate_limit_review_required: bool = field(default=True, init=False)
    provider_docs_review_required: bool = field(default=True, init=False)
    execution_authorized: bool = field(default=False, init=False)
    registration_authorized: bool = field(default=False, init=False)
    code_generation_authorized: bool = field(default=False, init=False)
    credential_generation_authorized: bool = field(default=False, init=False)
    network_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
