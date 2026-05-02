from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = PROJECT_ROOT / "backend" / "python"
sys.path.insert(0, str(PYTHON_ROOT))

import brain_service  # noqa: E402


def _request(method: str, url: str, payload: dict | None = None, content_type: str = "application/json") -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("content-type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_service_config_defaults_to_loopback_and_aliases(monkeypatch) -> None:
    for key in (
        "OMNI_PYTHON_SERVICE_HOST",
        "OMINI_PYTHON_SERVICE_HOST",
        "OMNI_PYTHON_SERVICE_PORT",
        "OMINI_PYTHON_SERVICE_PORT",
    ):
        monkeypatch.delenv(key, raising=False)
    assert brain_service.get_service_config() == {"host": "127.0.0.1", "port": 7010}

    monkeypatch.setenv("OMINI_PYTHON_SERVICE_HOST", "127.0.0.2")
    monkeypatch.setenv("OMINI_PYTHON_SERVICE_PORT", "7011")
    assert brain_service.get_service_config() == {"host": "127.0.0.2", "port": 7011}

    monkeypatch.setenv("OMNI_PYTHON_SERVICE_HOST", "127.0.0.3")
    monkeypatch.setenv("OMNI_PYTHON_SERVICE_PORT", "7012")
    assert brain_service.get_service_config() == {"host": "127.0.0.3", "port": 7012}


def test_health_and_readiness_payloads_are_public_safe() -> None:
    assert brain_service.health_payload() == {"ok": True, "service": "python-brain", "mode": "service"}
    readiness = brain_service.readiness_payload()
    assert readiness["ok"] is True
    assert readiness["service"] == "python-brain"
    assert readiness["checks"]["orchestrator_importable"] is True
    assert "env" not in json.dumps(readiness).lower()


def test_service_run_returns_sanitized_public_envelope_and_runtime_truth() -> None:
    raw = {
        "response": "ok",
        "runtime_mode": "FULL_COGNITIVE_RUNTIME",
        "error_public_code": "",
        "cognitive_runtime_inspection": {
            "runtime_mode": "FULL_COGNITIVE_RUNTIME",
            "runtime_truth": {"runtime_mode": "FULL_COGNITIVE_RUNTIME"},
            "signals": {
                "provider_actual": "openai",
                "stack": "secret stack",
                "env": {"TOKEN": "secret"},
            },
        },
        "raw_payload": {"token": "secret"},
    }
    with patch.object(brain_service, "build_public_chat_payload", return_value=raw):
        status, payload = brain_service.handle_run_payload(
            {"message": "ola", "session_id": "sess-1", "request_id": "req-1", "metadata": {"safe": True}}
        )

    serialized = json.dumps(payload, ensure_ascii=False)
    assert status == 200
    assert payload["response"] == "ok"
    assert payload["runtime_mode"] == "FULL_COGNITIVE_RUNTIME"
    assert payload["cognitive_runtime_inspection"]["runtime_mode"] == "FULL_COGNITIVE_RUNTIME"
    assert "secret stack" not in serialized
    assert "TOKEN" not in serialized
    assert "raw_payload" not in serialized


def test_service_run_error_and_malformed_request_use_taxonomy_shape() -> None:
    status, payload = brain_service.handle_run_payload({"message": ""})
    assert status == 400
    assert payload["error_public_code"] == "INPUT_VALIDATION_FAILED"
    assert payload["internal_error_redacted"] is True

    with patch.object(brain_service, "build_public_chat_payload", side_effect=RuntimeError("C:\\Users\\secret token=abc")):
        status, payload = brain_service.handle_run_payload({"message": "ola"})

    serialized = json.dumps(payload, ensure_ascii=False)
    assert status == 500
    assert payload["error_public_code"] == "PYTHON_ORCHESTRATOR_FAILED"
    assert payload["error_public_message"]
    assert payload["internal_error_redacted"] is True
    assert "C:\\Users" not in serialized
    assert "token=abc" not in serialized
    assert "RuntimeError" not in serialized


def test_http_endpoints_work_without_public_exposure_or_cors() -> None:
    server = brain_service.create_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, health = _request("GET", f"{base_url}/internal/brain/health")
        assert status == 200
        assert health["service"] == "python-brain"

        status, readiness = _request("GET", f"{base_url}/internal/brain/readiness")
        assert status == 200
        assert readiness["checks"]["public_payload_sanitizer"] is True

        status, bad = _request("POST", f"{base_url}/internal/brain/run", {"message": "ola"}, content_type="text/plain")
        assert status == 415
        assert bad["error_public_code"] == "INVALID_CONTENT_TYPE"
    finally:
        server.shutdown()
        server.server_close()


def test_stdin_main_path_still_emits_json() -> None:
    snippet = f"""
import json, sys
sys.path.insert(0, {str(PYTHON_ROOT)!r})
import main

class FakeOrchestrator:
    def __init__(self, paths):
        self.last_cognitive_runtime_inspection = {{
            "runtime_mode": "FULL_COGNITIVE_RUNTIME",
            "signals": {{"fallback_triggered": False}},
        }}
    def run(self, message, bridge=None):
        return {{"response": "ok", "server_conversation_id": "conv-1"}}

main.BrainOrchestrator = FakeOrchestrator
raise SystemExit(main.main())
"""
    proc = subprocess.run(
        [sys.executable, "-c", snippet],
        input=json.dumps({"message": "ola"}),
        text=True,
        capture_output=True,
        timeout=30,
        cwd=str(PROJECT_ROOT),
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert isinstance(payload.get("response"), str)
    assert "cognitive_runtime_inspection" in payload
    assert "traceback" not in proc.stdout.lower()
