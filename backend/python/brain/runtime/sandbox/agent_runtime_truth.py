"""Runtime Truth evidence for agent workflow policy decisions.

Phase 11 records agent workflow policy outcomes as evidence only. It does not
execute agents, run commands, call providers, use MCP, write vault notes, or
mutate Git state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .agent_types import AgentWorkflowPolicyDecision

AGENT_WORKFLOW_EVENT_TYPE = "agent.workflow.policy_decision"
AGENT_WORKFLOW_RUNTIME_MODE = "AGENT_POLICY_ONLY"
AGENT_WORKFLOW_EVIDENCE_VERSION = "1.0"
DEFAULT_USER_APPROVAL_STATE = "not_requested"

_REDACTION_MARKERS = (
    "sk" + "-",
    "API" + "_KEY",
    "SEC" + "RET",
    "TO" + "KEN",
    "PASS" + "WORD",
    "SUPA" + "BASE",
    "OPEN" + "AI",
    "J" + "WT",
    "PRIVATE" + "_KEY",
    "Authorization: " + "Bearer",
    "." + "env",
)


@dataclass(frozen=True)
class AgentWorkflowEvidence:
    event_type: str
    timestamp: str
    evidence_version: str
    runtime_mode: str
    agent_id: str
    agent_role: str
    requested_action: str
    workflow_mode: str
    requested_by: str
    session_id: Optional[str]
    task_id: Optional[str]
    related_phase: Optional[str]
    related_pr: Optional[str]
    target_branch: str
    base_branch: str
    policy_allowed: bool
    policy_blocked: bool
    policy_requires_approval: bool
    policy_category: str
    policy_risk_level: str
    policy_reason: str
    main_branch_protected: bool
    command_execution_allowed: bool
    direct_file_edit_allowed: bool
    git_push_allowed: bool
    git_merge_allowed: bool
    pr_open_allowed: bool
    network_allowed: bool
    provider_call_allowed: bool
    vault_write_allowed: bool
    mcp_write_allowed: bool
    runtime_truth_required: bool
    sandbox_required: bool
    agent_executed: bool
    command_executed: bool
    network_used: bool
    provider_called: bool
    mcp_used: bool
    vault_written: bool
    git_mutated: bool
    pr_created: bool
    main_modified: bool
    governance_decision: str
    user_approval_state: str
    notes: Optional[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_agent_workflow_evidence(
    decision: AgentWorkflowPolicyDecision | Mapping[str, Any],
    *,
    requested_by: Optional[str] = None,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    related_phase: Optional[str] = None,
    related_pr: Optional[str] = None,
    target_branch: Optional[str] = None,
    base_branch: Optional[str] = None,
    user_approval_state: str = DEFAULT_USER_APPROVAL_STATE,
    notes: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> AgentWorkflowEvidence:
    """Build JSON-safe evidence for an agent workflow policy decision."""
    policy_allowed = _bool_value(decision, "allowed")
    policy_blocked = _bool_value(decision, "blocked")
    policy_requires_approval = _bool_value(decision, "requires_approval", default=True)
    main_branch_protected = _bool_value(decision, "main_branch_protected", default=True)
    command_execution_allowed = _bool_value(decision, "command_execution_allowed")
    direct_file_edit_allowed = _bool_value(decision, "direct_file_edit_allowed")
    git_push_allowed = _bool_value(decision, "git_push_allowed")
    git_merge_allowed = _bool_value(decision, "git_merge_allowed")
    pr_open_allowed = _bool_value(decision, "pr_open_allowed")
    network_allowed = _bool_value(decision, "network_allowed")
    provider_call_allowed = _bool_value(decision, "provider_call_allowed")
    vault_write_allowed = _bool_value(decision, "vault_write_allowed")
    mcp_write_allowed = _bool_value(decision, "mcp_write_allowed")
    main_modified = False

    inconsistent = _is_inconsistent(
        policy_allowed=policy_allowed,
        policy_blocked=policy_blocked,
        command_execution_allowed=command_execution_allowed,
        direct_file_edit_allowed=direct_file_edit_allowed,
        git_push_allowed=git_push_allowed,
        network_allowed=network_allowed,
        provider_call_allowed=provider_call_allowed,
        vault_write_allowed=vault_write_allowed,
        mcp_write_allowed=mcp_write_allowed,
        git_merge_allowed=git_merge_allowed,
        main_branch_protected=main_branch_protected,
        main_modified=main_modified,
    )
    if inconsistent:
        policy_blocked = True

    safe_notes = _redact_optional(notes)
    if inconsistent:
        inconsistency_note = "Inconsistent unsafe policy evidence was forced to blocked."
        safe_notes = f"{safe_notes} {inconsistency_note}".strip() if safe_notes else inconsistency_note

    return AgentWorkflowEvidence(
        event_type=AGENT_WORKFLOW_EVENT_TYPE,
        timestamp=timestamp or _utc_timestamp(),
        evidence_version=AGENT_WORKFLOW_EVIDENCE_VERSION,
        runtime_mode=AGENT_WORKFLOW_RUNTIME_MODE,
        agent_id=_redact_text(_string_value(decision, "agent_id", default="unknown")),
        agent_role=_string_value(decision, "agent_role", default="unknown"),
        requested_action=_string_value(decision, "requested_action", default="unknown"),
        workflow_mode=_string_value(decision, "workflow_mode", default="unknown"),
        requested_by=_redact_text(requested_by or "unknown"),
        session_id=_redact_optional(session_id),
        task_id=_redact_optional(task_id),
        related_phase=_redact_optional(related_phase),
        related_pr=_redact_optional(related_pr),
        target_branch=_redact_text(
            target_branch
            if target_branch is not None
            else _string_value(decision, "target_branch", default="")
        ),
        base_branch=_redact_text(
            base_branch
            if base_branch is not None
            else _string_value(decision, "base_branch", default="main")
        ),
        policy_allowed=policy_allowed,
        policy_blocked=policy_blocked,
        policy_requires_approval=policy_requires_approval,
        policy_category=_string_value(decision, "category", default="unknown"),
        policy_risk_level=_string_value(decision, "risk_level", default="high"),
        policy_reason=_string_value(decision, "reason", default="Unknown policy decision."),
        main_branch_protected=main_branch_protected,
        command_execution_allowed=command_execution_allowed,
        direct_file_edit_allowed=direct_file_edit_allowed,
        git_push_allowed=git_push_allowed,
        git_merge_allowed=git_merge_allowed,
        pr_open_allowed=pr_open_allowed,
        network_allowed=network_allowed,
        provider_call_allowed=provider_call_allowed,
        vault_write_allowed=vault_write_allowed,
        mcp_write_allowed=mcp_write_allowed,
        runtime_truth_required=_bool_value(decision, "runtime_truth_required"),
        sandbox_required=_bool_value(decision, "sandbox_required"),
        agent_executed=False,
        command_executed=False,
        network_used=False,
        provider_called=False,
        mcp_used=False,
        vault_written=False,
        git_mutated=False,
        pr_created=False,
        main_modified=main_modified,
        governance_decision=_governance_decision(
            policy_allowed=policy_allowed,
            policy_blocked=policy_blocked,
            policy_requires_approval=policy_requires_approval,
            inconsistent=inconsistent,
        ),
        user_approval_state=_redact_text(user_approval_state or DEFAULT_USER_APPROVAL_STATE),
        notes=safe_notes,
    )


def agent_workflow_decision_to_evidence(
    decision: AgentWorkflowPolicyDecision | Mapping[str, Any],
    **metadata: Any,
) -> AgentWorkflowEvidence:
    return build_agent_workflow_evidence(decision, **metadata)


def _governance_decision(
    *,
    policy_allowed: bool,
    policy_blocked: bool,
    policy_requires_approval: bool,
    inconsistent: bool,
) -> str:
    if inconsistent or policy_blocked:
        return "blocked"
    if policy_allowed and policy_requires_approval:
        return "requires_approval"
    if policy_allowed:
        return "allowed"
    return "blocked"


def _is_inconsistent(
    *,
    policy_allowed: bool,
    policy_blocked: bool,
    command_execution_allowed: bool,
    direct_file_edit_allowed: bool,
    git_push_allowed: bool,
    network_allowed: bool,
    provider_call_allowed: bool,
    vault_write_allowed: bool,
    mcp_write_allowed: bool,
    git_merge_allowed: bool,
    main_branch_protected: bool,
    main_modified: bool,
) -> bool:
    return any(
        (
            policy_allowed and policy_blocked,
            command_execution_allowed,
            direct_file_edit_allowed,
            git_push_allowed,
            network_allowed,
            provider_call_allowed,
            vault_write_allowed,
            mcp_write_allowed,
            git_merge_allowed,
            not main_branch_protected,
            main_modified,
        )
    )


def _value(
    decision: AgentWorkflowPolicyDecision | Mapping[str, Any],
    key: str,
    default: Any = None,
) -> Any:
    if isinstance(decision, Mapping):
        return decision.get(key, default)
    return getattr(decision, key, default)


def _string_value(
    decision: AgentWorkflowPolicyDecision | Mapping[str, Any],
    key: str,
    *,
    default: str,
) -> str:
    value = _value(decision, key, default)
    if value is None:
        return default
    return str(value)


def _bool_value(
    decision: AgentWorkflowPolicyDecision | Mapping[str, Any],
    key: str,
    *,
    default: bool = False,
) -> bool:
    return bool(_value(decision, key, default))


def _redact_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return _redact_text(value)


def _redact_text(value: str) -> str:
    redacted = str(value)
    for marker in _REDACTION_MARKERS:
        redacted = redacted.replace(marker, "[REDACTED]")
    return redacted


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
