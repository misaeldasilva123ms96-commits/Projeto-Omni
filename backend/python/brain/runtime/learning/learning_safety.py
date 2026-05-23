from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from brain.runtime.error_taxonomy import ERROR_SEVERITY

from .redaction import REDACTED_INTERNAL_PAYLOAD


NON_POSITIVE_RUNTIME_MODES = {
    "MATCHER_SHORTCUT": "matcher_shortcut_not_training_quality",
    "SAFE_FALLBACK": "fallback_not_training_quality",
    "NODE_FALLBACK": "node_fallback_not_training_quality",
    "PROVIDER_UNAVAILABLE": "provider_unavailable",
    "TOOL_BLOCKED": "tool_blocked",
}

FAILURE_CLASSIFICATIONS = {
    "SAFE_FALLBACK": "failure_memory",
    "NODE_FALLBACK": "failure_memory",
    "PROVIDER_UNAVAILABLE": "failure_memory",
    "TOOL_BLOCKED": "governance_block_case",
}

EVALUATION_CLASSIFICATIONS = {
    "MATCHER_SHORTCUT": "routing_eval_case",
}

NEGATIVE_ERROR_SEVERITIES = {"degraded", "blocked", "error", "critical"}

REDACTION_MARKERS = (
    "[REDACTED_API_KEY]",
    "Bearer [REDACTED_TOKEN]",
    "[REDACTED_JWT]",
    "[REDACTED_EMAIL]",
    "[REDACTED_PHONE]",
    "[REDACTED_CPF]",
    "[REDACTED_SECRET]",
    "[REDACTED_SUPABASE_URL]",
    "[REDACTED_PATH]",
    REDACTED_INTERNAL_PAYLOAD,
)


def should_save_positive_learning(record: Mapping[str, Any] | None) -> bool:
    return bool(build_learning_safety_metadata(record).get("positive_training_candidate", False))


def classify_learning_record(record: Mapping[str, Any] | None) -> str:
    return str(build_learning_safety_metadata(record).get("learning_classification", "diagnostic_memory"))


