from __future__ import annotations

import json
import socket
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from brain.runtime.external.approval import (  # noqa: E402
    APPROVAL_MANIFEST_FORMAT_VERSION,
    ApprovalError,
    HumanReviewChecklist,
    create_human_approval_manifest,
    load_manifest,
    load_proposal,
    proposal_snapshot_sha256,
    verify_approval_against_proposal,
    verify_approval_manifest,
)
from brain.runtime.external.approval.models import HumanApprovalManifest  # noqa: E402
from brain.runtime.external.approval import manifest as manifest_module  # noqa: E402
from brain.runtime.external.approval.validation import select_server  # noqa: E402
from brain.runtime.external.schema_intake.analyzer import build_proposal_id  # noqa: E402
from brain.runtime.external.schema_intake.models import DeclaredServer  # noqa: E402
from approval_fixtures import proposal, with_operations  # noqa: E402

NOW = datetime(2026, 8, 30, 1, 2, 3, tzinfo=timezone.utc)
ALL_APPROVED = HumanReviewChecklist(True, True, True, True, True, True, True)


def approve(value=None, *, selected=("GET /pets",), **overrides) -> HumanApprovalManifest:
    value = value or proposal()
    arguments = {
        "reviewed_by": "Maintainer",
        "confirm_server_host": "api.example.com",
        "selected_operations": selected,
        "review_checklist": ALL_APPROVED,
        "acknowledged_review_blockers": tuple(value.review_blockers),
        "clock": lambda: NOW,
    }
    arguments.update(overrides)
    return create_human_approval_manifest(value, **arguments)


def test_manifest_binds_exact_proposal_snapshot_and_is_deterministic() -> None:
    value = proposal()
    first = approve(value)
    second = approve(value, acknowledged_review_blockers=tuple(reversed(value.review_blockers)))
    assert first == second
    assert first.approval_manifest_format_version == APPROVAL_MANIFEST_FORMAT_VERSION
    assert first.proposal_snapshot_sha256 == proposal_snapshot_sha256(value)
    assert first.approval_state == "approved_for_non_executable_scaffold"
    assert first.scaffold_generation_authorized is True
    assert first.reviewer_identity_cryptographically_verified is False
    for name in (
        "execution_authorized",
        "registration_authorized",
        "network_authority",
        "tool_registration_authorized",
        "runtime_activation_authorized",
        "credential_creation_authorized",
        "executable_code_generation_authorized",
    ):
        assert getattr(first, name) is False
    assert not any(hasattr(value, name) for name in ("approve", "register", "execute"))


def test_manifest_round_trip_integrity_and_authority_tampering() -> None:
    manifest = approve()
    loaded = load_manifest(json.loads(json.dumps(manifest.as_dict())))
    verify_approval_manifest(loaded)
    with pytest.raises(ApprovalError, match="approval_manifest_integrity_error"):
        verify_approval_manifest(replace(manifest, reviewed_by="Attacker"))
    raw = json.loads(json.dumps(manifest.as_dict()))
    raw["execution_authorized"] = True
    with pytest.raises(ApprovalError, match="approval_manifest_integrity_error"):
        load_manifest(raw)
    raw = json.loads(json.dumps(manifest.as_dict()))
    raw["unknown"] = True
    with pytest.raises(ApprovalError, match="approval_manifest_unknown_field"):
        load_manifest(raw)
    raw = json.loads(json.dumps(manifest.as_dict()))
    raw["approved_server"]["source"] = "caller_supplied"
    with pytest.raises(ApprovalError, match="approval_manifest_integrity_error"):
        load_manifest(raw)


@pytest.mark.parametrize(
    "field",
    (
        "approved_operations",
        "acknowledged_review_blockers",
        "proposal_issues",
        "acknowledged_mutating_operations",
        "acknowledged_security_exceptions",
    ),
)
def test_manifest_array_fields_reject_string_containers(field: str) -> None:
    raw = json.loads(json.dumps(approve().as_dict()))
    raw[field] = "abc"
    with pytest.raises(ApprovalError, match="approval_manifest_schema_error"):
        load_manifest(raw)


def test_rehashed_server_tampering_is_rejected_against_proposal() -> None:
    value = proposal()
    manifest = approve(value)
    changed = replace(
        manifest,
        approval_id="",
        approved_server=replace(manifest.approved_server, hostname="evil.example"),
    )
    changed = replace(changed, approval_id=manifest_module._approval_id(changed))
    with pytest.raises(ApprovalError, match="approval_manifest_integrity_error"):
        verify_approval_against_proposal(changed, value)


def test_reviewer_and_scope_change_approval_identity() -> None:
    value = proposal()
    baseline = approve(value)
    reviewer = approve(value, reviewed_by="Another Maintainer")
    scope = approve(value, selected=("HEAD /pets",))
    assert len({baseline.approval_id, reviewer.approval_id, scope.approval_id}) == 3


