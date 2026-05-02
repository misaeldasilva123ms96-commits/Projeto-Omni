from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.observability.public_runtime_payload import (  # noqa: E402
    build_public_cognitive_runtime_inspection,
    sanitize_public_runtime_payload,
)


def _contains_key_fragment(value: Any, fragment: str) -> bool:
    if isinstance(value, dict):
        return any(fragment in str(key).lower() or _contains_key_fragment(item, fragment) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_key_fragment(item, fragment) for item in value)
    return False


def _serialized(value: Any) -> str:
    return repr(value)


def test_public_runtime_payload_removes_internal_fields_recursively() -> None:
    payload = {
        "response": "ok",
        "stack": "Error stack",
        "traceback": "Traceback here",
        "stdout": "raw stdout",
        "stderr": "raw stderr",
        "command": "node runner",
        "args": ["--secret"],
        "env": {"OPENAI_API_KEY": "sk-proj-abcdefghijklmnop"},
        "api_key": "sk-proj-abcdefghijklmnop",
        "token": "secret-token",
        "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
        "secret": "hidden",
        "password": "hidden",
        "authorization": "Bearer abcdefghijklmnopqrstuvwxyz",
        "provider_raw": {"body": "raw"},
        "raw_provider": {"body": "raw"},
        "raw_response": {"body": "raw"},
        "raw_payload": {"body": "raw"},
        "raw_key": "secret",
        "raw_url": "https://project.supabase.co",
        "execution_request": {"actions": [{"name": "danger"}]},
        "tool_raw_result": {"content": "raw tool"},
        "memory_raw": {"rows": ["raw memory"]},
        "memory_content": "private memory",
        "nested": {
            "stderr_detail": "nested raw stderr",
            "provider_raw_response": "nested provider raw",
            "safe": "kept",
        },
    }

    sanitized = sanitize_public_runtime_payload(payload)

    for fragment in (
        "stack",
        "trace",
        "stdout",
        "stderr",
        "command",
        "args",
        "env",
        "api_key",
        "token",
        "jwt",
        "secret",
        "password",
        "authorization",
        "provider_raw",
        "raw_provider",
        "raw_response",
        "raw_payload",
        "raw_key",
        "raw_url",
        "execution_request",
        "tool_raw_result",
        "memory_raw",
        "memory_content",
    ):
        assert not _contains_key_fragment(sanitized, fragment)
    assert sanitized["response"] == "ok"
    assert sanitized["nested"]["safe"] == "kept"


def test_public_runtime_payload_redacts_sensitive_values() -> None:
    payload = {
        "response": (
            "Paths /home/render/project/.env /root/secret /tmp/x /var/log/app /usr/bin/node /etc/passwd "
            "C:\\Users\\Misael\\secret.txt C:\\Windows\\System32\\config "
            "C:\\Program Files\\Omni\\secret.txt sk-proj-abcdefghijklmnop "
            "Bearer abcdefghijklmnopqrstuvwxyz "
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature "
            "https://project.supabase.co/private"
        )
    }

    text = _serialized(sanitize_public_runtime_payload(payload))

    assert "/home/render" not in text
    assert "/root/secret" not in text
    assert "/tmp/x" not in text
    assert "/var/log" not in text
    assert "/usr/bin" not in text
    assert "/etc/passwd" not in text
    assert "C:\\Users\\Misael" not in text
    assert "C:\\Windows" not in text
    assert "C:\\Program Files" not in text
    assert "sk-proj-" not in text
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in text
    assert "eyJhbGci" not in text
    assert "project.supabase.co" not in text


def test_public_cognitive_runtime_inspection_preserves_public_fields_and_summary() -> None:
    inspection = {
        "runtime_mode": "MATCHER_SHORTCUT",
        "runtime_reason": "local_pattern",
        "cognitive_chain": "PARTIAL",
        "source_of_truth": "Matcher",
        "final_verdict": "HYBRID_UNSTABLE",
        "cognitive_chain_steps": {"raw": "not public"},
        "signals": {
            "fallback_triggered": False,
            "provider_actual": "local-heuristic",
            "provider_failed": False,
            "tool_succeeded": True,
            "duration_ms": 42,
            "execution_request": {"actions": []},
            "node_outcome": {"raw_payload": "hidden"},
            "stderr": "raw stderr",
        },
    }

    public = build_public_cognitive_runtime_inspection(inspection)

    assert public["runtime_mode"] == "MATCHER_SHORTCUT"
    assert public["runtime_reason"] == "local_pattern"
    assert public["cognitive_chain"] == "PARTIAL"
    assert public["source_of_truth"] == "Matcher"
    assert public["final_verdict"] == "HYBRID_UNSTABLE"
    assert public["fallback_triggered"] is False
    assert public["provider_actual"] == "local-heuristic"
    assert public["provider_failed"] is False
    assert public["tool_status"] == "succeeded"
    assert public["latency_ms"] == 42
    assert public["public_summary"] == "Responded using a local pattern matcher. No AI provider was used."
    assert "signals" not in public
    assert "cognitive_chain_steps" not in public
    assert "execution_request" not in _serialized(public)
    assert "stderr" not in _serialized(public)


def test_public_cognitive_runtime_summary_modes() -> None:
    fallback = build_public_cognitive_runtime_inspection({"runtime_mode": "SAFE_FALLBACK"})
    full = build_public_cognitive_runtime_inspection({"runtime_mode": "FULL_COGNITIVE_RUNTIME"})
    unknown = build_public_cognitive_runtime_inspection({"runtime_mode": "DIRECT_LOCAL_RESPONSE"})

    assert fallback["public_summary"] == "System operated in safe fallback mode due to runtime constraints."
    assert full["public_summary"] == "Full cognitive execution with provider and tool verification."
    assert unknown["public_summary"] == "Execution completed in DIRECT_LOCAL_RESPONSE mode."


def test_public_runtime_payload_does_not_mutate_original_payload() -> None:
    original = {
        "response": "ok",
        "cognitive_runtime_inspection": {
            "runtime_mode": "SAFE_FALLBACK",
            "signals": {
                "fallback_triggered": True,
                "execution_request": {"actions": [{"name": "read_file"}]},
                "memory_content": "private",
            },
        },
    }
    before = copy.deepcopy(original)

    sanitized = sanitize_public_runtime_payload(original)

    assert original == before
    assert sanitized["cognitive_runtime_inspection"]["runtime_mode"] == "SAFE_FALLBACK"
    assert sanitized["cognitive_runtime_inspection"]["fallback_triggered"] is True
    assert "execution_request" not in _serialized(sanitized)
    assert "memory_content" not in _serialized(sanitized)
