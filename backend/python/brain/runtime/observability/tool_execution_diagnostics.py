from __future__ import annotations

from typing import Any


TOOL_DENIAL_KINDS = {
    "permission_denied",
    "missing_approval",
    "policy_stop",
    "control_layer_block",
    "supervision_stop",
    "simulation_stop",
    "strict_governed_tool_block",
}


def build_tool_execution_diagnostic(
    *,
    selected_tool: str,
    result: dict[str, Any] | None,
    latency_ms: int | None = None,
    tool_available: bool | None = None,
) -> dict[str, Any]:
    payload = dict(result or {})
    error_payload = payload.get("error_payload") if isinstance(payload.get("error_payload"), dict) else {}
    selected = str(selected_tool or payload.get("selected_tool", "") or "").strip()
    failure_class = str(error_payload.get("kind", "") or "").strip() or None
    failure_reason = str(error_payload.get("message", "") or "").strip() or None
    tool_requested = bool(selected and selected != "none")
    tool_denied = bool(failure_class in TOOL_DENIAL_KINDS)
    tool_attempted = bool(tool_requested and (payload or tool_denied))
    tool_succeeded = bool(tool_attempted and payload.get("ok"))
    tool_failed = bool(tool_attempted and not tool_succeeded and not tool_denied)
    available = bool(tool_available) if tool_available is not None else tool_requested
    normalized_latency = max(0, int(latency_ms)) if isinstance(latency_ms, (int, float)) else None
    return {
        "tool_requested": tool_requested,
        "tool_selected": selected or None,
        "tool_available": available,
        "tool_attempted": tool_attempted,
        "tool_succeeded": tool_succeeded,
        "tool_failed": tool_failed,
        "tool_denied": tool_denied,
        "tool_failure_class": failure_class,
        "tool_failure_reason": failure_reason,
        "tool_latency_ms": normalized_latency,
    }


def summarize_tool_execution(
    *,
    step_results: list[dict[str, Any]] | None,
    selected_tools: list[str] | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    diagnostics: list[dict[str, Any]] = []
    for result in list(step_results or []):
        if not isinstance(result, dict):
            continue
        selected_tool = str(result.get("selected_tool", "") or "").strip()
        diagnostic = result.get("tool_execution")
        if isinstance(diagnostic, dict) and (selected_tool or diagnostic.get("tool_selected")):
            diagnostics.append(dict(diagnostic))
            continue
        if selected_tool and selected_tool != "none":
            diagnostics.append(
                build_tool_execution_diagnostic(
                    selected_tool=selected_tool,
                    result=result,
                    latency_ms=result.get("tool_latency_ms"),
                )
            )

    if diagnostics:
        return diagnostics[-1], diagnostics

    fallback_tool = str((selected_tools or [""])[0] or "").strip() if selected_tools else ""
    if fallback_tool:
        diagnostic = build_tool_execution_diagnostic(
            selected_tool=fallback_tool,
            result={},
            tool_available=True,
        )
        return diagnostic, [diagnostic]

    return None, []
