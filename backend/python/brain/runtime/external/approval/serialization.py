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
    try:
        init_names = [item.name for item in fields(ProviderDesignProposal) if item.init]
        converted = dict(raw)
        converted["declared_servers"] = tuple(
            DeclaredServer(**_mapping(item, "proposal_schema_error"))
            for item in raw["declared_servers"]
        )
        converted["operations"] = tuple(
            OperationSummary(
                **{
                    **_mapping(item, "proposal_schema_error"),
                    "parameter_locations": tuple(item["parameter_locations"]),
                    "request_content_types": tuple(item["request_content_types"]),
                    "response_content_types": tuple(item["response_content_types"]),
                }
            )
            for item in raw["operations"]
        )
        converted["security_schemes"] = tuple(
            SecuritySchemeSummary(
                **{
                    **_mapping(item, "proposal_schema_error"),
                    "oauth_flows": tuple(item["oauth_flows"]),
                }
            )
            for item in raw["security_schemes"]
        )
        converted["reference_audit"] = ReferenceAudit(
            **_mapping(raw["reference_audit"], "proposal_schema_error")
        )
        for name in (
            "method_counts",
            "external_resource_counts",
            "risk_signals",
            "issues",
            "review_blockers",
        ):
            converted[name] = tuple(
                tuple(item) if isinstance(item, list) else item for item in raw[name]
            )
        proposal = ProviderDesignProposal(**{name: converted[name] for name in init_names})
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
    try:
        checklist_raw = _mapping(raw["review_checklist"], "approval_manifest_schema_error")
        _exact_keys(
            checklist_raw,
            {item.name for item in fields(HumanReviewChecklist)},
            "approval_manifest",
        )
        checklist = HumanReviewChecklist(**checklist_raw)
        server_raw = _mapping(raw["approved_server"], "approval_manifest_schema_error")
        _exact_keys(
            server_raw,
            {item.name for item in fields(ApprovedServer)},
            "approval_manifest",
        )
        server = ApprovedServer(
            server_raw["scheme"],
            server_raw["hostname"],
            server_raw["port"],
            server_raw["base_path"],
        )
        operations = []
        for item in raw["approved_operations"]:
            operation_raw = _mapping(item, "approval_manifest_schema_error")
            _exact_keys(
                operation_raw,
                {field.name for field in fields(ApprovedOperation)},
                "approval_manifest",
            )
            operations.append(ApprovedOperation(**operation_raw))
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
            converted[name] = tuple(raw[name])
        manifest = HumanApprovalManifest(**{name: converted[name] for name in init_names})
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
    if set(raw) != expected:
        raise ApprovalError("scaffold_schema_error")
    try:
        server_raw = _mapping(raw["server"], "scaffold_schema_error")
        server = ApprovedServer(
            server_raw["scheme"],
            server_raw["hostname"],
            server_raw["port"],
            server_raw["base_path"],
        )
        operations = tuple(
            ApprovedOperation(**_mapping(item, "scaffold_schema_error"))
            for item in raw["operations"]
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
            converted[name] = tuple(raw[name])
        init_names = [item.name for item in fields(NonExecutableProviderScaffold) if item.init]
        scaffold = NonExecutableProviderScaffold(**{name: converted[name] for name in init_names})
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
