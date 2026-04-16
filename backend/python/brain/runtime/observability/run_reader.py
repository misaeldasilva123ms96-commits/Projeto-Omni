from pathlib import Path
from typing import Any

from brain.runtime.control import RunRegistry
from brain.runtime.control.run_identity import normalize_run_id
from brain.runtime.control.governance_read_model import build_operational_governance_snapshot
from brain.runtime.control.program_closure import (
    empty_operational_governance_fallback,
    empty_resolution_summary_fallback,
)


def read_active_runs(root: Path) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return [item.as_dict() for item in registry.get_active()]
    except Exception:
        return []


def read_run(root: Path, run_id: str) -> dict[str, Any] | None:
    raw = normalize_run_id(str(run_id or ""))
    if not raw:
        return None
    try:
        registry = RunRegistry(root)
        record = registry.get(raw)
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
        return empty_resolution_summary_fallback()


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


def read_recent_governance_timeline_events(root: Path, *, limit: int = 25) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return registry.recent_governance_timeline_events(limit=max(1, int(limit or 25)))
    except Exception:
        return []


def read_latest_governance_event_by_run(root: Path) -> dict[str, dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return registry.latest_governance_event_by_run()
    except Exception:
        return {}


def read_operational_governance(root: Path, *, timeline_limit: int = 25) -> dict[str, Any]:
    try:
        registry = RunRegistry(root)
        return build_operational_governance_snapshot(registry, timeline_limit=timeline_limit)
    except Exception:
        return empty_operational_governance_fallback(summary=read_resolution_summary(root))
