from __future__ import annotations

import sys
from dataclasses import fields, replace
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from approval_fixtures import proposal, with_operations  # noqa: E402
from brain.runtime.external.implementation_plan import (  # noqa: E402
    STATIC_PROVIDER_IMPLEMENTATION_PLAN_FORMAT_VERSION,
    build_runtime_capability_profile,
    build_static_provider_implementation_plan,
    runtime_capability_profile_sha256,
)
from brain.runtime.external.models import (  # noqa: E402
    AuthenticationType,
    ExternalAPIDefinition,
    ExternalAPIRequest,
    SafePathTemplate,
)
from brain.runtime.external.schema_intake.models import SecuritySchemeSummary  # noqa: E402
from test_implementation_plan import chain  # noqa: E402


def operation_plan(operation, *, schemes=(), selected=None, mutation=(), security=()):
    value = with_operations(proposal(), operation)
    value = replace(value, security_schemes=tuple(schemes))
    key = selected or f"{operation.method} {operation.path}"
    value, approval, scaffold = chain(value, selected=(key,), mutation=mutation, security=security)
    return build_static_provider_implementation_plan(
        scaffold, approval, value
    ).operation_compatibility[0]


def full_plan(operation, *, schemes=(), proposal_changes=None, selected=None, security=()):
    value = with_operations(proposal(), operation)
    value = replace(value, security_schemes=tuple(schemes), **(proposal_changes or {}))
    key = selected or f"{operation.method} {operation.path}"
    value, approval, scaffold = chain(value, selected=(key,), security=security)
    return build_static_provider_implementation_plan(scaffold, approval, value)


def test_runtime_profile_fingerprints_current_contracts() -> None:
    profile = build_runtime_capability_profile()
    assert profile.external_api_request_fields == tuple(
        item.name for item in fields(ExternalAPIRequest)
    )
    assert profile.external_api_definition_fields == tuple(
        item.name for item in fields(ExternalAPIDefinition)
    )
    assert profile.authentication_type_values == tuple(item.value for item in AuthenticationType)
    assert profile.safe_path_template_values == tuple(item.value for item in SafePathTemplate)
    assert (
        runtime_capability_profile_sha256(profile)
        == "421adf1db318749e2c0a6a0ba8de3e8eb43057c7660c510917ed9360f6856396"
    )
    assert STATIC_PROVIDER_IMPLEMENTATION_PLAN_FORMAT_VERSION.endswith("-v2")
    assert profile.arbitrary_json_request_body == "unsupported"
    assert profile.generated_plan_redirect_policy == "deny"
    assert profile.automatic_retry_method == "GET"


def test_dynamic_path_requires_maintainer_owned_template_but_creates_none() -> None:
    operation = replace(proposal().operations[0], path="/users/{id}", parameter_locations=("path",))
    result = operation_plan(operation)
    assert result.path_classification == "dynamic_path_template_design_required"
    assert result.path_status == "runtime_extension_required"
    assert "maintainer_owned_safe_path_template" in result.required_runtime_extensions
    assert len(SafePathTemplate) == 1


@pytest.mark.parametrize(
    ("locations", "request_media", "status", "marker"),
    (
        (("query",), (), "potentially_compatible", "adapter_input_validation_required"),
        (("header",), (), "runtime_extension_required", "governed_provider_header_surface"),
        (("cookie",), (), "unsupported_current_runtime", "cookie_parameters_unsupported"),
        (
            (),
            ("application/json",),
            "runtime_extension_required",
            "safe_json_request_body_serializer",
        ),
        (
            ("formData",),
            ("application/x-www-form-urlencoded",),
            "potentially_compatible",
            "form_field_allowlist_design_required",
        ),
        (
            (),
            ("multipart/form-data",),
            "unsupported_current_runtime",
            "multipart_or_file_upload_unsupported",
        ),
    ),
)
def test_request_compatibility_matrix(locations, request_media, status, marker) -> None:
    operation = replace(
        proposal().operations[0],
        parameter_locations=locations,
        request_content_types=request_media,
    )
    result = operation_plan(operation)
    assert result.request_status == status
    assert marker in (
        result.compatibility_issues
        + result.required_runtime_extensions
        + result.required_maintainer_decisions
    )


