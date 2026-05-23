from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.error_taxonomy import OmniErrorCode, build_public_error  # noqa: E402
from brain.runtime.learning.redaction import redact_sensitive_text  # noqa: E402
from brain.runtime.observability.public_runtime_payload import sanitize_public_runtime_payload  # noqa: E402


def test_env_example_uses_placeholders_only() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "SUPABASE_URL=<SUPABASE_URL>" in env_example
    assert "SUPABASE_ANON_KEY=<SUPABASE_ANON_KEY>" in env_example
    assert "OMNI_OPENAI_API_KEY=<OPENAI_API_KEY>" in env_example
    assert "OMINI_OPENAI_API_KEY=<OPENAI_API_KEY_LEGACY_ALIAS>" in env_example
    for forbidden in ("sk-", "sk-proj-", "Bearer ", "ghp_", "xoxb-", "eyJ"):
        assert forbidden not in env_example


def test_supabase_not_configured_public_error_is_safe() -> None:
    error = build_public_error(OmniErrorCode.SUPABASE_NOT_CONFIGURED)

    assert error["error_public_code"] == "SUPABASE_NOT_CONFIGURED"
    assert error["internal_error_redacted"] is True
    assert "SUPABASE_URL=" not in str(error)
    assert "SUPABASE_ANON_KEY=" not in str(error)


def test_public_payload_sanitizer_removes_secret_config_keys() -> None:
    payload = {
        "runtime_mode": "SAFE_FALLBACK",
        "api_key": "sk-proj-abcdefghijklmnop",
        "token": "secret-token",
        "secret": "hidden",
        "env": {"SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature"},
        "raw_key": "hidden",
        "raw_url": "https://project.supabase.co",
        "nested": {"safe": "kept"},
    }

    sanitized = sanitize_public_runtime_payload(payload)
    text = str(sanitized)

    assert sanitized["nested"]["safe"] == "kept"
    for forbidden in ("api_key", "token", "secret", "env", "raw_key", "raw_url", "sk-proj-", "eyJ", "supabase.co"):
        assert forbidden not in text


def test_learning_redaction_catches_provider_and_supabase_secrets() -> None:
    redacted = redact_sensitive_text(
        "provider sk-proj-abcdefghijklmnop supabase https://project.supabase.co "
        "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature"
    )

    assert "sk-proj-" not in redacted
    assert "supabase.co" not in redacted
    assert "eyJ" not in redacted
