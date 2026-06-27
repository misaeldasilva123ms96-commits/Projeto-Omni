# Omni Autonomy Session State Persistence Design

**Date:** 2026-06-27
**Branch:** `feature/autonomy-session-state-design`
**Base:** `main` after PR #423
**Status:** Draft design only
**Runtime impact:** None

---

## 1. Executive Summary

Omni currently tracks autonomy session state in process memory through
`AutonomySessionTracker`. This design proposes a future SQLite-backed session
state store, integrated through `MemoryFacade`, so safe advisory metadata can
survive process restarts when SQLite memory is explicitly enabled.

The proposed persistence model is deliberately narrow:

- JSONL remains the default memory backend.
- SQLite session state remains opt-in.
- Process-local tracking remains available as the fallback.
- Persistence is best-effort and must never crash runtime execution.
- Reads degrade to empty state when storage is unavailable or invalid.
- Persisted state is advisory evidence only and must not execute actions.

This document does not implement persistence or change runtime behavior.

**Contracts update:** `feature/autonomy-session-state-memoryfacade-contracts`
adds the safe `AutonomySessionStateRecord`, `MemoryFacade` methods, SQLite
adapter support, and tests for this design. Runtime autonomy wiring is still not
connected to these methods.

**Runtime opt-in update:** `feature/autonomy-session-state-runtime-opt-in-wiring`
wires `AutonomySessionTracker` to hydrate and upsert safe session state only
when a `MemoryFacade` is present and SQLite memory is explicitly enabled and
connected. JSONL/default behavior remains process-local, and autonomy decisions
remain advisory-only.

**Cockpit diagnostics update:** `feature/autonomy-session-state-cockpit-diagnostics`
exposes read-only session-state diagnostics in `autonomy_evaluation` and the
Cockpit Autonomia tab. Diagnostics are limited to categorical source, booleans,
safe timestamps, numeric field count, and a redacted error category. No raw
persisted session state is rendered.

**Cleanup observability update:** `feature/autonomy-session-state-cleanup-observability`
adds read-only lifecycle diagnostics for explicit cleanup support, last cleanup
attempt metadata, deleted count, cleanup degradation, TTL seconds, and expired
state count. No background cleanup job or autonomous cleanup scheduling is
introduced.

**Manual cleanup hook update:** `feature/autonomy-session-state-manual-cleanup-hook`
adds an internal explicit Python hook for expired autonomy session state cleanup.
The hook is not scheduled, not exposed as a public endpoint, and not rendered as
a destructive Cockpit control. It returns only safe metadata: `attempted`,
`supported`, `deleted_count`, `degraded`, `error_category`, and `attempted_at`.

**Protected cleanup entrypoint update:** `feature/autonomy-session-state-protected-cleanup-entrypoint`
does not add a new HTTP cleanup endpoint because the repository has protected
Supabase operator/control routes but no established admin-role MemoryFacade
maintenance route for destructive cleanup. The implemented protected invocation
surface is the existing local operator `control-cli`:
`cleanup_autonomy_session_states`. It reuses the manual hook, is explicit only,
and returns the same safe metadata fields.

## 2. Current State

The current autonomy stack is advisory-only:

- `SmartErrorProgressTracker` derives safe fingerprints, progress scores,
  stagnation scores, and strategy metadata.
- `AutonomySessionTracker` stores per-session state in a process-local dict.
- `AutonomyController` evaluates policy and records advisory receipts.
- Governance events may be recorded through `MemoryFacade`.
- `MemoryFacade` writes JSONL by default and can additionally use SQLite when
  `OMINI_ENABLE_SQLITE_MEMORY=true`.
- Cockpit autonomy views are read-only and display current decision, controller
  stats, and decision timeline metadata.

The process-local state is intentionally limited to safe metadata such as error
type, counts, runtime mode, provider failure type, response length, fallback
state, and last decision. It does not store raw prompts, raw responses, stack
traces, tool output, credentials, or file contents.

## 3. Problem Statement

Autonomy session state is lost when the runtime process restarts. This resets
stagnation and progress counters even when governance evidence and Cockpit
timeline data are durable elsewhere. The loss of state makes advisory decisions
less consistent across restarts and limits future supervised workflows that need
bounded, auditable continuity.