@pytest.mark.parametrize(
    ("media", "status"),
    (
        (("application/json",), "potentially_compatible"),
        (("application/problem+json",), "potentially_compatible"),
        (("text/plain",), "unsupported_current_runtime"),
        ((), "maintainer_decision_required"),
    ),
)
def test_response_compatibility_matrix(media, status) -> None:
    operation = replace(proposal().operations[0], response_content_types=media)
    assert operation_plan(operation).response_status == status


@pytest.mark.parametrize(
    ("scheme", "status", "marker"),
    (
        (
            SecuritySchemeSummary("key", "apiKey", "header"),
            "potentially_compatible",
            "credential_design_required",
        ),
        (
            SecuritySchemeSummary("key", "apiKey", "query"),
            "runtime_extension_required",
            "query_api_key_authentication",
        ),
        (
            SecuritySchemeSummary("key", "apiKey", "cookie"),
            "unsupported_current_runtime",
            "cookie_api_key_unsupported",
        ),
        (
            SecuritySchemeSummary("basic", "http", http_scheme="basic"),
            "runtime_extension_required",
            "basic_authentication_runtime",
        ),
        (
            SecuritySchemeSummary("basic", "basic"),
            "runtime_extension_required",
            "basic_authentication_runtime",
        ),
        (
            SecuritySchemeSummary("bearer", "http", http_scheme="bearer"),
            "maintainer_decision_required",
            "bearer_authentication_design_required",
        ),
        (
            SecuritySchemeSummary("oauth", "oauth2"),
            "runtime_extension_required",
            "oauth_authentication_runtime",
        ),
        (
            SecuritySchemeSummary("oidc", "openIdConnect"),
            "runtime_extension_required",
            "oauth_authentication_runtime",
        ),
        (
            SecuritySchemeSummary("mtls", "mutualTLS"),
            "unsupported_current_runtime",
            "mutual_tls_unsupported",
        ),
        (
            SecuritySchemeSummary("mystery", "unknown"),
            "unsupported_current_runtime",
            "unknown_authentication_scheme",
        ),
    ),
)
def test_declared_provider_security_scheme_compatibility_matrix(scheme, status, marker) -> None:
    plan = full_plan(proposal().operations[0], schemes=(scheme,))
    result = plan.security_schemes[0]
    assert result.runtime_status == status
    assert marker in (
        result.compatibility_issues
        + result.required_runtime_extensions
        + result.required_maintainer_decisions
    )


def test_unused_declared_schemes_do_not_poison_operation_auth() -> None:
    schemes = (
        SecuritySchemeSummary("key", "apiKey", "header"),
        SecuritySchemeSummary("oauth", "oauth2"),
        SecuritySchemeSummary("mtls", "mutualTLS"),
    )
    plan = full_plan(proposal().operations[0], schemes=schemes)
    operation = plan.operation_compatibility[0]
    assert operation.auth_status == "potentially_compatible"
    assert operation.required_runtime_extensions == ()
    assert operation.compatibility_issues == ()
    assert (
        "no_authentication_requirement_declared_revalidation_required"
        in operation.required_maintainer_decisions
    )
    assert [item.runtime_status for item in plan.security_schemes] == [
        "potentially_compatible",
        "runtime_extension_required",
        "unsupported_current_runtime",
    ]
    assert "declared_security_scheme_review_required" in plan.implementation_gaps
    assert "credential_design_required" not in plan.implementation_gaps


@pytest.mark.parametrize(
    "scheme", (SecuritySchemeSummary("mtls", "mutualTLS"), SecuritySchemeSummary("oauth", "oauth2"))
)
def test_explicit_empty_does_not_inherit_declared_scheme(scheme) -> None:
    operation = replace(proposal().operations[0], security_mode="explicit_empty")
    plan = full_plan(operation, schemes=(scheme,), security=("GET /pets",))
    result = plan.operation_compatibility[0]
    assert result.auth_status == "maintainer_decision_required"
    assert "authentication_semantics_revalidation_required" in result.required_maintainer_decisions
    assert not result.required_runtime_extensions
    assert not result.compatibility_issues


