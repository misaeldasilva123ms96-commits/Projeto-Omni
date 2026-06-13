"""Human Approval Gate for governed in-memory proposals.

Phase 14 decides whether a proposal may be presented for human review. It does
not approve proposals, write files, change vault status, execute agents, run
commands, call providers, use MCP, create PRs, merge PRs, or mutate Git.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .approval_types import HumanApprovalGateDecision, HumanApprovalGateRequest

APPROVAL_GATE_EVIDENCE_VERSION = "1.0"
DEFAULT_REQUESTED_DECISION = "submit_for_review"
TRUSTED_STATUS_REASON = "Automation cannot promote trusted or final vault statuses."
SECRET_REASON = "Credential-like content was detected and redacted."
SAFE_REVIEW_REASON = "Proposal may be presented for human review."

ALLOWED_DECISIONS = frozenset(
    {
        "submit_for_review",
        "request_changes",
        "reject",
        "hold",
    }
)

BLOCKED_DECISIONS = frozenset(
    {
        "approve",
        "auto_approve",
        "write_to_vault",
        "promote_to_reviewed",
        "promote_to_approved",
        "merge_pr",
        "push_main",
        "bypass_governance",
    }
)

ALLOWED_PROPOSAL_TYPES = frozenset(
    {
        "agent-sandbox-report",
        "sandbox-report",
        "runtime-report",
        "incident",
        "session-summary",
        "provider-evaluation",
        "agent-prompt",
    }
)

BLOCKED_PROPOSAL_TYPES = frozenset(
    {
        "adr",
        "governance-policy",
        "security-policy",
        "architecture-approved",
        "contract",
        "secret",
        "credential",
    }
)

FINAL_STATUSES = frozenset({"approved", "reviewed", "deprecated", "archived"})

ALLOWED_TARGET_PREFIXES = (
    "vault/09_Sandbox_Reports/",
    "vault/03_Runtime_Truth/",
    "vault/06_Incidents/",
    "vault/05_Agent_Prompts/",
    "vault/10_Provider_Research/",
)

_SECRET_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9])" + "s" + r"k-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile("API" + r"_KEY", re.IGNORECASE),
    re.compile("SEC" + r"RET", re.IGNORECASE),
    re.compile("TO" + r"KEN", re.IGNORECASE),
    re.compile("PASS" + r"WORD", re.IGNORECASE),
    re.compile("SUPA" + r"BASE", re.IGNORECASE),
    re.compile("OPEN" + r"AI", re.IGNORECASE),
    re.compile("J" + r"WT", re.IGNORECASE),
    re.compile("PRIVATE" + r"_KEY", re.IGNORECASE),
    re.compile(r"\." + "env", re.IGNORECASE),
)


def evaluate_human_approval_gate(
    request_or_proposal: HumanApprovalGateRequest | Mapping[str, Any] | Any,
    *,
    reviewer_id: Optional[str] = None,
    reviewer_role: Optional[str] = None,
    requested_decision: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    created_at: Optional[str] = None,
) -> HumanApprovalGateDecision:
    request = _coerce_request(
        request_or_proposal,
        reviewer_id=reviewer_id,
        reviewer_role=reviewer_role,
        requested_decision=requested_decision,
        metadata=metadata,
    )
    raw_metadata_text = _metadata_text(request.metadata)
    secret_detected = any(
        _contains_secret_like(value)
        for value in (
            request.proposal_id,
            request.requested_by,
            request.reviewer_id,
            request.reviewer_role,
            request.target_path,
            request.related_phase,
            request.related_pr,
            request.source_blocked_reason,
            raw_metadata_text,
        )
    )
    proposal_id, proposal_id_redacted = _redact_text(request.proposal_id)
    requested_by, requested_by_redacted = _redact_text(request.requested_by)
    safe_reviewer_id, reviewer_id_redacted = _redact_optional(request.reviewer_id)
    safe_reviewer_role, reviewer_role_redacted = _redact_optional(request.reviewer_role)
    safe_target_path, target_path_redacted = _redact_optional(request.target_path)
    safe_related_phase, related_phase_redacted = _redact_optional(request.related_phase)
    safe_related_pr, related_pr_redacted = _redact_optional(request.related_pr)
    safe_source_blocked_reason, blocked_reason_redacted = _redact_optional(
        request.source_blocked_reason
    )

    requested_action = str(request.requested_decision or DEFAULT_REQUESTED_DECISION).strip()
    normalized_status = str(request.requested_status or "draft").strip().lower() or "draft"
    proposal_type = str(request.proposal_type or "").strip()
    target_path_allowed = _target_path_allowed(safe_target_path)
    blocked_reasons = _blocked_reasons(
        request=request,
        requested_action=requested_action,
        normalized_status=normalized_status,
        proposal_type=proposal_type,
        target_path_allowed=target_path_allowed,
        secret_detected=secret_detected,
        source_blocked_reason=safe_source_blocked_reason,
    )
    blocked = bool(blocked_reasons)
    allowed_for_review = not blocked
    reason = _reason(
        blocked=blocked,
        requested_action=requested_action,
        normalized_status=normalized_status,
        secret_detected=secret_detected,
    )
    safe_reason, reason_redacted = _redact_text(reason)
    blocked_reason = "; ".join(blocked_reasons) if blocked_reasons else None
    safe_blocked_reason, blocked_reason_output_redacted = _redact_optional(blocked_reason)
    risk_level = _risk_level(
        blocked=blocked,
        requested_status=normalized_status,
        secret_detected=secret_detected,
        requested_risk=request.risk_level,
    )
    timestamp = created_at or _utc_timestamp()

    return HumanApprovalGateDecision(
        approval_gate_id=_approval_gate_id(timestamp, proposal_id),
        proposal_id=proposal_id,
        proposal_type=proposal_type,
        requested_decision=requested_action,
        requested_by=requested_by,
        reviewer_id=safe_reviewer_id,
        reviewer_role=safe_reviewer_role,
        allowed_for_review=allowed_for_review,
        blocked=blocked,
        requires_human_approval=True,
        can_auto_approve=False,
        can_auto_write=False,
        can_change_status=False,
        can_promote_to_reviewed=False,
        can_promote_to_approved=False,
        can_merge=False,
        can_push_main=False,
        normalized_status=normalized_status,
        target_path_allowed=target_path_allowed,
        governance_decision=_governance_decision(
            blocked=blocked,
            allowed_for_review=allowed_for_review,
            requested_action=requested_action,
        ),
        risk_level=risk_level,
        reason=safe_reason,
        blocked_reason=safe_blocked_reason,
        related_phase=safe_related_phase,
        related_pr=safe_related_pr,
        redacted=any(
            (
                proposal_id_redacted,
                requested_by_redacted,
                reviewer_id_redacted,
                reviewer_role_redacted,
                target_path_redacted,
                related_phase_redacted,
                related_pr_redacted,
                blocked_reason_redacted,
                reason_redacted,
                blocked_reason_output_redacted,
                secret_detected,
            )
        ),
        created_at=timestamp,
        evidence_version=request.evidence_version or APPROVAL_GATE_EVIDENCE_VERSION,
    )


def _coerce_request(
    value: HumanApprovalGateRequest | Mapping[str, Any] | Any,
    *,
    reviewer_id: Optional[str],
    reviewer_role: Optional[str],
    requested_decision: Optional[str],
    metadata: Optional[dict[str, Any]],
) -> HumanApprovalGateRequest:
    if isinstance(value, HumanApprovalGateRequest):
        if not any((reviewer_id, reviewer_role, requested_decision, metadata)):
            return value
        payload = value.to_dict()
    elif hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError("Approval gate input must be a request, mapping, or object with to_dict().")

    proposal_type = str(
        payload.get("proposal_type")
        or payload.get("report_type")
        or payload.get("note_type")
        or ""
    )
    return HumanApprovalGateRequest(
        proposal_id=str(payload.get("proposal_id") or ""),
        proposal_type=proposal_type,
        requested_by=str(payload.get("requested_by") or "unknown"),
        reviewer_id=reviewer_id if reviewer_id is not None else payload.get("reviewer_id"),
        reviewer_role=reviewer_role if reviewer_role is not None else payload.get("reviewer_role"),
        requested_decision=requested_decision
        or str(payload.get("requested_decision") or DEFAULT_REQUESTED_DECISION),
        source_governance_decision=payload.get("source_governance_decision")
        or payload.get("governance_decision"),
        source_allowed_for_human_review=bool(
            payload.get(
                "source_allowed_for_human_review",
                payload.get("allowed_for_human_review", False),
            )
        ),
        source_write_policy_allowed=bool(
            payload.get(
                "source_write_policy_allowed",
                payload.get("write_policy_allowed", False),
            )
        ),
        source_write_policy_requires_approval=bool(
            payload.get(
                "source_write_policy_requires_approval",
                payload.get("write_policy_requires_approval", True),
            )
        ),
        source_report_allowed_for_vault_draft=bool(
            payload.get(
                "source_report_allowed_for_vault_draft",
                payload.get("report_allowed_for_vault_draft", False),
            )
        ),
        source_blocked_reason=payload.get("source_blocked_reason") or payload.get("blocked_reason"),
        target_path=payload.get("target_path") or payload.get("suggested_vault_path"),
        note_type=payload.get("note_type"),
        requested_status=str(payload.get("requested_status") or "draft"),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        risk_level=payload.get("risk_level") or payload.get("write_policy_risk_level"),
        evidence_version=payload.get("evidence_version"),
        metadata=metadata or dict(payload.get("metadata") or {}),
    )


def _blocked_reasons(
    *,
    request: HumanApprovalGateRequest,
    requested_action: str,
    normalized_status: str,
    proposal_type: str,
    target_path_allowed: bool,
    secret_detected: bool,
    source_blocked_reason: Optional[str],
) -> list[str]:
    reasons: list[str] = []
    if secret_detected:
        reasons.append(SECRET_REASON)
    if requested_action in BLOCKED_DECISIONS or requested_action not in ALLOWED_DECISIONS:
        reasons.append("Requested decision is blocked by governance policy.")
    if normalized_status in FINAL_STATUSES:
        reasons.append(TRUSTED_STATUS_REASON)
    elif normalized_status != "draft":
        reasons.append("Only draft status may be presented to the approval gate.")
    if proposal_type in BLOCKED_PROPOSAL_TYPES or proposal_type not in ALLOWED_PROPOSAL_TYPES:
        reasons.append("Proposal type is blocked by governance policy.")
    if not target_path_allowed:
        reasons.append("Target path is outside governed review paths.")
    if not request.source_allowed_for_human_review:
        reasons.append("Source proposal is not allowed for human review.")
    if not request.source_write_policy_allowed:
        reasons.append("Source write policy did not allow draft proposal.")
    if not request.source_write_policy_requires_approval:
        reasons.append("Source write policy did not require human approval.")
    if not request.source_report_allowed_for_vault_draft:
        reasons.append("Source report is not allowed for vault draft.")
    if source_blocked_reason:
        reasons.append(str(source_blocked_reason))
    return reasons


def _reason(
    *,
    blocked: bool,
    requested_action: str,
    normalized_status: str,
    secret_detected: bool,
) -> str:
    if secret_detected:
        return SECRET_REASON
    if normalized_status in {"approved", "reviewed"}:
        return TRUSTED_STATUS_REASON
    if blocked:
        return "Proposal cannot be presented for human review."
    if requested_action == "request_changes":
        return "Proposal may be returned for human changes."
    if requested_action == "reject":
        return "Proposal may be rejected by human review flow."
    if requested_action == "hold":
        return "Proposal may be held for later human review."
    return SAFE_REVIEW_REASON


def _governance_decision(
    *,
    blocked: bool,
    allowed_for_review: bool,
    requested_action: str,
) -> str:
    if blocked:
        return "blocked"
    if requested_action == "request_changes":
        return "requires_changes"
    if requested_action == "reject":
        return "rejected"
    if requested_action == "hold":
        return "hold"
    if allowed_for_review:
        return "requires_human_approval"
    return "blocked"


def _risk_level(
    *,
    blocked: bool,
    requested_status: str,
    secret_detected: bool,
    requested_risk: Optional[str],
) -> str:
    if secret_detected or requested_status in {"approved", "reviewed"}:
        return "critical"
    if blocked:
        return str(requested_risk or "high")
    return str(requested_risk or "medium")


def _target_path_allowed(target_path: Optional[str]) -> bool:
    if not target_path:
        return True
    normalized = str(target_path).replace("\\", "/").strip()
    lowered = normalized.lower()
    if not normalized.endswith(".md"):
        return False
    if ".env" in lowered:
        return False
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        return False
    if normalized.startswith("../") or "/../" in normalized or normalized.endswith("/.."):
        return False
    if normalized.startswith("docs/"):
        return False
    if not normalized.startswith("vault/"):
        return False
    if normalized.startswith("vault/08_ADR/"):
        return False
    return any(normalized.startswith(prefix) for prefix in ALLOWED_TARGET_PREFIXES)


def _redact_optional(value: object) -> tuple[Optional[str], bool]:
    if value is None:
        return None, False
    return _redact_text(value)


def _redact_text(value: object) -> tuple[str, bool]:
    text = "" if value is None else str(value)
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted, redacted != text


def _contains_secret_like(value: object) -> bool:
    text = "" if value is None else str(value)
    return any(pattern.search(text) for pattern in _SECRET_PATTERNS)


def _metadata_text(metadata: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key, value in metadata.items():
        parts.append(str(key))
        if isinstance(value, Mapping):
            parts.append(_metadata_text(value))
        elif isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value)
        else:
            parts.append(str(value))
    return " ".join(parts)


def _approval_gate_id(created_at: str, proposal_id: str) -> str:
    day = str(created_at or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        day = datetime.now(timezone.utc).date().isoformat()
    digest = hashlib.sha256(str(proposal_id).encode("utf-8")).hexdigest()[:12]
    return f"approval-gate-{day}-{digest}"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
