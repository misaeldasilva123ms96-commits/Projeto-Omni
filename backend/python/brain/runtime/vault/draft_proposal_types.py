"""Types for governed in-memory vault draft proposals."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class VaultDraftProposal:
    proposal_id: str
    title: str
    note_type: str
    requested_status: str
    normalized_status: str
    suggested_vault_path: str
    suggested_filename: str
    markdown: str
    markdown_sha256: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    write_policy_allowed: bool
    write_policy_blocked: bool
    write_policy_requires_approval: bool
    write_policy_reason: str
    write_policy_risk_level: str
    report_allowed_for_vault_draft: bool
    allowed_for_human_review: bool
    blocked_reason: Optional[str]
    redacted: bool
    created_at: str
    evidence_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
