"""Policy-only validation for future governed draft vault writes.

This module never writes vault files. It only classifies future draft creation
requests and blocks trusted-status, destructive, secret, provider, network, and
command operations.
"""

from __future__ import annotations

import re

from .write_types import VaultWritePolicyDecision, VaultWritePolicyRequest

WRITE_POLICY_EVIDENCE_VERSION = "1.0"

WRITE_MODE_DISABLED = "disabled"
WRITE_MODE_DRAFT_ONLY = "draft_only"
WRITE_MODE_WRITE_BLOCKED = "write_blocked"

ALLOWED_DRAFT_OPERATIONS = frozenset(
    {
        "create_sandbox_report_draft",
        "create_runtime_report_draft",
        "create_incident_draft",
        "create_session_summary_draft",
        "create_provider_evaluation_draft",
        "create_agent_prompt_draft",
    }
)

BLOCKED_OPERATIONS = frozenset(
    {
        "approve_note",
        "edit_approved_note",
        "delete_note",
        "rename_note",
        "move_note",
        "overwrite_note",
        "update_approved_frontmatter",
        "remove_frontmatter",
        "set_status_approved",
        "set_status_reviewed",
        "modify_adr",
        "edit_governance_policy",
        "write_secret",
        "attach_file",
        "execute_command",
        "provider_call",
        "network_fetch",
    }
)

APPROVAL_OPERATIONS = frozenset(
    {
        "approve_note",
        "edit_approved_note",
        "update_approved_frontmatter",
        "set_status_approved",
        "set_status_reviewed",
    }
)

DESTRUCTIVE_OPERATIONS = frozenset(
    {
        "delete_note",
        "rename_note",
        "move_note",
        "overwrite_note",
        "remove_frontmatter",
        "attach_file",
        "modify_adr",
        "edit_governance_policy",
    }
)

NETWORK_OR_PROVIDER_OPERATIONS = frozenset({"provider_call", "network_fetch"})
COMMAND_OPERATIONS = frozenset({"execute_command"})
SECRET_OPERATIONS = frozenset({"write_secret"})

ALLOWED_NOTE_TYPES = frozenset(
    {
        "sandbox-report",
        "runtime-report",
        "incident",
        "session-summary",
        "provider-evaluation",
        "agent-prompt",
    }
)

SENSITIVE_NOTE_TYPES = frozenset(
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

TRUSTED_OR_FINAL_STATUSES = frozenset(
    {
        "approved",
        "reviewed",
        "deprecated",
        "archived",
    }
)

APPROVAL_STATUSES = frozenset({"approved", "reviewed"})

ALLOWED_TARGET_PREFIXES = (
    "vault/09_Sandbox_Reports/",
    "vault/03_Runtime_Truth/",
    "vault/06_Incidents/",
    "vault/05_Agent_Prompts/",
    "vault/10_Provider_Research/",
)

SECRET_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"API_KEY", re.IGNORECASE),
    re.compile(r"SECRET", re.IGNORECASE),
    re.compile(r"TOKEN", re.IGNORECASE),
    re.compile(r"PASSWORD", re.IGNORECASE),
    re.compile(r"SUPABASE", re.IGNORECASE),
    re.compile(r"OPENAI", re.IGNORECASE),
    re.compile(r"JWT", re.IGNORECASE),
    re.compile(r"PRIVATE_KEY", re.IGNORECASE),
    re.compile(r"\.env", re.IGNORECASE),
)

DISABLED_REASON = "Vault writing is disabled by default."
WRITE_BLOCKED_REASON = "Vault write mode blocks future vault writing."
DRAFT_ALLOWED_REASON = "Governed draft-only policy permits this future draft note proposal."
UNKNOWN_OPERATION_REASON = "Unknown vault write operation is blocked by default."
STATUS_BLOCKED_REASON = "Automation cannot set trusted or final vault note statuses."
NOTE_TYPE_BLOCKED_REASON = "Sensitive vault note type is blocked from automated draft writing."
TARGET_PATH_BLOCKED_REASON = "Requested target path is outside governed draft vault paths."
SECRET_BLOCKED_REASON = "Content preview contains secret-like material and is blocked."
BLOCKED_OPERATION_REASON = "Vault write operation is blocked by governance policy."


