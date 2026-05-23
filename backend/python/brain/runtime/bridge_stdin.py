"""
Structured stdin JSON from the Rust `/chat` subprocess bridge.

When Rust spawns Python with a JSON body on stdin, this module parses it and
exposes correlation fields via environment variables for `BrainOrchestrator`.
If stdin is empty or not JSON, callers fall back to argv-only behaviour.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# Guard against accidental huge payloads on stdin.
_MAX_STDIN_BYTES = 512_000


def read_bridge_stdin_dict() -> dict[str, Any]:
    if sys.stdin is None:
        return {}
    try:
        if sys.stdin.isatty():
            return {}
        raw = sys.stdin.read(_MAX_STDIN_BYTES)
    except Exception:
        return {}
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def resolve_entry_message(bridge: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    """Prefer `message` from stdin JSON; otherwise first argv token (legacy)."""
    if bridge is None:
        bridge = read_bridge_stdin_dict()
    msg = bridge.get("message")
    if isinstance(msg, str) and msg.strip():
        return msg.strip(), bridge
    if len(sys.argv) > 1 and isinstance(sys.argv[1], str) and sys.argv[1].strip():
        return sys.argv[1].strip(), {}
    return "", bridge


def apply_bridge_env(bridge: dict[str, Any]) -> None:
    """
    Publish bridge fields for orchestrator correlation.

    `OMNI_BRIDGE_CLIENT_SESSION_ID` is optional and maps into `_session_id()` when
    `AI_SESSION_ID` is unset (see `docs/backend/python-bridge-contract.md`).
    """
    cid = bridge.get("client_session_id")
    if isinstance(cid, str) and cid.strip():
        os.environ["OMNI_BRIDGE_CLIENT_SESSION_ID"] = cid.strip()[:256]
    else:
        os.environ.pop("OMNI_BRIDGE_CLIENT_SESSION_ID", None)

    rsv = bridge.get("runtime_session_version")
    if isinstance(rsv, bool):
        rsv = None
    if isinstance(rsv, int) and rsv >= 0:
        os.environ["OMNI_BRIDGE_RUNTIME_SESSION_VERSION"] = str(rsv)
    elif isinstance(rsv, float) and rsv >= 0 and rsv == int(rsv):
        os.environ["OMNI_BRIDGE_RUNTIME_SESSION_VERSION"] = str(int(rsv))
    else:
        os.environ.pop("OMNI_BRIDGE_RUNTIME_SESSION_VERSION", None)

    rs = bridge.get("request_source")
    if isinstance(rs, str) and rs.strip():
        os.environ["OMNI_BRIDGE_REQUEST_SOURCE"] = rs.strip()[:128]
    else:
        os.environ.pop("OMNI_BRIDGE_REQUEST_SOURCE", None)
