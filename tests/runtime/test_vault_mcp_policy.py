from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.vault import (
    VaultMCPPolicyDecision,
    VaultMCPRequest,
    evaluate_mcp_vault_request,
)
from brain.runtime.vault.mcp_policy import (
    ALLOWED_VAULT_STATUSES,
    BLOCKED_STATUSES,
    DISABLED_REASON,
    READ_ALLOWED_REASON,
    UNKNOWN_REASON,
)


def _decision(operation: str, *, mcp_mode: str = "read_only") -> VaultMCPPolicyDecision:
    return evaluate_mcp_vault_request(VaultMCPRequest(operation=operation, mcp_mode=mcp_mode))


def test_default_disabled_mode_blocks_list_notes() -> None:
    decision = evaluate_mcp_vault_request(VaultMCPRequest(operation="list_notes"))

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.requires_approval is True
    assert decision.operation == "list_notes"
    assert decision.category == "read_only"
    assert decision.risk_level == "high"
    assert decision.reason == DISABLED_REASON
    assert decision.mcp_mode == "disabled"
    assert decision.read_only is False
    assert decision.write_attempted is False
    assert decision.network_attempted is False
    assert decision.command_attempted is False
    assert decision.allowed_vault_statuses == ALLOWED_VAULT_STATUSES
    assert decision.blocked_statuses == BLOCKED_STATUSES
    assert decision.evidence_version == "1.0"


def test_default_disabled_mode_blocks_read_note() -> None:
    decision = evaluate_mcp_vault_request(
        VaultMCPRequest(operation="read_note", note_path="02_Architecture/example.md")
    )

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.reason == DISABLED_REASON


def test_read_only_mode_allows_read_operations() -> None:
    for operation in ("list_notes", "read_note", "search_notes", "get_frontmatter"):
        decision = _decision(operation)

        assert decision.allowed is True
        assert decision.blocked is False
        assert decision.requires_approval is False
        assert decision.category == "read_only"
        assert decision.risk_level == "low"
        assert decision.reason == READ_ALLOWED_REASON
        assert decision.mcp_mode == "read_only"
        assert decision.read_only is True
        assert decision.write_attempted is False
        assert decision.network_attempted is False
        assert decision.command_attempted is False


def test_write_blocked_mode_still_allows_read_only_policy_decisions() -> None:
    decision = _decision("search_notes", mcp_mode="write_blocked")

    assert decision.allowed is True
    assert decision.read_only is True
    assert decision.mcp_mode == "write_blocked"


def test_read_only_mode_blocks_write_and_mutation_operations() -> None:
    operations = (
        "write_note",
        "edit_note",
        "delete_note",
        "rename_note",
        "move_note",
        "create_note",
        "update_frontmatter",
        "attach_file",
    )

    for operation in operations:
        decision = _decision(operation)

        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.requires_approval is True
        assert decision.category == "write_or_mutation"
        assert decision.risk_level == "critical"
        assert decision.write_attempted is True
        assert decision.network_attempted is False
        assert decision.command_attempted is False


def test_read_only_mode_blocks_command_operations() -> None:
    for operation in ("run_command", "execute_tool"):
        decision = _decision(operation)

        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.requires_approval is True
        assert decision.category == "command_execution"
        assert decision.risk_level == "critical"
        assert decision.write_attempted is False
        assert decision.network_attempted is False
        assert decision.command_attempted is True


def test_read_only_mode_blocks_provider_and_network_operations() -> None:
    provider_decision = _decision("provider_call")
    network_decision = _decision("network_fetch")

    assert provider_decision.allowed is False
    assert provider_decision.category == "provider_call"
    assert provider_decision.risk_level == "critical"
    assert provider_decision.network_attempted is True
    assert network_decision.allowed is False
    assert network_decision.category == "network"
    assert network_decision.risk_level == "critical"
    assert network_decision.network_attempted is True


def test_unknown_operation_is_blocked() -> None:
    decision = _decision("summarize_note")

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.requires_approval is True
    assert decision.category == "unknown"
    assert decision.risk_level == "high"
    assert decision.reason == UNKNOWN_REASON


def test_unsupported_mcp_mode_is_blocked() -> None:
    decision = _decision("list_notes", mcp_mode="enabled")

    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.requires_approval is True
    assert decision.category == "unsupported_mode"
    assert decision.risk_level == "high"


def test_request_and_decision_objects_are_json_serializable() -> None:
    request = VaultMCPRequest(
        operation="search_notes",
        query="runtime truth",
        requested_by="codex",
        mcp_mode="read_only",
        include_blocked=True,
        max_body_chars=500,
    )
    decision = evaluate_mcp_vault_request(request)

    request_json = json.dumps(request.to_dict(), sort_keys=True)
    decision_json = json.dumps(decision.to_dict(), sort_keys=True)

    assert '"operation": "search_notes"' in request_json
    assert '"requested_by": "codex"' in request_json
    assert '"allowed": true' in decision_json
    assert '"read_only": true' in decision_json
