"""Centralized run_id validation and normalization (Phase 30.14).

``validate_run_id_for_new_write`` applies to **new** run rows (``RunRecord.build``,
orchestrator registration paths). Registry **read** paths use
``resolve_run_id_for_registry_lookup`` so legacy on-disk identifiers remain discoverable
without widening what may be **newly** persisted.
"""

from __future__ import annotations

import re
from typing import Final

RUN_ID_MAX_LEN: Final[int] = 128
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def normalize_run_id(value: str | None) -> str:
    """Trim boundaries only; preserve casing for backward compatibility."""
    return str(value or "").strip()


def validate_run_id_for_new_write(value: object) -> str:
    """Return a normalized run_id or raise ``ValueError`` with an explicit message."""
    s = normalize_run_id(str(value))
    if not s:
        raise ValueError("run_id must be a non-empty string")
    if len(s) > RUN_ID_MAX_LEN:
        raise ValueError(f"run_id exceeds maximum length ({RUN_ID_MAX_LEN})")
    if ".." in s or "/" in s or "\\" in s:
        raise ValueError("run_id must not contain path separators or traversal sequences")
    if not _RUN_ID_RE.fullmatch(s):
        raise ValueError(
            "run_id must contain only letters, digits, hyphen, and underscore (ASCII) after trimming"
        )
    return s


def resolve_run_id_for_registry_lookup(value: str | None) -> str:
    """Normalize for lookup; accept legacy keys that fail strict validation."""
    raw = normalize_run_id(str(value))
    if not raw:
        return ""
    try:
        return validate_run_id_for_new_write(raw)
    except ValueError:
        return raw


def run_id_lookup_keys(value: str | None) -> tuple[str, ...]:
    """Ordered candidate keys for registry ``get`` / ``update_status`` (strict first, then raw)."""
    raw = normalize_run_id(str(value))
    if not raw:
        return ()
    try:
        canon = validate_run_id_for_new_write(raw)
    except ValueError:
        return (raw,)
    return (canon, raw) if canon != raw else (canon,)


def validate_run_id_for_operator_cli(value: object) -> str:
    """
    Operator/CLI boundary: non-empty, max length, no path separators or traversal.

    Unlike :func:`validate_run_id_for_new_write`, this allows legacy punctuation and
    whitespace so existing on-disk run keys remain addressable from the control CLI.
    """
    s = normalize_run_id(str(value))
    if not s:
        raise ValueError("run_id must be a non-empty string")
    if len(s) > RUN_ID_MAX_LEN:
        raise ValueError(f"run_id exceeds maximum length ({RUN_ID_MAX_LEN})")
    if ".." in s or "/" in s or "\\" in s:
        raise ValueError("run_id must not contain path separators or traversal sequences")
    return s


def coerce_runtime_run_id(*, run_id: str | None, session_id: str, prefix: str = "run") -> str:
    """
    Coerce an untrusted runtime ``run_id`` (e.g. from node execution_request) to a
    validator-safe value. Invalid or empty inputs fall back to ``{prefix}-{session}``
    with unsafe characters stripped from the session token.
    """
    raw = normalize_run_id(str(run_id or ""))
    if raw:
        try:
            return validate_run_id_for_new_write(raw)
        except ValueError:
            pass
    pfx = normalize_run_id(str(prefix or "run"))
    if not pfx or not _RUN_ID_RE.fullmatch(pfx):
        pfx = "run"
    token = re.sub(r"[^A-Za-z0-9_-]+", "_", normalize_run_id(str(session_id or ""))).strip("_")
    if not token:
        token = "session"
    candidate = f"{pfx}-{token}"[:RUN_ID_MAX_LEN]
    return validate_run_id_for_new_write(candidate)
