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
from config.provider_registry import describe_provider_diagnostics, get_available_providers

USER_FALLBACK_RESPONSE = (
    "[degraded:python_main] O adaptador Python não pôde concluir o turno. "
    "Verifique dependências, variáveis de ambiente e logs do processo."
)
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

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
LOGGER = logging.getLogger(__name__)


def _load_project_dotenv(project_root: Path) -> None:
    """Load repo-root ``.env`` into the process with ``setdefault`` (real env wins). Never logged."""
    if str(os.getenv("CI", "")).strip().lower() in ("1", "true", "yes"):
        return
    path = project_root / ".env"
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, val = stripped.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, val)


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
            return {
                "response": USER_FALLBACK_RESPONSE,
                "error": {
                    "failure_class": "FRONTEND_RESPONSE_SHAPE_MISMATCH",
                    "message": "Python main received an empty string response.",
                },
            }
        if is_operational_message(trimmed):
            LOGGER.debug("python_sanitizer_blocked_operational: %r", trimmed)
            return {
                "response": USER_FALLBACK_RESPONSE,
                "error": {
                    "failure_class": "FRONTEND_RESPONSE_SHAPE_MISMATCH",
                    "message": "Python main blocked an operational/control-layer message from public response.",
                },
            }
        parsed = _parse_structured_string(trimmed)
        if parsed is not None:
            return sanitize_for_user(parsed)
        out: dict[str, Any] = {"response": trimmed}
        return out

    if internal_obj is None or isinstance(internal_obj, list):
        return {
            "response": USER_FALLBACK_RESPONSE,
            "error": {
                "failure_class": "FRONTEND_RESPONSE_SHAPE_MISMATCH",
                "message": "Python main received an unsupported public response shape.",
            },
        }

    if isinstance(internal_obj, dict):
        error_payload = internal_obj.get("error")
        error_out = error_payload if isinstance(error_payload, dict) else None
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
            if error_out:
                out["error"] = error_out
            return out
        if error_out:
            return {
                "response": USER_FALLBACK_RESPONSE,
                "error": error_out,
            }

    return {
        "response": USER_FALLBACK_RESPONSE,
        "error": {
            "failure_class": "FRONTEND_RESPONSE_SHAPE_MISMATCH",
            "message": "Python main could not normalize the internal response into the public shape.",
        },
    }


def build_public_error(
    *,
    failure_class: str,
    message: str,
    debug_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "failure_class": str(failure_class or "PYTHON_BRIDGE_INVALID_JSON"),
        "message": str(message or USER_FALLBACK_RESPONSE),
    }
    if str(os.getenv("OMINI_PUBLIC_DEBUG", "")).strip().lower() in ("1", "true", "yes"):
        if isinstance(debug_details, dict) and debug_details:
            error["debug"] = debug_details
    return error


def emit_public_json(payload: dict[str, Any]) -> int:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()
    return 0


def main() -> int:
    python_root = Path(__file__).resolve().parent
    project_root = python_root.parents[1]
    os.environ.setdefault("PYTHON_BASE_DIR", str(python_root))
    os.environ.setdefault("BASE_DIR", str(project_root))
    _load_project_dotenv(project_root)

    message, bridge = resolve_entry_message()
    apply_bridge_env(bridge)
    orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(Path(__file__)))
    raw_response = orchestrator.run(message, bridge=bridge)
    LOGGER.debug("python_main_pre_sanitize=%r", raw_response)
    safe_response = sanitize_for_user(raw_response)
    if not str(safe_response.get("response", "")).strip():
        safe_response["response"] = USER_FALLBACK_RESPONSE
        safe_response["error"] = build_public_error(
            failure_class="FRONTEND_RESPONSE_SHAPE_MISMATCH",
            message="Python main produced an empty public response after sanitization.",
        )
    safe_response.setdefault("stop_reason", "python_completed")
    inspection = getattr(orchestrator, "last_cognitive_runtime_inspection", None)
    if isinstance(inspection, dict):
        safe_response["cognitive_runtime_inspection"] = inspection
    signals = inspection.get("signals") if isinstance(inspection, dict) else None
    if isinstance(signals, dict):
        if "provider_diagnostics" in signals:
            safe_response["provider_diagnostics"] = signals.get("provider_diagnostics")
        if "provider_actual" in signals:
            safe_response["provider_actual"] = signals.get("provider_actual")
        if "provider_failed" in signals:
            safe_response["provider_failed"] = signals.get("provider_failed")
        if "failure_class" in signals:
            safe_response["failure_class"] = signals.get("failure_class")
    if not isinstance(safe_response.get("provider_diagnostics"), list):
        safe_response["provider_diagnostics"] = describe_provider_diagnostics(
            actual_provider=str(safe_response.get("provider_actual", "") or ""),
            attempted_provider=str(safe_response.get("provider_actual", "") or ""),
            failure_class=str(safe_response.get("failure_class", "") or ""),
            include_embedded_local=True,
        )
    safe_response.setdefault(
        "provider_diagnostics",
        describe_provider_diagnostics(
            actual_provider=str(safe_response.get("provider_actual", "") or ""),
            attempted_provider=str(safe_response.get("provider_actual", "") or ""),
            failure_class=str(safe_response.get("failure_class", "") or ""),
            include_embedded_local=True,
        ),
    )
    # JSON-only stdout for Rust bridge — never print() diagnostics here.
    safe_response["providers"] = get_available_providers()
    return emit_public_json(safe_response)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        logging.exception("Unhandled exception in main execution path")
        try:
            emit_public_json(
                {
                    "response": USER_FALLBACK_RESPONSE,
                    "stop_reason": "python_main_exception",
                    "error": build_public_error(
                        failure_class="PYTHON_BRIDGE_NONZERO_EXIT",
                        message="Python main raised an unhandled exception before completing the public response.",
                    ),
                    "cognitive_runtime_inspection": {
                        "runtime_mode": "SAFE_FALLBACK",
                        "runtime_reason": "PYTHON_BRIDGE_NONZERO_EXIT",
                        "execution_tier": "technical_fallback",
                        "layer": "python_main",
                        "reason": "unhandled_exception",
                        "signals": {
                            "failure_class": "PYTHON_BRIDGE_NONZERO_EXIT",
                            "fallback_triggered": True,
                            "execution_path_used": "python_main",
                            "compatibility_execution_active": False,
                            "provider_actual": "",
                            "provider_failed": False,
                            "execution_provenance": None,
                            "provider_diagnostics": describe_provider_diagnostics(include_embedded_local=True),
                        },
                    },
                    "provider_diagnostics": describe_provider_diagnostics(include_embedded_local=True),
                    "providers": get_available_providers(),
                }
            )
        except Exception:
            pass
        sys.exit(1)
