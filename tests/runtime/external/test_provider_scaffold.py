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
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from brain.runtime.external.approval import (  # noqa: E402
    ApprovalError,
    HumanReviewChecklist,
    create_human_approval_manifest,
    create_non_executable_scaffold,
    load_scaffold,
    verify_scaffold,
    verify_scaffold_against_approval_and_proposal,
    write_scaffold_artifacts,
)
from brain.runtime.external.approval.scaffold import build_scaffold_id  # noqa: E402
from brain.runtime.external.discovery.sources import build_discovery_source_registry  # noqa: E402
from brain.runtime.external.providers import build_external_api_registry  # noqa: E402
from brain.runtime.external.tools import EXTERNAL_TOOLS  # noqa: E402
from approval_fixtures import proposal  # noqa: E402
import external_api_approval  # noqa: E402
import external_api_scaffold  # noqa: E402


def approved(value=None):
    value = value or proposal()
    return create_human_approval_manifest(
        value,
        reviewed_by="Maintainer",
        confirm_server_host="api.example.com",
        selected_operations=("GET /pets",),
        review_checklist=HumanReviewChecklist(True, True, True, True, True, True, True),
        acknowledged_review_blockers=value.review_blockers,
        clock=lambda: datetime(2026, 8, 30, tzinfo=timezone.utc),
    )


def test_scaffold_is_deterministic_inert_and_round_trips(tmp_path: Path) -> None:
    value = proposal()
    manifest = approved(value)
    with (
        patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS called")),
        patch.object(socket, "create_connection", side_effect=AssertionError("HTTP called")),
    ):
        first = create_non_executable_scaffold(manifest, value)
        second = create_non_executable_scaffold(manifest, value)
        paths = write_scaffold_artifacts(tmp_path, first)
    assert first == second
    assert {item.name for item in paths} == {"provider-scaffold.json", "README.md"}
    assert {item.suffix for item in tmp_path.iterdir()} <= {".json", ".md"}
    assert "NON-EXECUTABLE REVIEW SCAFFOLD" in (tmp_path / "README.md").read_text()
    loaded = load_scaffold(json.loads((tmp_path / "provider-scaffold.json").read_text()))
    verify_scaffold(loaded)
    for name in (
        "execution_authorized",
        "registration_authorized",
        "network_authority",
        "runtime_activation_authorized",
        "credential_creation_authorized",
        "executable_code_generation_authorized",
    ):
        assert getattr(first, name) is False
    assert not any(hasattr(first, name) for name in ("register", "execute", "to_provider"))


def test_stale_approval_creates_no_files(tmp_path: Path) -> None:
    value = proposal()
    manifest = approved(value)
    stale = replace(value, review_blockers=value.review_blockers + ("new",))
    with pytest.raises(ApprovalError, match="approval_stale"):
        create_non_executable_scaffold(manifest, stale)
    assert list(tmp_path.iterdir()) == []


def test_scaffold_authority_tampering_is_rejected() -> None:
    scaffold = create_non_executable_scaffold(approved(), proposal())
    raw = json.loads(json.dumps(scaffold.as_dict()))
    raw["network_authority"] = True
    with pytest.raises(ApprovalError, match="scaffold_integrity_error"):
        load_scaffold(raw)


@pytest.mark.parametrize(
    "change",
    (
        lambda item: replace(item, server=replace(item.server, hostname="evil.example")),
        lambda item: replace(
            item,
            operations=(replace(item.operations[0], path="/admin"),),
        ),
        lambda item: replace(item, risk_signals=item.risk_signals + ("tampered",)),
        lambda item: replace(item, review_blockers=item.review_blockers + ("tampered",)),
        lambda item: replace(item, implementation_todos=item.implementation_todos + ("tampered",)),
    ),
)
def test_scaffold_content_tampering_invalidates_original_id(change) -> None:
    scaffold = create_non_executable_scaffold(approved(), proposal())
    tampered = change(scaffold)
    with pytest.raises(ApprovalError, match="scaffold_integrity_error"):
        verify_scaffold(tampered)
    assert tampered.scaffold_id == scaffold.scaffold_id


@pytest.mark.parametrize(
    "change",
    (
        lambda item: replace(item, server=replace(item.server, hostname="other.example")),
        lambda item: replace(item, operations=(replace(item.operations[0], path="/other"),)),
        lambda item: replace(item, risk_signals=item.risk_signals + ("different",)),
        lambda item: replace(item, review_blockers=item.review_blockers + ("different",)),
        lambda item: replace(item, implementation_todos=item.implementation_todos + ("different",)),
    ),
)
def test_different_scaffold_content_produces_different_id(change) -> None:
    scaffold = create_non_executable_scaffold(approved(), proposal())
    changed = change(replace(scaffold, scaffold_id=""))
    changed = replace(changed, scaffold_id=build_scaffold_id(changed))
    assert changed.scaffold_id != scaffold.scaffold_id


def test_rehashed_tampering_is_stale_against_original_approval_and_proposal() -> None:
    value = proposal()
    manifest = approved(value)
    scaffold = create_non_executable_scaffold(manifest, value)
    tampered = replace(
        scaffold,
        scaffold_id="",
        server=replace(scaffold.server, hostname="evil.example"),
    )
    tampered = replace(tampered, scaffold_id=build_scaffold_id(tampered))
    verify_scaffold(tampered)
    assert tampered.scaffold_id != scaffold.scaffold_id
    with pytest.raises(ApprovalError, match="scaffold_stale"):
        verify_scaffold_against_approval_and_proposal(tampered, manifest, value)


