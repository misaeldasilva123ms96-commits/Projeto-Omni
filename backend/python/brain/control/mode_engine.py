from __future__ import annotations

from enum import Enum
from typing import Any


class RuntimeMode(str, Enum):
    EXPLORE = "EXPLORE"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    RECOVER = "RECOVER"
    REPORT = "REPORT"


ALLOWED_MODE_TRANSITIONS: dict[RuntimeMode, set[RuntimeMode]] = {
    RuntimeMode.EXPLORE: {RuntimeMode.EXPLORE, RuntimeMode.PLAN, RuntimeMode.REPORT},
    RuntimeMode.PLAN: {RuntimeMode.PLAN, RuntimeMode.EXECUTE, RuntimeMode.VERIFY, RuntimeMode.REPORT},
    RuntimeMode.EXECUTE: {RuntimeMode.EXECUTE, RuntimeMode.VERIFY, RuntimeMode.RECOVER, RuntimeMode.REPORT},
    RuntimeMode.VERIFY: {RuntimeMode.VERIFY, RuntimeMode.REPORT, RuntimeMode.RECOVER, RuntimeMode.EXECUTE},
    RuntimeMode.RECOVER: {RuntimeMode.RECOVER, RuntimeMode.PLAN, RuntimeMode.EXECUTE, RuntimeMode.REPORT},
    RuntimeMode.REPORT: {RuntimeMode.REPORT, RuntimeMode.EXPLORE, RuntimeMode.PLAN},
}

MODE_ALLOWED_ACTIONS: dict[RuntimeMode, set[str]] = {
    RuntimeMode.EXPLORE: {"read", "inspect", "search", "retrieve_memory"},
    RuntimeMode.PLAN: {"classify", "plan", "route", "prepare_verification"},
    RuntimeMode.EXECUTE: {"execute", "mutate", "delegate"},
    RuntimeMode.VERIFY: {"test", "validate", "review"},
    RuntimeMode.RECOVER: {"retry", "rollback", "fallback"},
    RuntimeMode.REPORT: {"summarize", "emit_status", "generate_report"},
}


def can_transition(from_mode: RuntimeMode, to_mode: RuntimeMode) -> bool:
    return to_mode in ALLOWED_MODE_TRANSITIONS.get(from_mode, set())


def get_allowed_actions(mode: RuntimeMode) -> set[str]:
    return set(MODE_ALLOWED_ACTIONS.get(mode, set()))


def build_mode_transition_event(
    *,
    session_id: str,
    from_mode: RuntimeMode,
    to_mode: RuntimeMode,
    reason_code: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "from_mode": from_mode.value,
        "to_mode": to_mode.value,
        "reason_code": reason_code,
        "details": details or {},
    }
