"""Per-session autonomy state model.

Tracks safe session-level metadata for autonomy decisions across turns.
No raw prompts, responses, secrets, or credentials are stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_expires_at() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()


@dataclass(slots=True)
class AutonomySessionState:
    session_id: str
    last_error_type: str = ""
    current_error_count: int = 0
    stagnant_attempts: int = 0
    distinct_error_types: set[str] = field(default_factory=set)
    progressive_cycles: int = 0
    last_runtime_mode: str = ""
    last_provider_failure_type: str = ""
    last_response_length: int = 0
    last_response_was_safe_fallback: bool = False
    last_decision: str = ""
    last_fingerprint_id: str = ""
    last_progress_score: int = 0
    last_stagnation_score: int = 0
    repeated_strategy_count: int = 0
    strategies_attempted: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=_utc_now)
    expires_at: str = field(default_factory=_default_expires_at)
