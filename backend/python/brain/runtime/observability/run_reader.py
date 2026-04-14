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
