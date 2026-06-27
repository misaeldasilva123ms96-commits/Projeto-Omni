from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .memory_facade import MemoryFacade
from .memory_models import utc_now_iso
from .runtime_integration import get_memory_facade

_SAFE_ERROR_CATEGORIES = {"", "memory_unavailable", "cleanup_failed", "cleanup_degraded"}


@dataclass(frozen=True)
class AutonomySessionCleanupResult:
    attempted: bool
    supported: bool
    deleted_count: int
    degraded: bool
    error_category: str
    attempted_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempted": self.attempted,
            "supported": self.supported,
            "deleted_count": self.deleted_count,
            "degraded": self.degraded,
            "error_category": self.error_category,
            "attempted_at": self.attempted_at,
        }


def cleanup_expired_autonomy_session_states_manual(
    *,
    facade: MemoryFacade | None = None,
    now: str | None = None,
) -> AutonomySessionCleanupResult:
    """Explicit manual hook for expired autonomy session state cleanup."""
    attempted_at = utc_now_iso()
    try:
        memory = facade if facade is not None else get_memory_facade()
    except Exception:
        return AutonomySessionCleanupResult(
            attempted=True,
            supported=False,
            deleted_count=0,
            degraded=True,
            error_category="memory_unavailable",
            attempted_at=attempted_at,
        )

    if memory is None:
        return AutonomySessionCleanupResult(
            attempted=True,
            supported=False,
            deleted_count=0,
            degraded=True,
            error_category="memory_unavailable",
            attempted_at=attempted_at,
        )

    try:
        sqlite_supported = bool(
            getattr(memory, "sqlite_enabled", False)
            and getattr(memory, "is_sqlite_connected", False)
        )
    except Exception:
        sqlite_supported = False

    if not sqlite_supported:
        return AutonomySessionCleanupResult(
            attempted=True,
            supported=False,
            deleted_count=0,
            degraded=False,
            error_category="",
            attempted_at=attempted_at,
        )

    try:
        deleted = memory.cleanup_expired_autonomy_session_states(now)
        diagnostics = memory.get_autonomy_session_state_lifecycle_diagnostics(now)
        degraded = bool(diagnostics.get("cleanup_degraded", False))
        error_category = _safe_error_category(diagnostics.get("cleanup_last_error_category", ""))
        return AutonomySessionCleanupResult(
            attempted=True,
            supported=True,
            deleted_count=max(0, int(deleted)),
            degraded=degraded,
            error_category=error_category if degraded else "",
            attempted_at=str(diagnostics.get("last_cleanup_attempted_at") or attempted_at),
        )
    except Exception:
        return AutonomySessionCleanupResult(
            attempted=True,
            supported=True,
            deleted_count=0,
            degraded=True,
            error_category="cleanup_failed",
            attempted_at=attempted_at,
        )


def _safe_error_category(value: Any) -> str:
    category = str(value or "")
    if category in _SAFE_ERROR_CATEGORIES:
        return category
    return "cleanup_degraded" if category else ""
