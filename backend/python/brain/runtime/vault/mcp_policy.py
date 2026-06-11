"""Policy-only classification for future read-only MCP vault access.

This module does not start MCP, import MCP SDKs, call providers, read vault
files, write vault files, execute commands, or perform network access.
"""

from __future__ import annotations

from .mcp_types import VaultMCPPolicyDecision, VaultMCPRequest

MCP_POLICY_EVIDENCE_VERSION = "1.0"

MCP_MODE_DISABLED = "disabled"
MCP_MODE_READ_ONLY = "read_only"
MCP_MODE_WRITE_BLOCKED = "write_blocked"

ALLOWED_READ_ONLY_OPERATIONS = frozenset(
    {
        "list_notes",
        "read_note",
        "search_notes",
        "get_frontmatter",
    }
)

WRITE_OPERATIONS = frozenset(
    {
        "write_note",
        "edit_note",
        "delete_note",
        "rename_note",
        "move_note",
        "create_note",
        "update_frontmatter",
        "attach_file",
    }
)

COMMAND_OPERATIONS = frozenset(
    {
        "run_command",
        "execute_tool",
    }
)

PROVIDER_OPERATIONS = frozenset({"provider_call"})
NETWORK_OPERATIONS = frozenset({"network_fetch"})

BLOCKED_OPERATIONS = (
    WRITE_OPERATIONS | COMMAND_OPERATIONS | PROVIDER_OPERATIONS | NETWORK_OPERATIONS
)

SUPPORTED_MODES = frozenset(
    {
        MCP_MODE_DISABLED,
        MCP_MODE_READ_ONLY,
        MCP_MODE_WRITE_BLOCKED,
    }
)

ALLOWED_VAULT_STATUSES = ["approved", "reviewed"]
BLOCKED_STATUSES = ["draft", "review", "deprecated", "archived", "unknown"]

DISABLED_REASON = "MCP vault access is disabled by default."
UNKNOWN_REASON = "Unknown MCP vault operation is blocked by default."
WRITE_BLOCKED_REASON = "MCP vault write, delete, attach, and mutation operations are blocked."
COMMAND_BLOCKED_REASON = "MCP vault command execution operations are blocked."
NETWORK_BLOCKED_REASON = "MCP vault network operations are blocked."
PROVIDER_BLOCKED_REASON = "MCP vault provider calls are blocked."
READ_ALLOWED_REASON = "MCP vault read-only policy permits this future read operation."
UNSUPPORTED_MODE_REASON = "Unsupported MCP vault mode is blocked."


def evaluate_mcp_vault_request(request: VaultMCPRequest) -> VaultMCPPolicyDecision:
    operation = str(request.operation or "").strip()
    mode = str(request.mcp_mode or MCP_MODE_DISABLED).strip() or MCP_MODE_DISABLED

    if mode == MCP_MODE_DISABLED:
        return _decision(
            allowed=False,
            requires_approval=True,
            operation=operation,
            category=_category_for_operation(operation),
            risk_level="high",
            reason=DISABLED_REASON,
            mcp_mode=mode,
        )

    if mode not in SUPPORTED_MODES:
        return _decision(
            allowed=False,
            requires_approval=True,
            operation=operation,
            category="unsupported_mode",
            risk_level="high",
            reason=UNSUPPORTED_MODE_REASON,
            mcp_mode=mode,
        )

    if operation in ALLOWED_READ_ONLY_OPERATIONS:
        return _decision(
            allowed=True,
            requires_approval=False,
            operation=operation,
            category="read_only",
            risk_level="low",
            reason=READ_ALLOWED_REASON,
            mcp_mode=mode,
            read_only=True,
        )

    if operation in WRITE_OPERATIONS:
        return _decision(
            allowed=False,
            requires_approval=True,
            operation=operation,
            category="write_or_mutation",
            risk_level="critical",
            reason=WRITE_BLOCKED_REASON,
            mcp_mode=mode,
        )

    if operation in COMMAND_OPERATIONS:
        return _decision(
            allowed=False,
            requires_approval=True,
            operation=operation,
            category="command_execution",
            risk_level="critical",
            reason=COMMAND_BLOCKED_REASON,
            mcp_mode=mode,
        )

    if operation in NETWORK_OPERATIONS:
        return _decision(
            allowed=False,
            requires_approval=True,
            operation=operation,
            category="network",
            risk_level="critical",
            reason=NETWORK_BLOCKED_REASON,
            mcp_mode=mode,
        )

    if operation in PROVIDER_OPERATIONS:
        return _decision(
            allowed=False,
            requires_approval=True,
            operation=operation,
            category="provider_call",
            risk_level="critical",
            reason=PROVIDER_BLOCKED_REASON,
            mcp_mode=mode,
        )

    return _decision(
        allowed=False,
        requires_approval=True,
        operation=operation,
        category="unknown",
        risk_level="high",
        reason=UNKNOWN_REASON,
        mcp_mode=mode,
    )


def _decision(
    *,
    allowed: bool,
    requires_approval: bool,
    operation: str,
    category: str,
    risk_level: str,
    reason: str,
    mcp_mode: str,
    read_only: bool = False,
) -> VaultMCPPolicyDecision:
    return VaultMCPPolicyDecision(
        allowed=allowed,
        blocked=not allowed,
        requires_approval=requires_approval,
        operation=operation,
        category=category,
        risk_level=risk_level,
        reason=reason,
        mcp_mode=mcp_mode,
        read_only=read_only,
        write_attempted=operation in WRITE_OPERATIONS,
        network_attempted=operation in NETWORK_OPERATIONS or operation in PROVIDER_OPERATIONS,
        command_attempted=operation in COMMAND_OPERATIONS,
        allowed_vault_statuses=list(ALLOWED_VAULT_STATUSES),
        blocked_statuses=list(BLOCKED_STATUSES),
        evidence_version=MCP_POLICY_EVIDENCE_VERSION,
    )


def _category_for_operation(operation: str) -> str:
    if operation in ALLOWED_READ_ONLY_OPERATIONS:
        return "read_only"
    if operation in WRITE_OPERATIONS:
        return "write_or_mutation"
    if operation in COMMAND_OPERATIONS:
        return "command_execution"
    if operation in NETWORK_OPERATIONS:
        return "network"
    if operation in PROVIDER_OPERATIONS:
        return "provider_call"
    return "unknown"
