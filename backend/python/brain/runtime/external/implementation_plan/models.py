"""Immutable, non-executable contracts for static provider implementation analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeCapabilityProfile:
    profile_version: str
    query_parameters: str
    path_request: str
    request_form_urlencoded: str
    arbitrary_json_request_body: str
    multipart_request_body: str
    binary_upload: str
    cookie_parameters: str
    arbitrary_api_header_parameters: str
    governed_auth_header_injection: str
    json_response: str
    non_json_response: str
    binary_response: str
    streaming_response: str
    exact_allowed_paths: str
    closed_maintainer_owned_safe_path_template: str
    arbitrary_openapi_path_template: str
    generated_plan_redirect_policy: str
    automatic_retry_method: str
    external_api_request_fields: tuple[str, ...]
    external_api_definition_fields: tuple[str, ...]
    authentication_type_values: tuple[str, ...]
    safe_path_template_values: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ServerPlan:
    scheme: str
    hostname: str
    port: int | None
    base_path: str
    base_url_origin: str


@dataclass(frozen=True, slots=True)
class SecuritySchemePlan:
    name: str
    scheme_type: str
    location: str | None
    http_scheme: str | None
    oauth_flows: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExternalAPIDefinitionFieldPlan:
    field_name: str
    status: str
    design_metadata: str | None = None


@dataclass(frozen=True, slots=True)
class OperationRuntimeCompatibility:
    operation_key: str
    method: str
    effective_path: str
    path_classification: str
    path_status: str
    request_status: str
    response_status: str
    auth_status: str
    parameter_locations: tuple[str, ...]
    request_content_types: tuple[str, ...]
    response_content_types: tuple[str, ...]
    mutating_signal: bool
    security_mode: str
    security_requirement_count: int
    anonymous_security_option_present: bool
    compatibility_issues: tuple[str, ...]
    required_runtime_extensions: tuple[str, ...]
    required_maintainer_decisions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompatibilitySummary:
    compatible_operations: int
    potentially_compatible_operations: int
    operations_requiring_maintainer_decision: int
    operations_requiring_runtime_extension: int
    unsupported_operations: int
    unresolved_gap_count: int
    runtime_extension_count: int
    unsupported_surface_count: int


@dataclass(frozen=True, slots=True)
class StaticProviderImplementationPlan:
    implementation_plan_id: str
    implementation_plan_format_version: str
    runtime_capability_profile_version: str
    runtime_capability_profile_sha256: str
    scaffold_id: str
    scaffold_format_version: str
    approval_id: str
    proposal_id: str
    proposal_format_version: str
    candidate_id: str
    canonical_schema_sha256: str
    proposal_snapshot_sha256: str
    server: ServerPlan
    provider_definition_fields: tuple[ExternalAPIDefinitionFieldPlan, ...]
    security_schemes: tuple[SecuritySchemePlan, ...]
    operation_compatibility: tuple[OperationRuntimeCompatibility, ...]
    risk_signals: tuple[str, ...]
    review_blockers: tuple[str, ...]
    implementation_gaps: tuple[str, ...]
    excluded_scopes: tuple[str, ...]
    compatibility_summary: CompatibilitySummary
    required_initial_enabled_state: bool = field(default=False, init=False)
    required_redirect_policy: str = field(default="deny", init=False)
    non_get_retry_assumption: str = field(default="none", init=False)
    plan_state: str = field(default="static_design_analysis_only", init=False)
    source_code_generation_authorized: bool = field(default=False, init=False)
    execution_authorized: bool = field(default=False, init=False)
    registration_authorized: bool = field(default=False, init=False)
    network_authority: bool = field(default=False, init=False)
    tool_registration_authorized: bool = field(default=False, init=False)
    runtime_activation_authorized: bool = field(default=False, init=False)
    credential_creation_authorized: bool = field(default=False, init=False)
    feature_gate_creation_authorized: bool = field(default=False, init=False)
    provider_definition_creation_authorized: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
