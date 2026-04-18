"""Append-only tool outcome rows to Supabase Postgres via PostgREST (stdlib only)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _truncate(s: str, max_chars: int) -> str:
    t = str(s or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1] + "…"


def _sanitize_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict) or not raw:
        return {}
    out: dict[str, Any] = {}
    for k, v in list(raw.items())[:24]:
        key = _truncate(str(k), 64)
        if not key:
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[key] = v
        elif isinstance(v, dict):
            out[key] = _sanitize_metadata(v)
        else:
            out[key] = _truncate(str(v), 200)
    return out


def error_code_from_tool_result(result: dict[str, Any]) -> str | None:
    if bool(result.get("ok")):
        return None
    ep = result.get("error_payload")
    if isinstance(ep, dict):
        kind = str(ep.get("kind", "") or "").strip()
        return kind or None
    return "unknown_error"


def record_runtime_tool_event(
    *,
    session_id: str,
    task_id: str,
    run_id: str,
    tool_name: str,
    success: bool,
    error_code: str | None,
    latency_ms: int | None,
    provider: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """
    POST one row to Supabase REST. Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
    Never raises; returns False on misconfiguration or network errors.
    """
    if str(os.getenv("OMINI_SUPABASE_TOOL_EVENTS_DISABLE", "")).strip().lower() in ("1", "true", "yes"):
        return False
    base = str(os.getenv("SUPABASE_URL", "") or "").strip().rstrip("/")
    key = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or "").strip()
    if not base or not key:
        return False
    if not base.startswith("https://"):
        return False
    upper = base.upper()
    if "YOUR_" in key.upper() or "YOUR_" in upper or "<<PASTE" in key.upper():
        return False

    tn = _truncate(tool_name, 256) or "none"
    row = {
        "session_id": _truncate(session_id, 512),
        "task_id": _truncate(task_id, 256),
        "run_id": _truncate(run_id, 256),
        "tool_name": tn,
        "success": bool(success),
        "error_code": _truncate(error_code, 128) if error_code else None,
        "latency_ms": int(latency_ms) if latency_ms is not None else None,
        "provider": _truncate(provider, 64) if provider else None,
        "metadata": _sanitize_metadata(metadata),
    }
    payload = json.dumps([row], ensure_ascii=False).encode("utf-8")
    url = f"{base}/rest/v1/runtime_tool_events"
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "return=minimal",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            return 200 <= int(code) < 300
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        return False
