-- OMNI SQLite Memory Schema
-- This schema defines the structured system memory tables for the OMNI
-- SQLite Memory Facade. It is managed by the SQLiteAdapter class at runtime.
--
-- IMPORTANT SAFETY RULES:
--   - No secrets, credentials, auth tokens, or raw prompts are stored.
--   - Sensitive fields are redacted before any write.
--   - Runtime events store evidence references, not full raw payloads.
--   - Provider attempts store metadata only (no raw key material).

-- =================================================================
-- conversations: Tracks structured conversation records
-- =================================================================
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    title           TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    metadata        TEXT NOT NULL DEFAULT '{}'
);

-- =================================================================
-- messages: Individual messages within conversations
-- =================================================================
CREATE TABLE IF NOT EXISTS messages (
    message_id      TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    token_count     INTEGER NOT NULL DEFAULT 0,
    metadata        TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);

-- =================================================================
-- episodes: Structured episodic memory records
-- =================================================================
CREATE TABLE IF NOT EXISTS episodes (
    episode_id   TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    goal_id      TEXT NOT NULL DEFAULT '',
    event_type   TEXT NOT NULL,
    outcome      TEXT NOT NULL DEFAULT '',
    description  TEXT NOT NULL DEFAULT '',
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    created_at   TEXT NOT NULL,
    metadata     TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(session_id);
CREATE INDEX IF NOT EXISTS idx_episodes_goal   ON episodes(goal_id);
CREATE INDEX IF NOT EXISTS idx_episodes_type   ON episodes(event_type);

-- =================================================================
-- semantic_facts: Learned/consolidated semantic knowledge
-- =================================================================
CREATE TABLE IF NOT EXISTS semantic_facts (
    fact_id      TEXT PRIMARY KEY,
    subject      TEXT NOT NULL,
    predicate    TEXT NOT NULL,
    object_value TEXT NOT NULL DEFAULT '',
    confidence   REAL NOT NULL DEFAULT 0.0,
    source_ids   TEXT NOT NULL DEFAULT '[]',
    created_at   TEXT NOT NULL,
    metadata     TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_semantic_facts_subject ON semantic_facts(subject);

-- =================================================================
-- runtime_events: Tracked runtime execution events
-- =================================================================
CREATE TABLE IF NOT EXISTS runtime_events (
    event_id     TEXT PRIMARY KEY,
    event_type   TEXT NOT NULL,
    source       TEXT NOT NULL DEFAULT '',
    session_id   TEXT NOT NULL DEFAULT '',
    run_id       TEXT NOT NULL DEFAULT '',
    summary      TEXT NOT NULL DEFAULT '',
    evidence_refs TEXT NOT NULL DEFAULT '[]',
    created_at   TEXT NOT NULL,
    metadata     TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_runtime_events_session ON runtime_events(session_id);
CREATE INDEX IF NOT EXISTS idx_runtime_events_type    ON runtime_events(event_type);

-- =================================================================
-- provider_attempts: Provider API call records (no secrets stored)
-- =================================================================
CREATE TABLE IF NOT EXISTS provider_attempts (
    attempt_id  TEXT PRIMARY KEY,
    provider    TEXT NOT NULL,
    model       TEXT NOT NULL DEFAULT '',
    session_id  TEXT NOT NULL DEFAULT '',
    run_id      TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT '',
    duration_ms INTEGER NOT NULL DEFAULT 0,
    token_count INTEGER NOT NULL DEFAULT 0,
    error_type  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    metadata    TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_provider_attempts_provider ON provider_attempts(provider);
CREATE INDEX IF NOT EXISTS idx_provider_attempts_session  ON provider_attempts(session_id);

-- =================================================================
-- governance_events: Policy/governance resolution records
-- =================================================================
CREATE TABLE IF NOT EXISTS governance_events (
    event_id   TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    run_id     TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT '',
    reason     TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    metadata   TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_governance_events_session ON governance_events(session_id);

-- =================================================================
-- learning_artifacts: Training/learning data references
-- =================================================================
CREATE TABLE IF NOT EXISTS learning_artifacts (
    artifact_id    TEXT PRIMARY KEY,
    artifact_type  TEXT NOT NULL,
    source         TEXT NOT NULL DEFAULT '',
    session_id     TEXT NOT NULL DEFAULT '',
    content_summary TEXT NOT NULL DEFAULT '',
    confidence     REAL NOT NULL DEFAULT 0.0,
    created_at     TEXT NOT NULL,
    metadata       TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_learning_artifacts_type ON learning_artifacts(artifact_type);
