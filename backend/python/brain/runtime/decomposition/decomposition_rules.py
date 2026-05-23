from __future__ import annotations

from typing import Any

from .decomposition_limits import MAX_DEPTH


def strategy_mode(strategy_summary: dict[str, Any]) -> str:
    sel = strategy_summary.get("selected_strategy") if isinstance(strategy_summary.get("selected_strategy"), dict) else {}
    return str(sel.get("mode", "") or "").strip().lower()


def should_include_generation(step: dict[str, Any], mode: str) -> bool:
    st = str(step.get("step_type", "") or "").lower()
    if any(k in st for k in ("implement", "code", "write", "mutat", "patch", "build")):
        return True
    if mode in ("deep", "heavy") and "verify" not in st:
        return True
    return False


def validate_subtask_dependencies(subtasks: list[dict[str, Any]], valid_parent_ids: set[str]) -> list[str]:
    """Return issues (bounded); does not mutate plan."""
    issues: list[str] = []
    known_ids = {str(s.get("id", "")) for s in subtasks if str(s.get("id", "")).strip()}
    for s in subtasks:
        sid = str(s.get("id", "")).strip()
        pid = str(s.get("parent_step_id", "")).strip()
        if pid and pid not in valid_parent_ids:
            issues.append(f"subtask_parent_unknown:{sid}->{pid}")
        for dep in s.get("depends_on", []) or []:
            d = str(dep).strip()
            if d and d not in known_ids:
                issues.append(f"subtask_dep_unknown:{sid}->{d}")
        depth = int(s.get("depth", 0) or 0)
        if depth > MAX_DEPTH:
            issues.append(f"subtask_depth_exceeds_cap:{sid}")
    return issues[:12]
