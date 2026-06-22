from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .memory_models import (
    ConversationRecord,
    EpisodeRecord,
    GovernanceEventRecord,
    LearningArtifactRecord,
    MessageRecord,
    ProviderAttemptRecord,
    RuntimeEventRecord,
    SemanticFactRecord,
)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS episodes (
    episode_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    goal_id TEXT NOT NULL DEFAULT '',
    event_type TEXT NOT NULL,
    outcome TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS semantic_facts (
    fact_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_value TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.0,
    source_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS runtime_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    evidence_refs TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS provider_attempts (
    attempt_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    duration_ms INTEGER NOT NULL DEFAULT 0,
    token_count INTEGER NOT NULL DEFAULT 0,
    error_type TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS governance_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS learning_artifacts (
    artifact_id TEXT PRIMARY KEY,
    artifact_type TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    content_summary TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(session_id);
CREATE INDEX IF NOT EXISTS idx_episodes_goal ON episodes(goal_id);
CREATE INDEX IF NOT EXISTS idx_episodes_type ON episodes(event_type);
CREATE INDEX IF NOT EXISTS idx_semantic_facts_subject ON semantic_facts(subject);
CREATE INDEX IF NOT EXISTS idx_runtime_events_session ON runtime_events(session_id);
CREATE INDEX IF NOT EXISTS idx_runtime_events_type ON runtime_events(event_type);
CREATE INDEX IF NOT EXISTS idx_provider_attempts_provider ON provider_attempts(provider);
CREATE INDEX IF NOT EXISTS idx_provider_attempts_session ON provider_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_governance_events_session ON governance_events(session_id);
CREATE INDEX IF NOT EXISTS idx_learning_artifacts_type ON learning_artifacts(artifact_type);
"""


class SQLiteAdapter:
    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._lock = threading.RLock()
        self._closed = False
        self._conn: sqlite3.Connection | None = None
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    def connect(self) -> None:
        if self._conn is not None:
            return
        try:
            self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._create_schema()
        except sqlite3.Error:
            self._close_conn()
            raise

    def _create_schema(self) -> None:
        if self._conn is None:
            raise RuntimeError("Not connected")
        with self._lock:
            for statement in SCHEMA_SQL.split(";"):
                stripped = statement.strip()
                if stripped:
                    self._conn.execute(stripped)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._close_conn()

    def _close_conn(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def insert_conversation(self, record: ConversationRecord) -> None:
        self._execute(
            "INSERT OR REPLACE INTO conversations (conversation_id, session_id, title, created_at, updated_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            record.conversation_id, record.session_id, record.title,
            record.created_at, record.updated_at,
            _json(record.metadata),
        )

    def insert_message(self, record: MessageRecord) -> None:
        self._execute(
            "INSERT OR REPLACE INTO messages (message_id, conversation_id, role, content, created_at, token_count, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            record.message_id, record.conversation_id, record.role,
            record.content, record.created_at, record.token_count,
            _json(record.metadata),
        )

    def insert_episode(self, record: EpisodeRecord) -> None:
        self._execute(
            "INSERT OR REPLACE INTO episodes (episode_id, session_id, goal_id, event_type, outcome, description, evidence_ids, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            record.episode_id, record.session_id, record.goal_id,
            record.event_type, record.outcome, record.description,
            _json(record.evidence_ids), record.created_at,
            _json(record.metadata),
        )

    def insert_semantic_fact(self, record: SemanticFactRecord) -> None:
        self._execute(
            "INSERT OR REPLACE INTO semantic_facts (fact_id, subject, predicate, object_value, confidence, source_ids, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            record.fact_id, record.subject, record.predicate,
            record.object_value, record.confidence,
            _json(record.source_ids), record.created_at,
            _json(record.metadata),
        )

    def insert_runtime_event(self, record: RuntimeEventRecord) -> None:
        self._execute(
            "INSERT OR REPLACE INTO runtime_events (event_id, event_type, source, session_id, run_id, summary, evidence_refs, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            record.event_id, record.event_type, record.source,
            record.session_id, record.run_id, record.summary,
            _json(record.evidence_refs), record.created_at,
            _json(record.metadata),
        )

    def insert_provider_attempt(self, record: ProviderAttemptRecord) -> None:
        self._execute(
            "INSERT OR REPLACE INTO provider_attempts (attempt_id, provider, model, session_id, run_id, status, duration_ms, token_count, error_type, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            record.attempt_id, record.provider, record.model,
            record.session_id, record.run_id, record.status,
            record.duration_ms, record.token_count, record.error_type,
            record.created_at, _json(record.metadata),
        )

    def insert_governance_event(self, record: GovernanceEventRecord) -> None:
        self._execute(
            "INSERT OR REPLACE INTO governance_events (event_id, event_type, source, session_id, run_id, status, reason, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            record.event_id, record.event_type, record.source,
            record.session_id, record.run_id, record.status,
            record.reason, record.created_at,
            _json(record.metadata),
        )

    def insert_learning_artifact(self, record: LearningArtifactRecord) -> None:
        self._execute(
            "INSERT OR REPLACE INTO learning_artifacts (artifact_id, artifact_type, source, session_id, content_summary, confidence, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            record.artifact_id, record.artifact_type, record.source,
            record.session_id, record.content_summary, record.confidence,
            record.created_at, _json(record.metadata),
        )

    def query_runtime_events(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM runtime_events WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            session_id, max(1, limit),
        )
        return [_row_to_dict(columns, row) for columns, row in rows]

    def query_provider_attempts(self, provider: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM provider_attempts WHERE provider = ? ORDER BY created_at DESC LIMIT ?",
            provider, max(1, limit),
        )
        return [_row_to_dict(columns, row) for columns, row in rows]

    def table_count(self, table_name: str) -> int:
        if self._conn is None:
            return 0
        with self._lock:
            row = self._conn.execute(
                f"SELECT COUNT(*) FROM \"{table_name}\""
            ).fetchone()
        return int(row[0]) if row else 0

    def table_exists(self, table_name: str) -> bool:
        if self._conn is None:
            return False
        with self._lock:
            row = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()
        return row is not None

    def _execute(self, sql: str, *params: Any) -> None:
        if self._conn is None:
            raise RuntimeError("SQLiteAdapter is not connected")
        with self._lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def _fetchall(self, sql: str, *params: Any) -> list[tuple[list[str], sqlite3.Row]]:
        if self._conn is None:
            return []
        with self._lock:
            self._conn.row_factory = sqlite3.Row
            cursor = self._conn.execute(sql, params)
            columns = [description[0] for description in cursor.description or []]
            rows = cursor.fetchall()
        return [(columns, row) for row in rows]


def _json(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, default=str)


def _row_to_dict(columns: list[str], row: sqlite3.Row) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for idx, col in enumerate(columns):
        raw = row[idx]
        if isinstance(raw, str) and raw.startswith(("{", "[")):
            try:
                import json
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass
        result[col] = raw
    return result
