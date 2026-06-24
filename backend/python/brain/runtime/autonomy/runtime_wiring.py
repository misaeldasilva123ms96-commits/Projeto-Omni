"""Advisory-only autonomy wiring for the orchestrator runtime.

Builds an AutonomyContext from the cognitive runtime inspection and
the orchestrator's available state, then calls the AutonomyController
to produce an advisory decision. The decision is attached to the
inspection dict for observation only — no execution path is changed.
"""

from __future__ import annotations

import logging
from typing import Any

from .autonomy_controller import AutonomyController
from .autonomy_models import AutonomyContext
from .autonomy_session_tracker import AutonomySessionTracker
from .error_progress_tracker import SmartErrorProgressTracker

logger = logging.getLogger(__name__)

_DEFAULT_CONTROLLER: AutonomyController | None = None
_DEFAULT_TRACKER: AutonomySessionTracker | None = None
_DEFAULT_SMART_TRACKER: SmartErrorProgressTracker | None = None


def _get_controller() -> AutonomyController:
    global _DEFAULT_CONTROLLER
    if _DEFAULT_CONTROLLER is None:
        _DEFAULT_CONTROLLER = AutonomyController()
    return _DEFAULT_CONTROLLER


def _get_tracker() -> AutonomySessionTracker:
    global _DEFAULT_TRACKER
    if _DEFAULT_TRACKER is None:
        _DEFAULT_TRACKER = AutonomySessionTracker()
    return _DEFAULT_TRACKER


def _get_smart_tracker() -> SmartErrorProgressTracker:
    global _DEFAULT_SMART_TRACKER
    if _DEFAULT_SMART_TRACKER is None:
        _DEFAULT_SMART_TRACKER = SmartErrorProgressTracker()
    return _DEFAULT_SMART_TRACKER


def build_autonomy_context(
    inspection: dict[str, Any] | None,
    session_id: str,
    response: str,
) -> AutonomyContext:
    ctx = AutonomyContext(session_id=session_id)

    if not isinstance(inspection, dict):
        return ctx

    signals: dict[str, Any] = inspection.get("signals") or {}
    runtime_mode: str = str(signals.get("runtime_mode") or inspection.get("runtime_mode") or "")

    failure_class: str = str(signals.get("failure_class") or "")
    failure_reason: str = str(signals.get("failure_reason") or "")
    safe_fallback: str = "Nao consegui processar isso ainda, mas estou aprendendo."

    if failure_class:
        ctx.error_type = failure_class
        ctx.error_count = 1
    elif failure_reason:
        ctx.error_type = failure_reason
        ctx.error_count = 1
    elif runtime_mode in ("safe_fallback", "provider_failure", "node_fallback"):
        ctx.error_type = runtime_mode
        ctx.error_count = 1

    if response == safe_fallback:
        ctx.no_safe_next_action = True

    fallback_triggered = signals.get("fallback_triggered", False)
    provider_failed = signals.get("provider_failed", False)
    provider_actual: str = str(signals.get("provider_actual") or "")

    if provider_failed:
        ctx.metadata["provider_failure_type"] = provider_actual

    ctx.metadata["runtime_mode"] = runtime_mode
    ctx.metadata["fallback_triggered"] = str(fallback_triggered)
    ctx.metadata["provider_failed"] = str(provider_failed)
    ctx.metadata["response_length"] = len(response)

    return ctx


def _enrich_context_from_session(
    ctx: AutonomyContext,
    tracker: AutonomySessionTracker,
) -> AutonomyContext:
    state = tracker.get_or_create(ctx.session_id)

    if ctx.error_type:
        cumulative_errors = state.current_error_count + 1
        distinct_count = len(state.distinct_error_types)
        if ctx.error_type not in state.distinct_error_types:
            distinct_count += 1
        is_stagnation = _detect_stagnation(state, ctx)
        stagnant_count = state.stagnant_attempts + (1 if is_stagnation else 0)
        ctx.error_count = cumulative_errors
        ctx.stagnation_count = stagnant_count
        ctx.distinct_errors = distinct_count
        ctx.consecutive_same_error = stagnant_count
    else:
        ctx.error_count = 0
        ctx.stagnation_count = 0
        ctx.distinct_errors = 0
        ctx.consecutive_same_error = 0

    is_progress = _detect_progress(state, ctx)
    progressive_count = state.progressive_cycles + (1 if is_progress else 0)
    ctx.total_progressive_cycles = progressive_count

    return ctx


def _detect_stagnation(
    state: Any,
    ctx: AutonomyContext,
) -> bool:
    if ctx.error_type and state.last_error_type:
        if ctx.error_type == state.last_error_type:
            return True

    provider_failure: str = ctx.metadata.get("provider_failure_type", "")
    if provider_failure and state.last_provider_failure_type:
        if provider_failure == state.last_provider_failure_type:
            return True

    runtime_mode: str = ctx.metadata.get("runtime_mode", "")
    if runtime_mode and state.last_runtime_mode:
        if runtime_mode == state.last_runtime_mode:
            if runtime_mode in ("provider_failure", "safe_fallback", "node_fallback"):
                return True

    if ctx.no_safe_next_action and state.last_response_was_safe_fallback:
        return True

    return False