Before implementing persistence, Omni needs an explicit design for schema,
lifecycle, safety boundaries, fallback behavior, TTL cleanup, corruption
handling, and `MemoryFacade` integration.

## 4. Goals

- Define a SQLite schema for safe autonomy session state.
- Keep JSONL as the default behavior.
- Keep SQLite persistence opt-in.
- Preserve process-local fallback.
- Persist only bounded, sanitized advisory metadata.
- Make read/write failures non-fatal.
- Define TTL and cleanup behavior.
- Define migration and rollout gates before implementation.
- Preserve advisory-only behavior.

## 5. Non-Goals

- Do not implement persistence in this phase.
- Do not change runtime behavior.
- Do not enable autonomous `RETRY`, `REPLAN`, `SELF_REPAIR`,
  `SWITCH_PROVIDER`, or `ABORT_SAFE`.
- Do not add an executor for advisory decisions.
- Do not use persisted session state to perform actions.
- Do not change provider selection behavior.
- Do not change secrets, environment files, CI secrets, deploy config, or
  production settings.
- Do not make SQLite the default backend.
- Do not persist raw user, provider, tool, command, file, or credential data.

## 6. Proposed Architecture

Future implementation should add a small persistence adapter behind
`MemoryFacade` and keep `AutonomySessionTracker` as the runtime-facing API.

```text
Runtime metadata
      |
      v
SmartErrorProgressTracker
      |
      v
AutonomySessionTracker
      |       \
      |        \ process-local dict remains authoritative for current process
      v
MemoryFacade autonomy session state API
      |
      +-- JSONL default: no session-state hydration, process-local only
      |
      +-- SQLite opt-in: best-effort hydrate/update/delete safe state rows
```

The tracker should continue to work without a facade. When a facade is present,
it may hydrate state at session start and persist sanitized updates after an
advisory decision is evaluated. Persistence must not be on the decision path in
a way that can fail closed or block the user request.

## 7. Data Model

The persisted record represents one safe summary row per autonomy session. It is
not an event log and not a transcript. The record stores only the latest bounded
state needed to reconstruct advisory counters after restart.

Recommended logical model:

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | string | Primary key, bounded identifier |
| `last_error_type` | string | Safe enum-like value or empty string |
| `current_error_count` | integer | Non-negative |
| `stagnant_attempts` | integer | Non-negative |
| `distinct_error_count` | integer | Non-negative derived count |
| `distinct_error_types` | string array | Bounded safe strings only |
| `progressive_cycles` | integer | Non-negative |
| `last_runtime_mode` | string | Safe enum-like value or empty string |
| `last_provider_failure_type` | string | Safe enum-like value or empty string |
| `last_response_length` | integer | Non-negative length only |
| `last_response_was_safe_fallback` | boolean | Stored as 0/1 in SQLite |
| `last_decision` | string | Advisory decision name only |
| `last_fingerprint_id` | string | Short safe fingerprint id |
| `last_progress_score` | integer | Non-negative |
| `last_stagnation_score` | integer | Non-negative |
| `repeated_strategy_count` | integer | Non-negative |
| `strategies_attempted` | string array | Safe bounded strategy names only |
| `updated_at` | timestamp | UTC ISO-8601 |
| `expires_at` | timestamp | UTC ISO-8601 |

## 8. SQLite Schema Proposal

The table should live in the existing SQLite memory database managed by
`MemoryFacade` and `SQLiteAdapter`.

```sql
CREATE TABLE IF NOT EXISTS autonomy_session_states (
    session_id TEXT PRIMARY KEY,
    last_error_type TEXT NOT NULL DEFAULT '',
    current_error_count INTEGER NOT NULL DEFAULT 0,
    stagnant_attempts INTEGER NOT NULL DEFAULT 0,
    distinct_error_count INTEGER NOT NULL DEFAULT 0,
    distinct_error_types TEXT NOT NULL DEFAULT '[]',
    progressive_cycles INTEGER NOT NULL DEFAULT 0,
    last_runtime_mode TEXT NOT NULL DEFAULT '',
    last_provider_failure_type TEXT NOT NULL DEFAULT '',
    last_response_length INTEGER NOT NULL DEFAULT 0,
    last_response_was_safe_fallback INTEGER NOT NULL DEFAULT 0,
    last_decision TEXT NOT NULL DEFAULT '',
    last_fingerprint_id TEXT NOT NULL DEFAULT '',
    last_progress_score INTEGER NOT NULL DEFAULT 0,
    last_stagnation_score INTEGER NOT NULL DEFAULT 0,
    repeated_strategy_count INTEGER NOT NULL DEFAULT 0,
    strategies_attempted TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_autonomy_session_states_expires_at
    ON autonomy_session_states(expires_at);

CREATE INDEX IF NOT EXISTS idx_autonomy_session_states_updated_at
    ON autonomy_session_states(updated_at);
```

