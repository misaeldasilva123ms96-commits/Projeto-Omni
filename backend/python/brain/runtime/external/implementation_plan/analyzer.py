"""Pure offline derivation of runtime compatibility and static implementation plans."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, fields, replace

from brain.runtime.external.approval.manifest import canonical_json_bytes
from brain.runtime.external.approval.models import (
    HumanApprovalManifest,
    NonExecutableProviderScaffold,
)
from brain.runtime.external.approval.scaffold import (
    verify_scaffold_against_approval_and_proposal,
)
from brain.runtime.external.approval.validation import ApprovalError
from brain.runtime.external.models import ExternalAPIDefinition
from brain.runtime.external.schema_intake.models import (
    OperationSummary,
    ProviderDesignProposal,
)

from .capabilities import (
    build_runtime_capability_profile,
    runtime_capability_profile_sha256,
)
from .models import (
    CompatibilitySummary,
    ExternalAPIDefinitionFieldPlan,
    OperationRuntimeCompatibility,
    SecuritySchemePlan,
    ServerPlan,
    StaticProviderImplementationPlan,
)

STATIC_PROVIDER_IMPLEMENTATION_PLAN_FORMAT_VERSION = "static-provider-implementation-plan-v1"
_STATUS_PRIORITY = {
    "compatible": 0,
    "potentially_compatible": 1,
    "maintainer_decision_required": 2,
    "runtime_extension_required": 3,
    "unsupported_current_runtime": 4,
}
_UNRESOLVED_FIELDS = frozenset(
    {
        "api_id",
        "description",
        "risk_level",
        "estimated_cost",
        "latency_class",
        "timeout_seconds",
        "max_response_bytes",
        "cache_ttl_seconds",
        "max_attempts",
        "rate_limit_requests",
        "rate_limit_window_seconds",
        "provenance",
        "credential_id",
        "auth_header_name",
        "max_request_body_bytes",
    }
)
_BASE_GAPS = (
    "adapter_input_schema_required",
    "cache_policy_required",
    "cost_review_value_required",
    "fallback_design_required",
    "feature_gate_design_required",
    "provider_api_id_required",
    "provider_description_required",
    "provenance_text_required",
    "rate_limit_policy_required",
    "response_limit_policy_required",
    "response_normalizer_required",
    "risk_level_decision_required",
    "timeout_policy_required",
)


def build_implementation_plan_id(plan: StaticProviderImplementationPlan) -> str:
    payload = asdict(plan)
    payload.pop("implementation_plan_id")
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def safe_join_paths(base_path: str, operation_path: str) -> str:
    for value in (base_path, operation_path):
        if (
            not isinstance(value, str)
            or not value.startswith("/")
            or "?" in value
            or "#" in value
            or "\\" in value
            or any(part in {".", ".."} for part in value.split("/"))
        ):
            raise ApprovalError("effective_path_invalid")
    if "//" in base_path or "//" in operation_path:
        raise ApprovalError("effective_path_invalid")
    if base_path == "/":
        result = operation_path
    else:
        result = base_path.rstrip("/") + operation_path
    if not result.startswith("/") or "//" in result:
        raise ApprovalError("effective_path_invalid")
    return result


def _max_status(*statuses: str) -> str:
    return max(statuses, key=_STATUS_PRIORITY.__getitem__)


def _request_analysis(operation: OperationSummary) -> tuple[str, set[str], set[str], set[str]]:
    status = "compatible"
    issues: set[str] = set()
    extensions: set[str] = set()
    decisions: set[str] = set()
    locations = set(operation.parameter_locations)
    if "query" in locations:
        status = _max_status(status, "potentially_compatible")
        decisions.add("adapter_input_validation_required")
    if "path" in locations or "{" in operation.path:
        status = _max_status(status, "runtime_extension_required")
        extensions.add("maintainer_owned_safe_path_template")
    if "header" in locations:
        status = _max_status(status, "runtime_extension_required")
        extensions.add("governed_provider_header_surface")
    if "cookie" in locations:
        status = _max_status(status, "unsupported_current_runtime")
        issues.add("cookie_parameters_unsupported")
    if "body" in locations:
        status = _max_status(status, "runtime_extension_required")
        extensions.add("safe_request_body_serializer")
    media = {item.lower() for item in operation.request_content_types}
    if "application/x-www-form-urlencoded" in media or "formData" in locations:
        status = _max_status(status, "potentially_compatible")
        decisions.add("form_field_allowlist_design_required")
    if any(item == "application/json" or item.endswith("+json") for item in media):
        status = _max_status(status, "runtime_extension_required")
        extensions.add("safe_json_request_body_serializer")
    if "multipart/form-data" in media or "file" in locations:
        status = _max_status(status, "unsupported_current_runtime")
        issues.add("multipart_or_file_upload_unsupported")
    known = {"application/x-www-form-urlencoded", "application/json", "multipart/form-data"}
    if any(item not in known and not item.endswith("+json") for item in media):
        status = _max_status(status, "runtime_extension_required")
        extensions.add("request_media_type_support")
    return status, issues, extensions, decisions


def _response_status(operation: OperationSummary) -> tuple[str, set[str], set[str]]:
    media = {item.lower() for item in operation.response_content_types}
    if not media:
        return "maintainer_decision_required", set(), {"response_media_type_review_required"}
    if any(item == "application/json" or item.endswith("+json") for item in media):
        return "potentially_compatible", set(), {"response_adapter_design_required"}
    return "unsupported_current_runtime", {"non_json_response_unsupported"}, set()


def _auth_status(proposal: ProviderDesignProposal) -> tuple[str, set[str], set[str], set[str]]:
    if not proposal.security_schemes:
        return "potentially_compatible", set(), set(), set()
    statuses: list[str] = []
    issues: set[str] = set()
    extensions: set[str] = set()
    decisions: set[str] = set()
    for scheme in proposal.security_schemes:
        kind = scheme.scheme_type
        http = (scheme.http_scheme or "").lower()
        location = (scheme.location or "").lower()
        if kind == "apiKey" and location == "header":
            statuses.append("potentially_compatible")
            decisions.add("credential_design_required")
        elif kind == "apiKey" and location == "query":
            statuses.append("runtime_extension_required")
            extensions.add("query_api_key_authentication")
        elif kind == "apiKey" and location == "cookie":
            statuses.append("unsupported_current_runtime")
            issues.add("cookie_api_key_unsupported")
        elif kind in {"oauth2", "openIdConnect"}:
            statuses.append("runtime_extension_required")
            extensions.add("oauth_authentication_runtime")
        elif kind == "mutualTLS":
            statuses.append("unsupported_current_runtime")
            issues.add("mutual_tls_unsupported")
        elif kind == "basic" or (kind == "http" and http == "basic"):
            statuses.append("runtime_extension_required")
            extensions.add("basic_authentication_runtime")
        elif kind == "http" and http == "bearer":
            statuses.append("maintainer_decision_required")
            decisions.add("bearer_authentication_design_required")
        else:
            statuses.append("unsupported_current_runtime")
            issues.add("unknown_authentication_scheme")
    return _max_status(*statuses), issues, extensions, decisions


def _operation_plan(
    approved, operation: OperationSummary, proposal: ProviderDesignProposal, base_path: str
) -> OperationRuntimeCompatibility:
    effective = safe_join_paths(base_path, approved.path)
    dynamic = "{" in effective or "}" in effective
    path_status = "runtime_extension_required" if dynamic else "compatible"
    issues: set[str] = set()
    extensions = {"maintainer_owned_safe_path_template"} if dynamic else set()
    decisions: set[str] = set()
    request_status, req_issues, req_ext, req_decisions = _request_analysis(operation)
    response_status, response_issues, response_decisions = _response_status(operation)
    auth_status, auth_issues, auth_ext, auth_decisions = _auth_status(proposal)
    issues.update(req_issues | response_issues | auth_issues)
    extensions.update(req_ext | auth_ext)
    decisions.update(req_decisions | response_decisions | auth_decisions)
    if dynamic:
        decisions.add("dynamic_path_template_design_required")
    if "file_upload_surface_present" in proposal.risk_signals:
        request_status = _max_status(request_status, "unsupported_current_runtime")
        issues.add("multipart_or_file_upload_unsupported")
    if approved.mutating_signal:
        decisions.add("mutation_policy_design_required")
    if approved.security_mode == "explicit_empty" or approved.anonymous_security_option_present:
        decisions.add("authentication_semantics_revalidation_required")
        auth_status = _max_status(auth_status, "maintainer_decision_required")
    return OperationRuntimeCompatibility(
        approved.operation_key,
        approved.method,
        effective,
        ("dynamic_path_template_design_required" if dynamic else "exact_path_candidate"),
        path_status,
        request_status,
        response_status,
        auth_status,
        tuple(operation.parameter_locations),
        tuple(operation.request_content_types),
        tuple(operation.response_content_types),
        approved.mutating_signal,
        approved.security_mode,
        approved.security_requirement_count,
        approved.anonymous_security_option_present,
        tuple(sorted(issues)),
        tuple(sorted(extensions)),
        tuple(sorted(decisions)),
    )


def _field_plans(server: ServerPlan, operations) -> tuple[ExternalAPIDefinitionFieldPlan, ...]:
    derived = {
        "base_url": server.base_url_origin,
        "allowed_hosts": server.hostname,
        "allowed_methods": ",".join(sorted({item.method for item in operations})),
        "allowed_paths": ",".join(
            item.effective_path for item in operations if item.path_status == "compatible"
        ),
        "enabled": "false",
        "redirect_policy": "deny",
    }
    plans = []
    for item in fields(ExternalAPIDefinition):
        status = "unresolved"
        metadata = None
        if item.name in derived:
            status, metadata = "design_metadata_only", derived[item.name]
        elif item.name in _UNRESOLVED_FIELDS:
            status = "unresolved"
        else:
            status = "maintainer_decision_required"
        plans.append(ExternalAPIDefinitionFieldPlan(item.name, status, metadata))
    plans.append(ExternalAPIDefinitionFieldPlan("feature_gate", "unresolved", None))
    return tuple(plans)


def _summary(operations, gaps: tuple[str, ...]) -> CompatibilitySummary:
    categories = []
    extensions: set[str] = set()
    unsupported = 0
    for item in operations:
        category = _max_status(
            item.path_status, item.request_status, item.response_status, item.auth_status
        )
        categories.append(category)
        extensions.update(item.required_runtime_extensions)
        unsupported += len(item.compatibility_issues)
    return CompatibilitySummary(
        categories.count("compatible"),
        categories.count("potentially_compatible"),
        categories.count("maintainer_decision_required"),
        categories.count("runtime_extension_required"),
        categories.count("unsupported_current_runtime"),
        len(gaps),
        len(extensions),
        unsupported,
    )


def build_static_provider_implementation_plan(
    scaffold: NonExecutableProviderScaffold,
    approval: HumanApprovalManifest,
    proposal: ProviderDesignProposal,
) -> StaticProviderImplementationPlan:
    verify_scaffold_against_approval_and_proposal(scaffold, approval, proposal)
    profile = build_runtime_capability_profile()
    operation_index = {f"{item.method} {item.path}": item for item in proposal.operations}
    operations = tuple(
        _operation_plan(
            item, operation_index[item.operation_key], proposal, scaffold.server.base_path
        )
        for item in scaffold.operations
    )
    origin = f"{scaffold.server.scheme}://{scaffold.server.hostname}"
    if scaffold.server.port not in (None, 443):
        origin += f":{scaffold.server.port}"
    server = ServerPlan(
        scaffold.server.scheme,
        scaffold.server.hostname,
        scaffold.server.port,
        scaffold.server.base_path,
        origin,
    )
    gaps = set(_BASE_GAPS)
    if proposal.security_schemes:
        gaps.add("credential_design_required")
    excluded = []
    if proposal.callback_count:
        excluded.append("callbacks_implementation_scope_excluded")
    if proposal.webhook_count:
        excluded.append("webhooks_implementation_scope_excluded")
    if "external_refs_present" in proposal.review_blockers:
        excluded.append("external_reference_resolution_deferred")
    gap_tuple = tuple(sorted(gaps))
    plan = StaticProviderImplementationPlan(
        "",
        STATIC_PROVIDER_IMPLEMENTATION_PLAN_FORMAT_VERSION,
        profile.profile_version,
        runtime_capability_profile_sha256(profile),
        scaffold.scaffold_id,
        scaffold.scaffold_format_version,
        approval.approval_id,
        proposal.proposal_id,
        proposal.proposal_format_version,
        proposal.candidate_id,
        proposal.canonical_schema_sha256,
        approval.proposal_snapshot_sha256,
        server,
        _field_plans(server, operations),
        tuple(
            SecuritySchemePlan(
                item.name, item.scheme_type, item.location, item.http_scheme, item.oauth_flows
            )
            for item in proposal.security_schemes
        ),
        operations,
        tuple(scaffold.risk_signals),
        tuple(scaffold.review_blockers),
        gap_tuple,
        tuple(sorted(excluded)),
        _summary(operations, gap_tuple),
    )
    return replace(plan, implementation_plan_id=build_implementation_plan_id(plan))
