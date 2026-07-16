"""Canonical Omni environment access.

Runtime configuration is accepted exclusively through ``OMNI_*`` names.
"""

from __future__ import annotations

import os


def read_env(name: str, default: str = "") -> str:
    """Read a canonical environment variable without consulting aliases."""
    value = os.getenv(name)
    if value is not None and value.strip():
        return value.strip()
    return str(default).strip()


def read_env_bool(name: str, default: bool = False) -> bool:
    value = read_env(name, "true" if default else "false")
    return value.lower() in {"1", "true", "yes", "on"}


def read_env_int(name: str, default: int) -> int:
    try:
        return int(read_env(name, str(default)))
    except ValueError:
        return default


def read_env_float(name: str, default: float) -> float:
    try:
        return float(read_env(name, str(default)))
    except ValueError:
        return default


__all__ = ["read_env", "read_env_bool", "read_env_float", "read_env_int"]
