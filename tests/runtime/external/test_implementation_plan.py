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

from approval_fixtures import proposal  # noqa: E402
from brain.runtime.external.approval import (  # noqa: E402
    HumanReviewChecklist,
    create_human_approval_manifest,
    create_non_executable_scaffold,
)
from brain.runtime.external.implementation_plan import (  # noqa: E402
    ImplementationPlanError,
    build_implementation_plan_id,
    build_static_provider_implementation_plan,
    load_implementation_plan,
    safe_join_paths,
    verify_implementation_plan,
    verify_implementation_plan_against_inputs,
    write_implementation_plan_artifacts,
)
import external_api_implementation_plan  # noqa: E402


def chain(value=None, *, selected=("GET /pets",), mutation=(), security=()):
    value = value or proposal()
    approval = create_human_approval_manifest(
        value,
        reviewed_by="Maintainer",
        confirm_server_host="api.example.com",
        selected_operations=selected,
        review_checklist=HumanReviewChecklist(True, True, True, True, True, True, True),
        acknowledged_review_blockers=value.review_blockers,
        acknowledged_mutating_operations=mutation,
        acknowledged_security_exceptions=security,
        clock=lambda: datetime(2026, 8, 30, tzinfo=timezone.utc),
    )
    scaffold = create_non_executable_scaffold(approval, value)
    return value, approval, scaffold


def test_plan_is_content_bound_inert_and_strictly_round_trips(tmp_path: Path) -> None:
    value, approval, scaffold = chain()
    plan = build_static_provider_implementation_plan(scaffold, approval, value)
    paths = write_implementation_plan_artifacts(tmp_path, plan)
    assert {item.name for item in paths} == {
        "provider-implementation-plan.json",
        "README.md",
        "runtime-compatibility.md",
    }
    assert {item.suffix for item in tmp_path.iterdir()} <= {".json", ".md"}
    assert (
        (tmp_path / "README.md")
        .read_text(encoding="utf-8")
        .startswith("# STATIC IMPLEMENTATION PLAN — NON-EXECUTABLE")
    )
    loaded = load_implementation_plan(
        json.loads((tmp_path / "provider-implementation-plan.json").read_text(encoding="utf-8"))
    )
    assert loaded == plan
    verify_implementation_plan_against_inputs(loaded, scaffold, approval, value)
    assert plan.server.base_url_origin == "https://api.example.com"
    assert plan.operation_compatibility[0].effective_path == "/v1/pets"
    assert plan.operation_compatibility[0].path_classification == "exact_path_candidate"
    assert all(
        getattr(plan, name) is False
        for name in (
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
    )


@pytest.mark.parametrize(
    "change",
    (
        lambda plan: replace(plan, server=replace(plan.server, hostname="evil.example")),
        lambda plan: replace(
            plan,
            operation_compatibility=(
                replace(
                    plan.operation_compatibility[0],
                    request_status="unsupported_current_runtime",
                ),
            ),
        ),
        lambda plan: replace(plan, implementation_gaps=plan.implementation_gaps + ("tampered",)),
        lambda plan: replace(plan, runtime_capability_profile_sha256="0" * 64),
    ),
)
def test_original_identity_rejects_plan_tampering(change) -> None:
    value, approval, scaffold = chain()
    plan = build_static_provider_implementation_plan(scaffold, approval, value)
    with pytest.raises(ImplementationPlanError, match="implementation_plan_integrity_error"):
        verify_implementation_plan(change(plan))


def test_loader_rejects_authority_tampering() -> None:
    value, approval, scaffold = chain()
    plan = build_static_provider_implementation_plan(scaffold, approval, value)
    raw = json.loads(json.dumps(plan.as_dict()))
    raw["network_authority"] = True
    with pytest.raises(ImplementationPlanError, match="implementation_plan_integrity_error"):
        load_implementation_plan(raw)


def test_rehashed_tampering_is_stale_against_inputs() -> None:
    value, approval, scaffold = chain()
    plan = build_static_provider_implementation_plan(scaffold, approval, value)
    changed = replace(plan, implementation_plan_id="", review_blockers=("different",))
    changed = replace(changed, implementation_plan_id=build_implementation_plan_id(changed))
    verify_implementation_plan(changed)
    with pytest.raises(ImplementationPlanError, match="implementation_plan_stale"):
        verify_implementation_plan_against_inputs(changed, scaffold, approval, value)


def test_strict_loader_rejects_unknown_fields_coercion_and_old_scaffold() -> None:
    value, approval, scaffold = chain()
    plan = build_static_provider_implementation_plan(scaffold, approval, value)
    raw = json.loads(json.dumps(plan.as_dict()))
    raw["unknown"] = True
    with pytest.raises(ImplementationPlanError, match="implementation_plan_schema_error"):
        load_implementation_plan(raw)
    raw = json.loads(json.dumps(plan.as_dict()))
    raw["compatibility_summary"]["compatible_operations"] = True
    with pytest.raises(ImplementationPlanError, match="implementation_plan_schema_error"):
        load_implementation_plan(raw)
    with pytest.raises(ValueError, match="scaffold_integrity_error"):
        build_static_provider_implementation_plan(
            replace(scaffold, scaffold_format_version="non-executable-provider-scaffold-v1"),
            approval,
            value,
        )


@pytest.mark.parametrize(
    ("base", "operation", "expected"),
    (("/", "/pets", "/pets"), ("/api", "/pets", "/api/pets"), ("/api/", "/pets", "/api/pets")),
)
def test_safe_path_join(base: str, operation: str, expected: str) -> None:
    assert safe_join_paths(base, operation) == expected


@pytest.mark.parametrize("unsafe", ("/../x", "/a//b", "/x?q=1", "/x#f", "/x\\y"))
def test_safe_path_join_rejects_unsafe_metadata(unsafe: str) -> None:
    with pytest.raises(ValueError, match="effective_path_invalid"):
        safe_join_paths("/", unsafe)


def test_cli_is_offline_and_generates_no_source(tmp_path: Path) -> None:
    value, approval, scaffold = chain()
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    for name, artifact in (
        ("proposal.json", value),
        ("approval.json", approval),
        ("provider-scaffold.json", scaffold),
    ):
        (inputs / name).write_text(json.dumps(artifact.as_dict()), encoding="utf-8")
    output = tmp_path / "output"
    with (
        patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS called")),
        patch.object(socket, "create_connection", side_effect=AssertionError("HTTP called")),
    ):
        assert (
            external_api_implementation_plan.main(
                [
                    "--proposal-file",
                    str(inputs / "proposal.json"),
                    "--approval-file",
                    str(inputs / "approval.json"),
                    "--scaffold-file",
                    str(inputs / "provider-scaffold.json"),
                    "--output-dir",
                    str(output),
                ]
            )
            == 0
        )
    assert {item.suffix for item in output.iterdir()} <= {".json", ".md"}
    source = (PROJECT_ROOT / "scripts" / "external_api_implementation_plan.py").read_text()
    for forbidden in ("--host", "--url", "--path", "--method", "--auth", "--credential"):
        assert f'add_argument("{forbidden}"' not in source
