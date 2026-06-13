"""Markdown report rendering for agent Runtime Truth evidence.

Phase 12 renders report content and suggested vault metadata only. It does not
create files, execute agents, run commands, call providers, use MCP, or mutate
Git state.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

AGENT_REPORT_TYPE = "agent-sandbox-report"
AGENT_REPORT_EVIDENCE_VERSION = "1.0"
DEFAULT_GENERATED_BY = "omni"
DEFAULT_SUGGESTED_VAULT_DIR = "vault/09_Sandbox_Reports/"

_REDACTION_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile("s" + r"k-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile("OPEN" + r"AI[_A-Z0-9]*", re.IGNORECASE),
    re.compile("SUPA" + r"BASE[_A-Z0-9]*", re.IGNORECASE),
    re.compile("PRIVATE" + r"_KEY", re.IGNORECASE),
    re.compile("API" + r"_KEY", re.IGNORECASE),
    re.compile("SEC" + r"RET", re.IGNORECASE),
    re.compile("TO" + r"KEN", re.IGNORECASE),
    re.compile("PASS" + r"WORD", re.IGNORECASE),
    re.compile("J" + r"WT", re.IGNORECASE),
    re.compile(r"\." + "env", re.IGNORECASE),
)

_UNSAFE_FLAGS = (
    "agent_executed",
    "command_executed",
    "network_used",
    "provider_called",
    "mcp_used",
    "vault_written",
    "git_mutated",
    "main_modified",
    "command_execution_allowed",
    "network_allowed",
    "provider_call_allowed",
    "vault_write_allowed",
    "mcp_write_allowed",
    "git_merge_allowed",
)


@dataclass(frozen=True)
class AgentSandboxReport:
    markdown: str
    title: str
    suggested_filename: str
    suggested_vault_path: str
    report_type: str
    source_event_type: str
    source_evidence_version: str
    generated_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    governance_decision: str
    allowed_for_vault_draft: bool
    blocked_reason: Optional[str]
    redacted: bool
    evidence_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def render_agent_sandbox_report(
    evidence: Any,
    *,
    title: Optional[str] = None,
    generated_by: str = DEFAULT_GENERATED_BY,
    related_phase: Optional[str] = None,
    related_pr: Optional[str] = None,
    suggested_vault_dir: str = DEFAULT_SUGGESTED_VAULT_DIR,
) -> AgentSandboxReport:
    payload = _evidence_payload(evidence)
    created_at = str(payload.get("timestamp") or _utc_timestamp())
    source_event_type = _redact_text(payload.get("event_type", "unknown"))
    source_evidence_version = _redact_text(payload.get("evidence_version", "unknown"))
    governance_decision = _redact_text(payload.get("governance_decision", "blocked"))
    agent_id = _redact_text(payload.get("agent_id", "unknown"))
    requested_action = _redact_text(payload.get("requested_action", "unknown"))
    safe_title = _redact_text(title or "Agent Sandbox Report")
    safe_generated_by = _redact_text(generated_by or DEFAULT_GENERATED_BY)
    safe_related_phase = _redact_optional(related_phase or payload.get("related_phase"))
    safe_related_pr = _redact_optional(related_pr or payload.get("related_pr"))

    unsafe_reasons = _unsafe_reasons(payload)
    blocked_reason = "; ".join(unsafe_reasons) if unsafe_reasons else None
    safe_dir = _safe_vault_dir(suggested_vault_dir)
    filename = _suggested_filename(
        created_at=created_at,
        agent_id=agent_id,
        requested_action=requested_action,
        governance_decision=governance_decision,
    )
    suggested_vault_path = f"{safe_dir}{filename}"

    markdown = _render_markdown(
        payload=payload,
        title=safe_title,
        created_at=created_at,
        generated_by=safe_generated_by,
        related_phase=safe_related_phase,
        related_pr=safe_related_pr,
        governance_decision=governance_decision,
        blocked_reason=blocked_reason,
    )

    redacted = _contains_redaction(
        safe_title,
        filename,
        suggested_vault_path,
        markdown,
        safe_generated_by,
        safe_related_phase,
        safe_related_pr,
    )

    return AgentSandboxReport(
        markdown=markdown,
        title=safe_title,
        suggested_filename=filename,
        suggested_vault_path=suggested_vault_path,
        report_type=AGENT_REPORT_TYPE,
        source_event_type=source_event_type,
        source_evidence_version=source_evidence_version,
        generated_by=safe_generated_by,
        related_phase=safe_related_phase,
        related_pr=safe_related_pr,
        governance_decision=governance_decision,
        allowed_for_vault_draft=blocked_reason is None and not redacted,
        blocked_reason=blocked_reason,
        redacted=redacted,
        evidence_version=AGENT_REPORT_EVIDENCE_VERSION,
    )


def redact_agent_report_text(value: object) -> str:
    return _redact_text(value)


def _render_markdown(
    *,
    payload: Mapping[str, object],
    title: str,
    created_at: str,
    generated_by: str,
    related_phase: Optional[str],
    related_pr: Optional[str],
    governance_decision: str,
    blocked_reason: Optional[str],
) -> str:
    policy_reason = _redact_text(payload.get("policy_reason", ""))
    notes = _redact_text(payload.get("notes", ""))
    allowed_for_vault_draft = blocked_reason is None and not _contains_redaction(title, policy_reason, notes)

    lines = [
        "---",
        f"type: {AGENT_REPORT_TYPE}",
        "status: draft",
        f"owner: {generated_by}",
        f"created_at: {created_at}",
        f"source_event_type: {_redact_text(payload.get('event_type', 'unknown'))}",
        f"source_evidence_version: {_redact_text(payload.get('evidence_version', 'unknown'))}",
        f"governance_decision: {governance_decision}",
        f"related_phase: {related_phase or ''}",
        f"related_pr: {related_pr or ''}",
        "---",
        "",
        f"# {title}",
        "",
        "## Summary",
        "",
        "This report was rendered in memory from Agent Runtime Truth evidence. "
        "The suggested vault path is metadata only.",
        "",
        "## Agent Workflow",
        "",
        f"- Agent id: `{_redact_text(payload.get('agent_id', 'unknown'))}`",
        f"- Agent role: `{_redact_text(payload.get('agent_role', 'unknown'))}`",
        f"- Requested action: `{_redact_text(payload.get('requested_action', 'unknown'))}`",
        f"- Workflow mode: `{_redact_text(payload.get('workflow_mode', 'unknown'))}`",
        f"- Target branch: `{_redact_text(payload.get('target_branch', ''))}`",
        f"- Base branch: `{_redact_text(payload.get('base_branch', 'main'))}`",
        "",
        "## Policy Decision",
        "",
        f"- Policy allowed: `{_bool_text(payload.get('policy_allowed', False))}`",
        f"- Policy blocked: `{_bool_text(payload.get('policy_blocked', True))}`",
        f"- Requires approval: `{_bool_text(payload.get('policy_requires_approval', True))}`",
        f"- Category: `{_redact_text(payload.get('policy_category', 'unknown'))}`",
        f"- Risk level: `{_redact_text(payload.get('policy_risk_level', 'high'))}`",
        f"- Reason: {policy_reason}",
        f"- Governance decision: `{governance_decision}`",
        "",
        "## Safety Flags",
        "",
        f"- Main branch protected: `{_bool_text(payload.get('main_branch_protected', True))}`",
        f"- Command execution allowed: `{_bool_text(payload.get('command_execution_allowed', False))}`",
        f"- Direct file edit allowed: `{_bool_text(payload.get('direct_file_edit_allowed', False))}`",
        f"- Git push allowed: `{_bool_text(payload.get('git_push_allowed', False))}`",
        f"- Git merge allowed: `{_bool_text(payload.get('git_merge_allowed', False))}`",
        f"- PR open allowed: `{_bool_text(payload.get('pr_open_allowed', False))}`",
        f"- Network allowed: `{_bool_text(payload.get('network_allowed', False))}`",
        f"- Provider call allowed: `{_bool_text(payload.get('provider_call_allowed', False))}`",
        f"- Vault write allowed: `{_bool_text(payload.get('vault_write_allowed', False))}`",
        f"- MCP write allowed: `{_bool_text(payload.get('mcp_write_allowed', False))}`",
        "",
        "## Runtime Truth Flags",
        "",
        f"- Runtime Truth required: `{_bool_text(payload.get('runtime_truth_required', False))}`",
        f"- Sandbox required: `{_bool_text(payload.get('sandbox_required', False))}`",
        f"- Agent executed: `{_bool_text(payload.get('agent_executed', False))}`",
        f"- Command executed: `{_bool_text(payload.get('command_executed', False))}`",
        f"- Network used: `{_bool_text(payload.get('network_used', False))}`",
        f"- Provider called: `{_bool_text(payload.get('provider_called', False))}`",
        f"- MCP used: `{_bool_text(payload.get('mcp_used', False))}`",
        f"- Vault written: `{_bool_text(payload.get('vault_written', False))}`",
        f"- Git mutated: `{_bool_text(payload.get('git_mutated', False))}`",
        f"- PR created: `{_bool_text(payload.get('pr_created', False))}`",
        f"- Main modified: `{_bool_text(payload.get('main_modified', False))}`",
        "",
        "## Approval",
        "",
        f"- User approval state: `{_redact_text(payload.get('user_approval_state', 'not_requested'))}`",
        "- Human review required: `true`",
        "",
        "## Notes",
        "",
        notes or "No notes provided.",
        "",
        "## No-Execution Statement",
        "",
        "No agent was executed. No command was executed. No network request, provider call, MCP operation, "
        "vault write, Git mutation, file edit, PR creation, or PR merge occurred.",
        "",
        "## Vault Draft Safety",
        "",
        f"- Allowed for vault draft: `{str(allowed_for_vault_draft).lower()}`",
        f"- Blocked reason: {blocked_reason or 'none'}",
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
        raise TypeError("Evidence must be a mapping, dataclass, or object with to_dict().")
    return payload


def _unsafe_reasons(payload: Mapping[str, object]) -> list[str]:
    reasons = [f"{flag} is true" for flag in _UNSAFE_FLAGS if bool(payload.get(flag, False))]
    if not bool(payload.get("main_branch_protected", True)):
        reasons.append("main_branch_protected is false")
    return reasons


def _suggested_filename(
    *,
    created_at: str,
    agent_id: str,
    requested_action: str,
    governance_decision: str,
) -> str:
    day = _safe_day(created_at)
    parts = (
        "agent-report",
        day,
        agent_id,
        requested_action,
        governance_decision,
    )
    stem = "-".join(_slug(part) for part in parts)
    stem = re.sub(r"-+", "-", stem).strip("-") or "agent-report"
    return f"{stem}.md"


def _safe_vault_dir(value: str) -> str:
    raw = str(value or DEFAULT_SUGGESTED_VAULT_DIR).replace("\\", "/")
    if raw.startswith("/") or ":" in raw or ".." in raw.split("/"):
        return DEFAULT_SUGGESTED_VAULT_DIR
    if not raw.endswith("/"):
        raw = f"{raw}/"
    if not raw.startswith("vault/"):
        return DEFAULT_SUGGESTED_VAULT_DIR
    return raw


def _safe_day(value: str) -> str:
    day = str(value or "")[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return day
    return datetime.now(timezone.utc).date().isoformat()


def _slug(value: object) -> str:
    redacted = _redact_text(value).lower().replace("[redacted]", "redacted")
    redacted = redacted.replace("/", "-").replace("\\", "-").replace("..", "-")
    return re.sub(r"[^a-z0-9-]+", "-", redacted).strip("-")


def _redact_optional(value: object) -> Optional[str]:
    if value is None:
        return None
    return _redact_text(value)


def _redact_text(value: object) -> str:
    text = "" if value is None else str(value)
    for pattern in _REDACTION_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _contains_redaction(*values: object) -> bool:
    return any("[REDACTED]" in str(value) for value in values if value is not None)


def _bool_text(value: object) -> str:
    return str(bool(value)).lower()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
