"""Types for future governed draft-only vault write policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class VaultWritePolicyRequest:
    operation: str
    note_type: str
    requested_status: Optional[str] = None
    title: Optional[str] = None
    requested_by: str = "unknown"
    write_mode: str = "disabled"
    target_path: Optional[str] = None
    related_branch: Optional[str] = None
    related_phase: Optional[str] = None
    content_preview: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class VaultWritePolicyDecision:
    allowed: bool
    blocked: bool
    requires_approval: bool
    operation: str
    note_type: str
    requested_status: str
    normalized_status: str
    category: str
    risk_level: str
    reason: str
    write_mode: str
    draft_only: bool
    write_attempted: bool
    approval_attempted: bool
    destructive_attempted: bool
    secret_risk_detected: bool
    target_path_allowed: bool
    suggested_status: str
    evidence_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
