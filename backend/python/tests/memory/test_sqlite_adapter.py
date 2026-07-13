from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.sqlite_adapter import SQLiteAdapter
from brain.memory.memory_models import (
    ConversationRecord,
    EpisodeRecord,
    GovernanceEventRecord,
    LearningArtifactRecord,
    MessageRecord,
    ProviderAttemptRecord,
    RuntimeEventRecord,
    SemanticFactRecord,
)


class SQLiteAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="omni-sqlite-test-"))
        self._db_path = self._tmp / "test-omni-memory.sqlite"
        self.adapter = SQLiteAdapter(self._db_path)

    def tearDown(self) -> None:
        try:
            self.adapter.close()
        except Exception:
            pass
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ----------------------------------------------------------------
    # Connection
    # ----------------------------------------------------------------
    def test_can_connect_and_create_schema(self) -> None:
        self.assertFalse(self.adapter.is_connected)
        self.adapter.connect()
        self.assertTrue(self.adapter.is_connected)
        self.assertTrue(self._db_path.exists())

    def test_connect_idempotent(self) -> None:
        self.adapter.connect()
        self.adapter.connect()
        self.assertTrue(self.adapter.is_connected)

    def test_close_connection(self) -> None:
        self.adapter.connect()
        self.assertTrue(self.adapter.is_connected)
        self.adapter.close()
        self.assertFalse(self.adapter.is_connected)

    def test_close_idempotent(self) -> None:
        self.adapter.connect()
        self.adapter.close()
        self.adapter.close()

    # ----------------------------------------------------------------
    # Schema
    # ----------------------------------------------------------------
    def test_all_tables_created(self) -> None:
        self.adapter.connect()
        expected_tables = [
            "conversations",
            "messages",
            "episodes",
            "semantic_facts",
            "runtime_events",
            "provider_attempts",
            "governance_events",
            "learning_artifacts",
        ]
        for table in expected_tables:
            self.assertTrue(
                self.adapter.table_exists(table),
                f"Table {table} should exist",
            )

    # ----------------------------------------------------------------
    # Insert and count
    # ----------------------------------------------------------------
    def test_insert_conversation(self) -> None:
        self.adapter.connect()
        self.adapter.insert_conversation(
            ConversationRecord(
                conversation_id="conv-1",
                session_id="sess-1",
                title="Test Conversation",
            )
        )
        self.assertEqual(self.adapter.table_count("conversations"), 1)

    def test_insert_message(self) -> None:
        self.adapter.connect()
        self.adapter.insert_conversation(ConversationRecord(conversation_id="conv-1", session_id="sess-1"))
        self.adapter.insert_message(
            MessageRecord(
                message_id="msg-1",
                conversation_id="conv-1",
                role="user",
                content="Hello world",
                token_count=3,
            )
        )
        self.assertEqual(self.adapter.table_count("messages"), 1)

    def test_message_requires_existing_conversation(self) -> None:
        self.adapter.connect()
        with self.assertRaises(sqlite3.IntegrityError):
            self.adapter.insert_message(MessageRecord(
                message_id="orphan", conversation_id="missing", role="user", content="blocked"
            ))

    def test_insert_episode(self) -> None:
        self.adapter.connect()
        self.adapter.insert_episode(
            EpisodeRecord(
                episode_id="ep-1",
                session_id="sess-1",
                goal_id="goal-1",
                event_type="completion",
                outcome="success",
                description="Finished task",
            )
        )
        self.assertEqual(self.adapter.table_count("episodes"), 1)

    def test_insert_semantic_fact(self) -> None:
        self.adapter.connect()
        self.adapter.insert_semantic_fact(
            SemanticFactRecord(
                fact_id="fact-1",
                subject="python",
                predicate="is",
                object_value="dynamic",
                confidence=0.95,
            )
        )
        self.assertEqual(self.adapter.table_count("semantic_facts"), 1)

    def test_insert_runtime_event(self) -> None:
        self.adapter.connect()
        self.adapter.insert_runtime_event(
            RuntimeEventRecord(
                event_id="re-1",
                event_type="plan_selected",
                source="orchestrator",
                session_id="sess-1",
                summary="Selected mutation plan",
            )
        )
        self.assertEqual(self.adapter.table_count("runtime_events"), 1)

    def test_insert_provider_attempt(self) -> None:
        self.adapter.connect()
        self.adapter.insert_provider_attempt(
            ProviderAttemptRecord(
                attempt_id="pa-1",
                provider="openai",
                model="gpt-4",
                session_id="sess-1",
                status="success",
                duration_ms=1500,
                token_count=500,
            )
        )
        self.assertEqual(self.adapter.table_count("provider_attempts"), 1)

    def test_insert_governance_event(self) -> None:
        self.adapter.connect()
        self.adapter.insert_governance_event(
            GovernanceEventRecord(
                event_id="ge-1",
                event_type="approval",
                source="policy_engine",
                session_id="sess-1",
                status="granted",
                reason="Low risk mutation",
            )
        )
        self.assertEqual(self.adapter.table_count("governance_events"), 1)

    def test_insert_learning_artifact(self) -> None:
        self.adapter.connect()
        self.adapter.insert_learning_artifact(
            LearningArtifactRecord(
                artifact_id="la-1",
                artifact_type="pattern",
                source="consolidator",
                session_id="sess-1",
                content_summary="Retry pattern for execution goals",
                confidence=0.8,
            )
        )
        self.assertEqual(self.adapter.table_count("learning_artifacts"), 1)

    # ----------------------------------------------------------------
    # Query
    # ----------------------------------------------------------------
    def test_query_runtime_events(self) -> None:
        self.adapter.connect()
        self.adapter.insert_runtime_event(
            RuntimeEventRecord(
                event_id="q1",
                event_type="test_query",
                source="test",
                session_id="query-session",
                summary="first event",
            )
        )
        self.adapter.insert_runtime_event(
            RuntimeEventRecord(
                event_id="q2",
                event_type="test_query",
                source="test",
                session_id="query-session",
                summary="second event",
            )
        )
        results = self.adapter.query_runtime_events("query-session")
        self.assertGreaterEqual(len(results), 2)

    def test_query_runtime_events_empty_session(self) -> None:
        self.adapter.connect()
        results = self.adapter.query_runtime_events("nonexistent-session")
        self.assertEqual(results, [])

    def test_query_provider_attempts(self) -> None:
        self.adapter.connect()
        self.adapter.insert_provider_attempt(
            ProviderAttemptRecord(
                attempt_id="pa-query",
                provider="anthropic",
                session_id="sess-1",
                status="success",
            )
        )
        results = self.adapter.query_provider_attempts("anthropic")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].get("status"), "success")

    # ----------------------------------------------------------------
    # Safety - not connected
    # ----------------------------------------------------------------
    def test_operations_fail_when_not_connected(self) -> None:
        rec = RuntimeEventRecord(event_id="fail", event_type="test", source="test")
        with self.assertRaises(RuntimeError):
            self.adapter.insert_runtime_event(rec)

    def test_table_count_zero_when_not_connected(self) -> None:
        self.assertEqual(self.adapter.table_count("conversations"), 0)

    def test_table_exists_false_when_not_connected(self) -> None:
        self.assertFalse(self.adapter.table_exists("conversations"))

    # ----------------------------------------------------------------
    # Schema in temp directory
    # ----------------------------------------------------------------
    def test_can_create_schema_in_temp_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "temp-memory.sqlite"
            adapter = SQLiteAdapter(db_path)
            adapter.connect()
            self.assertTrue(db_path.exists())
            self.assertTrue(adapter.table_exists("conversations"))
            adapter.close()


if __name__ == "__main__":
    unittest.main()
