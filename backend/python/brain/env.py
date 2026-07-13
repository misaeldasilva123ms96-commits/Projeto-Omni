"""Canonical Omni environment access with legacy OMINI compatibility."""

from __future__ import annotations

import os
import warnings


EXPLICIT_LEGACY_ALIASES: dict[str, str] = {
    "OMNI_BASE_DIR": "BASE_DIR",
    "OMNI_PYTHON_BASE_DIR": "PYTHON_BASE_DIR",
    "OMNI_MEMORY_JSON_PATH": "MEMORY_JSON_PATH",
    "OMNI_MEMORY_DIR": "MEMORY_DIR",
    "OMNI_TRANSCRIPTS_DIR": "TRANSCRIPTS_DIR",
    "OMNI_SESSIONS_DIR": "SESSIONS_DIR",
    "OMNI_NODE_BIN": "NODE_BIN",
}


def legacy_env_names(name: str) -> tuple[str, ...]:
    aliases: list[str] = []
    explicit = EXPLICIT_LEGACY_ALIASES.get(name)
    if explicit:
        aliases.append(explicit)
    if name.startswith("OMNI_"):
        misspelled_alias = f"OMINI_{name.removeprefix('OMNI_')}"
        if misspelled_alias not in aliases:
            aliases.append(misspelled_alias)
    return tuple(aliases)


def read_env(name: str, default: str = "") -> str:
    """Read the canonical name first, then its deprecated legacy alias."""
    canonical_value = os.getenv(name)
    if canonical_value is not None and canonical_value.strip():
        return canonical_value.strip()

    for legacy_name in legacy_env_names(name):
        legacy_value = os.getenv(legacy_name)
        if legacy_value is not None and legacy_value.strip():
            warnings.warn(
                f"{legacy_name} is deprecated; use {name} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return legacy_value.strip()
    return str(default).strip()


def read_env_bool(name: str, default: bool = False) -> bool:
    return read_env(name, "true" if default else "false").lower() in {"1", "true", "yes", "on"}


def read_env_int(name: str, default: int = 0) -> int:
    try:
        return max(0, int(read_env(name, str(default))))
    except (TypeError, ValueError):
        return default


def read_env_float(name: str, default: float = 0.0) -> float:
    try:
        return max(0.0, float(read_env(name, str(default))))
    except (TypeError, ValueError):
        return default


__all__ = ["legacy_env_names", "read_env", "read_env_bool", "read_env_float", "read_env_int"]
