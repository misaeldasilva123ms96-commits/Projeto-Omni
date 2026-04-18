# Phase 26 - Packaged QueryEngine Promotion Readiness

## Scope

Phase 26 measures packaged QueryEngine adoption without changing routing policy.

- packaged engine remains opt-in via the existing runner logic
- authority fallback remains active
- promotion readiness is observational only

## Counter Model

Engine adoption is persisted to:

- `.logs/fusion-runtime/engine_adoption.json`

The counters are **session-scoped**.

- the file persists the current session state while the session is active
- when a new `session_id` is observed, counters reset to that new session
- this avoids stale historical traffic making promotion readiness look safer than the current runtime really is

Persisted structure:

```json
{
  "scope": "session",
  "session_id": "current-session-id",
  "engine_counters": {
    "packaged_upstream": 0,
    "authority_fallback": 0,
    "fallback_by_reason": {
      "heavy_execution_request": 0,
      "packaged_import_failed": 0,
      "fallback_policy_triggered": 0
    }
  }
}
```

## Promotion Criteria

`promotion_ready` becomes `true` only when all of the following are true for the current session:

- `adoption_rate >= 0.80`
- `packaged_import_failed == 0`
- `total_requests >= 10`

Definitions:

- `adoption_rate = packaged_upstream_count / total_requests`
- `total_requests = packaged_upstream_count + authority_fallback_count`

## Interpretation

This signal is intentionally conservative.

- high adoption alone is not enough if import failures are present
- a very small sample is not enough to justify promotion
- `promotion_ready = true` means "safe to consider promotion", not "promote automatically"

## Phase 27 Promotion Decision

The first controlled promotion expands packaged handling to the scenario:

- `executor_bridge_light_request`

Rationale:

- the request still carries bridge context via `session.executor_bridge`
- no execution-heavy session markers are present
- no repository-analysis or milestone payload is present
- no engineering-heavy message signals are present
- this is the smallest bounded case that previously fell back by policy but can safely use the packaged engine

Rollback threshold:

- if `packaged_import_failed > 2` in the current session, this promoted scenario is automatically reverted to `authority_fallback`
- the rollback is recorded in WorkingMemory as `engine_promotion_rollback`

Expected safe usage envelope:

- conversational or explanatory requests
- bridge-aware requests that keep `session.executor_bridge`
- requests without repository, planning, checkpoint, resume, or execution-heavy markers
