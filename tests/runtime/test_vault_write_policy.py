from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.vault import (
    VaultWritePolicyDecision,
    VaultWritePolicyRequest,
    evaluate_vault_write_request,
)
from brain.runtime.vault.write_policy import (
    DISABLED_REASON,
    DRAFT_ALLOWED_REASON,
    STATUS_BLOCKED_REASON,
    TARGET_PATH_BLOCKED_REASON,
)


def _request(
    operation: str,
    *,
    note_type: str = "sandbox-report",
    requested_status: str | None = "draft",
    write_mode: str = "draft_only",
    target_path: str | None = None,
    content_preview: str | None = None,
) -> VaultWritePolicyRequest:
    return VaultWritePolicyRequest(
        operation=operation,
        note_type=note_type,
        requested_status=requested_status,
        write_mode=write_mode,
        target_path=target_path,
        content_preview=content_preview,
        requested_by="codex",
        related_branch="vault/write-draft-policy",
        related_phase="phase-9",
    )


def _decision(
    operation: str,
    *,
    note_type: str = "sandbox-report",
    requested_status: str | None = "draft",
    write_mode: str = "draft_only",
    target_path: str | None = None,
    content_preview: str | None = None,
) -> VaultWritePolicyDecision:
    return evaluate_vault_write_request(
        _request(
            operation,
            note_type=note_type,
            requested_status=requested_status,
            write_mode=write_mode,
            target_path=target_path,
            content_preview=content_preview,
        )
    )


def test_disabled_mode_blocks_create_sandbox_report_draft() -> None:
    decision = _decision("create_sandbox_report_draft", write_mode="disabled")

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.requires_approval is True
    assert decision.reason == DISABLED_REASON
    assert decision.write_mode == "disabled"
    assert decision.draft_only is False
    assert decision.write_attempted is True
    assert decision.suggested_status == "draft"
    assert decision.evidence_version == "1.0"


def test_draft_only_mode_allows_draft_creation_operations() -> None:
    cases = (
        ("create_sandbox_report_draft", "sandbox-report"),
        ("create_runtime_report_draft", "runtime-report"),
        ("create_incident_draft", "incident"),
        ("create_session_summary_draft", "session-summary"),
        ("create_provider_evaluation_draft", "provider-evaluation"),
        ("create_agent_prompt_draft", "agent-prompt"),
    )

    for operation, note_type in cases:
        decision = _decision(operation, note_type=note_type)

        assert decision.allowed is True
        assert decision.blocked is False
        assert decision.requires_approval is True
        assert decision.category == "draft_creation"
        assert decision.risk_level == "medium"
        assert decision.reason == DRAFT_ALLOWED_REASON
        assert decision.normalized_status == "draft"
        assert decision.suggested_status == "draft"
        assert decision.draft_only is True
        assert decision.write_attempted is True
        assert decision.approval_attempted is False
        assert decision.destructive_attempted is False
        assert decision.secret_risk_detected is False
        assert decision.target_path_allowed is True


def test_missing_requested_status_defaults_to_draft() -> None:
    decision = _decision("create_runtime_report_draft", note_type="runtime-report", requested_status=None)

    assert decision.allowed is True
    assert decision.requested_status == ""
    assert decision.normalized_status == "draft"
    assert decision.suggested_status == "draft"


def test_trusted_and_final_status_requests_are_blocked() -> None:
    cases = (
        ("approved", True, "critical"),
        ("reviewed", True, "critical"),
        ("deprecated", False, "high"),
        ("archived", False, "high"),
    )

    for status, approval_attempted, risk_level in cases:
        decision = _decision("create_sandbox_report_draft", requested_status=status)

        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.reason == STATUS_BLOCKED_REASON
        assert decision.approval_attempted is approval_attempted
        assert decision.risk_level == risk_level
        assert decision.suggested_status == "draft"


def test_blocked_governance_operations_are_critical() -> None:
    operations = (
        "approve_note",
        "edit_approved_note",
        "delete_note",
        "rename_note",
        "move_note",
        "overwrite_note",
        "modify_adr",
        "edit_governance_policy",
    )

    for operation in operations:
        decision = _decision(operation)

        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.requires_approval is True
        assert decision.risk_level == "critical"


def test_approval_and_destructive_flags_are_set() -> None:
    approve = _decision("approve_note")
    delete = _decision("delete_note")
    rename = _decision("rename_note")
    move = _decision("move_note")
    overwrite = _decision("overwrite_note")

    assert approve.approval_attempted is True
    assert delete.destructive_attempted is True
    assert rename.destructive_attempted is True
    assert move.destructive_attempted is True
    assert overwrite.destructive_attempted is True


def test_unknown_operation_is_blocked() -> None:
    decision = _decision("create_architecture_draft")

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.requires_approval is True
    assert decision.category == "unknown"
    assert decision.risk_level == "high"


def test_sensitive_note_types_are_blocked() -> None:
    for note_type in ("adr", "governance-policy", "security-policy", "secret"):
        decision = _decision("create_sandbox_report_draft", note_type=note_type)

        assert decision.allowed is False
        assert decision.category == "sensitive_note_type"
        assert decision.risk_level == "critical"


def test_target_path_safety_blocks_unsafe_paths() -> None:
    paths = (
        "../vault/09_Sandbox_Reports/report.md",
        "C:/Users/Misael/vault/09_Sandbox_Reports/report.md",
        "vault/09_Sandbox_Reports/report.txt",
        "docs/report.md",
        "vault/08_ADR/adr.md",
        "outside/report.md",
        "vault/09_Sandbox_Reports/.env.md",
    )

    for target_path in paths:
        decision = _decision("create_sandbox_report_draft", target_path=target_path)

        assert decision.allowed is False
        assert decision.reason == TARGET_PATH_BLOCKED_REASON
        assert decision.target_path_allowed is False
        assert decision.risk_level == "critical"


def test_allowed_vault_report_path_is_accepted() -> None:
    decision = _decision(
        "create_sandbox_report_draft",
        target_path="vault/09_Sandbox_Reports/phase-9-report.md",
    )

    assert decision.allowed is True
    assert decision.target_path_allowed is True


def test_secret_like_content_preview_is_blocked() -> None:
    cases = (
        "contains OPENAI_API_KEY placeholder",
        "Authorization: Bearer token",
    )

    for content_preview in cases:
        decision = _decision("create_sandbox_report_draft", content_preview=content_preview)

        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.secret_risk_detected is True
        assert decision.risk_level == "critical"


def test_network_provider_command_and_secret_operations_are_blocked() -> None:
    for operation in ("network_fetch", "provider_call", "execute_command", "write_secret"):
        decision = _decision(operation)

        assert decision.allowed is False
        assert decision.risk_level == "critical"
        assert decision.write_attempted is True


def test_write_blocked_mode_blocks_draft_creation() -> None:
    decision = _decision("create_incident_draft", note_type="incident", write_mode="write_blocked")

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.write_mode == "write_blocked"
    assert decision.draft_only is False


def test_request_and_decision_objects_are_json_serializable() -> None:
    request = _request(
        "create_provider_evaluation_draft",
        note_type="provider-evaluation",
        target_path="vault/10_Provider_Research/provider.md",
    )
    decision = evaluate_vault_write_request(request)

    request_json = json.dumps(request.to_dict(), sort_keys=True)
    decision_json = json.dumps(decision.to_dict(), sort_keys=True)

    assert '"operation": "create_provider_evaluation_draft"' in request_json
    assert '"allowed": true' in decision_json
    assert '"suggested_status": "draft"' in decision_json
