"""Per-session state tracker for autonomy decisions.

Tracks safe session-level metadata across turns to detect repeated errors,
stagnation, and progress. Process-local state remains the default source of
truth; MemoryFacade persistence is SQLite opt-in and best-effort.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from .autonomy_session_state import AutonomySessionState
from .autonomy_models import AutonomyContext, AutonomyDecision

logger = logging.getLogger(__name__)

try:
    from brain.memory.memory_facade import MemoryFacade
    from brain.memory.memory_models import AutonomySessionStateRecord

    _HAS_MEMORY_CONTRACTS = True
except ImportError:
    MemoryFacade = Any  # type: ignore[misc,assignment]
    AutonomySessionStateRecord = Any  # type: ignore[misc,assignment]
    _HAS_MEMORY_CONTRACTS = False

_RUNTIME_MODE_ORDER: dict[str, int] = {
    "provider_failure": 0,
    "safe_fallback": 1,
    "node_fallback": 2,
    "standard": 3,
    "default": 3,
    "normal": 3,
}

_PROCESS_LOCAL_DIAGNOSTIC = {
    "session_state_source": "process_local",
    "session_state_persistence_enabled": False,
    "session_state_hydrated": False,
    "session_state_upserted": False,
    "session_state_degraded": False,
    "session_state_last_error_category": "",
    "session_state_updated_at": "",
    "session_state_expires_at": "",
    "session_state_fields_count": 0,
    "expired_state_cleanup_supported": False,
    "last_cleanup_attempted_at": "",
    "last_cleanup_deleted_count": 0,
    "cleanup_degraded": False,
    "cleanup_last_error_category": "",
    "session_state_ttl_seconds": 604800,
    "expired_state_count": 0,
}


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _safe_diagnostic_string(value: Any) -> str:
    text = str(value or "").replace("\x00", "").strip()
    lowered = text.lower()
    if any(marker in lowered for marker in ("sk-", "api_key", "authorization:", "bearer ", "token=", "secret=")):
        return "[REDACTED]"
    return text[:80]


class AutonomySessionTracker:
    """Tracks per-session autonomy state across turns.

    Process-local storage. Detects progress and stagnation based on
    safe metadata only. No raw prompts, responses, or secrets stored.
    """

    def __init__(self, *, memory_facade: MemoryFacade | None = None) -> None:
        self._sessions: dict[str, AutonomySessionState] = {}
        self._memory_facade = memory_facade
        self._hydrated_sessions: set[str] = set()
        self._session_diagnostics: dict[str, dict[str, Any]] = {}

    def _set_diagnostic(
        self,
        session_id: str,
        *,
        source: str,
        persistence_enabled: bool,
        hydrated: bool = False,
        upserted: bool = False,
        degraded: bool = False,
        last_error_category: str = "",
        state: AutonomySessionState | None = None,
    ) -> None:
        diagnostic = {
            "session_state_source": source,
            "session_state_persistence_enabled": persistence_enabled,
            "session_state_hydrated": hydrated,
            "session_state_upserted": upserted,
            "session_state_degraded": degraded,
            "session_state_last_error_category": _safe_diagnostic_string(last_error_category),
            "session_state_updated_at": state.updated_at if state else "",
            "session_state_expires_at": state.expires_at if state else "",
            "session_state_fields_count": _state_fields_count(state),
        }
        diagnostic.update(self._cleanup_lifecycle_diagnostics())
        self._session_diagnostics[session_id] = diagnostic

    def _cleanup_lifecycle_diagnostics(self) -> dict[str, Any]:
        default = {
            "expired_state_cleanup_supported": False,
            "last_cleanup_attempted_at": "",
            "last_cleanup_deleted_count": 0,
            "cleanup_degraded": False,
            "cleanup_last_error_category": "",
            "session_state_ttl_seconds": 604800,
            "expired_state_count": 0,
        }
        facade = self._memory_facade
        if facade is None or not _HAS_MEMORY_CONTRACTS:
            return default
        getter = getattr(facade, "get_autonomy_session_state_lifecycle_diagnostics", None)
        if getter is None:
            return default
        try:
            raw = getter()
        except Exception:
            default["cleanup_degraded"] = True
            default["cleanup_last_error_category"] = "diagnostics_failed"
            return default
        if not isinstance(raw, dict):
            return default
        return {
            "expired_state_cleanup_supported": bool(raw.get("expired_state_cleanup_supported", False)),
            "last_cleanup_attempted_at": _safe_diagnostic_string(raw.get("last_cleanup_attempted_at", "")),
            "last_cleanup_deleted_count": _safe_int(raw.get("last_cleanup_deleted_count", 0)),
            "cleanup_degraded": bool(raw.get("cleanup_degraded", False)),
            "cleanup_last_error_category": _safe_diagnostic_string(raw.get("cleanup_last_error_category", "")),
            "session_state_ttl_seconds": _safe_int(raw.get("session_state_ttl_seconds", 604800)),
            "expired_state_count": _safe_int(raw.get("expired_state_count", 0)),
        }

    def _sqlite_persistence_enabled(self) -> bool:
        facade = self._memory_facade
        if facade is None or not _HAS_MEMORY_CONTRACTS:
            return False
        return bool(
            getattr(facade, "sqlite_enabled", False)
            and getattr(facade, "is_sqlite_connected", False)
        )

    @staticmethod
    def _record_to_state(record: AutonomySessionStateRecord) -> AutonomySessionState:
        return AutonomySessionState(
            session_id=record.session_id,
            last_error_type=record.last_error_type,
            current_error_count=record.current_error_count,
            stagnant_attempts=record.stagnant_attempts,
            distinct_error_types=set(record.distinct_error_types),
            progressive_cycles=record.progressive_cycles,
            last_runtime_mode=record.last_runtime_mode,
            last_provider_failure_type=record.last_provider_failure_type,
            last_response_length=record.last_response_length,
            last_response_was_safe_fallback=record.last_response_was_safe_fallback,
            last_decision=record.last_decision,
            last_fingerprint_id=record.last_fingerprint_id,
            last_progress_score=record.last_progress_score,
            last_stagnation_score=record.last_stagnation_score,
            repeated_strategy_count=record.repeated_strategy_count,
            strategies_attempted=list(record.strategies_attempted),
            updated_at=record.updated_at,
            expires_at=record.expires_at,
        )

    @staticmethod
    def _state_to_record(state: AutonomySessionState) -> AutonomySessionStateRecord | None:
        if not _HAS_MEMORY_CONTRACTS:
            return None
        return AutonomySessionStateRecord.from_dict({
            "session_id": state.session_id,
            "last_error_type": state.last_error_type,
            "current_error_count": state.current_error_count,
            "stagnant_attempts": state.stagnant_attempts,
            "distinct_error_count": len(state.distinct_error_types),
            "distinct_error_types": sorted(state.distinct_error_types),
            "progressive_cycles": state.progressive_cycles,
            "last_runtime_mode": state.last_runtime_mode,
            "last_provider_failure_type": state.last_provider_failure_type,
            "last_response_length": state.last_response_length,
            "last_response_was_safe_fallback": state.last_response_was_safe_fallback,
            "last_decision": state.last_decision,
            "last_fingerprint_id": state.last_fingerprint_id,
            "last_progress_score": state.last_progress_score,
            "last_stagnation_score": state.last_stagnation_score,
            "repeated_strategy_count": state.repeated_strategy_count,
            "strategies_attempted": list(state.strategies_attempted),
            "updated_at": state.updated_at,
            "expires_at": state.expires_at,
        })

    def _hydrate_from_memory(self, session_id: str) -> AutonomySessionState | None:
        if session_id in self._hydrated_sessions:
            return None
        self._hydrated_sessions.add(session_id)
        persistence_requested = bool(getattr(self._memory_facade, "sqlite_enabled", False)) if self._memory_facade else False
        if not persistence_requested:
            self._set_diagnostic(
                session_id,
                source="process_local",
                persistence_enabled=False,
            )
            return None
        if not self._sqlite_persistence_enabled():
            self._set_diagnostic(
                session_id,
                source="sqlite_unavailable",
                persistence_enabled=True,
                degraded=True,
            )
            return None
        try:
            record = self._memory_facade.get_autonomy_session_state(session_id)
        except Exception as exc:
            logger.debug("Autonomy session state hydrate failed: %s", exc)
            self._set_diagnostic(
                session_id,
                source="sqlite_read_failed",
                persistence_enabled=True,
                degraded=True,
            )
            return None
        if record is None:
            self._set_diagnostic(
                session_id,
                source="sqlite_missing",
                persistence_enabled=True,
            )
            return None
        try:
            state = self._record_to_state(record)
            self._set_diagnostic(
                session_id,
                source="sqlite_hydrated",
                persistence_enabled=True,
                hydrated=True,
                state=state,
            )
            return state
        except Exception as exc:
            logger.debug("Autonomy session state hydrate decode failed: %s", exc)
            self._set_diagnostic(
                session_id,
                source="sqlite_read_failed",
                persistence_enabled=True,
                degraded=True,
            )
            return None

    def _persist_to_memory(self, state: AutonomySessionState) -> None:
        if not self._sqlite_persistence_enabled():
            previous = self._session_diagnostics.get(state.session_id, {})
            persistence_requested = bool(getattr(self._memory_facade, "sqlite_enabled", False)) if self._memory_facade else False
            self._set_diagnostic(
                state.session_id,
                source=str(previous.get("session_state_source") or "process_local"),
                persistence_enabled=persistence_requested,
                hydrated=bool(previous.get("session_state_hydrated")),
                upserted=False,
                degraded=bool(previous.get("session_state_degraded")),
                last_error_category=state.last_error_type,
                state=state,
            )
            return
        try:
            record = self._state_to_record(state)
            if record is not None:
                self._memory_facade.record_autonomy_session_state(record)
                previous = self._session_diagnostics.get(state.session_id, {})
                self._set_diagnostic(
                    state.session_id,
                    source=str(previous.get("session_state_source") or "sqlite_missing"),
                    persistence_enabled=True,
                    hydrated=bool(previous.get("session_state_hydrated")),
                    upserted=True,
                    degraded=bool(previous.get("session_state_degraded")),
                    last_error_category=state.last_error_type,
                    state=state,
                )
        except Exception as exc:
            logger.debug("Autonomy session state persist failed: %s", exc)
            previous = self._session_diagnostics.get(state.session_id, {})
            self._set_diagnostic(
                state.session_id,
                source="sqlite_write_failed",
                persistence_enabled=True,
                hydrated=bool(previous.get("session_state_hydrated")),
                upserted=False,
                degraded=True,
                last_error_category=state.last_error_type,
                state=state,
            )

    def get_or_create(self, session_id: str) -> AutonomySessionState:
        if session_id not in self._sessions:
            hydrated = self._hydrate_from_memory(session_id)
            self._sessions[session_id] = hydrated or AutonomySessionState(session_id=session_id)
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
        tracker_fields = ctx.metadata.get("error_progress_tracker")
        if isinstance(tracker_fields, dict):
            state.last_fingerprint_id = str(tracker_fields.get("fingerprint_id") or "")
            state.last_progress_score = _safe_int(tracker_fields.get("progress_score", 0))
            state.last_stagnation_score = _safe_int(tracker_fields.get("stagnation_score", 0))
            state.repeated_strategy_count = _safe_int(tracker_fields.get("repeated_strategy_count", 0))
            strategies = tracker_fields.get("strategies_attempted", [])
            if isinstance(strategies, list):
                state.strategies_attempted = [str(item) for item in strategies]
        state.updated_at = datetime.now(timezone.utc).isoformat()
        state.expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        self._persist_to_memory(state)

        return state

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def reset_all(self) -> None:
        self._sessions.clear()

    def get_state(self, session_id: str) -> AutonomySessionState | None:
        return self._sessions.get(session_id)

    def all_sessions(self) -> dict[str, AutonomySessionState]:
        return dict(self._sessions)

    def get_session_diagnostics(self, session_id: str) -> dict[str, Any]:
        diagnostic = self._session_diagnostics.get(session_id)
        if diagnostic is None:
            return dict(_PROCESS_LOCAL_DIAGNOSTIC)
        return dict(diagnostic)


def _state_fields_count(state: AutonomySessionState | None) -> int:
    if state is None:
        return 0
    return sum(
        1
        for value in (
            state.session_id,
            state.last_error_type,
            state.current_error_count,
            state.stagnant_attempts,
            len(state.distinct_error_types),
            state.progressive_cycles,
            state.last_runtime_mode,
            state.last_provider_failure_type,
            state.last_response_length,
            state.last_response_was_safe_fallback,
            state.last_decision,
            state.last_fingerprint_id,
            state.last_progress_score,
            state.last_stagnation_score,
            state.repeated_strategy_count,
            len(state.strategies_attempted),
            state.updated_at,
            state.expires_at,
        )
        if value not in ("", 0, False, None)
    )
