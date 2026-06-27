# Autonomy Session State Cleanup Runbook

**Date:** 2026-06-27
**Entrypoint:** `control-cli cleanup_autonomy_session_states`
**Runtime impact:** None

## 1. Purpose

This runbook explains how an operator can safely invoke the explicit manual
cleanup command for expired autonomy session state rows.

Use it when SQLite-backed autonomy session state is enabled and operators need
to remove expired metadata rows according to the configured TTL policy.

## 2. Scope

This runbook covers only autonomy session state cleanup through the local
operator CLI:

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states
```

It does not cover database backup administration, production deployment
changes, provider routing, Cockpit UI changes, or autonomous execution.

## 3. What This Cleanup Does

The cleanup deletes only expired rows from the SQLite
`autonomy_session_states` table.

A row is eligible for deletion only when its `expires_at` timestamp is earlier
than the cleanup reference time. The command returns safe metadata about the
attempt and never returns raw rows.

## 4. What This Cleanup Does NOT Do

This cleanup does not:

- Execute autonomy decisions.
- Execute `RETRY`, `REPLAN`, `SELF_REPAIR`, `SWITCH_PROVIDER`, or `ABORT_SAFE`.
- Affect provider routing.
- Change runtime response strings.
- Modify prompts, responses, provider payloads, tool payloads, or secrets.
- Delete non-expired autonomy session state rows.
- Delete JSONL audit records.
- Delete process-local tracker state already held in a running process.
- Make Omni approved for autonomous execution.

## 5. Safety Boundaries

- This is a local operator CLI, not a public HTTP endpoint.
- Do not expose this command through an unprotected web route.
- Do not add a Cockpit destructive button without admin-role protection.
- Do not schedule this command unless a future reviewed design approves a
  scheduler.
- Do not run this from autonomous repair, CI repair, self-upgrade, or provider
  switching workflows.
- Cleanup is best-effort and must be treated as maintenance, not as a runtime
  decision input.

## 6. Required Permissions/Access

The operator needs:

- Local shell access to the Omni backend environment.
- Read/write access to the SQLite memory database file.
- Permission to run the Python backend CLI.
- Knowledge of the intended SQLite database path when using a non-default path.

Do not pass secrets, provider credentials, API keys, cookies, headers, or raw
payloads to this command.

## 7. Preconditions

Before running cleanup:

- Confirm the working environment is the intended Omni instance.
- Confirm SQLite memory is intentionally enabled for the target database.
- Confirm the SQLite path points to the intended memory database.
- Confirm no incident investigation depends on expired session-state rows.
- Confirm there is no expectation that JSONL/default mode will delete anything.

## 8. When To Run Cleanup

Run cleanup when:

- SQLite autonomy session state is enabled and expired rows have accumulated.
- Cockpit or runtime diagnostics show `expired_state_count` above zero.
- Operators are performing planned maintenance.
- A test/dev database needs to clear expired autonomy metadata.

## 9. When NOT To Run Cleanup

Do not run cleanup when:

- You are not sure which SQLite database file is targeted.
- SQLite memory is not enabled or not connected and you expect deletion.
- An incident review requires preserving expired metadata rows.
- You are trying to change autonomy decisions or provider behavior.
- You are trying to repair runtime output.
- You are operating through an unprotected web route or ad hoc public endpoint.

## 10. Command Examples

Default invocation:

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states
```

Explicit reference time:

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states `
  --now 2026-06-27T00:00:00+00:00
```

Explicit SQLite database path:

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states `
  --enable-sqlite `
  --sqlite-path .omni/memory/omni-memory.sqlite
```

Explicit SQLite and JSONL paths:

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states `
  --enable-sqlite `
  --sqlite-path .omni/memory/omni-memory.sqlite `
  --jsonl-path .omni/memory/omni-audit.jsonl
```

## 11. Dry-Run Status

Dry-run is available through the same local operator CLI by passing
`--dry-run`.

Dry-run counts expired rows that would be deleted, returns safe metadata only,
and deletes zero rows. It does not expose raw SQLite rows or persisted session
state. The output includes a safe operation identifier and a fingerprint of the
operator-supplied SQLite path, not the raw path.

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states `
  --dry-run `
  --enable-sqlite `
  --sqlite-path .omni/memory/omni-memory.sqlite `
  --now 2026-06-27T00:00:00+00:00
```

