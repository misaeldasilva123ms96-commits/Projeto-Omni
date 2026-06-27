# Autonomy Session State Cleanup Dry-Run Design

**Date:** 2026-06-27
**Branch:** `feature/autonomy-session-state-cleanup-dry-run-design`
**Status:** Design approved; contracts implemented by
`feature/autonomy-session-state-cleanup-dry-run-contracts`
**Runtime impact:** None

## 1. Executive Summary

Omni currently has an explicit local operator CLI for autonomy session state
cleanup:

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states
```

That command can delete expired SQLite `autonomy_session_states` rows when
SQLite memory is enabled and connected.

This design defines a dry-run mode that counts expired rows that would be
deleted, returns only safe metadata, and deletes nothing. The follow-up
contracts branch implements the explicit helper/CLI contract without adding a
scheduler, exposing HTTP cleanup, adding a Cockpit destructive control, or
changing runtime behavior.

## 2. Current Cleanup Behavior

Current cleanup behavior is explicit and manual:

- The internal helper is `cleanup_expired_autonomy_session_states_manual`.
- The protected invocation surface is the local operator CLI command
  `cleanup_autonomy_session_states`.
- SQLite cleanup is supported only when SQLite memory is enabled and connected.
- JSONL/default mode returns an unsupported no-op.
- Cleanup deletes only expired autonomy session state rows.
- Cleanup result metadata is limited to safe fields.

Baseline cleanup result fields are:

- `attempted`
- `supported`
- `dry_run`
- `would_delete_count`
- `deleted_count`
- `degraded`
- `error_category`
- `attempted_at`
- `sqlite_enabled`
- `sqlite_connected`
- `cutoff_time`

## 3. Problem Statement

Operators must currently verify cleanup impact indirectly before running the
destructive cleanup command. This creates two operational risks:

- Operators may run cleanup against the wrong SQLite path before seeing how
  many rows are eligible.
- Operators may skip cleanup because the only supported command is destructive.

Omni needs a dry-run design that lets operators estimate expired-row cleanup
impact without exposing raw rows or changing runtime behavior.

## 4. Goals

- Define dry-run semantics for autonomy session state cleanup.
- Count only expired rows that would be deleted.
- Return safe metadata only.
- Preserve SQLite opt-in behavior.
- Preserve JSONL/default no-op behavior.
- Preserve process-local fallback behavior.
- Avoid raw row or session-state exposure.
- Avoid runtime behavior changes.
- Avoid autonomous execution.
- Give operators a clear pre-cleanup verification workflow.

## 5. Non-Goals

- Do not add background cleanup implementation.
- Do not add a scheduler.
- Do not add an automatic cleanup loop.
- Do not add a public HTTP endpoint.
- Do not add a Cockpit destructive control.
- Do not change provider routing.
- Do not change runtime output.
- Do not execute autonomy decisions.
- Do not expose raw rows, session dumps, prompts, responses, provider payloads,
  file contents, command args, headers, cookies, credentials, or secrets.

## 6. Proposed Dry-Run Semantics

Dry-run should mean:

- No rows are deleted.
- Only expired rows that would be deleted are counted.
- The cutoff is the same timestamp that cleanup would use.
- The result includes `dry_run=true`.
- `deleted_count` is always `0`.
- `would_delete_count` reports the number of rows eligible for deletion.
- All returned fields are safe booleans, numbers, categorical strings, or safe
  timestamps.

Dry-run must not affect the process-local `AutonomySessionTracker`, JSONL audit
records, autonomy decisions, provider routing, runtime responses, or Cockpit
state.

## 7. CLI UX Proposal

Use the explicit flag on the existing local operator CLI:

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states --dry-run
```

SQLite-enabled dry-run example:

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states `
  --dry-run `
  --enable-sqlite `
  --sqlite-path .omni/memory/omni-memory.sqlite `
  --now 2026-06-27T00:00:00+00:00
