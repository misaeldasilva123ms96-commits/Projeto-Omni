"""Public-safe provider health cache and circuit-breaker state.

The cache stores only bounded health metadata. Provider credentials, endpoint
URLs, user ids, response bodies, and exception details are never persisted.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

HEALTH_SCHEMA_VERSION = 1
DEFAULT_HEALTH_TTL_MS = 5 * 60 * 1000
DEFAULT_CIRCUIT_FAILURE_THRESHOLD = 3
DEFAULT_CIRCUIT_OPEN_MS = 60 * 1000


def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(str(os.environ.get(name, "") or "").strip())
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


def _health_ttl_ms() -> int:
    return _bounded_env_int(
        "OMNI_PROVIDER_HEALTH_TTL_MS",
        DEFAULT_HEALTH_TTL_MS,
        1_000,
        24 * 60 * 60 * 1000,
    )


def _failure_threshold() -> int:
    return _bounded_env_int(
        "OMNI_PROVIDER_HEALTH_FAILURE_THRESHOLD",
        DEFAULT_CIRCUIT_FAILURE_THRESHOLD,
        1,
        20,
    )


def _circuit_open_ms() -> int:
    return _bounded_env_int(
        "OMNI_PROVIDER_HEALTH_CIRCUIT_OPEN_MS",
        DEFAULT_CIRCUIT_OPEN_MS,
        1_000,
        60 * 60 * 1000,
    )


def _cache_root() -> Path:
    configured = str(os.environ.get("OMNI_PROVIDER_HEALTH_CACHE_DIR", "") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / ".logs" / "provider-health"


def _cache_path(user_id: str, provider_id: str) -> Path:
    user_digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:24]
    safe_provider = "".join(
        character for character in provider_id.lower() if character.isalnum() or character in "-_"
    )[:64]
    if not safe_provider:
        raise ValueError("Provider id is required for health cache")
    return _cache_root() / f"{user_digest}.{safe_provider}.json"


def _empty_health() -> dict[str, Any]:
    return {
        "reachable": None,
        "healthy": None,
        "health_valid": False,
        "last_checked_at": None,
        "valid_until": None,
        "latency_ms": None,
        "cache_status": "missing",
        "circuit_state": "closed",
        "consecutive_failures": 0,
        "next_probe_at": None,
    }


def read_provider_health(
    user_id: str,
    provider_id: str,
    *,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Read a cached health snapshot without contacting the provider."""
    path = _cache_path(user_id, provider_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return _empty_health()
    if not isinstance(payload, dict) or payload.get("schema_version") != HEALTH_SCHEMA_VERSION:
        return _empty_health()

    current_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    checked_at = payload.get("last_checked_at")
    valid_until = payload.get("valid_until")
    next_probe_at = payload.get("next_probe_at")
    health_valid = isinstance(valid_until, int) and current_ms <= valid_until
    circuit_state = str(payload.get("circuit_state", "closed") or "closed")
    if circuit_state == "open" and isinstance(next_probe_at, int) and current_ms >= next_probe_at:
        circuit_state = "half_open"

    return {
        "reachable": (
            payload.get("reachable") if isinstance(payload.get("reachable"), bool) else None
        ),
        "healthy": payload.get("healthy") if isinstance(payload.get("healthy"), bool) else None,
        "health_valid": health_valid,
        "last_checked_at": checked_at if isinstance(checked_at, int) else None,
        "valid_until": valid_until if isinstance(valid_until, int) else None,
        "latency_ms": (
            payload.get("latency_ms") if isinstance(payload.get("latency_ms"), int) else None
        ),
        "cache_status": "fresh" if health_valid else "stale",
        "circuit_state": circuit_state,
        "consecutive_failures": int(payload.get("consecutive_failures", 0) or 0),
        "next_probe_at": next_probe_at if isinstance(next_probe_at, int) else None,
    }


def provider_health_probe_allowed(
    user_id: str,
    provider_id: str,
    *,
    now_ms: int | None = None,
) -> tuple[bool, dict[str, Any]]:
    snapshot = read_provider_health(user_id, provider_id, now_ms=now_ms)
    return snapshot["circuit_state"] != "open", snapshot


def record_provider_health(
    user_id: str,
    provider_id: str,
    *,
    reachable: bool,
    healthy: bool,
    latency_ms: int,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Persist one bounded provider test outcome and update circuit state."""
    current_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    previous = read_provider_health(user_id, provider_id, now_ms=current_ms)
    failures = 0 if healthy else int(previous.get("consecutive_failures", 0) or 0) + 1
    circuit_state = "closed"
    next_probe_at = None
    if not healthy and failures >= _failure_threshold():
        circuit_state = "open"
        next_probe_at = current_ms + _circuit_open_ms()

    payload = {
        "schema_version": HEALTH_SCHEMA_VERSION,
        "reachable": bool(reachable),
        "healthy": bool(healthy),
        "last_checked_at": current_ms,
        "valid_until": current_ms + _health_ttl_ms(),
        "latency_ms": min(max(int(latency_ms), 0), 120_000),
        "circuit_state": circuit_state,
        "consecutive_failures": failures,
        "next_probe_at": next_probe_at,
    }
    path = _cache_path(user_id, provider_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        if os.name != "nt":
            temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return read_provider_health(user_id, provider_id, now_ms=current_ms)


def invalidate_provider_health(user_id: str, provider_id: str) -> None:
    """Remove health derived from a credential that changed or was deleted."""
    try:
        _cache_path(user_id, provider_id).unlink(missing_ok=True)
    except OSError:
        return


__all__ = [
    "invalidate_provider_health",
    "provider_health_probe_allowed",
    "read_provider_health",
    "record_provider_health",
]