Do not simulate dry-run behavior by dumping raw SQLite rows into logs or
user-facing tools.

## 12. SQLite Enabled Example

Command:

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states `
  --enable-sqlite `
  --sqlite-path .omni/memory/omni-memory.sqlite `
  --now 2026-06-27T00:00:00+00:00
```

Example response:

```json
{
  "status": "ok",
  "cleanup": {
    "operation_id": "cleanup-6f3a2b8c9d10",
    "operation_type": "cleanup_autonomy_session_states",
    "attempted": true,
    "supported": true,
    "dry_run": false,
    "sqlite_path_fingerprint": "sha256:9f81b9f2c2e5a0d4",
    "sqlite_path_present": true,
    "would_delete_count": 0,
    "deleted_count": 3,
    "degraded": false,
    "error_category": "",
    "attempted_at": "2026-06-27T00:00:01+00:00",
    "sqlite_enabled": true,
    "sqlite_connected": true,
    "cutoff_time": "2026-06-27T00:00:00+00:00"
  }
}
```

## 13. JSONL/Default No-Op Example

When SQLite is not enabled or not connected, cleanup is unsupported and should
return a safe no-op.

Command:

```powershell
python -m brain.runtime.control.cli cleanup_autonomy_session_states
```

Example response:

```json
{
  "status": "ok",
  "cleanup": {
    "operation_id": "cleanup-1a2b3c4d5e6f",
    "operation_type": "cleanup_autonomy_session_states",
    "attempted": true,
    "supported": false,
    "dry_run": false,
    "sqlite_path_fingerprint": "",
    "sqlite_path_present": false,
    "would_delete_count": 0,
    "deleted_count": 0,
    "degraded": false,
    "error_category": "",
    "attempted_at": "2026-06-27T00:00:01+00:00",
    "sqlite_enabled": false,
    "sqlite_connected": false,
    "cutoff_time": "2026-06-27T00:00:01+00:00"
  }
}
```

## 14. Expected Result Fields

The cleanup payload contains only:

- `operation_id`: safe unique identifier for this cleanup invocation.
- `operation_type`: fixed value `cleanup_autonomy_session_states`.
- `attempted`: whether the command attempted cleanup.
- `supported`: whether SQLite cleanup was available.
- `dry_run`: whether the invocation was count-only.
- `sqlite_path_fingerprint`: stable SHA-256 fingerprint of the operator-supplied
  SQLite path, never the raw path.
- `sqlite_path_present`: whether an explicit SQLite path was supplied to the
  CLI/helper.
- `would_delete_count`: number of expired rows dry-run would delete.
- `deleted_count`: number of expired rows deleted.
- `degraded`: whether cleanup failed or partially degraded.
- `error_category`: safe categorical error label, if degraded.
- `attempted_at`: safe timestamp for the cleanup attempt.
- `sqlite_enabled`: whether SQLite memory was enabled.
- `sqlite_connected`: whether SQLite was connected.
- `cutoff_time`: timestamp used for count/delete eligibility.

No raw session records, prompts, responses, provider payloads, stack traces, or
secrets are returned. Raw SQLite paths are not returned; use
`sqlite_path_fingerprint` to compare whether two invocations targeted the same
operator-supplied path.

## 15. How To Interpret `deleted_count`

`deleted_count` is the number of expired autonomy session state rows removed by
the explicit cleanup invocation.

- In dry-run, `deleted_count` must always be `0`.
- `0` with `supported=true` usually means no expired rows were present.
- `0` with `supported=false` means cleanup was not available.
- A positive value means expired rows were deleted.

`deleted_count` does not count JSONL records, process-local tracker entries, or
non-expired rows.

## 16. How To Interpret `degraded=true`

`degraded=true` means cleanup could not complete normally or the cleanup hook
encountered a safe failure condition.

Use `error_category` for the safe category. Expected categories are limited and
must not include stack traces, database paths, secrets, command arguments, or
raw exception text.

## 16a. Comparing Dry-Run And Cleanup Outputs

When using dry-run before destructive cleanup, compare only safe metadata:

