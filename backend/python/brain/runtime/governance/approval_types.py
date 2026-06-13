"""Types for the Human Approval Gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class HumanApprovalGateRequest:
    proposal_id: str
    proposal_type: str
    requested_by: str = "unknown"
    reviewer_id: Optional[str] = None
    reviewer_role: Optional[str] = None
    requested_decision: str = "submit_for_review"
    source_governance_decision: Optional[str] = None
    source_allowed_for_human_review: bool = False
    source_write_policy_allowed: bool = False
    source_write_policy_requires_approval: bool = True
    source_report_allowed_for_vault_draft: bool = False
    source_blocked_reason: Optional[str] = None
    target_path: Optional[str] = None
    note_type: Optional[str] = None
    requested_status: str = "draft"
    related_phase: Optional[str] = None
    related_pr: Optional[str] = None
    risk_level: Optional[str] = None
    evidence_version: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class HumanApprovalGateDecision:
    approval_gate_id: str
    proposal_id: str
    proposal_type: str
    requested_decision: str
    requested_by: str
    reviewer_id: Optional[str]
    reviewer_role: Optional[str]
    allowed_for_review: bool
    blocked: bool
    requires_human_approval: bool
    can_auto_approve: bool
    can_auto_write: bool
    can_change_status: bool
    can_promote_to_reviewed: bool
    can_promote_to_approved: bool
    can_merge: bool
    can_push_main: bool
    normalized_status: str
    target_path_allowed: bool
    governance_decision: str
    risk_level: str
    reason: str
    blocked_reason: Optional[str]
    related_phase: Optional[str]
    related_pr: Optional[str]
    redacted: bool
    created_at: str
    evidence_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
