from __future__ import annotations

import json
import logging
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from brain.runtime.error_taxonomy import OmniErrorCode, build_public_error
from brain.runtime.observability.public_runtime_payload import sanitize_public_runtime_payload
from main import build_public_chat_payload

LOGGER = logging.getLogger(__name__)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7010
MAX_SERVICE_BODY_BYTES = 65_536


def _env_value(primary: str, legacy: str, default: str) -> str:
    primary_value = str(os.getenv(primary, "") or "").strip()
    if primary_value:
        return primary_value
    legacy_value = str(os.getenv(legacy, "") or "").strip()
    if legacy_value:
        return legacy_value
    return default


def get_service_config() -> dict[str, Any]:
    port_raw = _env_value("OMNI_PYTHON_SERVICE_PORT", "OMINI_PYTHON_SERVICE_PORT", str(DEFAULT_PORT))
    try:
        port = int(port_raw)
    except ValueError:
        port = DEFAULT_PORT
    return {
        "host": _env_value("OMNI_PYTHON_SERVICE_HOST", "OMINI_PYTHON_SERVICE_HOST", DEFAULT_HOST),
        "port": max(1, min(65535, port)),
    }


def health_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "python-brain",
        "mode": "service",
    }


def readiness_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "python-brain",
        "checks": {
            "orchestrator_importable": True,
            "public_payload_sanitizer": True,
            "stdin_subprocess_entrypoint_preserved": True,
        },
    }


def build_service_error(code: OmniErrorCode, *, status: int, reason: str) -> tuple[int, dict[str, Any]]:
    error = build_public_error(code)
    payload = {
        "ok": False,
        "service": "python-brain",
        "response": "",
        "error": error,
        **error,
        "cognitive_runtime_inspection": {
            "runtime_mode": "SAFE_FALLBACK",
            "runtime_reason": str(code.value),
            "fallback_triggered": True,
            "error_public_code": error["error_public_code"],
            "error_public_message": error["error_public_message"],
            "severity": error["severity"],
            "retryable": error["retryable"],
            "internal_error_redacted": True,
            "public_summary": "System operated in safe fallback mode due to runtime constraints.",
        },
        "failure_class": str(code.value),
        "reason": reason,
    }
    return status, sanitize_public_runtime_payload(payload)


def handle_run_payload(payload: Any) -> tuple[int, dict[str, Any]]:
    if not isinstance(payload, dict):
        return build_service_error(
            OmniErrorCode.INPUT_VALIDATION_FAILED,
            status=HTTPStatus.BAD_REQUEST,
            reason="request_body_must_be_object",
        )

    message = str(payload.get("message", "") or "").strip()
    if not message:
        return build_service_error(
            OmniErrorCode.INPUT_VALIDATION_FAILED,
            status=HTTPStatus.BAD_REQUEST,
            reason="message_required",
        )

    bridge = {
        "session": {},
        "client_context": {},
    }
    if isinstance(payload.get("metadata"), dict):
        bridge["client_context"] = dict(payload.get("metadata") or {})
    if isinstance(payload.get("session_id"), str):
        bridge["session"]["client_session_id"] = str(payload.get("session_id") or "")
    if isinstance(payload.get("request_id"), str):
        bridge["request_id"] = str(payload.get("request_id") or "")

    try:
        result = build_public_chat_payload(message, bridge)
    except Exception:
        LOGGER.error("python_brain_service_run_failed")
        return build_service_error(
            OmniErrorCode.PYTHON_ORCHESTRATOR_FAILED,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            reason="orchestrator_failed",
        )

    safe = sanitize_public_runtime_payload(result)
    safe.setdefault("service", "python-brain")
    safe.setdefault("mode", "service")
    return HTTPStatus.OK, safe


class BrainServiceHandler(BaseHTTPRequestHandler):
    server_version = "OmniPythonBrain/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/internal/brain/health":
            self._write_json(HTTPStatus.OK, health_payload())
            return
        if self.path == "/internal/brain/readiness":
            self._write_json(HTTPStatus.OK, readiness_payload())
            return
        self._write_json(*build_service_error(OmniErrorCode.INPUT_VALIDATION_FAILED, status=HTTPStatus.NOT_FOUND, reason="not_found"))

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/internal/brain/run":
            self._write_json(*build_service_error(OmniErrorCode.INPUT_VALIDATION_FAILED, status=HTTPStatus.NOT_FOUND, reason="not_found"))
            return

        content_type = str(self.headers.get("content-type", "") or "").lower()
        if "application/json" not in content_type:
            self._write_json(*build_service_error(OmniErrorCode.INVALID_CONTENT_TYPE, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE, reason="invalid_content_type"))
            return

        try:
            length = int(self.headers.get("content-length", "0") or "0")
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_SERVICE_BODY_BYTES:
            self._write_json(*build_service_error(OmniErrorCode.PAYLOAD_TOO_LARGE, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE, reason="invalid_body_size"))
            return

        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._write_json(*build_service_error(OmniErrorCode.INVALID_JSON, status=HTTPStatus.BAD_REQUEST, reason="invalid_json"))
            return
        self._write_json(*handle_run_payload(payload))

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.debug("python_brain_service_http_event")

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(sanitize_public_runtime_payload(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(int(status))
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(host: str | None = None, port: int | None = None) -> ThreadingHTTPServer:
    config = get_service_config()
    return ThreadingHTTPServer((host or config["host"], int(port or config["port"])), BrainServiceHandler)


def main() -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    config = get_service_config()
    server = create_server(config["host"], config["port"])
    LOGGER.info("python brain service listening on %s:%s", config["host"], config["port"])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
