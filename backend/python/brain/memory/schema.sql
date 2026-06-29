-- OMNI SQLite Memory Schema
-- This schema defines the structured system memory tables for the OMNI
-- SQLite Memory Facade. It is managed by the SQLiteAdapter class at runtime.
--
-- IMPORTANT SAFETY RULES:
--   - No secrets, credentials, auth tokens, or raw prompts are stored.
--   - Sensitive fields are redacted before any write.
--   - Runtime events store evidence references, not full raw payloads.
--   - Provider attempts store metadata only (no raw key material).
--   - Autonomy session state stores bounded advisory metadata only.
--   - Dry-run replan evidence stores sanitized audit metadata only.
--   - Dry-run retry evidence stores sanitized audit metadata only.

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

-- =================================================================
-- autonomy_session_states: Safe advisory autonomy state summaries
-- =================================================================
CREATE TABLE IF NOT EXISTS autonomy_session_states (
    session_id                       TEXT PRIMARY KEY,
    last_error_type                  TEXT NOT NULL DEFAULT '',
    current_error_count              INTEGER NOT NULL DEFAULT 0,
    stagnant_attempts                INTEGER NOT NULL DEFAULT 0,
    distinct_error_count             INTEGER NOT NULL DEFAULT 0,
    distinct_error_types             TEXT NOT NULL DEFAULT '[]',
    progressive_cycles               INTEGER NOT NULL DEFAULT 0,
    last_runtime_mode                TEXT NOT NULL DEFAULT '',
    last_provider_failure_type       TEXT NOT NULL DEFAULT '',
    last_response_length             INTEGER NOT NULL DEFAULT 0,
    last_response_was_safe_fallback  INTEGER NOT NULL DEFAULT 0,
    last_decision                    TEXT NOT NULL DEFAULT '',
    last_fingerprint_id              TEXT NOT NULL DEFAULT '',
    last_progress_score              INTEGER NOT NULL DEFAULT 0,
    last_stagnation_score            INTEGER NOT NULL DEFAULT 0,
    repeated_strategy_count          INTEGER NOT NULL DEFAULT 0,
    strategies_attempted             TEXT NOT NULL DEFAULT '[]',
    updated_at                       TEXT NOT NULL,
    expires_at                       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_autonomy_session_states_expires_at
    ON autonomy_session_states(expires_at);
CREATE INDEX IF NOT EXISTS idx_autonomy_session_states_updated_at
    ON autonomy_session_states(updated_at);

-- =================================================================
-- dry_run_replan_plan_evidence: Sanitized dry-run REPLAN audit metadata
-- =================================================================
CREATE TABLE IF NOT EXISTS dry_run_replan_plan_evidence (
    plan_id                  TEXT PRIMARY KEY,
    event_type               TEXT NOT NULL,
    plan_type                TEXT NOT NULL,
    advisory                 INTEGER NOT NULL DEFAULT 1,
    would_replan             INTEGER NOT NULL DEFAULT 0,
    replan_reason            TEXT NOT NULL DEFAULT '',
    blocked                  INTEGER NOT NULL DEFAULT 0,
    block_reasons            TEXT NOT NULL DEFAULT '[]',
    replan_eligibility_score REAL NOT NULL DEFAULT 0.0,
    risk_level               TEXT NOT NULL DEFAULT '',
    source_decision          TEXT NOT NULL DEFAULT '',
    fingerprint_id           TEXT NOT NULL DEFAULT '',
    stagnation_score         INTEGER NOT NULL DEFAULT 0,
    progress_score           INTEGER NOT NULL DEFAULT 0,
    repeated_strategy_count  INTEGER NOT NULL DEFAULT 0,
    suggested_strategy       TEXT NOT NULL DEFAULT '',
    evidence_summary         TEXT NOT NULL DEFAULT '',
    created_at               TEXT NOT NULL,
    session_id               TEXT NOT NULL DEFAULT '',
    request_id               TEXT NOT NULL DEFAULT '',
    trace_id                 TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_dry_run_replan_plan_evidence_created_at
    ON dry_run_replan_plan_evidence(created_at);
CREATE INDEX IF NOT EXISTS idx_dry_run_replan_plan_evidence_session
    ON dry_run_replan_plan_evidence(session_id);

-- =================================================================
-- dry_run_retry_plan_evidence: Sanitized dry-run RETRY audit metadata
-- =================================================================
CREATE TABLE IF NOT EXISTS dry_run_retry_plan_evidence (
    plan_id                  TEXT PRIMARY KEY,
    event_type               TEXT NOT NULL,
    plan_type                TEXT NOT NULL,
    advisory                 INTEGER NOT NULL DEFAULT 1,
    would_retry              INTEGER NOT NULL DEFAULT 0,
    retry_reason             TEXT NOT NULL DEFAULT '',
    blocked                  INTEGER NOT NULL DEFAULT 0,
    block_reasons            TEXT NOT NULL DEFAULT '[]',
    retry_eligibility_score  REAL NOT NULL DEFAULT 0.0,
    risk_level               TEXT NOT NULL DEFAULT '',
    source_decision          TEXT NOT NULL DEFAULT '',
    fingerprint_id           TEXT NOT NULL DEFAULT '',
    stagnation_score         INTEGER NOT NULL DEFAULT 0,
    progress_score           INTEGER NOT NULL DEFAULT 0,
    suggested_retry_strategy TEXT NOT NULL DEFAULT '',
    evidence_summary         TEXT NOT NULL DEFAULT '',
    created_at               TEXT NOT NULL,
    recorded_at              TEXT NOT NULL,
    session_id               TEXT NOT NULL DEFAULT '',
    request_id               TEXT NOT NULL DEFAULT '',
    trace_id                 TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_dry_run_retry_plan_evidence_created_at
    ON dry_run_retry_plan_evidence(created_at);
CREATE INDEX IF NOT EXISTS idx_dry_run_retry_plan_evidence_session
    ON dry_run_retry_plan_evidence(session_id);