```

UX rules:

- `--dry-run` and destructive cleanup share the same cutoff semantics.
- `--dry-run` must not require write access beyond what is needed to open the
  SQLite database safely.
- `--dry-run` should be valid in JSONL/default mode and return unsupported
  no-op metadata.
- The command should not print raw rows or raw SQLite errors.

## 8. Result Fields

Proposed dry-run result fields:

- `operation_id`
- `operation_type`
- `attempted`
- `supported`
- `dry_run`
- `sqlite_path_fingerprint`
- `sqlite_path_present`
- `would_delete_count`
- `deleted_count`
- `degraded`
- `error_category`
- `attempted_at`
- `sqlite_enabled`
- `sqlite_connected`
- `cutoff_time`

In dry-run mode, `deleted_count` must always be `0`.

Example:

```json
{
  "status": "ok",
  "cleanup": {
    "operation_id": "cleanup-6f3a2b8c9d10",
    "operation_type": "cleanup_autonomy_session_states",
    "attempted": true,
    "supported": true,
    "dry_run": true,
    "sqlite_path_fingerprint": "sha256:9f81b9f2c2e5a0d4",
    "sqlite_path_present": true,
    "would_delete_count": 3,
    "deleted_count": 0,
    "degraded": false,
    "error_category": "",
    "attempted_at": "2026-06-27T00:00:01+00:00",
    "sqlite_enabled": true,
    "sqlite_connected": true,
    "cutoff_time": "2026-06-27T00:00:00+00:00"
  }
}
```

## 9. SQLite Behavior

When SQLite memory is enabled and connected, dry-run should count rows from
`autonomy_session_states` where `expires_at < cutoff_time`.

The query should return only a count. It must not select or serialize row
contents.

Recommended adapter behavior:

- Reuse the existing expired-state count path if available.
- Use the same cutoff timestamp rules as destructive cleanup.
- Return `supported=true` only when SQLite is enabled and connected.
- Return `sqlite_enabled=true` and `sqlite_connected=true` when safe.
- Return a stable fingerprint for an operator-supplied SQLite path, never the
  raw path.
- On read/count failure, return safe degraded metadata.

## 10. JSONL/Default Behavior

JSONL remains the default memory behavior. Dry-run in JSONL/default mode should
not try to derive cleanup candidates from JSONL.

Expected JSONL/default dry-run result:

- `attempted=true`
- `supported=false`
- `dry_run=true`
- `sqlite_path_fingerprint` populated only when an operator-supplied SQLite path
  is present
- `would_delete_count=0`
- `deleted_count=0`
- `degraded=false`
- `error_category=""`
- `sqlite_enabled=false`
- `sqlite_connected=false`, if emitted

This is an expected no-op, not a runtime failure.

## 11. Process-Local Behavior

Dry-run must not inspect, mutate, reset, or delete process-local
`AutonomySessionTracker` state.

Process-local state remains the runtime fallback and is not part of SQLite
cleanup. A running process may still hold in-memory state after dry-run reports
eligible SQLite rows.

## 12. Safety Boundaries

- Dry-run is explicit/manual only.
- Dry-run must not delete rows.
- Dry-run must not execute autonomy decisions.
- Dry-run must not change provider routing.
- Dry-run must not change runtime output.
- Dry-run must not add scheduler behavior.
- Dry-run must not add an automatic cleanup loop.
- Dry-run must not add a public HTTP endpoint.
- Dry-run must not add a Cockpit destructive control.
- Dry-run must return safe metadata only.

## 13. Forbidden Data Exposure

Dry-run must never expose:

- Raw rows
- Raw session state
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
- Provider payloads

Errors must be mapped to safe categories such as `memory_unavailable`,
`count_failed`, or `sqlite_unavailable`.

## 14. Operator Workflow

Recommended future workflow:

1. Confirm target environment.
2. Confirm intended SQLite database path.
3. Run dry-run with `--dry-run`.
4. Review `supported`, `degraded`, and `would_delete_count`.
5. If the count is expected, run destructive cleanup without `--dry-run`.
6. Record both safe result payloads as maintenance evidence.

Operators should not use dry-run as an approval for autonomous execution. It is
only a maintenance visibility step.

## 15. Pre-Cleanup Verification

Before destructive cleanup, dry-run should help verify:

- SQLite cleanup is supported.
- SQLite is connected.
- The cutoff time is what the operator intended.
- The number of expired rows is plausible.
- No degraded condition is present.

If `would_delete_count` is unexpectedly high, stop and verify the SQLite path
and cutoff time before running destructive cleanup.

## 16. Post-Cleanup Verification

After destructive cleanup, operators should compare:

- Dry-run `would_delete_count`
- Cleanup `deleted_count`
- Cleanup `degraded`
- Post-cleanup lifecycle diagnostics, if available

The numbers may differ if rows are added, updated, or expired between dry-run
and cleanup. That race is acceptable for advisory metadata but should be noted
as maintenance evidence.

## 17. Testing Plan

Future implementation should add tests for:

- Dry-run with SQLite disabled returns unsupported no-op.
- Dry-run with SQLite enabled counts expired rows.
- Dry-run does not delete expired rows.
- Dry-run does not count non-expired rows.
- Dry-run returns `deleted_count=0`.
- Dry-run returns safe metadata only.
- Dry-run count failure returns degraded safe metadata.
- Dry-run does not expose raw rows or session dumps.
- Dry-run does not change advisory decisions.
- Dry-run does not change runtime output.
- Existing destructive cleanup tests still pass.
- Existing memory and autonomy tests still pass.

## 18. Failure Handling

Dry-run failures should be best-effort and non-fatal.

Recommended failure behavior:

- MemoryFacade unavailable: `supported=false`, `degraded=true`,
  `error_category="memory_unavailable"`.
- SQLite disabled: `supported=false`, `degraded=false`,
  `error_category=""`.
- SQLite count failure: `supported=true`, `degraded=true`,
  `error_category="count_failed"`.
- Invalid cutoff timestamp: return safe degraded metadata or normalize through
  the same cutoff behavior as destructive cleanup.

No raw exception text should be returned.

## 19. Audit/Evidence Behavior

Dry-run should return safe evidence that operators can record manually:

- Command timestamp
- Target environment label
- `supported`
- `dry_run`
- `would_delete_count`
- `deleted_count`
- `degraded`
- `error_category`
- `cutoff_time`

Dry-run should not append raw row data to JSONL and should not persist raw
diagnostic payloads. If future implementation records a maintenance audit
event, it must be metadata-only and follow the same allowlist.

## 20. Future Cockpit Considerations

Do not add a Cockpit destructive control as part of dry-run.

A future read-only Cockpit display may show safe lifecycle diagnostics such as
expired count, last cleanup attempt, and degraded status. A future admin
maintenance UI would require an approved admin-role protection pattern and a
separate design.

## 21. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Operator trusts stale dry-run count | Medium | Document that counts can change before cleanup |
| Wrong SQLite path is used | Medium | Include `sqlite_enabled`, `sqlite_connected`, and path verification in workflow without echoing sensitive paths |
| Raw rows accidentally exposed | High | Count-only query and strict result allowlist |
| Dry-run mistaken for autonomous approval | High | Document that dry-run is maintenance-only |
| Dry-run added to scheduler later | Medium | Require separate design for scheduling |

## 22. Open Questions

- Should `cutoff_time` always echo the normalized cleanup cutoff?
- Should dry-run require `--enable-sqlite`, or should environment opt-in be
  sufficient?
- Should a future maintenance audit event be emitted for dry-run attempts?
- Should dry-run support a maximum warning threshold, such as requiring a second
  confirmation when `would_delete_count` is high?
- Should `sqlite_connected` be emitted in all modes or only when safe and known?

## 23. Go/No-Go Checklist

Before enabling or extending dry-run:

- [x] Design reviewed and approved.
- [x] No destructive behavior in dry-run.
- [x] `deleted_count` remains `0` in dry-run.
- [x] `would_delete_count` uses count-only SQLite query.
- [x] JSONL/default mode remains unsupported no-op.
- [x] Process-local state remains untouched.
- [x] Result fields are allowlisted.
- [x] Forbidden data exposure tests are added.
- [x] Failure categories are safe and categorical.
- [x] No scheduler is added.
- [x] No automatic cleanup loop is added.
- [x] No public HTTP endpoint is added.
- [x] No Cockpit destructive control is added.
- [x] Runtime output remains unchanged.
- [x] Provider routing remains unchanged.
- [x] Advisory-only autonomy remains enforced.