def _detect_progress(
    state: Any,
    ctx: AutonomyContext,
) -> bool:
    if ctx.error_type and state.last_error_type:
        if ctx.error_type != state.last_error_type:
            return True

    runtime_mode: str = ctx.metadata.get("runtime_mode", "")
    if runtime_mode and state.last_runtime_mode:
        current_rank = _RUNTIME_MODE_ORDER.get(runtime_mode, -1)
        last_rank = _RUNTIME_MODE_ORDER.get(state.last_runtime_mode, -1)
        if current_rank > last_rank:
            return True

    if state.last_runtime_mode in ("safe_fallback", "node_fallback", "provider_failure"):
        if runtime_mode not in ("safe_fallback", "node_fallback", "provider_failure"):
            return True

    if state.last_provider_failure_type and not ctx.metadata.get("provider_failure_type", ""):
        return True

    prev_response_len: int = state.last_response_length
    current_response_len: Any = ctx.metadata.get("response_length", 0)
    if isinstance(current_response_len, str):
        try:
            current_response_len = int(current_response_len)
        except (ValueError, TypeError):
            current_response_len = 0
    if prev_response_len == 0 and current_response_len > 0:
        return True

    if state.last_response_was_safe_fallback and not ctx.no_safe_next_action:
        return True

    return False


_RUNTIME_MODE_ORDER: dict[str, int] = {
    "provider_failure": 0,
    "safe_fallback": 1,
    "node_fallback": 2,
    "standard": 3,
    "default": 3,
    "normal": 3,
}


def evaluate_autonomy(
    inspection: dict[str, Any] | None,
    session_id: str,
    response: str,
    *,
    controller: AutonomyController | None = None,
    tracker: AutonomySessionTracker | None = None,
    smart_tracker: SmartErrorProgressTracker | None = None,
) -> dict[str, Any]:
    if controller is None:
        controller = _get_controller()
    if tracker is None:
        tracker = _get_tracker()
    if smart_tracker is None:
        smart_tracker = _get_smart_tracker()

    ctx = build_autonomy_context(
        inspection=inspection,
        session_id=session_id,
        response=response,
    )

    ctx = _enrich_context_from_session(ctx, tracker)

    smart_output = smart_tracker.classify(session_id, ctx, inspection)
    ctx.metadata["error_progress_tracker"] = smart_output.as_dict()

    decision = controller.decide(ctx)

    smart_tracker.update(session_id, ctx, inspection, decision)

    tracker.update(session_id, ctx, decision)

    tracker_fields = smart_output.as_dict()

    result: dict[str, Any] = {
        "decision": decision.decision.value,
        "advisory": decision.advisory,
        "reason": decision.reason,
        "risk_level": decision.risk_level,
        "session_id": ctx.session_id,
        "fingerprint_id": tracker_fields.get("fingerprint_id", ""),
        "progress_score": tracker_fields.get("progress_score", 0),
        "stagnation_score": tracker_fields.get("stagnation_score", 0),
        "is_progress": tracker_fields.get("is_progress", False),
        "is_stagnation": tracker_fields.get("is_stagnation", False),
        "stagnant_attempts": tracker_fields.get("stagnant_attempts", 0),
        "recommended_decision_hint": tracker_fields.get("recommended_decision_hint", ""),
        "evidence_summary": tracker_fields.get("evidence_summary", ""),
    }

    logger.debug(
        "Autonomy evaluation: decision=%s advisory=%s reason=%s session=%s",
        decision.decision.value,
        decision.advisory,
        decision.reason,
        ctx.session_id,
    )

    return result


def get_autonomy_controller_stats() -> dict[str, Any]:
    controller = _get_controller()
    tracker = _get_tracker()
    stats = controller.get_controller_stats()
    stats["active_session_count"] = len(tracker.all_sessions())
    return stats


def evaluate_and_attach(
    inspection: dict[str, Any] | None,
    session_id: str,
    response: str,
) -> None:
    try:
        result = evaluate_autonomy(
            inspection=inspection,
            session_id=session_id,
            response=response,
        )
        if isinstance(inspection, dict):
            inspection["autonomy_evaluation"] = result
            inspection["autonomy_controller_stats"] = get_autonomy_controller_stats()
    except Exception as exc:
        logger.debug("Autonomy evaluation failed (advisory-only, ignored): %s", exc)


def reset_controller_for_testing() -> None:
    global _DEFAULT_CONTROLLER, _DEFAULT_TRACKER, _DEFAULT_SMART_TRACKER
    _DEFAULT_CONTROLLER = None
    _DEFAULT_TRACKER = None
    _DEFAULT_SMART_TRACKER = None
