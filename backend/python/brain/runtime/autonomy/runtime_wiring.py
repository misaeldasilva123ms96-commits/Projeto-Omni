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

logger = logging.getLogger(__name__)

_DEFAULT_CONTROLLER: AutonomyController | None = None


def _get_controller() -> AutonomyController:
    global _DEFAULT_CONTROLLER
    if _DEFAULT_CONTROLLER is None:
        _DEFAULT_CONTROLLER = AutonomyController()
    return _DEFAULT_CONTROLLER


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


def evaluate_autonomy(
    inspection: dict[str, Any] | None,
    session_id: str,
    response: str,
    *,
    controller: AutonomyController | None = None,
) -> dict[str, Any]:
    if controller is None:
        controller = _get_controller()

    ctx = build_autonomy_context(
        inspection=inspection,
        session_id=session_id,
        response=response,
    )

    decision = controller.decide(ctx)

    result: dict[str, Any] = {
        "decision": decision.decision.value,
        "advisory": decision.advisory,
        "reason": decision.reason,
        "risk_level": decision.risk_level,
        "session_id": ctx.session_id,
    }

    logger.debug(
        "Autonomy evaluation: decision=%s advisory=%s reason=%s",
        decision.decision.value,
        decision.advisory,
        decision.reason,
    )

    return result


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
    except Exception as exc:
        logger.debug("Autonomy evaluation failed (advisory-only, ignored): %s", exc)


def reset_controller_for_testing() -> None:
    global _DEFAULT_CONTROLLER
    _DEFAULT_CONTROLLER = None