def build_learning_safety_metadata(record: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(record or {})
    execution_outcome = _dict(payload.get("execution_outcome"))
    metadata = _dict(payload.get("metadata"))
    tool_execution = _dict(metadata.get("tool_execution"))
    decision_evaluation = _dict(payload.get("decision_evaluation"))

    runtime_mode = _text(payload.get("runtime_mode") or execution_outcome.get("runtime_mode"))
    fallback_triggered = _bool(execution_outcome.get("fallback_triggered") or metadata.get("fallback_triggered"))
    provider_succeeded = _provider_succeeded(payload, execution_outcome, metadata)
    provider_failed = _bool(execution_outcome.get("provider_failed") or metadata.get("provider_failed"))
    tool_status = _tool_status(payload, execution_outcome, metadata, tool_execution)
    governance_status = _governance_status(payload, metadata, tool_execution)
    error_public_code = _text(
        payload.get("error_public_code")
        or metadata.get("error_public_code")
        or execution_outcome.get("error_public_code")
    )
    error_severity = _text(metadata.get("error_severity") or ERROR_SEVERITY.get(error_public_code, ""))
    internal_error_redacted = _bool(
        payload.get("internal_error_redacted")
        or metadata.get("internal_error_redacted")
        or execution_outcome.get("internal_error_redacted")
    )
    redaction_applied = _redaction_applied(payload)
    decision_issue = _text(decision_evaluation.get("decision_issue"))
    success = _bool(payload.get("success"))

    learning_classification = "diagnostic_memory"
    positive = False
    negative = False
    reason = "runtime_quality_unverified"

    if fallback_triggered:
        learning_classification = "failure_memory"
        negative = True
        reason = "fallback_triggered"
    elif runtime_mode in NON_POSITIVE_RUNTIME_MODES:
        learning_classification = FAILURE_CLASSIFICATIONS.get(
            runtime_mode,
            EVALUATION_CLASSIFICATIONS.get(runtime_mode, "diagnostic_memory"),
        )
        negative = runtime_mode != "MATCHER_SHORTCUT"
        reason = NON_POSITIVE_RUNTIME_MODES[runtime_mode]
    elif provider_failed or provider_succeeded is False:
        learning_classification = "failure_memory"
        negative = True
        reason = "provider_not_successful"
    elif tool_status in {"failed", "blocked", "denied"}:
        learning_classification = "tool_failure_case" if tool_status == "failed" else "governance_block_case"
        negative = True
        reason = f"tool_{tool_status}"
    elif governance_status == "blocked":
        learning_classification = "governance_block_case"
        negative = True
        reason = "governance_blocked"
    elif error_public_code and error_severity in NEGATIVE_ERROR_SEVERITIES:
        learning_classification = "failure_memory" if error_severity in {"degraded", "error", "critical"} else "governance_block_case"
        negative = True
        reason = f"public_error_{error_severity}"
    elif internal_error_redacted:
        learning_classification = "diagnostic_memory"
        reason = "internal_error_redacted_unknown_quality"
    elif _redaction_too_heavy(payload):
        learning_classification = "diagnostic_memory"
        reason = "redaction_applied_unknown_training_quality"
    elif success and _runtime_truth_confidence_high(metadata) and _provider_requirement_satisfied(runtime_mode, provider_succeeded) and _tool_requirement_satisfied(tool_status, metadata, execution_outcome):
        learning_classification = "positive_training_candidate"
        positive = True
        reason = "clean_high_confidence_success"
    elif decision_issue:
        learning_classification = "routing_eval_case"
        reason = f"decision_issue_{decision_issue}"

    return {
        "learning_classification": learning_classification,
        "positive_training_candidate": positive,
        "negative_training_candidate": negative,
        "runtime_mode": runtime_mode,
        "fallback_triggered": fallback_triggered,
        "provider_succeeded": provider_succeeded,
        "tool_status": tool_status,
        "governance_status": governance_status,
        "error_public_code": error_public_code,
        "redaction_applied": redaction_applied,
        "learning_safety_reason": reason,
    }


def _provider_succeeded(payload: Mapping[str, Any], outcome: Mapping[str, Any], metadata: Mapping[str, Any]) -> bool | None:
    for value in (
        payload.get("llm_provider_succeeded"),
        payload.get("provider_succeeded"),
        metadata.get("llm_provider_succeeded"),
        metadata.get("provider_succeeded"),
        metadata.get("node_execution_successful"),
        outcome.get("provider_succeeded"),
    ):
        coerced = _optional_bool(value)
        if coerced is not None:
            return coerced
    if _bool(outcome.get("provider_failed")):
        return False
    return None


def _tool_status(payload: Mapping[str, Any], outcome: Mapping[str, Any], metadata: Mapping[str, Any], tool_execution: Mapping[str, Any]) -> str:
    explicit = _text(payload.get("tool_status") or metadata.get("tool_status") or tool_execution.get("tool_status"))
    if explicit:
        return explicit.lower()
    if _bool(outcome.get("tool_failed") or tool_execution.get("tool_failed")):
        return "failed"
    if _bool(outcome.get("tool_denied") or tool_execution.get("tool_denied")):
        return "blocked"
    if _bool(outcome.get("tool_succeeded") or tool_execution.get("tool_succeeded")):
        return "succeeded"
    if _text(outcome.get("tool_used") or tool_execution.get("tool_selected")):
        return "unknown"
    return ""


def _governance_status(payload: Mapping[str, Any], metadata: Mapping[str, Any], tool_execution: Mapping[str, Any]) -> str:
    value = _text(
        payload.get("governance_status")
        or metadata.get("governance_status")
        or metadata.get("governance_decision")
        or tool_execution.get("governance_status")
        or tool_execution.get("governance_decision")
    ).lower()
    if value:
        return value
    audit = tool_execution.get("governance_audit") if isinstance(tool_execution.get("governance_audit"), Mapping) else {}
    if _bool(audit.get("allowed")):
        return "allowed"
    if _bool(audit.get("approval_required")) or _bool(audit.get("public_demo_blocked")):
        return "blocked"
    return ""


def _runtime_truth_confidence_high(metadata: Mapping[str, Any]) -> bool:
    value = _text(metadata.get("runtime_truth_confidence") or metadata.get("confidence"))
    if value:
        return value.lower() == "high"
    numeric = metadata.get("confidence_score")
    try:
        return float(numeric) >= 0.8
    except (TypeError, ValueError):
        return True


def _provider_requirement_satisfied(runtime_mode: str, provider_succeeded: bool | None) -> bool:
    if runtime_mode in {"FULL_COGNITIVE_RUNTIME", "PARTIAL_COGNITIVE"}:
        return provider_succeeded is True
    return provider_succeeded is not False


def _tool_requirement_satisfied(tool_status: str, metadata: Mapping[str, Any], outcome: Mapping[str, Any]) -> bool:
    tool_required = _bool(metadata.get("decision_requires_tools") or metadata.get("decision_must_execute")) or bool(_text(outcome.get("tool_used")))
    if not tool_required:
        return tool_status not in {"failed", "blocked", "denied"}
    return tool_status == "succeeded"


def _redaction_applied(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return any(marker in text for marker in REDACTION_MARKERS)


def _redaction_too_heavy(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return text.count(REDACTED_INTERNAL_PAYLOAD) > 0


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


__all__ = [
    "build_learning_safety_metadata",
    "classify_learning_record",
    "should_save_positive_learning",
]