List fields should be JSON arrays serialized by the SQLite adapter after
sanitization and bounds checks.

## 9. JSONL/Default Behavior

JSONL remains the default memory backend. In default mode:

- No SQLite session-state table is required.
- `AutonomySessionTracker` continues to use process-local state.
- Governance events may still be mirrored to JSONL as they are today.
- Session-state hydration returns empty state.
- Session-state writes are skipped or treated as no-op.
- Runtime behavior remains identical to the current process-local model.

JSONL should not become the durable session-state source in this design because
the session state is an upserted summary record, while the existing JSONL path
is append-only audit evidence.

## 10. SQLite Opt-In Behavior

SQLite-backed autonomy session state should activate only when all future
implementation gates are true:

- SQLite memory is enabled through the existing opt-in mechanism.
- The `MemoryFacade` SQLite adapter initializes successfully.
- The session-state table is available or can be created safely.
- The caller explicitly wires the tracker to the facade.

When enabled, future behavior should be:

- On session start or first access, attempt to read the row for `session_id`.
- Ignore rows whose `expires_at` is in the past.
- If a valid row exists, hydrate only allowed fields.
- After tracker update, sanitize and upsert the latest safe state.
- On reset, best-effort delete the row for the session.
- On explicit manual cleanup, best-effort delete expired rows.

All SQLite failures must be swallowed after sanitized diagnostic logging.

## 11. MemoryFacade Integration Plan

Future implementation should add narrow methods to `MemoryFacade` rather than
allowing autonomy runtime code to access `SQLiteAdapter` directly:

- `load_autonomy_session_state(session_id: str) -> dict | None`
- `save_autonomy_session_state(state: AutonomySessionStateRecord) -> None`
- `delete_autonomy_session_state(session_id: str) -> None`
- `cleanup_expired_autonomy_session_states(now: str | None = None) -> int`

`MemoryFacade` should own:

- SQLite opt-in checks.
- Adapter initialization.
- Schema creation.
- Sanitization before persistence.
- Exception handling.
- Empty-state fallback on read failures.

`AutonomySessionTracker` should own:

- In-process state mutation.
- Progress/stagnation semantics.
- Conversion to and from the safe persisted record.

## 12. Session Lifecycle

Recommended lifecycle for a future implementation:

1. Runtime receives or creates a `session_id`.
2. Tracker calls `get_or_create(session_id)`.
3. If SQLite session persistence is enabled and local state is absent, tracker
   asks `MemoryFacade` for a persisted row.
4. Missing, expired, corrupt, or invalid rows hydrate as empty state.
5. Tracker evaluates progress/stagnation using local state.
6. Controller produces an advisory decision.
7. Tracker updates process-local state.
8. Tracker asks `MemoryFacade` to best-effort persist sanitized state.
9. Session reset deletes local state and best-effort deletes persisted state.
10. Explicit manual cleanup may remove expired rows.

Hydration must happen before advisory evaluation, but failure to hydrate must
not prevent evaluation.

## 13. TTL/Cleanup Policy

The persisted state should be short lived. Recommended defaults:

- Default TTL: 7 days from `updated_at`.
- Maximum TTL: 30 days unless a later ADR approves a longer value.
- Cleanup trigger: explicit/manual hook invocation only. No background
  scheduler, startup cleanup, or automatic runtime-turn cleanup is implemented.
- Protected invocation: local operator `control-cli cleanup_autonomy_session_states`
  with optional `--enable-sqlite`, `--sqlite-path`, `--jsonl-path`, and `--now`.
  Without SQLite enabled and connected, the command is a safe unsupported no-op.
- Cleanup query: delete rows where `expires_at < now_utc`.
- Cleanup failure: log sanitized diagnostic and continue.

