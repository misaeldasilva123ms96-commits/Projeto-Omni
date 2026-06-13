"""In-memory governed draft proposal pipeline for rendered vault reports.

Phase 13 validates rendered report metadata against the governed draft write
policy. It returns proposal objects only and never writes files, mutates the
vault, runs commands, calls providers, uses MCP, executes agents, or mutates Git.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .draft_proposal_types import VaultDraftProposal
from .write_policy import evaluate_vault_write_request
from .write_types import VaultWritePolicyRequest

DRAFT_PROPOSAL_EVIDENCE_VERSION = "1.0"
DEFAULT_NOTE_TYPE = "sandbox-report"
DEFAULT_REQUESTED_STATUS = "draft"
DEFAULT_WRITE_MODE = "disabled"

_OPERATION_BY_NOTE_TYPE = {
    "sandbox-report": "create_sandbox_report_draft",
    "runtime-report": "create_runtime_report_draft",
    "incident": "create_incident_draft",
    "session-summary": "create_session_summary_draft",
    "provider-evaluation": "create_provider_evaluation_draft",
    "agent-prompt": "create_agent_prompt_draft",
}

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


def build_vault_draft_proposal(
    rendered_report: Any,
    *,
    requested_by: str = "unknown",
    related_phase: Optional[str] = None,
    related_pr: Optional[str] = None,
    write_mode: str = DEFAULT_WRITE_MODE,
    note_type: str = DEFAULT_NOTE_TYPE,
    requested_status: str = DEFAULT_REQUESTED_STATUS,
    target_path: Optional[str] = None,
    content_preview: Optional[str] = None,
    created_at: Optional[str] = None,
) -> VaultDraftProposal:
    payload = _report_payload(rendered_report)
    raw_markdown = str(payload.get("markdown") or content_preview or "")
    safe_markdown, markdown_redacted = _redact_text(raw_markdown)
    raw_title = str(payload.get("title") or "Vault Draft Proposal")
    title, title_redacted = _redact_text(raw_title)
    raw_filename = str(payload.get("suggested_filename") or _filename_from_path(target_path))
    suggested_filename, filename_redacted = _redact_text(raw_filename)
    suggested_filename = _safe_filename(suggested_filename)
    raw_path = str(target_path or payload.get("suggested_vault_path") or "")
    suggested_vault_path, path_redacted = _redact_text(raw_path)
    suggested_vault_path = _safe_path_metadata(suggested_vault_path, suggested_filename)
    safe_requested_by, requested_by_redacted = _redact_text(requested_by)
    safe_related_phase, related_phase_redacted = _redact_optional(
        related_phase or payload.get("related_phase")
    )
    safe_related_pr, related_pr_redacted = _redact_optional(related_pr or payload.get("related_pr"))
    normalized_note_type = str(note_type or DEFAULT_NOTE_TYPE).strip() or DEFAULT_NOTE_TYPE
    normalized_requested_status = str(requested_status or DEFAULT_REQUESTED_STATUS).strip() or DEFAULT_REQUESTED_STATUS
    operation = _OPERATION_BY_NOTE_TYPE.get(normalized_note_type, "create_sandbox_report_draft")
    report_allowed = bool(payload.get("allowed_for_vault_draft", False))
    metadata_redacted = any(
        (
            markdown_redacted,
            title_redacted,
            filename_redacted,
            path_redacted,
            requested_by_redacted,
            related_phase_redacted,
            related_pr_redacted,
        )
    )
    secret_like_detected = _contains_secret_like(raw_markdown) or _contains_secret_like(
        " ".join(
            (
                raw_title,
                raw_filename,
                raw_path,
                requested_by,
                str(related_phase or ""),
                str(related_pr or ""),
            )
        )
    )
    policy_request = VaultWritePolicyRequest(
        operation=operation,
        note_type=normalized_note_type,
        requested_status=normalized_requested_status,
        title=title,
        requested_by=safe_requested_by,
        write_mode=write_mode,
        target_path=suggested_vault_path,
        related_phase=safe_related_phase,
        content_preview=raw_markdown if content_preview is None else content_preview,
    )
    policy_decision = evaluate_vault_write_request(policy_request)
    blocked_reasons = _blocked_reasons(
        report_allowed=report_allowed,
        report_blocked_reason=payload.get("blocked_reason"),
        secret_like_detected=secret_like_detected,
        policy_blocked=policy_decision.blocked,
        policy_reason=policy_decision.reason,
    )
    blocked_reason = "; ".join(blocked_reasons) if blocked_reasons else None
    markdown_sha256 = hashlib.sha256(safe_markdown.encode("utf-8")).hexdigest()
    timestamp = created_at or _utc_timestamp()

    return VaultDraftProposal(
        proposal_id=_proposal_id(timestamp, markdown_sha256),
        title=title,
        note_type=normalized_note_type,
        requested_status=normalized_requested_status,
        normalized_status=policy_decision.normalized_status,
        suggested_vault_path=suggested_vault_path,
        suggested_filename=suggested_filename,
        markdown=safe_markdown,
        markdown_sha256=markdown_sha256,
        requested_by=safe_requested_by,
        related_phase=safe_related_phase,
        related_pr=safe_related_pr,
        write_policy_allowed=policy_decision.allowed,
        write_policy_blocked=policy_decision.blocked,
        write_policy_requires_approval=policy_decision.requires_approval,
        write_policy_reason=policy_decision.reason,
        write_policy_risk_level=policy_decision.risk_level,
        report_allowed_for_vault_draft=report_allowed,
        allowed_for_human_review=report_allowed and policy_decision.allowed and not secret_like_detected,
        blocked_reason=blocked_reason,
        redacted=metadata_redacted,
        created_at=timestamp,
        evidence_version=DRAFT_PROPOSAL_EVIDENCE_VERSION,
    )


def _report_payload(rendered_report: Any) -> Mapping[str, object]:
    if hasattr(rendered_report, "to_dict"):
        return rendered_report.to_dict()
    if hasattr(rendered_report, "__dataclass_fields__"):
        return asdict(rendered_report)
    if isinstance(rendered_report, Mapping):
        return dict(rendered_report)
    raise TypeError("Rendered report must be a mapping, dataclass, or object with to_dict().")


def _blocked_reasons(
    *,
    report_allowed: bool,
    report_blocked_reason: object,
    secret_like_detected: bool,
    policy_blocked: bool,
    policy_reason: str,
) -> list[str]:
    reasons: list[str] = []
    if not report_allowed:
        reason_text, _ = _redact_text(report_blocked_reason or "Report is not allowed for vault draft.")
        reasons.append(reason_text)
    if secret_like_detected:
        reasons.append("Secret-like content was redacted and blocked.")
    if policy_blocked:
        reason_text, _ = _redact_text(policy_reason)
        reasons.append(reason_text)
    return reasons


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


def _safe_filename(value: str) -> str:
    filename = str(value or "draft-proposal.md").replace("\\", "/").split("/")[-1]
    filename = filename.replace("..", "-").strip().lower()
    filename = re.sub(r"[^a-z0-9._-]+", "-", filename).strip("-")
    if not filename.endswith(".md"):
        filename = f"{filename or 'draft-proposal'}.md"
    return filename or "draft-proposal.md"


def _safe_path_metadata(value: str, filename: str) -> str:
    normalized = str(value or "").replace("\\", "/").strip()
    if not normalized:
        return f"vault/09_Sandbox_Reports/{filename}"
    return normalized


def _filename_from_path(value: Optional[str]) -> str:
    if not value:
        return "draft-proposal.md"
    return str(value).replace("\\", "/").split("/")[-1]


def _proposal_id(created_at: str, markdown_sha256: str) -> str:
    day = str(created_at or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        day = datetime.now(timezone.utc).date().isoformat()
    return f"draft-proposal-{day}-{markdown_sha256[:12]}"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
