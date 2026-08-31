"""Integrity and staleness checks for static implementation plans."""

from __future__ import annotations

from brain.runtime.external.approval.models import (
    HumanApprovalManifest,
    NonExecutableProviderScaffold,
)
from brain.runtime.external.approval.validation import ApprovalError
from brain.runtime.external.schema_intake.models import ProviderDesignProposal

from .analyzer import (
    STATIC_PROVIDER_IMPLEMENTATION_PLAN_FORMAT_VERSION,
    build_implementation_plan_id,
    build_static_provider_implementation_plan,
)
from .capabilities import (
    RUNTIME_CAPABILITY_PROFILE_VERSION,
    build_runtime_capability_profile,
    runtime_capability_profile_sha256,
)
from .models import StaticProviderImplementationPlan


class ImplementationPlanError(ApprovalError):
    """Stable failure code for the non-executable implementation-plan boundary."""


_COMPATIBILITY_STATUSES = frozenset(
    {
        "compatible",
        "potentially_compatible",
        "maintainer_decision_required",
        "runtime_extension_required",
        "unsupported_current_runtime",
    }
)


def verify_implementation_plan(plan: StaticProviderImplementationPlan) -> None:
    if (
        plan.implementation_plan_format_version
        != STATIC_PROVIDER_IMPLEMENTATION_PLAN_FORMAT_VERSION
    ):
        raise ImplementationPlanError("unsupported_implementation_plan_format")
    if plan.runtime_capability_profile_version != RUNTIME_CAPABILITY_PROFILE_VERSION:
        raise ImplementationPlanError("unsupported_runtime_capability_profile")
    expected_profile_hash = runtime_capability_profile_sha256(build_runtime_capability_profile())
    authority_names = (
        "source_code_generation_authorized",
        "execution_authorized",
        "registration_authorized",
        "network_authority",
        "tool_registration_authorized",
        "runtime_activation_authorized",
        "credential_creation_authorized",
        "feature_gate_creation_authorized",
        "provider_definition_creation_authorized",
    )
    if (
        plan.plan_state != "static_design_analysis_only"
        or plan.required_initial_enabled_state is not False
        or plan.required_redirect_policy != "deny"
        or plan.non_get_retry_assumption != "none"
        or type(plan.global_security_present) is not bool
        or type(plan.global_security_requirement_count) is not int
        or plan.global_security_requirement_count < 0
        or plan.operation_security_binding_precision
        != "scheme_identity_not_preserved_by_proposal_v2"
        or any(item.runtime_status not in _COMPATIBILITY_STATUSES for item in plan.security_schemes)
        or any(
            status not in _COMPATIBILITY_STATUSES
            for item in plan.operation_compatibility
            for status in (
                item.path_status,
                item.request_status,
                item.response_status,
                item.auth_status,
            )
        )
        or any(getattr(plan, name, None) is not False for name in authority_names)
        or plan.runtime_capability_profile_sha256 != expected_profile_hash
        or plan.implementation_plan_id != build_implementation_plan_id(plan)
    ):
        raise ImplementationPlanError("implementation_plan_integrity_error")


def verify_implementation_plan_against_inputs(
    plan: StaticProviderImplementationPlan,
    scaffold: NonExecutableProviderScaffold,
    approval: HumanApprovalManifest,
    proposal: ProviderDesignProposal,
) -> None:
    verify_implementation_plan(plan)
    expected = build_static_provider_implementation_plan(scaffold, approval, proposal)
    if plan != expected:
        raise ImplementationPlanError("implementation_plan_stale")
