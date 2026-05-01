"""
Public Runtime Outcome & Tool Diagnostics Normalization.

Derives clear public-facing fields from existing runtime signals
without altering execution logic or orchestrator behavior.
"""

from __future__ import annotations

import typing as _t

# Valid values for normalized fields
TOOL_STATUS_VALUES = {"succeeded", "failed", "skipped", "not_requested", "partial"}
TOOL_SKIP_REASON_VALUES = {"cached_response", "static_knowledge", "preflight_failed", "not_applicable", None}
ERROR_TYPE_VALUES = {"file_not_found", "missing_dependency", "tool_execution_error", None}


def normalize_public_runtime_outcome(
    *,
    runtime_mode: str,
    signals: dict[str, _t.Any],
    response: str = "",
    execution_provenance: dict[str, _t.Any] | None = None,
    tool_diagnostics: list[dict[str, _t.Any]] | None = None,
) -> dict[str, _t.Any]:
    """
    Derive public-friendly diagnostic fields from existing runtime signals.

    Rules match the specification exactly:
    1. Tool succeeded → full_success
    2. DIRECT_LOCAL_RESPONSE without tool → direct_local_response
    3. SAFE_FALLBACK / fallback_triggered → fallback
    4. Tool selected but not attempted → skipped (preflight_failed / static_knowledge / cached_response)
    5. Tool failed → failed (missing_dependency / file_not_found / tool_execution_error + partial_result)
    6. Compatibility execution without error → compatibility_response
    """
    runtime_mode = str(runtime_mode or "").strip()
    response_text = str(response or "").strip()
    signals = dict(signals) if isinstance(signals, dict) else {}
    tool_execution = signals.get("tool_execution") if isinstance(signals.get("tool_execution"), dict) else {}

    # Initialize normalized fields
    result = {
        "tool_status": "not_requested",
        "tool_skip_reason": None,
        "controlled_tool_error": False,
        "error_type": None,
        "partial_result": False,
        "public_runtime_outcome": "fallback",
    }

    tool_selected = tool_execution.get("tool_selected") if isinstance(tool_execution, dict) else signals.get("tool_selected")
    tool_attempted = bool(tool_execution.get("tool_attempted") if isinstance(tool_execution, dict) else signals.get("tool_attempted"))
    tool_succeeded = bool(tool_execution.get("tool_succeeded") if isinstance(tool_execution, dict) else signals.get("tool_succeeded"))
    tool_failed = bool(tool_execution.get("tool_failed") if isinstance(tool_execution, dict) else signals.get("tool_failed"))
    fallback_triggered = bool(signals.get("fallback_triggered", False))
    execution_path_used = str(signals.get("execution_path_used") or "").strip()
    tool_failure_reason = str(
        tool_execution.get("tool_failure_reason") if isinstance(tool_execution, dict) else signals.get("tool_failure_reason") or ""
    ).lower()
    response_lower = response_text.lower()

    # Rule 1: Tool succeeded
    if tool_succeeded is True:
        result["tool_status"] = "succeeded"
        result["controlled_tool_error"] = False
        result["partial_result"] = False
        result["public_runtime_outcome"] = "full_success"
        return result

    # Rule 2: DIRECT_LOCAL_RESPONSE without tool
    if runtime_mode == "DIRECT_LOCAL_RESPONSE" and not tool_selected:
        result["tool_status"] = "not_requested"
        result["tool_skip_reason"] = "not_applicable"
        result["controlled_tool_error"] = False
        result["partial_result"] = False
        result["public_runtime_outcome"] = "direct_local_response"
        return result

    # Rule 3: SAFE_FALLBACK or fallback triggered
    if runtime_mode == "SAFE_FALLBACK" or fallback_triggered:
        result["public_runtime_outcome"] = "fallback"
        if tool_selected:
            result["tool_status"] = "failed" if tool_failed else "succeeded" if tool_succeeded else "skipped"
        else:
            result["tool_status"] = "not_requested"
        return result

    # Rule 4: Tool selected but not attempted
    if tool_selected and tool_attempted is False:
        result["tool_status"] = "skipped"
        # Check for file not found preflight
        if "no such file or directory" in response_lower or "no such file or directory" in tool_failure_reason:
            result["tool_skip_reason"] = "preflight_failed"
            result["controlled_tool_error"] = True
            result["error_type"] = "file_not_found"
            result["public_runtime_outcome"] = "controlled_tool_error"
        else:
            # Check for cached/static response
            if response_text and not tool_failure_reason:
                # Heuristic: if there's a useful response without error, likely cached or static
                result["tool_skip_reason"] = "cached_response"
                result["controlled_tool_error"] = False
                result["public_runtime_outcome"] = "compatibility_response"
            else:
                result["tool_skip_reason"] = "static_knowledge"
                result["controlled_tool_error"] = False
                result["public_runtime_outcome"] = "compatibility_response"
        return result

    # Rule 5: Tool failed
    if tool_failed is True or (tool_succeeded is False and tool_failure_reason):
        result["tool_status"] = "failed"
        # Determine error_type
        if "no such file or directory: 'cargo'" in tool_failure_reason or "no such file or directory: cargo" in tool_failure_reason:
            result["error_type"] = "missing_dependency"
        elif "no such file or directory" in tool_failure_reason and tool_selected == "read_file":
            result["error_type"] = "file_not_found"
        else:
            result["error_type"] = "tool_execution_error"
        # Check for partial result (useful response beyond error)
        result["partial_result"] = bool(response_text and response_text not in {"", tool_failure_reason})
        result["controlled_tool_error"] = True
        if result["partial_result"]:
            result["public_runtime_outcome"] = "tool_failure_partial_result"
        else:
            result["public_runtime_outcome"] = "controlled_tool_error"
        return result

    # Rule 6: Compatibility execution
    if execution_path_used == "compatibility_execution" and not tool_failure_reason:
        if runtime_mode == "DIRECT_LOCAL_RESPONSE":
            result["public_runtime_outcome"] = "direct_local_response"
        else:
            result["public_runtime_outcome"] = "compatibility_response"
        result["tool_status"] = "not_requested" if not tool_selected else ("succeeded" if tool_succeeded else "failed")
        return result

    # Default fallback
    return result


__all__ = ["normalize_public_runtime_outcome", "TOOL_STATUS_VALUES", "TOOL_SKIP_REASON_VALUES", "ERROR_TYPE_VALUES"]