def test_optional_anonymous_does_not_inherit_declared_oauth() -> None:
    operation = replace(
        proposal().operations[0],
        security_mode="explicit_optional_anonymous",
        anonymous_security_option_present=True,
    )
    plan = full_plan(
        operation, schemes=(SecuritySchemeSummary("oauth", "oauth2"),), security=("GET /pets",)
    )
    result = plan.operation_compatibility[0]
    assert result.auth_status == "maintainer_decision_required"
    assert "oauth_authentication_runtime" not in result.required_runtime_extensions


def test_inherited_global_security_binding_is_unresolved() -> None:
    plan = full_plan(
        proposal().operations[0],
        schemes=(SecuritySchemeSummary("key", "apiKey", "header"),),
        proposal_changes={"global_security_present": True, "global_security_requirement_count": 1},
    )
    result = plan.operation_compatibility[0]
    assert result.auth_status == "maintainer_decision_required"
    assert "global_security_scheme_binding_unresolved" in result.required_maintainer_decisions
    assert plan.global_security_present is True
    assert plan.global_security_requirement_count == 1


def test_explicit_security_requirement_binding_is_unresolved() -> None:
    operation = replace(
        proposal().operations[0],
        security_mode="explicit_requirements",
        security_requirement_count=1,
    )
    result = full_plan(operation).operation_compatibility[0]
    assert result.auth_status == "maintainer_decision_required"
    assert "operation_security_scheme_binding_unresolved" in result.required_maintainer_decisions


def test_global_file_signal_does_not_poison_clean_selected_operation() -> None:
    operation = replace(proposal().operations[0], request_content_types=())
    plan = full_plan(
        operation,
        proposal_changes={
            "risk_signals": proposal().risk_signals + ("file_upload_surface_present",)
        },
    )
    result = plan.operation_compatibility[0]
    assert result.request_status != "unsupported_current_runtime"
    assert "multipart_or_file_upload_unsupported" not in result.compatibility_issues
    assert "file_upload_operation_attribution_unresolved" in plan.implementation_gaps


def test_octet_stream_remains_extension_with_global_attribution_gap() -> None:
    operation = replace(
        proposal().operations[0], request_content_types=("application/octet-stream",)
    )
    plan = full_plan(
        operation,
        proposal_changes={
            "risk_signals": proposal().risk_signals + ("file_upload_surface_present",)
        },
    )
    result = plan.operation_compatibility[0]
    assert result.request_status == "runtime_extension_required"
    assert "request_media_type_support" in result.required_runtime_extensions
    assert "multipart_or_file_upload_unsupported" not in result.compatibility_issues
    assert "file_upload_operation_attribution_unresolved" in plan.implementation_gaps


def test_unselected_upload_does_not_poison_selected_get() -> None:
    get = replace(proposal().operations[0], path="/health", request_content_types=())
    upload = replace(
        proposal().operations[0],
        method="POST",
        path="/upload",
        request_content_types=("multipart/form-data",),
        mutating_signal=True,
    )
    value = with_operations(proposal(), get, upload)
    value = replace(value, risk_signals=value.risk_signals + ("file_upload_surface_present",))
    value, approval, scaffold = chain(value, selected=("GET /health",))
    plan = build_static_provider_implementation_plan(scaffold, approval, value)
    assert plan.operation_compatibility[0].request_status != "unsupported_current_runtime"
    assert "file_upload_operation_attribution_unresolved" in plan.implementation_gaps


def test_mutation_and_anonymous_security_remain_maintainer_decisions() -> None:
    operation = replace(
        proposal().operations[0],
        method="POST",
        path="/items",
        mutating_signal=True,
        security_mode="explicit_empty",
    )
    key = "POST /items"
    result = operation_plan(operation, mutation=(key,), security=(key,))
    assert "mutation_policy_design_required" in result.required_maintainer_decisions
    assert "authentication_semantics_revalidation_required" in result.required_maintainer_decisions
