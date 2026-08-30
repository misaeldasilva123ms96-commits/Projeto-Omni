"""Strict JSON loaders and atomic writers for offline approval artifacts."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import fields
from pathlib import Path
from typing import Any

from brain.runtime.external.approval.manifest import canonical_json_bytes
from brain.runtime.external.approval.models import (
    ApprovedOperation,
    ApprovedServer,
    HumanApprovalManifest,
    HumanReviewChecklist,
    NonExecutableProviderScaffold,
)
from brain.runtime.external.approval.validation import ApprovalError, validate_proposal
from brain.runtime.external.schema_intake.models import (
    DeclaredServer,
    OperationSummary,
    ProviderDesignProposal,
    ReferenceAudit,
    SecuritySchemeSummary,
)


def _mapping(value: object, code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ApprovalError(code)
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], prefix: str) -> None:
    if set(value) - expected:
        raise ApprovalError(f"{prefix}_unknown_field")
    if expected - set(value):
        raise ApprovalError(f"{prefix}_missing_field")


def _array(value: object, code: str) -> list[Any]:
    if not isinstance(value, list):
        raise ApprovalError(code)
    return value


def _string_array(value: object, code: str) -> tuple[str, ...]:
    items = _array(value, code)
    if not all(isinstance(item, str) for item in items):
        raise ApprovalError(code)
    return tuple(items)


def _require_booleans(raw: dict[str, Any], names: tuple[str, ...], code: str) -> None:
    if any(type(raw.get(name)) is not bool for name in names):
        raise ApprovalError(code)


def _approved_server(
    value: object, *, prefix: str, schema_code: str, integrity_code: str
) -> ApprovedServer:
    raw = _mapping(value, schema_code)
    _exact_keys(raw, {item.name for item in fields(ApprovedServer)}, prefix)
    if raw.get("source") != "proposal_declared_server":
        raise ApprovalError(integrity_code)
    if (
        not isinstance(raw.get("scheme"), str)
        or not isinstance(raw.get("hostname"), str)
        or (raw.get("port") is not None and type(raw.get("port")) is not int)
        or not isinstance(raw.get("base_path"), str)
    ):
        raise ApprovalError(schema_code)
    return ApprovedServer(raw["scheme"], raw["hostname"], raw["port"], raw["base_path"])


def _approved_operation(value: object, *, prefix: str, schema_code: str) -> ApprovedOperation:
    raw = _mapping(value, schema_code)
    _exact_keys(raw, {item.name for item in fields(ApprovedOperation)}, prefix)
    if (
        not isinstance(raw.get("operation_key"), str)
        or not isinstance(raw.get("method"), str)
        or not isinstance(raw.get("path"), str)
        or (raw.get("operation_id") is not None and not isinstance(raw.get("operation_id"), str))
        or not isinstance(raw.get("security_mode"), str)
        or type(raw.get("security_requirement_count")) is not int
        or type(raw.get("anonymous_security_option_present")) is not bool
        or type(raw.get("mutating_signal")) is not bool
    ):
        raise ApprovalError(schema_code)
    return ApprovedOperation(**raw)


def load_json_file(path: str | Path) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ApprovalError("artifact_json_invalid") from exc


def load_proposal(value: object) -> ProviderDesignProposal:
    raw = _mapping(value, "proposal_schema_error")
    expected = {item.name for item in fields(ProviderDesignProposal)}
    if set(raw) != expected:
        raise ApprovalError("proposal_schema_error")
    _require_booleans(
        raw,
        (
            "license_url_present",
            "terms_of_service_present",
            "operation_details_truncated",
            "global_security_present",
            "maintainer_review_required",
            "terms_review_required",
            "security_review_required",
            "privacy_review_required",
            "cost_review_required",
            "rate_limit_review_required",
            "provider_docs_review_required",
            "execution_authorized",
            "registration_authorized",
            "code_generation_authorized",
            "credential_generation_authorized",
            "network_authority",
        ),
        "proposal_schema_error",
    )
    try:
        init_names = [item.name for item in fields(ProviderDesignProposal) if item.init]
        converted = dict(raw)
        servers = []
        for item in _array(raw["declared_servers"], "proposal_schema_error"):
            server_raw = _mapping(item, "proposal_schema_error")
            _exact_keys(
                server_raw,
                {field.name for field in fields(DeclaredServer)},
                "proposal",
            )
            if (
                (
                    server_raw.get("scheme") is not None
                    and not isinstance(server_raw.get("scheme"), str)
                )
                or (
                    server_raw.get("hostname") is not None
                    and not isinstance(server_raw.get("hostname"), str)
                )
                or (server_raw.get("port") is not None and type(server_raw.get("port")) is not int)
                or not isinstance(server_raw.get("base_path"), str)
                or type(server_raw.get("templated")) is not bool
            ):
                raise ApprovalError("proposal_schema_error")
            servers.append(DeclaredServer(**server_raw))
        converted["declared_servers"] = tuple(servers)
        operations = []
        for item in _array(raw["operations"], "proposal_schema_error"):
            operation_raw = _mapping(item, "proposal_schema_error")
            _exact_keys(
                operation_raw,
                {field.name for field in fields(OperationSummary)},
                "proposal",
            )
            if (
                not isinstance(operation_raw.get("method"), str)
                or not isinstance(operation_raw.get("path"), str)
                or (
                    operation_raw.get("operation_id") is not None
                    and not isinstance(operation_raw.get("operation_id"), str)
                )
                or not isinstance(operation_raw.get("summary"), str)
                or type(operation_raw.get("deprecated")) is not bool
                or type(operation_raw.get("security_override_present")) is not bool
                or not isinstance(operation_raw.get("security_mode"), str)
                or type(operation_raw.get("security_requirement_count")) is not int
                or type(operation_raw.get("anonymous_security_option_present")) is not bool
                or type(operation_raw.get("mutating_signal")) is not bool
            ):
                raise ApprovalError("proposal_schema_error")
            operations.append(
                OperationSummary(
                    **{
                        **operation_raw,
                        "parameter_locations": _string_array(
                            item["parameter_locations"], "proposal_schema_error"
                        ),
                        "request_content_types": _string_array(
                            item["request_content_types"], "proposal_schema_error"
                        ),
                        "response_content_types": _string_array(
                            item["response_content_types"], "proposal_schema_error"
                        ),
                    }
                )
            )
        converted["operations"] = tuple(operations)
        converted["security_schemes"] = tuple(
            SecuritySchemeSummary(
                **{
                    **_mapping(item, "proposal_schema_error"),
                    "oauth_flows": _string_array(item["oauth_flows"], "proposal_schema_error"),
                }
            )
            for item in _array(raw["security_schemes"], "proposal_schema_error")
        )
        converted["reference_audit"] = ReferenceAudit(
            **_mapping(raw["reference_audit"], "proposal_schema_error")
        )
        for name in ("method_counts", "external_resource_counts"):
            items = _array(raw[name], "proposal_schema_error")
            converted[name] = tuple(
                tuple(item) if isinstance(item, list) and len(item) == 2 else () for item in items
            )
            if any(
                not item or not isinstance(item[0], str) or type(item[1]) is not int
                for item in converted[name]
            ):
                raise ApprovalError("proposal_schema_error")
        for name in ("risk_signals", "issues", "review_blockers"):
            converted[name] = _string_array(raw[name], "proposal_schema_error")
        proposal = ProviderDesignProposal(**{name: converted[name] for name in init_names})
    except ApprovalError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ApprovalError("proposal_schema_error") from exc
    for item in fields(ProviderDesignProposal):
        if not item.init and raw[item.name] != getattr(proposal, item.name):
            raise ApprovalError("proposal_authority_invalid")
    validate_proposal(proposal)
    return proposal


def load_manifest(value: object) -> HumanApprovalManifest:
    raw = _mapping(value, "approval_manifest_schema_error")
    expected = {item.name for item in fields(HumanApprovalManifest)}
    _exact_keys(raw, expected, "approval_manifest")
    _require_booleans(
        raw,
        (
            "scaffold_generation_authorized",
            "execution_authorized",
            "registration_authorized",
            "network_authority",
            "tool_registration_authorized",
            "runtime_activation_authorized",
            "credential_creation_authorized",
            "executable_code_generation_authorized",
            "reviewer_identity_cryptographically_verified",
        ),
        "approval_manifest_schema_error",
    )
    try:
        checklist_raw = _mapping(raw["review_checklist"], "approval_manifest_schema_error")
        _exact_keys(
            checklist_raw,
            {item.name for item in fields(HumanReviewChecklist)},
            "approval_manifest",
        )
        _require_booleans(
            checklist_raw,
            tuple(item.name for item in fields(HumanReviewChecklist)),
            "approval_manifest_schema_error",
        )
        checklist = HumanReviewChecklist(**checklist_raw)
        server = _approved_server(
            raw["approved_server"],
            prefix="approval_manifest",
            schema_code="approval_manifest_schema_error",
            integrity_code="approval_manifest_integrity_error",
        )
        operations = []
        for item in _array(raw["approved_operations"], "approval_manifest_schema_error"):
            operations.append(
                _approved_operation(
                    item,
                    prefix="approval_manifest",
                    schema_code="approval_manifest_schema_error",
                )
            )
        init_names = [item.name for item in fields(HumanApprovalManifest) if item.init]
        converted = dict(raw)
        converted.update(
            review_checklist=checklist,
            approved_server=server,
            approved_operations=tuple(operations),
        )
        for name in (
            "acknowledged_review_blockers",
            "proposal_issues",
            "acknowledged_mutating_operations",
            "acknowledged_security_exceptions",
        ):
            converted[name] = _string_array(raw[name], "approval_manifest_schema_error")
        manifest = HumanApprovalManifest(**{name: converted[name] for name in init_names})
    except ApprovalError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ApprovalError("approval_manifest_schema_error") from exc
    if any(
        raw[item.name] != getattr(manifest, item.name)
        for item in fields(HumanApprovalManifest)
        if not item.init
    ):
        raise ApprovalError("approval_manifest_integrity_error")
    from brain.runtime.external.approval.manifest import verify_approval_manifest

    verify_approval_manifest(manifest)
    return manifest


def load_scaffold(value: object) -> NonExecutableProviderScaffold:
    raw = _mapping(value, "scaffold_schema_error")
    expected = {item.name for item in fields(NonExecutableProviderScaffold)}
    _exact_keys(raw, expected, "scaffold")
    _require_booleans(
        raw,
        (
            "execution_authorized",
            "registration_authorized",
            "network_authority",
            "tool_registration_authorized",
            "runtime_activation_authorized",
            "credential_creation_authorized",
            "executable_code_generation_authorized",
        ),
        "scaffold_schema_error",
    )
    try:
        server = _approved_server(
            raw["server"],
            prefix="scaffold",
            schema_code="scaffold_schema_error",
            integrity_code="scaffold_integrity_error",
        )
        operations = tuple(
            _approved_operation(item, prefix="scaffold", schema_code="scaffold_schema_error")
            for item in _array(raw["operations"], "scaffold_schema_error")
        )
        converted = dict(raw)
        converted["server"] = server
        converted["operations"] = operations
        for name in (
            "declared_security_scheme_types",
            "risk_signals",
            "review_blockers",
            "implementation_todos",
        ):
            converted[name] = _string_array(raw[name], "scaffold_schema_error")
        init_names = [item.name for item in fields(NonExecutableProviderScaffold) if item.init]
        scaffold = NonExecutableProviderScaffold(**{name: converted[name] for name in init_names})
    except ApprovalError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ApprovalError("scaffold_schema_error") from exc
    if any(
        raw[item.name] != getattr(scaffold, item.name)
        for item in fields(NonExecutableProviderScaffold)
        if not item.init
    ):
        raise ApprovalError("scaffold_integrity_error")
    from brain.runtime.external.approval.scaffold import verify_scaffold

    verify_scaffold(scaffold)
    return scaffold


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def write_json(path: Path, value: object) -> None:
    atomic_write(path, canonical_json_bytes(value) + b"\n")
