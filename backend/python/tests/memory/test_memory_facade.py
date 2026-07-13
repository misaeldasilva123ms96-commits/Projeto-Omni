from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.memory_facade import MemoryFacade
from brain.memory.memory_models import (
    MEMORY_BACKEND_JSONL,
    ConversationRecord,
    EpisodeRecord,
    GovernanceEventRecord,
    LearningArtifactRecord,
    MessageRecord,
    ProviderAttemptRecord,
    RuntimeEventRecord,
    SemanticFactRecord,
    redact_payload,
    utc_now_iso,
)


class MemoryFacadeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-mem-test-"))
        self._audit_path = self._tmp / "test-audit.jsonl"
        self._sqlite_path = self._tmp / "test-memory.sqlite"

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ----------------------------------------------------------------
    # Default safe backend
    # ----------------------------------------------------------------
    def test_default_backend_is_jsonl(self) -> None:
        facade = MemoryFacade()
        self.assertEqual(facade.backend, MEMORY_BACKEND_JSONL)

    def test_facade_initializes_with_default_safe_backend(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path)
        facade.initialize()
        self.assertEqual(facade.backend, MEMORY_BACKEND_JSONL)
        self.assertFalse(facade.sqlite_enabled)
        self.assertFalse(facade.is_sqlite_connected)

    # ----------------------------------------------------------------
    # SQLite disabled by default
    # ----------------------------------------------------------------
    def test_sqlite_disabled_by_default(self) -> None:
        facade = MemoryFacade(
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()
        self.assertFalse(facade.sqlite_enabled)
        self.assertFalse(facade.is_sqlite_connected)
        self.assertIsNone(facade.init_error)

    def test_sqlite_disabled_when_configured_false(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=False,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()
        self.assertFalse(facade.is_sqlite_connected)

    def test_sqlite_backend_requested_but_disabled_reports_error(self) -> None:
        facade = MemoryFacade(
            backend="sqlite",
            enable_sqlite=False,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()
        self.assertIsNotNone(facade.init_error)
        self.assertIn("SQLite backend requested but SQLite is not enabled", facade.init_error)

    # ----------------------------------------------------------------
    # SQLite enabled
    # ----------------------------------------------------------------
    def test_sqlite_enabled_creates_schema(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()
        self.assertTrue(facade.sqlite_enabled)
        self.assertTrue(facade.is_sqlite_connected)
        self.assertTrue(self._sqlite_path.exists())

    def test_post_init_sqlite_failure_is_observable_without_breaking_contract(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path)
        facade.initialize()
        failing = Mock()
        failing.insert_conversation.side_effect = RuntimeError("database unavailable")
        facade._sqlite = failing
        facade.record_conversation(ConversationRecord(conversation_id="c-fail", session_id="s-fail"))
        diagnostics = facade.operation_diagnostics
        self.assertTrue(diagnostics["degraded"])
        self.assertEqual(diagnostics["failure_count"], 1)
        self.assertEqual(diagnostics["last_failed_operation"], "record_conversation")
        self.assertEqual(len(facade.audit_records()), 1)

    def test_sqlite_with_env_var(self) -> None:
        custom_path = self._tmp / "env-memory.sqlite"
        os.environ["OMINI_ENABLE_SQLITE_MEMORY"] = "true"
        os.environ["OMINI_SQLITE_MEMORY_PATH"] = str(custom_path)
        try:
            facade = MemoryFacade(jsonl_path=self._audit_path)
            facade.initialize()
            self.assertTrue(facade.sqlite_enabled)
            self.assertTrue(facade.is_sqlite_connected)
            self.assertTrue(custom_path.exists())
        finally:
            os.environ.pop("OMINI_ENABLE_SQLITE_MEMORY", None)
            os.environ.pop("OMINI_SQLITE_MEMORY_PATH", None)

    # ----------------------------------------------------------------
    # JSONL fallback still works
    # ----------------------------------------------------------------
    def test_jsonl_fallback_works(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path)
        facade.initialize()

        conv = ConversationRecord(
            conversation_id="test-conv-1",
            session_id="sess-1",
            title="Test Conversation",
        )
        facade.record_conversation(conv)

        records = facade.audit_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["type"], "conversation")

    def test_jsonl_mirror_is_append_only(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path)
        facade.initialize()

        for i in range(3):
            ev = RuntimeEventRecord(
                event_id=f"ev-{i}",
                event_type="test",
                source="test",
                summary=f"event {i}",
            )
            facade.record_runtime_event(ev)

        self.assertEqual(len(facade.audit_records()), 3)

    # ----------------------------------------------------------------
    # Facade write/read runtime event
    # ----------------------------------------------------------------
    def test_write_read_runtime_event(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()

        ev = RuntimeEventRecord(
            event_id="test-ev-1",
            event_type="test_write",
            source="unit_test",
            session_id="sess-1",
            summary="test runtime event",
        )
        facade.record_runtime_event(ev)

        results = facade.query_runtime_events("sess-1")
        self.assertGreaterEqual(len(results), 1)
        found = [r for r in results if r.get("event_id") == "test-ev-1"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["event_type"], "test_write")

        audit = facade.audit_records()
        self.assertGreaterEqual(len(audit), 1)

    # ----------------------------------------------------------------
    # Sensitive fields redacted before write
    # ----------------------------------------------------------------
    def test_redact_payload_removes_sensitive_keys(self) -> None:
        payload = {
            "name": "test",
            "api_key": "dummy-api-key-value-for-test",
            "token": "dummy-secret-token-for-test",
            "metadata": {"password": "dummy-pwd-for-test", "normal": "ok"},
        }
        redacted = redact_payload(payload)
        self.assertEqual(redacted["name"], "test")
        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertEqual(redacted["token"], "[REDACTED]")
        self.assertEqual(redacted["metadata"]["password"], "[REDACTED]")
        self.assertEqual(redacted["metadata"]["normal"], "ok")

    def test_redact_payload_max_depth(self) -> None:
        deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "secret"}}}}}}}
        redacted = redact_payload(deep)
        self.assertEqual(
            redacted["a"]["b"]["c"]["d"]["e"]["f"],
            {"_redacted": "max_depth"},
        )

    def test_sensitive_fields_redacted_in_audit(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path)
        facade.initialize()

        attempt = ProviderAttemptRecord(
            attempt_id="attempt-1",
            provider="openai",
            model="gpt-4",
            status="success",
            metadata={"api_key": "dummy-api-key-for-test", "normal_field": "ok"},
        )
        facade.record_provider_attempt(attempt)

        records = facade.audit_records()
        self.assertGreaterEqual(len(records), 1)
        payload = records[0]["payload"]
        api_key = (
            payload.get("metadata", {}).get("api_key")
            or next(
                (r.get("api_key") for r in [payload] if "api_key" in r),
                None,
            )
        )
        if payload.get("metadata", {}).get("api_key") == "[REDACTED]":
            pass
        elif payload.get("metadata", {}).get("api_key") is None:
            pass
        else:
            self.fail("api_key was not redacted")

    # ----------------------------------------------------------------
    # SQLite init failure handled safely
    # ----------------------------------------------------------------
    def test_sqlite_init_failure_falls_back_gracefully(self) -> None:
        clash_file = self._tmp / "db_container"
        clash_file.write_text("", encoding="utf-8")
        facade = MemoryFacade(
            enable_sqlite=True,
            sqlite_path=clash_file / "nested" / "db.sqlite",
            jsonl_path=self._audit_path,
        )
        facade.initialize()
        self.assertIsNotNone(facade.init_error)
        self.assertFalse(facade.is_sqlite_connected)

        ev = RuntimeEventRecord(
            event_id="fallback-ev",
            event_type="fallback_test",
            source="test",
            summary="should still work",
        )
        facade.record_runtime_event(ev)
        records = facade.audit_records()
        self.assertGreaterEqual(len(records), 1)

    # ----------------------------------------------------------------
    # No secrets appear in logs/errors
    # ----------------------------------------------------------------
    def test_error_messages_do_not_contain_sensitive_paths(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            sqlite_path=self._sqlite_path,
            jsonl_path=self._audit_path,
        )
        facade.initialize()
        self.assertIsNone(facade.init_error)

        bad_facade = MemoryFacade(
            enable_sqlite=True,
            sqlite_path=Path("\\\\invalid\\\\path\\\\test.sqlite"),
            jsonl_path=self._audit_path,
        )
        bad_facade.initialize()
        if bad_facade.init_error is not None:
            self.assertNotIn("api_key", bad_facade.init_error.lower())
            self.assertNotIn("secret", bad_facade.init_error.lower())
            self.assertNotIn("token", bad_facade.init_error.lower())

    def test_no_credentials_in_logged_errors(self) -> None:
        facade = MemoryFacade(
            jsonl_path=self._audit_path,
        )
        try:
            facade.record_runtime_event(
                RuntimeEventRecord(
                    event_id="safe-test",
                    event_type="safe",
                    source="test",
                    metadata={"api_key": "should-not-log"},
                )
            )
        except Exception as exc:
            msg = str(exc).lower()
            self.assertNotIn("should-not-log", msg)
            self.assertNotIn("api_key", msg)

    # ----------------------------------------------------------------
    # Record all types
    # ----------------------------------------------------------------
    def test_record_all_types(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()

        facade.record_conversation(ConversationRecord(conversation_id="c1", session_id="s1"))
        facade.record_message(MessageRecord(message_id="m1", conversation_id="c1", role="user", content="hello"))
        facade.record_episode(EpisodeRecord(episode_id="e1", session_id="s1", event_type="test", outcome="success"))
        facade.record_semantic_fact(SemanticFactRecord(fact_id="f1", subject="test", predicate="is", object_value="ok"))
        facade.record_runtime_event(RuntimeEventRecord(event_id="r1", event_type="test", source="test"))
        facade.record_provider_attempt(ProviderAttemptRecord(attempt_id="p1", provider="openai", status="success"))
        facade.record_governance_event(GovernanceEventRecord(event_id="g1", event_type="approval", status="granted"))
        facade.record_learning_artifact(LearningArtifactRecord(artifact_id="l1", artifact_type="pattern", source="test"))

        audit = facade.audit_records()
        types = {r["type"] for r in audit}
        expected_types = {
            "conversation", "message", "episode", "semantic_fact",
            "runtime_event", "provider_attempt", "governance_event",
            "learning_artifact",
        }
        self.assertEqual(types, expected_types)

        if facade.is_sqlite_connected:
            self.assertGreater(facade._sqlite.table_count("conversations"), 0)

    # ----------------------------------------------------------------
    # Close / cleanup
    # ----------------------------------------------------------------
    def test_close_cleans_up(self) -> None:
        facade = MemoryFacade(
            enable_sqlite=True,
            jsonl_path=self._audit_path,
            sqlite_path=self._sqlite_path,
        )
        facade.initialize()
        self.assertTrue(facade.is_sqlite_connected)
        facade.close()
        self.assertFalse(facade.is_sqlite_connected)

    def test_close_can_be_called_twice(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path)
        facade.initialize()
        facade.close()
        facade.close()

    # ----------------------------------------------------------------
    # Empty state
    # ----------------------------------------------------------------
    def test_empty_audit_returns_empty_list(self) -> None:
        facade = MemoryFacade(jsonl_path=self._audit_path)
        facade.initialize()
        self.assertEqual(facade.audit_records(), [])


if __name__ == "__main__":
    unittest.main()
