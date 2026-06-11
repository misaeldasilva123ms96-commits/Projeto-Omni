"""Types for future read-only MCP access to governed vault notes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class VaultMCPRequest:
    operation: str
    note_path: Optional[str] = None
    query: Optional[str] = None
    requested_by: str = "unknown"
    mcp_mode: str = "disabled"
    include_blocked: bool = False
    max_body_chars: int = 12000

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class VaultMCPPolicyDecision:
    allowed: bool
    blocked: bool
    requires_approval: bool
    operation: str
    category: str
    risk_level: str
    reason: str
    mcp_mode: str
    read_only: bool
    write_attempted: bool
    network_attempted: bool
    command_attempted: bool
    allowed_vault_statuses: list[str]
    blocked_statuses: list[str]
    evidence_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
