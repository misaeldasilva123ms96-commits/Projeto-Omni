from __future__ import annotations

import os
from typing import Any

from brain.runtime.error_taxonomy import OmniErrorCode, build_public_error

TRUE_VALUES = {"1", "true", "yes", "on"}
POLICY_VERSION = "tool_governance_v1"

READ_SAFE = {"status", "health", "list", "directory_tree", "git_status", "git_diff", "dependency_inspection", "glob_search", "grep_search", "code_search"}
READ_SENSITIVE = {"read_file", "filesystem_read", "memory_read", "debug_inspection"}
WRITE = {"write_file", "edit_file", "filesystem_write", "filesystem_patch_set", "generated_file_write"}
DESTRUCTIVE = {"delete", "overwrite", "git_reset", "git_clean", "rm", "remove_file"}
SHELL = {"shell_command", "run_command", "test_runner", "verification_runner", "package_manager", "autonomous_debug_loop"}
NETWORK = {"curl", "fetch", "web_request", "network_request"}
GIT_SENSITIVE = {"git_commit", "git_push", "git_branch_mutation"}


def _truthy_env(*names: str) -> bool:
    for name in names:
        if str(os.getenv(name, "") or "").strip().lower() in TRUE_VALUES:
            return True
    return False


def is_public_demo_mode() -> bool:
    return _truthy_env("OMNI_PUBLIC_DEMO_MODE", "OMINI_PUBLIC_DEMO_MODE")


def classify_tool_category(tool_name: str) -> str:
    tool = str(tool_name or "").strip()
    if tool in READ_SAFE:
        return "read_safe"
    if tool in READ_SENSITIVE:
        return "read_sensitive"
    if tool in WRITE:
        return "write"
    if tool in DESTRUCTIVE:
        return "destructive"
    if tool in SHELL:
        return "shell"
    if tool in NETWORK:
        return "network"
    if tool in GIT_SENSITIVE:
        return "git_sensitive"
    if tool.startswith("git_") and tool not in {"git_status", "git_diff"}:
        return "git_sensitive"
    return "unknown"


def build_public_governance_audit(
    *,
    allowed: bool,
    category: str,
    reason_code: str,
    approval_required: bool,
    public_demo_blocked: bool,
) -> dict[str, Any]:
    return {
        "allowed": bool(allowed),
        "category": str(category or "unknown"),
        "reason_code": str(reason_code or "unknown"),
        "approval_required": bool(approval_required),
        "public_demo_blocked": bool(public_demo_blocked),
        "policy_version": POLICY_VERSION,
    }


def evaluate_tool_governance(action: dict[str, Any] | None) -> dict[str, Any]:
    action = dict(action or {})
    tool = str(action.get("selected_tool") or action.get("tool") or "").strip()
    arguments = action.get("tool_arguments") if isinstance(action.get("tool_arguments"), dict) else {}
    category = classify_tool_category(tool)
    approval_state = str(action.get("approval_state") or action.get("approvalState") or "").strip().lower()
    explicit_scope = bool(
        action.get("explicit_scope")
        or action.get("scope")
        or arguments.get("path")
        or arguments.get("workspace_root")
    )

    if is_public_demo_mode() and category in {"shell", "write", "destructive", "network", "git_sensitive"}:
        return _decision(False, category, "public_demo_mode", approval_required=False, public_demo_blocked=True)
    if category == "read_safe":
        return _decision(True, category, "read_safe_allowed")
    if category == "read_sensitive":
        if not explicit_scope:
            return _decision(False, category, "missing_explicit_scope", approval_required=True)
        return _decision(True, category, "read_sensitive_scope_allowed")
    if category == "write":
        if approval_state != "approved":
            return _decision(False, category, "missing_approval", approval_required=True)
        return _decision(True, category, "write_approved")
    if category == "destructive":
        return _decision(False, category, "destructive_tool_blocked", approval_required=True)
    if category == "shell":
        return _decision(True, category, "shell_delegated_to_shell_policy")
    if category == "network":
        return _decision(False, category, "network_tool_requires_governance", approval_required=True)
    if category == "git_sensitive":
        if approval_state != "approved":
            return _decision(False, category, "git_sensitive_requires_approval", approval_required=True)
        return _decision(True, category, "git_sensitive_approved")
    return _decision(False, category, "unknown_tool_requires_governance", approval_required=True)


def _decision(
    allowed: bool,
    category: str,
    reason: str,
    *,
    approval_required: bool = False,
    public_demo_blocked: bool = False,
) -> dict[str, Any]:
    if public_demo_blocked:
        error = build_public_error(OmniErrorCode.TOOL_BLOCKED_PUBLIC_DEMO)
    elif approval_required:
        error = build_public_error(OmniErrorCode.TOOL_APPROVAL_REQUIRED)
    elif allowed:
        error = {
            "error_public_code": "",
            "error_public_message": "",
            "severity": "info",
            "retryable": False,
            "internal_error_redacted": True,
        }
    else:
        error = build_public_error(OmniErrorCode.TOOL_BLOCKED_BY_GOVERNANCE)
    return {
        "allowed": bool(allowed),
        "category": category,
        "reason": reason,
        **error,
        "approval_required": bool(approval_required),
        "public_demo_blocked": bool(public_demo_blocked),
        "governance_audit": build_public_governance_audit(
            allowed=allowed,
            category=category,
            reason_code=reason,
            approval_required=approval_required,
            public_demo_blocked=public_demo_blocked,
        ),
    }


def build_governance_blocked_result(tool: str, decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "selected_tool": str(tool or ""),
        "tool_status": "blocked",
        "error_public_code": str(decision.get("error_public_code") or "TOOL_BLOCKED_BY_GOVERNANCE"),
        "error_public_message": str(
            decision.get("error_public_message") or "Tool execution was blocked by governance policy."
        ),
        "severity": str(decision.get("severity") or "blocked"),
        "retryable": bool(decision.get("retryable", False)),
        "internal_error_redacted": True,
        "governance_audit": dict(decision.get("governance_audit") or {}),
        "tool_execution": {
            "tool_requested": True,
            "tool_selected": str(tool or ""),
            "tool_available": True,
            "tool_attempted": False,
            "tool_succeeded": False,
            "tool_failed": False,
            "tool_denied": True,
            "tool_failure_class": str(decision.get("error_public_code") or "TOOL_BLOCKED_BY_GOVERNANCE"),
            "tool_failure_reason": str(decision.get("error_public_message") or "Tool execution was blocked by governance policy."),
        },
        "error_payload": {
            "kind": "tool_blocked",
            "message": "Tool execution was blocked by governance policy.",
            "public_code": str(decision.get("error_public_code") or "TOOL_BLOCKED_BY_GOVERNANCE"),
        },
    }


__all__ = [
    "POLICY_VERSION",
    "build_governance_blocked_result",
    "build_public_governance_audit",
    "classify_tool_category",
    "evaluate_tool_governance",
    "is_public_demo_mode",
]