- `operation_type` should be `cleanup_autonomy_session_states` in both outputs.
- `sqlite_path_fingerprint` should match if both invocations used the same
  operator-supplied SQLite path.
- `cutoff_time` should match when validating the exact same cleanup window.
- Dry-run should report `dry_run=true`, `would_delete_count=N`, and
  `deleted_count=0`.
- Destructive cleanup should report `dry_run=false`, `would_delete_count=0`,
  and `deleted_count` equal to the rows actually deleted at that cutoff.

Do not compare raw SQLite paths in logs or tickets. Keep the safe
`operation_id` values as separate evidence for each invocation.

## 17. How To Interpret Unsupported/No-Op

Unsupported cleanup is represented by:

```json
{
  "attempted": true,
  "supported": false,
  "deleted_count": 0,
  "degraded": false
}
```

This is expected in JSONL/default mode or when SQLite is not connected. It is
not a runtime failure.

## 18. Pre-Cleanup Checklist

- Confirm the command is being run locally by an operator.
- Confirm this is not being exposed through HTTP or Cockpit.
- Confirm SQLite cleanup is intended for this environment.
- Confirm the SQLite path is correct.
- Capture current safe lifecycle diagnostics if available.
- Confirm no manual investigation needs expired rows preserved.
- Confirm there is no expectation of autonomy decision execution.

## 19. Post-Cleanup Checklist

- Verify the command returned `status: ok`.
- Check `cleanup.supported`.
- Check `cleanup.deleted_count`.
- Check `cleanup.degraded`.
- If degraded, record the safe `error_category` and investigate locally.
- Confirm runtime behavior and provider routing were not changed.
- Keep the result payload as maintenance evidence when appropriate.

## 20. Troubleshooting

`supported=false`:

- Confirm `--enable-sqlite` was provided when needed.
- Confirm the SQLite database path is correct.
- Confirm the SQLite memory database can be opened by the backend process.

`deleted_count=0` with `supported=true`:

- There may be no expired rows.
- The `--now` value may be earlier than the rows' `expires_at` values.
- Existing rows may be non-expired and intentionally retained.

`degraded=true`:

- Treat cleanup as best-effort failed or partially degraded.
- Use only the safe `error_category`.
- Do not paste raw logs containing secrets or payloads into user-facing tools.
- Re-run only after verifying the SQLite path and local permissions.

## 21. Security Considerations

- This command is destructive maintenance and must stay local/operator-only.
- Do not expose it through an unprotected public route.
- Do not add a Cockpit destructive button without admin-role protection.
- Do not log raw SQLite rows.
- Do not return raw persisted session state.
- Do not include prompts, responses, provider payloads, headers, cookies,
  credentials, `.env` contents, file contents, stdout/stderr, stack traces, or
  command args in cleanup evidence.

## 22. Known Risks

- Dry-run can confirm count and cutoff only; it cannot prove the operator chose
  the intended environment or SQLite path.
- Running against the wrong SQLite path may clean the wrong local database.
- SQLite cleanup is last-state maintenance only; it does not coordinate across
  distributed instances.
- Expired metadata may be unavailable for later investigation after deletion.
- Operators may misread `supported=false` as failure even though it is expected
  for JSONL/default mode.

## 23. Audit/Evidence Notes

The safe cleanup result can be kept as maintenance evidence. It should contain
only the expected result fields and no raw rows.

Recommended evidence to retain:

- Command time.
- Target environment label.
- Whether SQLite was enabled.
- Safe cleanup result payload.
- Operator note explaining why cleanup was run.

Do not retain secrets, full provider payloads, prompts, responses, or raw SQLite
rows as cleanup evidence.

## 24. Manual Merge/Governance Note

This cleanup command does not merge code, approve PRs, repair CI, apply
patches, switch providers, or execute autonomy decisions.

It does not make Omni approved for autonomous execution. Governance remains
manual where manual approval is required.

## 25. Future Improvements

Potential future improvements require separate review:

- Add richer dry-run warnings or confirmation thresholds for unexpectedly high
  `would_delete_count` values.
- Add an admin-role protected HTTP maintenance endpoint if a safe admin pattern
  is approved.
- Add structured maintenance audit events with safe metadata only.
- Add richer operator documentation for database path discovery.
- Add a protected Cockpit maintenance surface only after admin-role protection
  exists.
