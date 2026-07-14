from __future__ import annotations

import os
from pathlib import Path


_WINDOWS_RESERVED_STEMS = {
    "AUX",
    "CON",
    "NUL",
    "PRN",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class WorkspacePathError(ValueError):
    """Raised when a caller-controlled path cannot be contained in a workspace."""

    def __init__(self, code: str = "path_outside_workspace") -> None:
        super().__init__(code)
        self.code = code


def resolve_workspace_path(
    workspace_root: Path,
    raw_path: str,
    *,
    allow_workspace_root: bool = False,
) -> Path:
    """Resolve a relative path and prove that its canonical target stays in the workspace."""

    value = str(raw_path or "")
    if not value.strip() or "\x00" in value:
        raise WorkspacePathError("invalid_workspace_path")

    relative_path = Path(value)
    if relative_path.is_absolute() or relative_path.anchor or relative_path.drive:
        raise WorkspacePathError()
    if any(part == ".." for part in relative_path.parts):
        raise WorkspacePathError()
    if os.name == "nt" and any(_is_unsafe_windows_part(part) for part in relative_path.parts):
        raise WorkspacePathError("invalid_workspace_path")

    try:
        root = Path(workspace_root).resolve()
        target = (root / relative_path).resolve()
        target.relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise WorkspacePathError() from error

    if not allow_workspace_root and target == root:
        raise WorkspacePathError("invalid_workspace_path")
    return target


def validate_workspace_glob_pattern(raw_pattern: str) -> str:
    """Reject glob patterns that can address paths outside the selected search root."""

    pattern = str(raw_pattern or "").strip()
    if not pattern or "\x00" in pattern:
        raise WorkspacePathError("invalid_glob_pattern")

    pattern_path = Path(pattern)
    if pattern_path.is_absolute() or pattern_path.anchor or pattern_path.drive:
        raise WorkspacePathError("invalid_glob_pattern")
    if any(part == ".." for part in pattern_path.parts):
        raise WorkspacePathError("invalid_glob_pattern")
    if os.name == "nt" and any(_is_unsafe_windows_part(part) for part in pattern_path.parts):
        raise WorkspacePathError("invalid_glob_pattern")
    return pattern


def resolve_workspace_entry(workspace_root: Path, entry_path: Path) -> tuple[Path, Path]:
    """Return a safe canonical entry and its original relative path during enumeration."""

    try:
        root = Path(workspace_root).resolve()
        relative_path = Path(entry_path).relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise WorkspacePathError() from error
    target = resolve_workspace_path(root, str(relative_path))
    return target, relative_path


def _is_unsafe_windows_part(part: str) -> bool:
    if ":" in part or part != part.rstrip(" ."):
        return True
    stem = part.split(".", 1)[0].upper()
    return stem in _WINDOWS_RESERVED_STEMS
