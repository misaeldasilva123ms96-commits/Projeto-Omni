from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.learning.learning_store import ControlledLearningStore  # noqa: E402
from brain.runtime.learning.redaction import (  # noqa: E402
    REDACTED_INTERNAL_PAYLOAD,
    redact_learning_record,
    redact_sensitive_payload,
    redact_sensitive_text,
)


def test_redact_sensitive_text_covers_required_pii_and_secret_patterns() -> None:
    raw = (
        "email user@example.com phone +55 11 99999-9999 cpf 123.456.789-09 "
        "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature "
        "openai sk-proj-abcdefghijklmnop anthropic sk-ant-abcdefghijkl groq sk-groq-abcdefghijkl "
        "generic sk-abcdefghijkl Bearer abcdefghijklmnopqrstuvwxyz "
        "password=hunter2 token=abc secret=hidden api_key=value "
        "url https://demo-project.supabase.co/rest/v1/table "
        "unix /home/render/project/.env /root/secret /tmp/x /var/log/app /usr/bin/node /etc/passwd "
        "win C:\\Users\\Misael\\secret.txt C:\\Windows\\System32\\config C:\\Program Files\\Omni\\secret.txt"
    )

    redacted = redact_sensitive_text(raw)

    assert "user@example.com" not in redacted
    assert "+55 11 99999-9999" not in redacted
    assert "123.456.789-09" not in redacted
    assert "eyJhbGci" not in redacted
    assert "sk-proj-" not in redacted
    assert "sk-ant-" not in redacted
    assert "sk-groq-" not in redacted
    assert "sk-abcdefghijkl" not in redacted
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "hunter2" not in redacted
    assert "token=abc" not in redacted
    assert "secret=hidden" not in redacted
    assert "api_key=value" not in redacted
    assert "supabase.co" not in redacted
    assert "/home/render" not in redacted
    assert "/root/secret" not in redacted
    assert "/tmp/x" not in redacted
    assert "/var/log" not in redacted
    assert "/usr/bin" not in redacted
    assert "/etc/passwd" not in redacted
    assert "C:\\Users\\Misael" not in redacted
    assert "C:\\Windows" not in redacted
    assert "C:\\Program Files" not in redacted

    for placeholder in (
        "[REDACTED_EMAIL]",
        "[REDACTED_PHONE]",
        "[REDACTED_CPF]",
        "[REDACTED_JWT]",
        "[REDACTED_API_KEY]",
        "Bearer [REDACTED_TOKEN]",
        "[REDACTED_SECRET]",
        "[REDACTED_SUPABASE_URL]",
        "[REDACTED_PATH]",
    ):
        assert placeholder in redacted


def test_redact_sensitive_payload_recurses_and_preserves_safe_metadata() -> None:
    original = {
        "record_id": "clr-1",
        "runtime_mode": "FULL_COGNITIVE_RUNTIME",
        "success": True,
        "metadata": {
            "decision_reason_codes": ["explicit_file_read"],
            "notes": ["safe", "user@example.com", {"path": "/home/render/project/.env"}],
            "nested": {
                "stack": "raw stack",
                "traceback": "traceback",
                "stdout": "raw stdout",
                "stderr": "raw stderr",
                "command": "node runner",
                "args": ["--token"],
                "env": {"OPENAI_API_KEY": "sk-proj-abcdefghijklmnop"},
                "authorization": "Bearer abcdefghijklmnopqrstuvwxyz",
                "provider_raw": {"body": "raw"},
                "raw_provider": "raw",
                "raw_response": "raw",
                "raw_payload": "raw",
                "raw_key": "raw",
                "raw_url": "https://project.supabase.co/private",
                "execution_request": {"actions": []},
                "tool_raw_result": "raw tool",
                "memory_raw": "raw memory",
                "memory_content": "private memory",
            },
        },
    }
    before = copy.deepcopy(original)

    redacted = redact_sensitive_payload(original)
    text = json.dumps(redacted, ensure_ascii=False)

    assert original == before
    assert redacted["record_id"] == "clr-1"
    assert redacted["runtime_mode"] == "FULL_COGNITIVE_RUNTIME"
    assert redacted["metadata"]["decision_reason_codes"] == ["explicit_file_read"]
    assert "user@example.com" not in text
    assert "/home/render" not in text
    for key in (
        "stack",
        "traceback",
        "stdout",
        "stderr",
        "command",
        "args",
        "env",
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
        assert redacted["metadata"]["nested"][key] == REDACTED_INTERNAL_PAYLOAD


def test_redact_learning_record_is_alias_for_record_payloads() -> None:
    record = {
        "input_preview": "Misael user@example.com pediu arquivo C:\\Users\\Misael\\secret.txt",
        "metadata": {"tool_execution": {"tool_raw_result": "raw"}},
    }

    redacted = redact_learning_record(record)

    assert "[REDACTED_EMAIL]" in redacted["input_preview"]
    assert "[REDACTED_PATH]" in redacted["input_preview"]
    assert redacted["metadata"]["tool_execution"]["tool_raw_result"] == REDACTED_INTERNAL_PAYLOAD


def test_controlled_learning_store_redacts_before_persisting_jsonl() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = ControlledLearningStore(Path(tmp), max_records=10)
        store.append_learning_record(
            {
                "record_id": "clr-1",
                "input_preview": "user@example.com sk-proj-abcdefghijklmnop",
                "runtime_mode": "SAFE_FALLBACK",
                "metadata": {
                    "tool_execution": {
                        "tool_selected": "read_file",
                        "tool_raw_result": "raw",
                    },
                    "memory_content": "private",
                },
            }
        )

        raw_text = store.records_path.read_text(encoding="utf-8")
        loaded = store.read_recent_learning_records(limit=1)[0]

        assert "user@example.com" not in raw_text
        assert "sk-proj-" not in raw_text
        assert '"raw"' not in raw_text
        assert "private" not in raw_text
        assert loaded["input_preview"] == "[REDACTED_EMAIL] [REDACTED_API_KEY]"
        assert loaded["metadata"]["tool_execution"]["tool_raw_result"] == REDACTED_INTERNAL_PAYLOAD
        assert loaded["metadata"]["memory_content"] == REDACTED_INTERNAL_PAYLOAD


def test_non_object_and_non_sensitive_values_are_safe() -> None:
    assert redact_sensitive_payload(None) is None
    assert redact_sensitive_payload(123) == 123
    assert redact_sensitive_payload(["safe", "user@example.com"]) == ["safe", "[REDACTED_EMAIL]"]