def test_proposal_loader_is_strict_and_recomputes_identity() -> None:
    value = proposal()
    loaded = load_proposal(json.loads(json.dumps(value.as_dict())))
    assert loaded == value
    raw = json.loads(json.dumps(value.as_dict()))
    raw["proposal_id"] = "0" * 64
    with pytest.raises(ApprovalError, match="proposal_identity_invalid"):
        load_proposal(raw)
    unsupported = replace(value, proposal_format_version="provider-design-proposal-v1")
    unsupported = replace(
        unsupported,
        proposal_id=build_proposal_id(
            unsupported.candidate_id,
            unsupported.canonical_schema_sha256,
            unsupported.proposal_format_version,
        ),
    )
    with pytest.raises(ApprovalError, match="unsupported_proposal_format"):
        create_human_approval_manifest(
            unsupported,
            reviewed_by="Maintainer",
            confirm_server_host="api.example.com",
            selected_operations=("GET /pets",),
            review_checklist=ALL_APPROVED,
            acknowledged_review_blockers=unsupported.review_blockers,
            clock=lambda: NOW,
        )
    raw = json.loads(json.dumps(value.as_dict()))
    raw["review_blockers"] = "abc"
    with pytest.raises(ApprovalError, match="proposal_schema_error"):
        load_proposal(raw)
    raw = json.loads(json.dumps(value.as_dict()))
    raw["operations"][0]["path"] = 123
    with pytest.raises(ApprovalError, match="proposal_schema_error"):
        load_proposal(raw)


def test_human_checklist_and_exact_blockers_are_mandatory() -> None:
    value = proposal()
    with pytest.raises(ApprovalError, match="human_review_incomplete"):
        approve(value, review_checklist=replace(ALL_APPROVED, cost_approved=False))
    with pytest.raises(ApprovalError, match="human_review_incomplete"):
        approve(value, acknowledged_review_blockers=value.review_blockers[:-1])
    with pytest.raises(ApprovalError, match="unknown_review_blocker_acknowledgement"):
        approve(value, acknowledged_review_blockers=value.review_blockers + ("typo",))
    with pytest.raises(ApprovalError, match="proposal_operation_details_incomplete"):
        approve(replace(value, operation_details_truncated=True))
    assert all(
        getattr(HumanReviewChecklist(), name) is False
        for name in HumanReviewChecklist.__dataclass_fields__
    )


@pytest.mark.parametrize("reviewer", ("x", "Maintainer\nInjected", "A\x00B"))
def test_reviewer_identity_is_bounded_and_control_free(reviewer: str) -> None:
    with pytest.raises(ApprovalError, match="reviewer_identity_invalid"):
        approve(reviewed_by=reviewer)


def test_stale_snapshot_detects_new_blocker_with_same_proposal_id() -> None:
    value = proposal()
    manifest = approve(value)
    changed = replace(value, review_blockers=value.review_blockers + ("new_blocker",))
    with pytest.raises(ApprovalError, match="approval_stale"):
        verify_approval_against_proposal(manifest, changed)


@pytest.mark.parametrize("method", ("POST", "PUT", "PATCH", "DELETE"))
def test_mutating_methods_require_exact_acknowledgement(method: str) -> None:
    operation = replace(
        proposal().operations[0], method=method, path="/change", mutating_signal=True
    )
    value = with_operations(proposal(), operation)
    key = f"{method} /change"
    with pytest.raises(ApprovalError, match="mutating_operation_not_acknowledged"):
        approve(value, selected=(key,))
    assert (
        approve(value, selected=(key,), acknowledged_mutating_operations=(key,))
        .approved_operations[0]
        .mutating_signal
    )


@pytest.mark.parametrize("method", ("QUERY", "TRACE", "OPTIONS", "PURGE"))
def test_unsupported_scaffold_methods_are_rejected(method: str) -> None:
    operation = replace(proposal().operations[0], method=method)
    value = with_operations(proposal(), operation)
    with pytest.raises(ApprovalError, match="operation_method_not_supported_for_scaffold"):
        approve(value, selected=(f"{method} /pets",))


def test_operation_injection_duplicates_bounds_and_security_semantics() -> None:
    value = proposal()
    with pytest.raises(ApprovalError, match="selected_operation_not_found"):
        approve(value, selected=("DELETE /admin",))
    with pytest.raises(ApprovalError, match="duplicate_selected_operation"):
        approve(value, selected=("GET /pets", "GET /pets"))
    with pytest.raises(ApprovalError, match="no_operations_selected"):
        approve(value, selected=())
    with pytest.raises(ApprovalError, match="too_many_operations_selected"):
        approve(value, selected=tuple(f"GET /{index}" for index in range(21)))
    with pytest.raises(ApprovalError, match="operation_security_exception_not_acknowledged"):
        approve(
            value,
            selected=("DELETE /pets/{id}",),
            acknowledged_mutating_operations=("DELETE /pets/{id}",),
        )
    approved = approve(
        value,
        selected=("DELETE /pets/{id}",),
        acknowledged_mutating_operations=("DELETE /pets/{id}",),
        acknowledged_security_exceptions=("DELETE /pets/{id}",),
    )
    assert approved.approved_operations[0].security_mode == "explicit_empty"
    invalid = replace(value.operations[0], security_mode="invalid")
    with pytest.raises(ApprovalError, match="selected_operation_security_invalid"):
        approve(with_operations(value, invalid))


