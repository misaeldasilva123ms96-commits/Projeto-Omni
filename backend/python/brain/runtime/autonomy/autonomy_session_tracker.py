"""Per-session state tracker for autonomy decisions.

Tracks safe session-level metadata across turns to detect repeated errors,
stagnation, and progress. Process-local — no persistence yet.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .autonomy_session_state import AutonomySessionState
from .autonomy_models import AutonomyContext, AutonomyDecision

logger = logging.getLogger(__name__)

_RUNTIME_MODE_ORDER: dict[str, int] = {
    "provider_failure": 0,
    "safe_fallback": 1,
    "node_fallback": 2,
    "standard": 3,
    "default": 3,
    "normal": 3,
}


class AutonomySessionTracker:
    """Tracks per-session autonomy state across turns.

    Process-local storage. Detects progress and stagnation based on
    safe metadata only. No raw prompts, responses, or secrets stored.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, AutonomySessionState] = {}

    def get_or_create(self, session_id: str) -> AutonomySessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = AutonomySessionState(session_id=session_id)
        return self._sessions[session_id]

    def _detect_stagnation(
        self,
        state: AutonomySessionState,
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
        self,
        state: AutonomySessionState,
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

    def update(
        self,
        session_id: str,
        ctx: AutonomyContext,
        decision: AutonomyDecision,
    ) -> AutonomySessionState:
        state = self.get_or_create(session_id)

        if ctx.error_type:
            state.current_error_count += 1
            state.distinct_error_types.add(ctx.error_type)

        is_stagnation = self._detect_stagnation(state, ctx)
        is_progress = self._detect_progress(state, ctx)

        if is_progress:
            state.progressive_cycles += 1
            state.stagnant_attempts = 0
        elif is_stagnation:
            state.stagnant_attempts += 1

        if ctx.error_type:
            state.last_error_type = ctx.error_type
        runtime_mode: str = ctx.metadata.get("runtime_mode", "")
        if runtime_mode:
            state.last_runtime_mode = runtime_mode
        provider_failure: str = ctx.metadata.get("provider_failure_type", "")
        if provider_failure:
            state.last_provider_failure_type = provider_failure
        response_length: Any = ctx.metadata.get("response_length", 0)
        if isinstance(response_length, str):
            try:
                response_length = int(response_length)
            except (ValueError, TypeError):
                response_length = 0
        state.last_response_length = int(response_length) if not isinstance(response_length, int) else response_length
        state.last_response_was_safe_fallback = ctx.no_safe_next_action
        state.last_decision = decision.decision.value
        state.updated_at = datetime.now(timezone.utc).isoformat()

        return state

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def reset_all(self) -> None:
        self._sessions.clear()

    def get_state(self, session_id: str) -> AutonomySessionState | None:
        return self._sessions.get(session_id)

    def all_sessions(self) -> dict[str, AutonomySessionState]:
        return dict(self._sessions)
