from pathlib import Path
from typing import Any

from brain.runtime.control import RunRegistry


def read_active_runs(root: Path) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return [item.as_dict() for item in registry.get_active()]
    except Exception:
        return []


def read_run(root: Path, run_id: str) -> dict[str, Any] | None:
    if not str(run_id or "").strip():
        return None
    try:
        registry = RunRegistry(root)
        record = registry.get(str(run_id).strip())
    except Exception:
        return None
    return record.as_dict() if record is not None else None


def read_runs(root: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return [item.as_dict() for item in registry.get_all(limit=max(1, int(limit or 50)))]
    except Exception:
        return []


def read_resolution_summary(root: Path) -> dict[str, Any]:
    try:
        registry = RunRegistry(root)
        return registry.get_resolution_summary()
    except Exception:
        return {"total_runs": 0, "resolution_counts": {}, "reason_counts": {}}


def read_runs_waiting_operator(root: Path) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return [item.as_dict() for item in registry.get_runs_waiting_operator()]
    except Exception:
        return []


def read_runs_with_rollback(root: Path) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return [item.as_dict() for item in registry.get_runs_with_rollback()]
    except Exception:
        return []


def read_recent_resolution_events(root: Path, *, limit: int = 25) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return registry.recent_resolution_events(limit=max(1, int(limit or 25)))
    except Exception:
        return []