def evaluate_vault_write_request(
    request: VaultWritePolicyRequest,
) -> VaultWritePolicyDecision:
    operation = str(request.operation or "").strip()
    note_type = str(request.note_type or "").strip()
    mode = str(request.write_mode or WRITE_MODE_DISABLED).strip() or WRITE_MODE_DISABLED
    requested_status = str(request.requested_status or "").strip()
    normalized_status = requested_status.lower() if requested_status else "draft"
    target_path_allowed = _target_path_allowed(request.target_path)
    secret_risk_detected = _contains_secret_like_content(request.content_preview)

    if mode == WRITE_MODE_DISABLED:
        return _decision(
            allowed=False,
            operation=operation,
            note_type=note_type,
            requested_status=requested_status,
            normalized_status=normalized_status,
            category=_category_for_operation(operation),
            risk_level="high",
            reason=DISABLED_REASON,
            write_mode=mode,
            target_path_allowed=target_path_allowed,
            secret_risk_detected=secret_risk_detected,
        )

    if secret_risk_detected:
        return _decision(
            allowed=False,
            operation=operation,
            note_type=note_type,
            requested_status=requested_status,
            normalized_status=normalized_status,
            category="secret_risk",
            risk_level="critical",
            reason=SECRET_BLOCKED_REASON,
            write_mode=mode,
            target_path_allowed=target_path_allowed,
            secret_risk_detected=True,
        )

    if normalized_status in TRUSTED_OR_FINAL_STATUSES:
        return _decision(
            allowed=False,
            operation=operation,
            note_type=note_type,
            requested_status=requested_status,
            normalized_status=normalized_status,
            category="status_escalation",
            risk_level="critical" if normalized_status in APPROVAL_STATUSES else "high",
            reason=STATUS_BLOCKED_REASON,
            write_mode=mode,
            target_path_allowed=target_path_allowed,
        )

    if note_type in SENSITIVE_NOTE_TYPES:
        return _decision(
            allowed=False,
            operation=operation,
            note_type=note_type,
            requested_status=requested_status,
            normalized_status=normalized_status,
            category="sensitive_note_type",
            risk_level="critical",
            reason=NOTE_TYPE_BLOCKED_REASON,
            write_mode=mode,
            target_path_allowed=target_path_allowed,
        )

    if not target_path_allowed:
        return _decision(
            allowed=False,
            operation=operation,
            note_type=note_type,
            requested_status=requested_status,
            normalized_status=normalized_status,
            category="target_path",
            risk_level="critical",
            reason=TARGET_PATH_BLOCKED_REASON,
            write_mode=mode,
            target_path_allowed=False,
        )

    if mode == WRITE_MODE_WRITE_BLOCKED:
        return _decision(
            allowed=False,
            operation=operation,
            note_type=note_type,
            requested_status=requested_status,
            normalized_status=normalized_status,
            category=_category_for_operation(operation),
            risk_level="high",
            reason=WRITE_BLOCKED_REASON,
            write_mode=mode,
            target_path_allowed=target_path_allowed,
        )

    if operation in BLOCKED_OPERATIONS:
        return _decision(
            allowed=False,
            operation=operation,
            note_type=note_type,
            requested_status=requested_status,
            normalized_status=normalized_status,
            category=_category_for_operation(operation),
            risk_level="critical",
            reason=BLOCKED_OPERATION_REASON,
            write_mode=mode,
            target_path_allowed=target_path_allowed,
        )

    if operation in ALLOWED_DRAFT_OPERATIONS and mode == WRITE_MODE_DRAFT_ONLY:
        if note_type not in ALLOWED_NOTE_TYPES:
            return _decision(
                allowed=False,
                operation=operation,
                note_type=note_type,
                requested_status=requested_status,
                normalized_status=normalized_status,
                category="unsupported_note_type",
                risk_level="high",
                reason=NOTE_TYPE_BLOCKED_REASON,
                write_mode=mode,
                target_path_allowed=target_path_allowed,
            )
        return _decision(
            allowed=True,
            operation=operation,
            note_type=note_type,
            requested_status=requested_status,
            normalized_status="draft",
            category="draft_creation",
            risk_level="medium",
            reason=DRAFT_ALLOWED_REASON,
            write_mode=mode,
            target_path_allowed=target_path_allowed,
            draft_only=True,
        )

    return _decision(
        allowed=False,
        operation=operation,
        note_type=note_type,
        requested_status=requested_status,
        normalized_status=normalized_status,
        category="unknown",
        risk_level="high",
        reason=UNKNOWN_OPERATION_REASON,
        write_mode=mode,
        target_path_allowed=target_path_allowed,
    )


def _decision(
    *,
    allowed: bool,
    operation: str,
    note_type: str,
    requested_status: str,
    normalized_status: str,
    category: str,
    risk_level: str,
    reason: str,
    write_mode: str,
    target_path_allowed: bool,
    secret_risk_detected: bool = False,
    draft_only: bool = False,
) -> VaultWritePolicyDecision:
    return VaultWritePolicyDecision(
        allowed=allowed,
        blocked=not allowed,
        requires_approval=True,
        operation=operation,
        note_type=note_type,
        requested_status=requested_status,
        normalized_status=normalized_status,
        category=category,
        risk_level=risk_level,
        reason=reason,
        write_mode=write_mode,
        draft_only=draft_only,
        write_attempted=operation in ALLOWED_DRAFT_OPERATIONS or operation in BLOCKED_OPERATIONS,
        approval_attempted=operation in APPROVAL_OPERATIONS or normalized_status in APPROVAL_STATUSES,
        destructive_attempted=operation in DESTRUCTIVE_OPERATIONS,
        secret_risk_detected=secret_risk_detected or operation in SECRET_OPERATIONS,
        target_path_allowed=target_path_allowed,
        suggested_status="draft",
        evidence_version=WRITE_POLICY_EVIDENCE_VERSION,
    )


def _contains_secret_like_content(content_preview: str | None) -> bool:
    text = str(content_preview or "")
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def _target_path_allowed(target_path: str | None) -> bool:
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


def _category_for_operation(operation: str) -> str:
    if operation in ALLOWED_DRAFT_OPERATIONS:
        return "draft_creation"
    if operation in APPROVAL_OPERATIONS:
        return "approval"
    if operation in DESTRUCTIVE_OPERATIONS:
        return "destructive"
    if operation in NETWORK_OR_PROVIDER_OPERATIONS:
        return "network_or_provider"
    if operation in COMMAND_OPERATIONS:
        return "command_execution"
    if operation in SECRET_OPERATIONS:
        return "secret_risk"
    return "unknown"
