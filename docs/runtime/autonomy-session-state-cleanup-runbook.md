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

There is no dry-run mode yet.

To estimate cleanup impact without deleting rows, use existing read-only
lifecycle diagnostics where available, such as Cockpit session-state cleanup
diagnostics or MemoryFacade lifecycle diagnostics in a controlled diagnostic
context. Do not simulate dry-run behavior by dumping raw SQLite rows into logs
or user-facing tools.

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
    "attempted": true,
    "supported": true,
    "deleted_count": 3,
    "degraded": false,
    "error_category": "",
    "attempted_at": "2026-06-27T00:00:01+00:00"
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
    "attempted": true,
    "supported": false,
    "deleted_count": 0,
    "degraded": false,
    "error_category": "",
    "attempted_at": "2026-06-27T00:00:01+00:00"
  }
}
```

## 14. Expected Result Fields

The cleanup payload contains only:

- `attempted`: whether the command attempted cleanup.
- `supported`: whether SQLite cleanup was available.
- `deleted_count`: number of expired rows deleted.
- `degraded`: whether cleanup failed or partially degraded.
- `error_category`: safe categorical error label, if degraded.
- `attempted_at`: safe timestamp for the cleanup attempt.

No raw session records, prompts, responses, provider payloads, stack traces, or
secrets are returned.

## 15. How To Interpret `deleted_count`

`deleted_count` is the number of expired autonomy session state rows removed by
the explicit cleanup invocation.

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

- There is no dry-run mode yet.
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

- Add a read-only dry-run/count mode.
- Add an admin-role protected HTTP maintenance endpoint if a safe admin pattern
  is approved.
- Add structured maintenance audit events with safe metadata only.
- Add richer operator documentation for database path discovery.
- Add a protected Cockpit maintenance surface only after admin-role protection
  exists.
