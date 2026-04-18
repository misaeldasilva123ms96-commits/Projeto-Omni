from __future__ import annotations

import json
import logging
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any

from brain.runtime.bridge_stdin import apply_bridge_env, resolve_entry_message
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths

USER_FALLBACK_RESPONSE = "Entendido. Como posso ajudá-lo?"
RESPONSE_CANDIDATE_KEYS = ("response", "message", "text", "answer", "output", "result")
OPERATIONAL_MESSAGE_MARKERS = (
    "execucao bloqueada",
    "camada de controle",
    "mode transition",
    "control mode",
    "not allowed from current",
    "requested mode",
    "transition is not allowed",
    "execution blocked",
    "delegation failed",
    "execution_request",
    "plan_graph",
    "execution_tree",
    "source_map",
    "policy_summary",
    "runtimemode",
    "specialists",
)

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def _parse_structured_string(value: str) -> Any | None:
    trimmed = value.strip()
    if not trimmed:
        return None
    if not (
        (trimmed.startswith("{") and trimmed.endswith("}"))
        or (trimmed.startswith("[") and trimmed.endswith("]"))
    ):
        return None
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        return None


def _normalize_for_matching(value: str) -> str:
    """
    Lowercase + accent folding for marker comparison.
    Must use the module-level unicodedata import.
    """
    nfd = unicodedata.normalize("NFD", value)
    stripped = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return stripped.lower()


def is_operational_message(value: str) -> bool:
    """
    Returns True if the string contains markers that identify it
    as an internal control-layer or execution-envelope message.
    Matching is case-insensitive and accent-insensitive.

    Only blocks strings that clearly identify control-layer or
    execution-envelope messages. Does not over-block legitimate
    explanatory or technical user-facing text.
    """
    normalized = _normalize_for_matching(value)
    return any(marker in normalized for marker in OPERATIONAL_MESSAGE_MARKERS)


def _extract_truthful_conversation_id(d: dict) -> str | None:
    """Return a single canonical id string when the orchestrator supplied one; never invent."""
    for key in ("server_conversation_id", "conversation_id"):
        v = d.get(key)
        if not isinstance(v, str):
            continue
        s = v.strip()
        if not s or len(s) > 256:
            continue
        if "\n" in s or "\r" in s:
            continue
        if is_operational_message(s):
            continue
        return s
    return None


def sanitize_for_user(internal_obj: Any) -> dict[str, Any]:
    if isinstance(internal_obj, str):
        trimmed = internal_obj.strip()
        if not trimmed:
            return {"response": USER_FALLBACK_RESPONSE}
        if is_operational_message(trimmed):
            LOGGER.debug("python_sanitizer_blocked_operational: %r", trimmed)
            return {"response": USER_FALLBACK_RESPONSE}
        parsed = _parse_structured_string(trimmed)
        if parsed is not None:
            return sanitize_for_user(parsed)
        out: dict[str, Any] = {"response": trimmed}
        return out

    if internal_obj is None or isinstance(internal_obj, list):
        return {"response": USER_FALLBACK_RESPONSE}

    if isinstance(internal_obj, dict):
        for key in RESPONSE_CANDIDATE_KEYS:
            value = internal_obj.get(key)
            if not isinstance(value, str):
                continue
            trimmed = value.strip()
            if not trimmed:
                continue
            if is_operational_message(trimmed):
                LOGGER.debug("python_sanitizer_blocked_operational: %r", trimmed)
                continue
            parsed = _parse_structured_string(trimmed)
            if parsed is not None:
                return sanitize_for_user(parsed)
            out: dict[str, Any] = {"response": trimmed}
            cid = _extract_truthful_conversation_id(internal_obj)
            if cid:
                out["conversation_id"] = cid
            return out

    return {"response": USER_FALLBACK_RESPONSE}


def main() -> int:
    python_root = Path(__file__).resolve().parent
    project_root = python_root.parents[1]
    os.environ.setdefault("PYTHON_BASE_DIR", str(python_root))
    os.environ.setdefault("BASE_DIR", str(project_root))

    message, bridge = resolve_entry_message()
    apply_bridge_env(bridge)
    orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(Path(__file__)))
    raw_response = orchestrator.run(message)
    LOGGER.debug("python_main_pre_sanitize=%r", raw_response)
    safe_response = sanitize_for_user(raw_response)
    inspection = getattr(orchestrator, "last_cognitive_runtime_inspection", None)
    if isinstance(inspection, dict):
        safe_response["cognitive_runtime_inspection"] = inspection
    print(json.dumps(safe_response, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        logging.exception("Unhandled exception in main execution path")
        try:
            print(json.dumps({"response": USER_FALLBACK_RESPONSE}, ensure_ascii=False), flush=True)
        except Exception:
            pass
        sys.exit(1)
