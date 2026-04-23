from __future__ import annotations

from typing import Any

LANE_MATCHER_SHORTCUT = "matcher_shortcut"
LANE_LOCAL_DIRECT_RESPONSE = "local_direct_response"
LANE_BRIDGE_EXECUTION_REQUEST = "bridge_execution_request"
LANE_TRUE_ACTION_EXECUTION = "true_action_execution"
LANE_COMPATIBILITY_EXECUTION = "compatibility_execution"
LANE_SAFE_DEGRADED_FALLBACK = "safe_degraded_fallback"

TRANSPORT_SUCCESS = "success"
TRANSPORT_FALLBACK = "fallback"
TRANSPORT_UNKNOWN = "unknown"


def _hint_lane(node_cognitive_hint: dict[str, Any] | None) -> str:
    if not isinstance(node_cognitive_hint, dict):
        return ""
    return str(node_cognitive_hint.get("lane") or node_cognitive_hint.get("detail") or "").strip().lower()


def _response_present(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _metadata_execution_mode(parsed: dict[str, Any] | None) -> str:
    if not isinstance(parsed, dict):
        return ""
    metadata = parsed.get("metadata")
    if not isinstance(metadata, dict):
        return ""
    provenance = metadata.get("execution_provenance")
    if not isinstance(provenance, dict):
        return ""
    return str(provenance.get("execution_mode") or "").strip().lower()


def derive_node_cognitive_hint(parsed: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(parsed, dict):
        return None
    hint = parsed.get("cognitive_runtime_hint")
    if isinstance(hint, dict):
        return hint
    execution_mode = _metadata_execution_mode(parsed)
    if execution_mode:
        return {"lane": execution_mode}
    return None


def normalize_node_outcome(
    *,
    transport_status: str,
    semantic_lane: str,
    reason_code: str,
    node_cognitive_hint: dict[str, Any] | None = None,
    node_result_envelope: dict[str, Any] | None = None,
    response_text: str = "",
) -> dict[str, Any]:
    execution_request = (
        node_result_envelope.get("execution_request")
        if isinstance(node_result_envelope, dict)
        else None
    )
    actions = execution_request.get("actions") if isinstance(execution_request, dict) else None
    return {
        "transport_status": str(transport_status or TRANSPORT_UNKNOWN),
        "semantic_lane": str(semantic_lane or ""),
        "reason_code": str(reason_code or ""),
        "node_hint_lane": _hint_lane(node_cognitive_hint),
        "has_execution_request": isinstance(execution_request, dict),
        "has_actions": isinstance(actions, list) and bool(actions),
        "response_present": _response_present(response_text)
        or _response_present(node_result_envelope.get("response") if isinstance(node_result_envelope, dict) else None),
    }


def extract_node_envelope_for_provenance(parsed: dict[str, Any]) -> dict[str, Any]:
    keys = ("metadata", "memory", "execution_request", "cognitive_runtime_hint", "confidence", "response")
    return {k: parsed[k] for k in keys if k in parsed}


def interpret_node_payload(
    *,
    parsed: dict[str, Any] | None,
    stdout: str = "",
) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {
            "fallback": True,
            "response_text": "",
            "reason_code": "invalid_node_payload",
            "semantic_lane": LANE_SAFE_DEGRADED_FALLBACK,
            "node_cognitive_hint": None,
            "node_result_envelope": None,
            "execution_request": None,
            "node_outcome": normalize_node_outcome(
                transport_status=TRANSPORT_FALLBACK,
                semantic_lane=LANE_SAFE_DEGRADED_FALLBACK,
                reason_code="invalid_node_payload",
            ),
        }

    node_cognitive_hint = derive_node_cognitive_hint(parsed)
    node_result_envelope = extract_node_envelope_for_provenance(parsed)
    response = parsed.get("response")
    normalized = str(response).strip() if isinstance(response, str) else str(stdout or "").strip()
    execution_request = parsed.get("execution_request")
    hint_lane = _hint_lane(node_cognitive_hint)

    if not isinstance(execution_request, dict):
        if normalized:
            semantic_lane = (
                LANE_MATCHER_SHORTCUT
                if hint_lane in {"matcher_shortcut", "conversational_matcher"} or "matcher" in hint_lane
                else LANE_BRIDGE_EXECUTION_REQUEST
                if hint_lane in {"python_executor_bridge", "node_execution_graph", "bridge_execution_request"}
                or "bridge" in hint_lane
                else LANE_LOCAL_DIRECT_RESPONSE
            )
            return {
                "fallback": False,
                "response_text": normalized,
                "reason_code": "direct_node_response",
                "semantic_lane": semantic_lane,
                "node_cognitive_hint": node_cognitive_hint,
                "node_result_envelope": node_result_envelope,
                "execution_request": None,
                "node_outcome": normalize_node_outcome(
                    transport_status=TRANSPORT_SUCCESS,
                    semantic_lane=semantic_lane,
                    reason_code="direct_node_response",
                    node_cognitive_hint=node_cognitive_hint,
                    node_result_envelope=node_result_envelope,
                    response_text=normalized,
                ),
            }
        return {
            "fallback": True,
            "response_text": "",
            "reason_code": "invalid_node_payload",
            "semantic_lane": LANE_SAFE_DEGRADED_FALLBACK,
            "node_cognitive_hint": node_cognitive_hint,
            "node_result_envelope": node_result_envelope,
            "execution_request": None,
            "node_outcome": normalize_node_outcome(
                transport_status=TRANSPORT_FALLBACK,
                semantic_lane=LANE_SAFE_DEGRADED_FALLBACK,
                reason_code="invalid_node_payload",
                node_cognitive_hint=node_cognitive_hint,
                node_result_envelope=node_result_envelope,
            ),
        }

    actions = execution_request.get("actions", [])
    if not isinstance(actions, list) or not actions:
        if normalized:
            return {
                "fallback": False,
                "response_text": normalized,
                "reason_code": "node_response_without_actions",
                "semantic_lane": LANE_BRIDGE_EXECUTION_REQUEST,
                "node_cognitive_hint": node_cognitive_hint,
                "node_result_envelope": node_result_envelope,
                "execution_request": execution_request,
                "node_outcome": normalize_node_outcome(
                    transport_status=TRANSPORT_SUCCESS,
                    semantic_lane=LANE_BRIDGE_EXECUTION_REQUEST,
                    reason_code="node_response_without_actions",
                    node_cognitive_hint=node_cognitive_hint,
                    node_result_envelope=node_result_envelope,
                    response_text=normalized,
                ),
            }
        return {
            "fallback": True,
            "response_text": "",
            "reason_code": "invalid_execution_request",
            "semantic_lane": LANE_SAFE_DEGRADED_FALLBACK,
            "node_cognitive_hint": node_cognitive_hint,
            "node_result_envelope": node_result_envelope,
            "execution_request": execution_request,
            "node_outcome": normalize_node_outcome(
                transport_status=TRANSPORT_FALLBACK,
                semantic_lane=LANE_SAFE_DEGRADED_FALLBACK,
                reason_code="invalid_execution_request",
                node_cognitive_hint=node_cognitive_hint,
                node_result_envelope=node_result_envelope,
            ),
        }

    return {
        "fallback": False,
        "response_text": normalized,
        "reason_code": "node_execution_request",
        "semantic_lane": LANE_TRUE_ACTION_EXECUTION,
        "node_cognitive_hint": node_cognitive_hint,
        "node_result_envelope": node_result_envelope,
        "execution_request": execution_request,
        "node_outcome": normalize_node_outcome(
            transport_status=TRANSPORT_SUCCESS,
            semantic_lane=LANE_TRUE_ACTION_EXECUTION,
            reason_code="node_execution_request",
            node_cognitive_hint=node_cognitive_hint,
            node_result_envelope=node_result_envelope,
            response_text=normalized,
        ),
    }


def classify_runtime_lane(
    *,
    response: str,
    safe_fallback: str,
    node_fallback: str,
    mock_response: str,
    last_runtime_mode: str,
    last_runtime_reason: str,
    node_cognitive_hint: dict[str, Any] | None,
    node_outcome: dict[str, Any] | None,
    direct_memory_hit: bool,
    strategy_dispatch_applied: bool,
) -> dict[str, Any]:
    r = str(response or "").strip()
    safe = str(safe_fallback or "").strip()
    node_fb = str(node_fallback or "").strip()
    mock = str(mock_response or "").strip()
    hint_lane = _hint_lane(node_cognitive_hint)

    if r in {safe, node_fb, mock} or str(last_runtime_mode or "").strip() == "fallback":
        return {
            "semantic_lane": LANE_SAFE_DEGRADED_FALLBACK,
            "transport_status": TRANSPORT_FALLBACK,
            "node_hint_lane": hint_lane,
            "reason_code": str(last_runtime_reason or ""),
        }

    if isinstance(node_outcome, dict) and str(node_outcome.get("semantic_lane") or "").strip():
        return {
            "semantic_lane": str(node_outcome.get("semantic_lane") or ""),
            "transport_status": str(node_outcome.get("transport_status") or TRANSPORT_UNKNOWN),
            "node_hint_lane": str(node_outcome.get("node_hint_lane") or hint_lane),
            "reason_code": str(node_outcome.get("reason_code") or last_runtime_reason or ""),
        }

    if hint_lane in {"matcher_shortcut", "conversational_matcher"} or "matcher" in hint_lane:
        return {
            "semantic_lane": LANE_MATCHER_SHORTCUT,
            "transport_status": TRANSPORT_SUCCESS,
            "node_hint_lane": hint_lane,
            "reason_code": str(last_runtime_reason or ""),
        }

    if str(last_runtime_mode or "").strip() == "live" and str(last_runtime_reason or "").strip() == "node_execution_request":
        return {
            "semantic_lane": LANE_TRUE_ACTION_EXECUTION,
            "transport_status": TRANSPORT_SUCCESS,
            "node_hint_lane": hint_lane,
            "reason_code": str(last_runtime_reason or ""),
        }

    if direct_memory_hit or strategy_dispatch_applied:
        return {
            "semantic_lane": LANE_COMPATIBILITY_EXECUTION,
            "transport_status": TRANSPORT_SUCCESS if r else TRANSPORT_UNKNOWN,
            "node_hint_lane": hint_lane,
            "reason_code": str(last_runtime_reason or ""),
        }

    return {
        "semantic_lane": LANE_LOCAL_DIRECT_RESPONSE if r else LANE_COMPATIBILITY_EXECUTION,
        "transport_status": TRANSPORT_SUCCESS if r else TRANSPORT_UNKNOWN,
        "node_hint_lane": hint_lane,
        "reason_code": str(last_runtime_reason or ""),
    }


def classify_execution_runtime_lane(
    *,
    semantic_lane: str,
    direct_memory_hit: bool,
    strategy_dispatch_applied: bool,
    executor_used: str = "",
    execution_trace_summary: str = "",
    explicit_execution_runtime_lane: str = "",
    explicit_compatibility_execution_active: bool | None = None,
    actions_executed: bool = False,
) -> dict[str, Any]:
    summary = str(execution_trace_summary or "").strip().lower()
    executor = str(executor_used or "").strip().lower()
    explicit_lane = str(explicit_execution_runtime_lane or "").strip().lower()
    if actions_executed or explicit_lane == LANE_TRUE_ACTION_EXECUTION:
        return {
            "execution_runtime_lane": LANE_TRUE_ACTION_EXECUTION,
            "compatibility_execution_active": False,
            "semantic_lane": semantic_lane,
            "strategy_dispatch_applied": bool(strategy_dispatch_applied),
        }
    compatibility_active = bool(
        explicit_compatibility_execution_active
        if explicit_compatibility_execution_active is not None
        else (
            direct_memory_hit
            or executor == "compatibility_path"
            or "compatibility runtime path" in summary
            or "compatibility execution path" in summary
        )
    )
    execution_lane = explicit_lane or (LANE_COMPATIBILITY_EXECUTION if compatibility_active else (semantic_lane or ""))
    if execution_lane == LANE_TRUE_ACTION_EXECUTION:
        compatibility_active = False
    return {
        "execution_runtime_lane": execution_lane,
        "compatibility_execution_active": compatibility_active,
        "semantic_lane": semantic_lane,
        "strategy_dispatch_applied": bool(strategy_dispatch_applied),
    }
