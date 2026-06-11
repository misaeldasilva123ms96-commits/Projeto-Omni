"""Markdown report rendering for sandbox Runtime Truth evidence.

Phase 6 renders report content and suggested vault metadata only. It does not
create files, execute commands, call MCP, invoke agents, or perform network
access.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping, Optional


DEFAULT_REPORT_OWNER = "Misael"
DEFAULT_REPORT_PHASE = "Phase 6"
DEFAULT_REPORT_STATUS = "draft"
SANDBOX_REPORT_TYPE = "sandbox-report"
SANDBOX_REPORT_FILENAME_SUFFIX = "sandbox-policy-decision.md"

REDACTION_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"OPENAI[_A-Z0-9]*", re.IGNORECASE),
    re.compile(r"SUPABASE[_A-Z0-9]*", re.IGNORECASE),
    re.compile(r"PRIVATE_KEY", re.IGNORECASE),
    re.compile(r"API_KEY", re.IGNORECASE),
    re.compile(r"SECRET", re.IGNORECASE),
    re.compile(r"TOKEN", re.IGNORECASE),
    re.compile(r"PASSWORD", re.IGNORECASE),
    re.compile(r"JWT", re.IGNORECASE),
    re.compile(r"\.env", re.IGNORECASE),
)


@dataclass(frozen=True)
class SandboxReport:
    suggested_filename: str
    suggested_vault_path: str
    markdown: str
    status: str
    evidence_event_type: str
    governance_decision: str
    execution_attempted: bool
    command_executed: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def render_sandbox_policy_report(
    evidence: Any,
    *,
    title: str = "Sandbox Report",
    report_status: str = DEFAULT_REPORT_STATUS,
    owner: str = DEFAULT_REPORT_OWNER,
    related_branch: Optional[str] = None,
    related_phase: str = DEFAULT_REPORT_PHASE,
    report_date: Optional[str] = None,
) -> SandboxReport:
    payload = _evidence_payload(evidence)
    created_at = report_date or str(payload.get("timestamp") or _utc_timestamp())
    report_day = _safe_report_date(created_at)
    filename = f"{report_day}-{SANDBOX_REPORT_FILENAME_SUFFIX}"
    suggested_vault_path = f"vault/09_Sandbox_Reports/{filename}"

    evidence_event_type = str(payload.get("event_type", "unknown"))
    governance_decision = str(payload.get("governance_decision", "blocked"))
    execution_attempted = bool(payload.get("execution_attempted", False))
    command_executed = bool(payload.get("command_executed", False))

    markdown = _render_markdown(
        payload=payload,
        title=title,
        report_status=report_status,
        owner=owner,
        related_branch=related_branch,
        related_phase=related_phase,
        created_at=created_at,
    )

    return SandboxReport(
        suggested_filename=filename,
        suggested_vault_path=suggested_vault_path,
        markdown=markdown,
        status=report_status,
        evidence_event_type=evidence_event_type,
        governance_decision=governance_decision,
        execution_attempted=execution_attempted,
        command_executed=command_executed,
    )


def redact_report_text(value: object) -> str:
    text = "" if value is None else str(value)
    for pattern in REDACTION_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _render_markdown(
    *,
    payload: Mapping[str, object],
    title: str,
    report_status: str,
    owner: str,
    related_branch: Optional[str],
    related_phase: str,
    created_at: str,
) -> str:
    command = redact_report_text(payload.get("command", ""))
    normalized_command = redact_report_text(payload.get("normalized_command", ""))
    policy_reason = redact_report_text(payload.get("policy_reason", ""))
    matched_rule = redact_report_text(payload.get("matched_rule", ""))
    governance_decision = str(payload.get("governance_decision", "blocked"))
    risk_level = str(payload.get("policy_risk_level", "high"))
    execution_attempted = bool(payload.get("execution_attempted", False))
    command_executed = bool(payload.get("command_executed", False))

    lines = [
        "---",
        f"type: {SANDBOX_REPORT_TYPE}",
        f"status: {report_status}",
        f"created_at: {created_at}",
        f"owner: {owner}",
        f"related_phase: {related_phase}",
        f"related_branch: {related_branch or ''}",
        f"risk_level: {risk_level}",
        f"governance_decision: {governance_decision}",
        f"execution_attempted: {str(execution_attempted).lower()}",
        f"command_executed: {str(command_executed).lower()}",
        f"evidence_version: {payload.get('evidence_version', 'unknown')}",
        "---",
        "",
        "# Sandbox Report",
        "",
        "## Summary",
        "",
        f"{title} for `{governance_decision}` sandbox policy evidence.",
        "",
        "## Policy Decision",
        "",
        f"- Category: `{payload.get('policy_category', 'unknown')}`",
        f"- Risk level: `{risk_level}`",
        f"- Reason: {policy_reason}",
        f"- Matched rule: `{matched_rule}`",
        "",
        "## Runtime Truth Evidence",
        "",
        f"- Event type: `{payload.get('event_type', 'unknown')}`",
        f"- Evidence version: `{payload.get('evidence_version', 'unknown')}`",
        f"- Runtime mode: `{payload.get('runtime_mode', 'unknown')}`",
        f"- Sandbox mode: `{payload.get('sandbox_mode', 'unknown')}`",
        f"- Requested by: `{payload.get('requested_by', 'unknown')}`",
        "",
        "## Command Safety",
        "",
        f"- Command: `{command}`",
        f"- Normalized command: `{normalized_command}`",
        f"- Policy allowed: `{str(bool(payload.get('policy_allowed', False))).lower()}`",
        f"- Policy blocked: `{str(bool(payload.get('policy_blocked', True))).lower()}`",
        "- Requires approval: "
        f"`{str(bool(payload.get('policy_requires_approval', True))).lower()}`",
        "",
        "## Governance Decision",
        "",
        f"`{governance_decision}`",
        "",
        "## Execution Status",
        "",
        f"- Execution attempted: `{str(execution_attempted).lower()}`",
        f"- Command executed: `{str(command_executed).lower()}`",
        f"- Network used: `{str(bool(payload.get('network_used', False))).lower()}`",
        f"- Secrets detected: `{str(bool(payload.get('secrets_detected', False))).lower()}`",
        "",
        "## Risks",
        "",
        "The report is generated from policy evidence only. "
        "It does not prove command execution.",
        "",
        "## Next Recommended Action",
        "",
        "Review the evidence manually before saving any report into the governed vault.",
        "",
    ]
    return "\n".join(lines)


def _evidence_payload(evidence: Any) -> Mapping[str, object]:
    if hasattr(evidence, "to_dict"):
        payload = evidence.to_dict()
    elif hasattr(evidence, "__dataclass_fields__"):
        payload = asdict(evidence)
    elif isinstance(evidence, Mapping):
        payload = dict(evidence)
    else:
        raise TypeError(
            "Evidence must be a mapping, dataclass, or object with to_dict()."
        )
    return payload


def _safe_report_date(value: str) -> str:
    candidate = str(value or "")[:10]
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).date().isoformat()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