TTL exists to prevent stale advisory metadata from influencing future sessions
and to reduce the amount of retained metadata.

## 14. Corruption Handling

Reads must degrade to empty state when:

- SQLite connection fails.
- The table is missing and cannot be created.
- A row contains invalid JSON.
- A row contains invalid timestamps.
- Counts are negative or exceed configured bounds.
- String fields exceed bounds or fail allowlist validation.
- Required fields are missing.
- `expires_at` is in the past.

Corrupt rows may be deleted best-effort, but deletion failure must not crash the
runtime.

## 15. Multi-Process/Multi-Instance Limitations

The proposed design is not a distributed coordination mechanism.

- SQLite can support multiple readers and limited concurrent writers, but Omni
  must not treat it as cross-instance locking.
- Last-writer-wins upsert semantics are acceptable for advisory metadata.
- No autonomous action may depend on persisted state.
- Multi-instance deployments may observe stale or overwritten counters.
- If stronger guarantees are needed later, a separate design must define
  locking, leases, conflict resolution, and instance identity.

## 16. Safety/Redaction Rules

Persistence must be sanitized before write:

- Use allowlist-based serialization, not denylist-only redaction.
- Bound every string length.
- Bound every list length.
- Store only enum-like labels, counts, timestamps, booleans, and safe ids.
- Never store raw exception text unless it has already been classified into a
  safe error type.
- Never store prompts, responses, tool payloads, file contents, command
  arguments, headers, cookies, credentials, or provider payloads.
- Sanitized logging must not include database paths, secrets, or raw payloads.

Recommended bounds:

- `session_id`: 128 characters.
- Enum-like strings: 80 characters.
- `last_fingerprint_id`: 64 characters.
- `distinct_error_types`: max 20 items, 80 characters each.
- `strategies_attempted`: max 20 items, 80 characters each.
- Counts and scores: clamp to non-negative integers with a documented maximum.

## 17. Fields Allowed To Persist

Only these fields are approved for persistence in this design:

- `session_id`
- `last_error_type`
- `current_error_count`
- `stagnant_attempts`
- `distinct_error_count`
- `distinct_error_types` only if serialized safely as bounded strings
- `progressive_cycles`
- `last_runtime_mode`
- `last_provider_failure_type`
- `last_response_length`
- `last_response_was_safe_fallback`
- `last_decision`
- `last_fingerprint_id`
- `last_progress_score`
- `last_stagnation_score`
- `repeated_strategy_count`
- `strategies_attempted` only as safe bounded strategy names
- `updated_at`
- `expires_at`

## 18. Fields Forbidden To Persist

These fields and data classes are explicitly forbidden:

- Raw prompt
- Raw response
- Raw receipt
- Stack trace
- Traceback
- `stdout` or `stderr`
- Command args
- Headers or cookies
- API keys, tokens, or secrets
- Provider credentials
- File contents
- `.env` content
- Full user message content
- Full tool output
- Full provider payload

If a future implementation needs a new field, it must update this document or a
successor ADR before implementation.

## 19. Migration Plan

Recommended migration sequence:

1. Add safe record model and serializer tests. Done in the contracts branch.
2. Add `SQLiteAdapter` schema and query/upsert/delete helpers. Done in the
   contracts branch.
3. Add `MemoryFacade` session-state methods with SQLite disabled by default.
   Done in the contracts branch.
4. Add tracker hydration/persistence behind explicit constructor injection.
   Done in the runtime opt-in wiring branch.
5. Keep process-local tracker as the default and fallback.
6. Add explicit/manual cleanup for expired rows.
7. Add docs for the opt-in flag and operational behavior.
8. Run docs, unit, and focused runtime autonomy tests.

No existing data migration is required because current session state is
process-local and cannot be recovered after restart.

## 20. Testing Plan

Future implementation should include:

- Serializer tests proving forbidden fields cannot be emitted.
- Bounds tests for strings, arrays, counts, and timestamps.
- SQLite schema creation tests.
- SQLite upsert/load/delete tests.
- Expired-row tests.
- Corrupt JSON array tests.
- Invalid timestamp tests.
- SQLite unavailable tests showing reads return empty state.
- SQLite write failure tests showing runtime continues.
- Tracker hydration tests.
- Tracker fallback tests when `MemoryFacade` is absent.
- Advisory-only regression tests proving decisions are not executed.
- Cockpit regression tests if any new read-only status field is exposed.

