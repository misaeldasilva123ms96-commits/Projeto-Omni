"""Strict JSON loading and inert JSON/Markdown output for implementation plans."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any

from brain.runtime.external.approval.serialization import atomic_write, write_json

from .models import (
    CompatibilitySummary,
    ExternalAPIDefinitionFieldPlan,
    OperationRuntimeCompatibility,
    SecuritySchemePlan,
    ServerPlan,
    StaticProviderImplementationPlan,
)
from .validation import ImplementationPlanError, verify_implementation_plan


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ImplementationPlanError("implementation_plan_schema_error")
    return value


def _exact(raw: dict[str, Any], cls: type) -> None:
    if set(raw) != {item.name for item in fields(cls)}:
        raise ImplementationPlanError("implementation_plan_schema_error")


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ImplementationPlanError("implementation_plan_schema_error")
    return tuple(value)


def _simple(cls: type, value: object, *, optional: tuple[str, ...] = ()):
    raw = _mapping(value)
    _exact(raw, cls)
    for item in fields(cls):
        current = raw[item.name]
        if item.name in optional:
            if current is not None and not isinstance(current, str):
                raise ImplementationPlanError("implementation_plan_schema_error")
        elif not isinstance(current, str):
            raise ImplementationPlanError("implementation_plan_schema_error")
    return cls(**raw)


def _operation(value: object) -> OperationRuntimeCompatibility:
    raw = _mapping(value)
    _exact(raw, OperationRuntimeCompatibility)
    string_fields = (
        "operation_key",
        "method",
        "effective_path",
        "path_classification",
        "path_status",
        "request_status",
        "response_status",
        "auth_status",
        "security_mode",
    )
    if any(not isinstance(raw[name], str) for name in string_fields):
        raise ImplementationPlanError("implementation_plan_schema_error")
    if type(raw["security_requirement_count"]) is not int or any(
        type(raw[name]) is not bool
        for name in ("mutating_signal", "anonymous_security_option_present")
    ):
        raise ImplementationPlanError("implementation_plan_schema_error")
    converted = dict(raw)
    for name in (
        "parameter_locations",
        "request_content_types",
        "response_content_types",
        "compatibility_issues",
        "required_runtime_extensions",
        "required_maintainer_decisions",
    ):
        converted[name] = _strings(raw[name])
    return OperationRuntimeCompatibility(**converted)


def _summary(value: object) -> CompatibilitySummary:
    raw = _mapping(value)
    _exact(raw, CompatibilitySummary)
    if any(type(value) is not int or value < 0 for value in raw.values()):
        raise ImplementationPlanError("implementation_plan_schema_error")
    return CompatibilitySummary(**raw)


def load_implementation_plan(value: object) -> StaticProviderImplementationPlan:
    raw = _mapping(value)
    _exact(raw, StaticProviderImplementationPlan)
    bool_names = (
        "required_initial_enabled_state",
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
    if any(type(raw[name]) is not bool for name in bool_names):
        raise ImplementationPlanError("implementation_plan_schema_error")
    scalar_strings = (
        "implementation_plan_id",
        "implementation_plan_format_version",
        "runtime_capability_profile_version",
        "runtime_capability_profile_sha256",
        "scaffold_id",
        "scaffold_format_version",
        "approval_id",
        "proposal_id",
        "proposal_format_version",
        "candidate_id",
        "canonical_schema_sha256",
        "proposal_snapshot_sha256",
        "required_redirect_policy",
        "non_get_retry_assumption",
        "plan_state",
    )
    if any(not isinstance(raw[name], str) for name in scalar_strings):
        raise ImplementationPlanError("implementation_plan_schema_error")
    server_raw = _mapping(raw["server"])
    _exact(server_raw, ServerPlan)
    if any(
        not isinstance(server_raw[name], str)
        for name in ("scheme", "hostname", "base_path", "base_url_origin")
    ) or (server_raw["port"] is not None and type(server_raw["port"]) is not int):
        raise ImplementationPlanError("implementation_plan_schema_error")
    converted = dict(raw)
    converted["server"] = ServerPlan(**server_raw)
    list_builders = {
        "provider_definition_fields": lambda item: _simple(
            ExternalAPIDefinitionFieldPlan, item, optional=("design_metadata",)
        ),
        "security_schemes": lambda item: _security_scheme(item),
        "operation_compatibility": _operation,
    }
    for name, builder in list_builders.items():
        if not isinstance(raw[name], list):
            raise ImplementationPlanError("implementation_plan_schema_error")
        converted[name] = tuple(builder(item) for item in raw[name])
    for name in ("risk_signals", "review_blockers", "implementation_gaps", "excluded_scopes"):
        converted[name] = _strings(raw[name])
    converted["compatibility_summary"] = _summary(raw["compatibility_summary"])
    try:
        plan = StaticProviderImplementationPlan(
            **{
                item.name: converted[item.name]
                for item in fields(StaticProviderImplementationPlan)
                if item.init
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ImplementationPlanError("implementation_plan_schema_error") from exc
    if any(raw[item.name] != getattr(plan, item.name) for item in fields(plan) if not item.init):
        raise ImplementationPlanError("implementation_plan_integrity_error")
    verify_implementation_plan(plan)
    return plan


def _security_scheme(value: object) -> SecuritySchemePlan:
    raw = _mapping(value)
    _exact(raw, SecuritySchemePlan)
    if not isinstance(raw["name"], str) or not isinstance(raw["scheme_type"], str):
        raise ImplementationPlanError("implementation_plan_schema_error")
    for name in ("location", "http_scheme"):
        if raw[name] is not None and not isinstance(raw[name], str):
            raise ImplementationPlanError("implementation_plan_schema_error")
    return SecuritySchemePlan(
        raw["name"],
        raw["scheme_type"],
        raw["location"],
        raw["http_scheme"],
        _strings(raw["oauth_flows"]),
    )


def write_implementation_plan_artifacts(
    output_dir: str | Path, plan: StaticProviderImplementationPlan
) -> tuple[Path, Path, Path]:
    verify_implementation_plan(plan)
    destination = Path(output_dir)
    json_path = destination / "provider-implementation-plan.json"
    readme_path = destination / "README.md"
    compatibility_path = destination / "runtime-compatibility.md"
    warning = (
        "# STATIC IMPLEMENTATION PLAN — NON-EXECUTABLE\n\n"
        "This artifact describes implementation requirements only.\n"
        "It does not create or authorize provider code, credentials,\n"
        "network access, tools, registration, or runtime activation.\n"
    )
    rows = [
        "# Runtime compatibility\n",
        "| Operation | Method | Effective Path | Path Status | Request Status | "
        "Response Status | Auth Status | Runtime Extensions | Maintainer Decisions |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in plan.operation_compatibility:
        rows.append(
            "| "
            + " | ".join(
                (
                    item.operation_key,
                    item.method,
                    item.effective_path,
                    item.path_status,
                    item.request_status,
                    item.response_status,
                    item.auth_status,
                    ", ".join(item.required_runtime_extensions),
                    ", ".join(item.required_maintainer_decisions),
                )
            )
            + " |"
        )
    try:
        write_json(json_path, plan.as_dict())
        atomic_write(readme_path, warning.encode("utf-8"))
        atomic_write(compatibility_path, ("\n".join(rows) + "\n").encode("utf-8"))
    except BaseException:
        for path in (json_path, readme_path, compatibility_path):
            path.unlink(missing_ok=True)
        raise
    return json_path, readme_path, compatibility_path
