from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from .memory_facade import MemoryFacade
from .memory_models import utc_now_iso
from .runtime_integration import get_memory_facade

_SAFE_ERROR_CATEGORIES = {"", "memory_unavailable", "cleanup_failed", "cleanup_degraded", "count_failed"}
_OPERATION_TYPE = "cleanup_autonomy_session_states"


@dataclass(frozen=True)
class AutonomySessionCleanupResult:
    operation_id: str
    operation_type: str
    attempted: bool
    supported: bool
    dry_run: bool
    sqlite_path_fingerprint: str
    sqlite_path_present: bool
    would_delete_count: int
    deleted_count: int
    degraded: bool
    error_category: str
    attempted_at: str
    sqlite_enabled: bool
    sqlite_connected: bool
    cutoff_time: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "attempted": self.attempted,
            "supported": self.supported,
            "dry_run": self.dry_run,
            "sqlite_path_fingerprint": self.sqlite_path_fingerprint,
            "sqlite_path_present": self.sqlite_path_present,
            "would_delete_count": self.would_delete_count,
            "deleted_count": self.deleted_count,
            "degraded": self.degraded,
            "error_category": self.error_category,
            "attempted_at": self.attempted_at,
            "sqlite_enabled": self.sqlite_enabled,
            "sqlite_connected": self.sqlite_connected,
            "cutoff_time": self.cutoff_time,
        }


def cleanup_expired_autonomy_session_states_manual(
    *,
    facade: MemoryFacade | None = None,
    now: str | None = None,
    dry_run: bool = False,
    sqlite_path: str | Path | None = None,
) -> AutonomySessionCleanupResult:
    """Explicit manual hook for expired autonomy session state cleanup."""
    attempted_at = utc_now_iso()
    cutoff_time = str(now or attempted_at)
    operation_id = _new_operation_id()
    sqlite_path_present, sqlite_path_fingerprint = _sqlite_path_observability(sqlite_path)
    try:
        memory = facade if facade is not None else get_memory_facade()
    except Exception:
        return AutonomySessionCleanupResult(
            operation_id=operation_id,
            operation_type=_OPERATION_TYPE,
            attempted=True,
            supported=False,
            dry_run=dry_run,
            sqlite_path_fingerprint=sqlite_path_fingerprint,
            sqlite_path_present=sqlite_path_present,
            would_delete_count=0,
            deleted_count=0,
            degraded=True,
            error_category="memory_unavailable",
            attempted_at=attempted_at,
            sqlite_enabled=False,
            sqlite_connected=False,
            cutoff_time=cutoff_time,
        )

    if memory is None:
        return AutonomySessionCleanupResult(
            operation_id=operation_id,
            operation_type=_OPERATION_TYPE,
            attempted=True,
            supported=False,
            dry_run=dry_run,
            sqlite_path_fingerprint=sqlite_path_fingerprint,
            sqlite_path_present=sqlite_path_present,
            would_delete_count=0,
            deleted_count=0,
            degraded=True,
            error_category="memory_unavailable",
            attempted_at=attempted_at,
            sqlite_enabled=False,
            sqlite_connected=False,
            cutoff_time=cutoff_time,
        )

    try:
        sqlite_enabled = bool(getattr(memory, "sqlite_enabled", False))
        sqlite_connected = bool(getattr(memory, "is_sqlite_connected", False))
        sqlite_supported = bool(
            sqlite_enabled
            and sqlite_connected
        )
    except Exception:
        sqlite_enabled = False
        sqlite_connected = False
        sqlite_supported = False

    if not sqlite_supported:
        return AutonomySessionCleanupResult(
            operation_id=operation_id,
            operation_type=_OPERATION_TYPE,
            attempted=True,
            supported=False,
            dry_run=dry_run,
            sqlite_path_fingerprint=sqlite_path_fingerprint,
            sqlite_path_present=sqlite_path_present,
            would_delete_count=0,
            deleted_count=0,
            degraded=False,
            error_category="",
            attempted_at=attempted_at,
            sqlite_enabled=sqlite_enabled,
            sqlite_connected=sqlite_connected,
            cutoff_time=cutoff_time,
        )

    try:
        if dry_run:
            diagnostics = memory.get_autonomy_session_state_lifecycle_diagnostics(cutoff_time)
            degraded = bool(diagnostics.get("cleanup_degraded", False))
            error_category = _safe_error_category(diagnostics.get("cleanup_last_error_category", ""))
            return AutonomySessionCleanupResult(
                operation_id=operation_id,
                operation_type=_OPERATION_TYPE,
                attempted=True,
                supported=True,
                dry_run=True,
                sqlite_path_fingerprint=sqlite_path_fingerprint,
                sqlite_path_present=sqlite_path_present,
                would_delete_count=max(0, int(diagnostics.get("expired_state_count", 0))),
                deleted_count=0,
                degraded=degraded,
                error_category=error_category if degraded else "",
                attempted_at=attempted_at,
                sqlite_enabled=sqlite_enabled,
                sqlite_connected=sqlite_connected,
                cutoff_time=cutoff_time,
            )
        deleted = memory.cleanup_expired_autonomy_session_states(now)
        diagnostics = memory.get_autonomy_session_state_lifecycle_diagnostics(now)
        degraded = bool(diagnostics.get("cleanup_degraded", False))
        error_category = _safe_error_category(diagnostics.get("cleanup_last_error_category", ""))
        return AutonomySessionCleanupResult(
            operation_id=operation_id,
            operation_type=_OPERATION_TYPE,
            attempted=True,
            supported=True,
            dry_run=False,
            sqlite_path_fingerprint=sqlite_path_fingerprint,
            sqlite_path_present=sqlite_path_present,
            would_delete_count=0,
            deleted_count=max(0, int(deleted)),
            degraded=degraded,
            error_category=error_category if degraded else "",
            attempted_at=str(diagnostics.get("last_cleanup_attempted_at") or attempted_at),
            sqlite_enabled=sqlite_enabled,
            sqlite_connected=sqlite_connected,
            cutoff_time=cutoff_time,
        )
    except Exception:
        return AutonomySessionCleanupResult(
            operation_id=operation_id,
            operation_type=_OPERATION_TYPE,
            attempted=True,
            supported=True,
            dry_run=dry_run,
            sqlite_path_fingerprint=sqlite_path_fingerprint,
            sqlite_path_present=sqlite_path_present,
            would_delete_count=0,
            deleted_count=0,
            degraded=True,
            error_category="cleanup_failed",
            attempted_at=attempted_at,
            sqlite_enabled=sqlite_enabled,
            sqlite_connected=sqlite_connected,
            cutoff_time=cutoff_time,
        )


def _safe_error_category(value: Any) -> str:
    category = str(value or "")
    if category in _SAFE_ERROR_CATEGORIES:
        return category
    return "cleanup_degraded" if category else ""


def _new_operation_id() -> str:
    return f"cleanup-{uuid4().hex[:12]}"


def _sqlite_path_observability(sqlite_path: str | Path | None) -> tuple[bool, str]:
    if sqlite_path is None:
        return False, ""
    raw = str(sqlite_path).strip()
    if not raw:
        return False, ""
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return True, f"sha256:{digest}"
