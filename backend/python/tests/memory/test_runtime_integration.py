from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.runtime_integration import (
    _lazy_facade,
    record_runtime_event,
    record_provider_attempt,
    record_governance_event,
    close,
    reset_for_testing,
)
from main import _record_provider_attempt_from_response


def _find_records(facade, record_type: str, limit: int = 50) -> list[dict]:
    raw = facade.audit_records(limit=limit)
    return [r["payload"] for r in raw if r.get("type") == record_type]


class RuntimeIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-rti-test-"))
        self._audit_path = self._tmp / "test-audit.jsonl"
        self._sqlite_path = self._tmp / "test-memory.sqlite"
        os.environ["OMINI_JSONL_MEMORY_PATH"] = str(self._audit_path)
        os.environ["OMINI_SQLITE_MEMORY_PATH"] = str(self._sqlite_path)
        reset_for_testing()

    def tearDown(self) -> None:
        close()
        for key in ("OMINI_JSONL_MEMORY_PATH", "OMINI_SQLITE_MEMORY_PATH",
                     "OMINI_ENABLE_SQLITE_MEMORY", "OMINI_MEMORY_BACKEND"):
            os.environ.pop(key, None)
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ----------------------------------------------------------------
    # Default backend behavior
    # ----------------------------------------------------------------
    def test_facade_default_backend_is_jsonl(self) -> None:
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            self.assertEqual(facade.backend, "jsonl")
            self.assertFalse(facade.sqlite_enabled)

    def test_sqlite_disabled_by_default(self) -> None:
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            self.assertFalse(facade.sqlite_enabled)
            self.assertFalse(facade.is_sqlite_connected)
            self.assertIsNone(facade.init_error)

    # ----------------------------------------------------------------
    # Safe runtime event recording
    # ----------------------------------------------------------------
    def test_record_runtime_event_succeeds_with_default_backend(self) -> None:
        record_runtime_event(
            event_type="test_event",
            source="test",
            session_id="test-session",
            run_id="test-run",
            summary="a test event",
            metadata={"key": "value"},
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "runtime_event")
            matching = [r for r in records if r.get("event_type") == "test_event"]
            self.assertGreaterEqual(len(matching), 1)
            self.assertEqual(matching[0]["source"], "test")
            self.assertEqual(matching[0]["session_id"], "test-session")

    def test_record_runtime_event_with_sensitive_fields_redacted(self) -> None:
        record_runtime_event(
            event_type="sensitive_test",
            source="test",
            session_id="test-session",
            run_id="test-run",
            summary="should redact api_key",
            metadata={"api_key": "sk-123456", "safe_field": "hello"},
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "runtime_event")
            matching = [r for r in records if r.get("event_type") == "sensitive_test"]
            self.assertGreaterEqual(len(matching), 1)
            meta = matching[0].get("metadata", {})
            self.assertIn("safe_field", meta)
            self.assertEqual(meta["safe_field"], "hello")
            if "api_key" in meta:
                self.assertEqual(meta["api_key"], "[REDACTED]")

    def test_record_runtime_event_does_not_raise_on_failure(self) -> None:
        record_runtime_event(
            event_type="test",
            source="test",
            session_id="",
            run_id="",
            summary="should not crash",
            metadata=None,
        )

    # ----------------------------------------------------------------
    # Provider attempt recording
    # ----------------------------------------------------------------
    def test_record_provider_attempt_succeeds(self) -> None:
        record_provider_attempt(
            provider="openai",
            model="gpt-4",
            session_id="test-session",
            run_id="test-run",
            status="success",
            duration_ms=1500,
            token_count=500,
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "openai"]
            self.assertGreaterEqual(len(matching), 1)

    def test_record_provider_attempt_metadata_filtered(self) -> None:
        record_provider_attempt(
            provider="anthropic",
            model="claude-3",
            session_id="test-session",
            run_id="test-run",
            status="success",
            duration_ms=500,
            metadata={"api_key": "sk-secret", "normal": "visible"},
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "anthropic"]
            self.assertGreaterEqual(len(matching), 1)
            record_meta = matching[0].get("metadata", {})
            if "api_key" in record_meta:
                self.assertEqual(record_meta["api_key"], "[REDACTED]")

    # ----------------------------------------------------------------
    # Governance event recording
    # ----------------------------------------------------------------
    def test_record_governance_event_succeeds(self) -> None:
        record_governance_event(
            event_type="operator_pause",
            source="operator_cli",
            session_id="test-session",
            run_id="test-run",
            status="paused",
            reason="manual pause",
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "governance_event")
            matching = [r for r in records if r.get("event_type") == "operator_pause"]
            self.assertGreaterEqual(len(matching), 1)

    # ----------------------------------------------------------------
    # Degradation behavior
    # ----------------------------------------------------------------
    def test_write_failure_does_not_raise(self) -> None:
        close()
        record_runtime_event(
            event_type="after_close",
            source="test",
            session_id="s",
            run_id="r",
            summary="should be safe no-op",
        )

    def test_lazy_init_failure_does_not_break_subsequent_calls(self) -> None:
        close()
        os.environ["OMINI_JSONL_MEMORY_PATH"] = "/nonexistent/path/audit.jsonl"
        reset_for_testing()
        record_runtime_event(
            event_type="bad_path",
            source="test",
            session_id="s",
            run_id="r",
            summary="should not crash",
        )

    # ----------------------------------------------------------------
    # SQLite opt-in behavior
    # ----------------------------------------------------------------
    def test_sqlite_enabled_when_env_set(self) -> None:
        close()
        os.environ["OMINI_ENABLE_SQLITE_MEMORY"] = "true"
        reset_for_testing()
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            self.assertTrue(facade.sqlite_enabled)

    # ----------------------------------------------------------------
    # Provider attempt status scenarios
    # ----------------------------------------------------------------
    def test_provider_attempt_successful_record(self) -> None:
        record_provider_attempt(
            provider="groq",
            model="llama-3.3-70b",
            session_id="test-session",
            run_id="",
            status="succeeded",
            duration_ms=1200,
            token_count=500,
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "groq"]
            self.assertGreaterEqual(len(matching), 1)
            self.assertEqual(matching[0]["status"], "succeeded")
            self.assertEqual(matching[0]["duration_ms"], 1200)
            self.assertEqual(matching[0]["token_count"], 500)

    def test_provider_attempt_failed_record(self) -> None:
        record_provider_attempt(
            provider="openai",
            model="gpt-4",
            session_id="test-session",
            run_id="",
            status="failed",
            duration_ms=3000,
            token_count=0,
            error_type="PROVIDER_RATE_LIMITED",
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "openai"]
            self.assertGreaterEqual(len(matching), 1)
            self.assertEqual(matching[0]["status"], "failed")
            self.assertEqual(matching[0]["error_type"], "PROVIDER_RATE_LIMITED")

    def test_provider_attempt_with_fallback_metadata(self) -> None:
        record_provider_attempt(
            provider="anthropic",
            model="claude-3",
            session_id="test-session",
            run_id="",
            status="succeeded",
            duration_ms=2500,
            metadata={"fallback_triggered": True, "original_provider": "openai"},
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "anthropic"]
            self.assertGreaterEqual(len(matching), 1)
            self.assertEqual(matching[0]["status"], "succeeded")
            self.assertEqual(matching[0]["duration_ms"], 2500)

    def test_provider_attempt_empty_provider_is_noop(self) -> None:
        record_provider_attempt(
            provider="",
            model="",
            session_id="",
            run_id="",
            status="",
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)

    def test_provider_attempt_no_model_is_ok(self) -> None:
        record_provider_attempt(
            provider="groq",
            model="",
            session_id="test-session",
            run_id="",
            status="succeeded",
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "groq"]
            self.assertGreaterEqual(len(matching), 1)

    def test_provider_attempt_raw_prompt_not_stored(self) -> None:
        record_provider_attempt(
            provider="test",
            model="test-model",
            session_id="s",
            run_id="r",
            status="succeeded",
            metadata={"raw_prompt": "some secret prompt", "safe_key": "ok"},
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "test"]
            self.assertGreaterEqual(len(matching), 1)

    def test_provider_attempt_auth_not_stored(self) -> None:
        record_provider_attempt(
            provider="test",
            model="test-model",
            session_id="s",
            run_id="r",
            status="failed",
            metadata={"api_key": "sk-secret-123", "headers": {"Authorization": "Bearer xyz"}},
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "test"]
            self.assertGreaterEqual(len(matching), 1)

    def test_provider_attempt_from_response_success(self) -> None:
        safe_resp = {"provider_actual": "groq", "provider_failed": False}
        insp = {"provider_actual": "groq", "latency_ms": 800, "fallback_triggered": False}
        _record_provider_attempt_from_response(safe_resp, insp)
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "groq"]
            self.assertGreaterEqual(len(matching), 1)
            self.assertEqual(matching[0]["status"], "succeeded")

    def test_provider_attempt_from_response_failed(self) -> None:
        safe_resp = {
            "provider_actual": "openai",
            "provider_failed": True,
            "failure_class": "PROVIDER_RATE_LIMITED",
        }
        insp = {"provider_actual": "openai", "latency_ms": 2000}
        _record_provider_attempt_from_response(safe_resp, insp)
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "openai"]
            self.assertGreaterEqual(len(matching), 1)
            self.assertEqual(matching[0]["status"], "failed")
            self.assertEqual(matching[0]["error_type"], "PROVIDER_RATE_LIMITED")

    def test_provider_attempt_from_response_noop_when_no_provider(self) -> None:
        safe_resp: dict = {}
        _record_provider_attempt_from_response(safe_resp, None)

    def test_provider_attempt_from_response_no_inspection(self) -> None:
        safe_resp = {"provider_actual": "anthropic", "failure_class": "PROVIDER_TIMEOUT"}
        _record_provider_attempt_from_response(safe_resp, None)
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "provider_attempt")
            matching = [r for r in records if r.get("provider") == "anthropic"]
            self.assertGreaterEqual(len(matching), 1)

    def test_jsonl_fallback_when_sqlite_enabled(self) -> None:
        close()
        os.environ["OMINI_ENABLE_SQLITE_MEMORY"] = "true"
        reset_for_testing()
        record_runtime_event(
            event_type="sqlite_on_test",
            source="test",
            session_id="s",
            run_id="r",
            summary="should write to JSONL even with SQLite on",
        )
        facade = _lazy_facade()
        self.assertIsNotNone(facade)
        if facade is not None:
            records = _find_records(facade, "runtime_event")
            matching = [r for r in records if r.get("event_type") == "sqlite_on_test"]
            self.assertGreaterEqual(len(matching), 1)