def test_scaffold_nested_loader_is_strict_and_checks_server_source() -> None:
    raw = json.loads(json.dumps(create_non_executable_scaffold(approved(), proposal()).as_dict()))
    for field in ("extra",):
        changed = json.loads(json.dumps(raw))
        changed["server"][field] = True
        with pytest.raises(ApprovalError, match="scaffold_unknown_field"):
            load_scaffold(changed)
    changed = json.loads(json.dumps(raw))
    del changed["server"]["base_path"]
    with pytest.raises(ApprovalError, match="scaffold_missing_field"):
        load_scaffold(changed)
    changed = json.loads(json.dumps(raw))
    changed["server"]["source"] = "caller_supplied"
    with pytest.raises(ApprovalError, match="scaffold_integrity_error"):
        load_scaffold(changed)
    changed = json.loads(json.dumps(raw))
    changed["operations"][0]["extra"] = True
    with pytest.raises(ApprovalError, match="scaffold_unknown_field"):
        load_scaffold(changed)


@pytest.mark.parametrize(
    ("target", "field", "value"),
    (
        ("server", "hostname", 123),
        ("server", "scheme", True),
        ("server", "port", False),
        ("operation", "method", 123),
        ("operation", "path", False),
        ("operation", "security_requirement_count", True),
        ("operation", "mutating_signal", 0),
    ),
)
def test_scaffold_nested_security_types_are_strict(target: str, field: str, value) -> None:
    raw = json.loads(json.dumps(create_non_executable_scaffold(approved(), proposal()).as_dict()))
    owner = raw["server"] if target == "server" else raw["operations"][0]
    owner[field] = value
    with pytest.raises(ApprovalError, match="scaffold_schema_error"):
        load_scaffold(raw)


@pytest.mark.parametrize(
    "field",
    (
        "operations",
        "declared_security_scheme_types",
        "risk_signals",
        "review_blockers",
        "implementation_todos",
    ),
)
def test_scaffold_array_fields_reject_string_containers(field: str) -> None:
    raw = json.loads(json.dumps(create_non_executable_scaffold(approved(), proposal()).as_dict()))
    raw[field] = "abc"
    with pytest.raises(ApprovalError, match="scaffold_schema_error"):
        load_scaffold(raw)


def test_registry_tool_and_conversion_surfaces_remain_isolated() -> None:
    execution_ids = {item.api_id for item in build_external_api_registry().list()}
    discovery_ids = {item.api_id for item in build_discovery_source_registry().list()}
    assert "approval" not in execution_ids
    assert discovery_ids == {"discovery_apis_guru", "discovery_public_apis"}
    assert not any("approval" in item or "scaffold" in item for item in EXTERNAL_TOOLS)


def test_review_approve_verify_and_scaffold_clis_are_offline(tmp_path: Path) -> None:
    value = proposal()
    proposal_path = tmp_path / "proposal.json"
    manifest_path = tmp_path / "approval.json"
    scaffold_dir = tmp_path / "scaffold"
    proposal_path.write_text(json.dumps(value.as_dict()), encoding="utf-8")
    common_approval = [
        "approve",
        "--proposal-file",
        str(proposal_path),
        "--reviewed-by",
        "Maintainer",
        "--confirm-server-host",
        "api.example.com",
        "--operation",
        "GET /pets",
        "--approve-terms",
        "--approve-security",
        "--approve-privacy",
        "--approve-cost",
        "--approve-rate-limit",
        "--approve-provider-docs",
        "--approve-implementation-scope",
    ]
    for blocker in value.review_blockers:
        common_approval.extend(("--ack-blocker", blocker))
    common_approval.extend(("--output", str(manifest_path)))
    with (
        patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS called")),
        patch.object(socket, "create_connection", side_effect=AssertionError("HTTP called")),
    ):
        assert external_api_approval.main(["review", "--proposal-file", str(proposal_path)]) == 0
        assert external_api_approval.main(common_approval) == 0
        assert (
            external_api_approval.main(
                [
                    "verify",
                    "--proposal-file",
                    str(proposal_path),
                    "--manifest",
                    str(manifest_path),
                ]
            )
            == 0
        )
        assert (
            external_api_scaffold.main(
                [
                    "--proposal-file",
                    str(proposal_path),
                    "--approval-file",
                    str(manifest_path),
                    "--output-dir",
                    str(scaffold_dir),
                ]
            )
            == 0
        )
    assert {item.name for item in scaffold_dir.iterdir()} == {
        "provider-scaffold.json",
        "README.md",
    }
    approval_source = (PROJECT_ROOT / "scripts" / "external_api_approval.py").read_text()
    for forbidden in ("--url", "--base-url", "--server-url", "--host-override", "--port"):
        assert f'add_argument("{forbidden}"' not in approval_source
    for forbidden in ("--yes", "--accept-all", "--force", "--ignore-blockers", "--auto-approve"):
        assert f'add_argument("{forbidden}"' not in approval_source