Docs-only validation for this branch is limited to `git diff --check` and
`git status --short`.

## 21. Rollout Plan

Recommended rollout phases:

| Phase | Behavior |
|-------|----------|
| Phase 0 | Design only, no runtime changes |
| Phase 1 | Add model, schema, facade methods, and unit tests, still unused by runtime |
| Phase 2 | Wire tracker with persistence disabled by default and explicit test injection |
| Phase 3 | Enable SQLite opt-in in local/dev only |
| Phase 4 | Add lifecycle diagnostics for hydrate/save/cleanup success and failure |
| Phase 5 | Add explicit/manual cleanup hook without scheduler or public endpoint |
| Phase 6 | Add protected local operator CLI entrypoint for explicit cleanup |
| Phase 7 | Consider broader opt-in after review and incident-free soak |

No phase enables autonomous execution.

## 22. Cockpit Impact

This design has no immediate Cockpit impact. The Cockpit remains read-only.

Future implementation may expose non-sensitive persistence diagnostics, such as:

- State persistence mode: `process-local`, `jsonl-default`, or `sqlite-opt-in`.
- Last hydrate status: `ok`, `empty`, `expired`, or `unavailable`.
- Last save status: `ok`, `skipped`, or `failed`.
- Expired rows cleaned count.

Cockpit must not display forbidden fields or raw storage errors.

Implemented diagnostics use these safe fields:

- `session_state_source`
- `session_state_persistence_enabled`
- `session_state_hydrated`
- `session_state_upserted`
- `session_state_degraded`
- `session_state_last_error_category`
- `session_state_updated_at`
- `session_state_expires_at`
- `session_state_fields_count`
- `expired_state_cleanup_supported`
- `last_cleanup_attempted_at`
- `last_cleanup_deleted_count`
- `cleanup_degraded`
- `cleanup_last_error_category`
- `session_state_ttl_seconds`
- `expired_state_count`

Implemented manual cleanup hook result fields:

- `attempted`
- `supported`
- `deleted_count`
- `degraded`
- `error_category`
- `attempted_at`

Implemented protected cleanup entrypoint:

- `control-cli cleanup_autonomy_session_states`
- Explicit local/operator invocation only
- No HTTP endpoint
- No Cockpit button
- No scheduler or automatic loop
- Same safe result fields as the manual hook

## 23. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Unsafe data accidentally persisted | High | Strict allowlist serializer and tests |
| SQLite failure affects runtime | High | Best-effort writes and empty-state reads |
| Stale state affects decisions | Medium | TTL, expiry checks, cleanup |
| Multi-process writes overwrite counters | Medium | Document last-writer-wins limitation |
| Operators assume state enables automation | High | Keep advisory-only labels and docs |
| JSONL users expect durable session state | Low | Document JSONL default as process-local only |

## 24. Open Questions

- Should TTL default to 7 days or a shorter value such as 24 hours?
- Should `session_id` be hashed before persistence, or is the bounded id safe as
  currently used by memory records?
- Should cleanup remain internal-only, or should a future protected admin
  surface invoke the manual hook?
- Should persistence diagnostics be surfaced in Cockpit immediately, or only
  after implementation stabilizes?
- What maximum count clamp should be used for long-running sessions?
- Should `distinct_error_types` store labels or only a count in the first
  implementation?

## 25. Go/No-Go Checklist

Before implementing SQLite-backed autonomy session state:

- [ ] Design/ADR reviewed and approved.
- [ ] SQLite remains opt-in.
- [ ] JSONL remains default.
- [ ] Process-local fallback remains available.
- [ ] Serializer uses an allowlist.
- [ ] Forbidden fields have regression tests.
- [ ] Read failures degrade to empty state.
- [ ] Write failures are best-effort and non-fatal.
- [ ] TTL and cleanup are implemented.
- [ ] Corrupt rows do not crash runtime.
- [ ] Multi-process limitations are documented.
- [ ] Cockpit remains read-only.
- [ ] Persisted state is not used to execute actions.
- [ ] Advisory-only mode remains enforced.
- [ ] No provider auto-switching is enabled.
- [ ] No autonomous commit, push, PR, CI repair, self-upgrade, or patching is
  enabled.
