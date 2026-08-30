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
    assert len(runtime_capability_profile_sha256(profile)) == 64
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
    ),
)
def test_authentication_compatibility_matrix(scheme, status, marker) -> None:
    result = operation_plan(proposal().operations[0], schemes=(scheme,))
    assert result.auth_status == status
    assert marker in (
        result.compatibility_issues
        + result.required_runtime_extensions
        + result.required_maintainer_decisions
    )


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