@pytest.mark.parametrize(
    "path",
    (
        "/../admin",
        "/%2e%2e/admin",
        "/pets?admin=1",
        "/pets#fragment",
        "/bad\\path",
        "/bad\npath",
        "/%252e%252e/admin",
        "/items%252fadmin",
        "/items%255cadmin",
        123,
    ),
)
def test_selected_operation_path_must_be_safe_metadata(path: object) -> None:
    operation = replace(proposal().operations[0], path=path)
    value = with_operations(proposal(), operation)
    with pytest.raises(ApprovalError, match="operation_path_invalid"):
        approve(value, selected=(f"GET {path}",))


def test_exact_twenty_operations_and_selection_order_are_supported() -> None:
    base = proposal().operations[0]
    operations = tuple(replace(base, path=f"/items/{index}") for index in range(20))
    value = with_operations(proposal(), *operations)
    keys = tuple(f"GET /items/{index}" for index in range(20))
    first = approve(value, selected=keys)
    second = approve(value, selected=tuple(reversed(keys)))
    assert len(first.approved_operations) == 20
    assert first.approval_id == second.approval_id


@pytest.mark.parametrize("method", ("GET", "HEAD"))
def test_read_methods_are_supported_without_mutation_ack(method: str) -> None:
    operation = replace(proposal().operations[0], method=method)
    value = with_operations(proposal(), operation)
    assert approve(value, selected=(f"{method} /pets",)).approved_operations[0].method == method


@pytest.mark.parametrize(
    ("mode", "anonymous", "requires_ack"),
    (
        ("inherits_global", False, False),
        ("explicit_requirements", False, False),
        ("explicit_empty", False, True),
        ("explicit_optional_anonymous", True, True),
        ("explicit_requirements", True, True),
    ),
)
def test_security_exception_matrix(mode: str, anonymous: bool, requires_ack: bool) -> None:
    operation = replace(
        proposal().operations[0],
        security_mode=mode,
        anonymous_security_option_present=anonymous,
    )
    value = with_operations(proposal(), operation)
    key = "GET /pets"
    if requires_ack:
        with pytest.raises(ApprovalError, match="operation_security_exception_not_acknowledged"):
            approve(value)
        manifest = approve(value, acknowledged_security_exceptions=(key,))
    else:
        manifest = approve(value)
    assert manifest.approved_operations[0].security_mode == mode


@pytest.mark.parametrize(
    ("server", "code"),
    (
        (DeclaredServer("https", None, None, "/", False), "provider_scaffold_server_unavailable"),
        (
            DeclaredServer("https", None, None, "/", True),
            "templated_server_not_supported_for_scaffold",
        ),
        (
            DeclaredServer("http", "api.example.com", None, "/", False),
            "insecure_server_not_supported_for_scaffold",
        ),
        (
            DeclaredServer("https", "api.example.com", 8443, "/", False),
            "non_standard_server_port_not_supported",
        ),
        (DeclaredServer("https", "127.0.0.1", None, "/", False), "ip_literal_server_not_supported"),
        (
            DeclaredServer("https", "localhost", None, "/", False),
            "provider_scaffold_server_unavailable",
        ),
        (
            DeclaredServer("https", "singlelabel", None, "/", False),
            "provider_scaffold_server_unavailable",
        ),
        (
            DeclaredServer("https", "service.local", None, "/", False),
            "provider_scaffold_server_unavailable",
        ),
    ),
)
def test_server_rejections_are_syntactic_and_offline(server, code: str) -> None:
    value = replace(proposal(), declared_servers=(server,))
    with patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS called")):
        with pytest.raises(ApprovalError, match=code):
            select_server(value, server.hostname or "missing")


def test_server_ambiguity_and_arbitrary_host_injection() -> None:
    value = proposal()
    with pytest.raises(ApprovalError, match="confirmed_server_mismatch"):
        select_server(value, "evil.example")
    multiple = replace(value, declared_servers=value.declared_servers * 2)
    with pytest.raises(ApprovalError, match="provider_scaffold_server_ambiguous"):
        select_server(multiple, "api.example.com")
    with pytest.raises(ApprovalError, match="provider_scaffold_server_unavailable"):
        select_server(replace(value, declared_servers=()), "api.example.com")
