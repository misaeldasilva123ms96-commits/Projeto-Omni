# Autonomy Pre Dry-Run Review

**Date:** 2026-06-27
**Branch:** `feature/autonomy-pre-dry-run-review`
**Base:** `main` after PR #436
**Status:** Review report only
**Runtime impact:** None

## 1. Executive Summary

Omni's autonomy stack is mature enough to begin a future dry-run-only
RETRY/REPLAN planning phase, but it is not approved for autonomous execution.
The current implementation provides advisory decisions, safe evidence,
read-only Cockpit visibility, SQLite opt-in session-state persistence, explicit
cleanup tooling, dry-run cleanup contracts, and operator evidence notes.

The review result is:

- Approved only for dry-run planning work.
- Not approved for autonomous execution.

## 2. Current Autonomy Mode

The current autonomy mode is advisory-only.

`AutonomyController` can evaluate context and produce decisions such as RETRY,
REPLAN, SELF_REPAIR, SWITCH_PROVIDER, ABORT_SAFE, and escalation, but those
decisions are metadata. No executor is allowed to interpret the advisory output
as permission to perform an action.

Runtime output and provider routing remain outside the autonomy controller's
authority.

## 3. What Is Implemented

The implemented advisory stack includes:

- Autonomy Controller.
- Per-session autonomy state.
- Smart Error Progress Tracker.
- Tracker-aware autonomy policy.
- Persisted autonomy decision evidence.
- Cockpit Autonomia tab.
- Controller stats.
- Decision timeline.
- Hardened advisory evidence payload.
- SQLite opt-in session state persistence through MemoryFacade.
- Session state diagnostics.
- Cleanup lifecycle observability.
- Internal manual cleanup hook.
- Local operator CLI cleanup entrypoint.
- Cleanup runbook.
- Cleanup dry-run contracts.
- Dry-run observability fields.
- Dry-run evidence notes.

## 4. What Remains Advisory-Only

The following remain advisory-only:

- RETRY decisions.
- REPLAN decisions.
- SELF_REPAIR decisions.
- SWITCH_PROVIDER decisions.
- ABORT_SAFE decisions.
- Escalation signals.
- Persisted decision evidence.
- Session state counters and progress/stagnation scores.
- Cockpit autonomy displays.
- Cleanup diagnostics and maintenance evidence.

These surfaces may inform humans and future dry-run planning, but they must not
execute actions.

## 5. What Is Explicitly Disabled

The following are not enabled:

- Autonomous patching.
- Autonomous commit, push, or PR creation.
- CI repair.
- Self-upgrade.
- Provider auto-switching.
- Automatic RETRY execution.
- Automatic REPLAN execution.
- Automatic SELF_REPAIR execution.
- Automatic SWITCH_PROVIDER execution.
- Automatic ABORT_SAFE execution.
- Cleanup scheduler or automatic cleanup loop.
- Public cleanup endpoint.
- Cockpit destructive cleanup control.

## 6. Evidence Flow Review

Autonomy evidence is captured as safe metadata. The flow includes policy
inputs, advisory decision metadata, tracker evidence, fingerprints, risk level,
reason, and advisory flags.

Evidence retrieval is read-only and must degrade safely. Evidence payloads must
not include raw prompts, raw responses, raw receipts, stack traces,
stdout/stderr, full provider payloads, secrets, file contents, or command
argument dumps.

The evidence model is suitable for dry-run planning review because it gives
humans enough context to understand why a future plan would recommend RETRY or
REPLAN without executing either action.

## 7. Session State Persistence Review

Session state persistence is SQLite opt-in and MemoryFacade-mediated. JSONL
remains the default audit path, and process-local state remains the runtime
fallback.

Persisted state is limited to safe bounded metadata, including session ID,
error counts, distinct safe error types, progressive cycles, runtime mode,
provider failure category, response length, fallback flag, last decision,
fingerprint ID, progress/stagnation scores, strategy counts, safe strategy
names, update time, and expiration time.

Reads degrade to empty state. Writes are best-effort. Corrupt or unavailable
SQLite state must not crash runtime execution.

## 8. Cleanup/Dry-Run Cleanup Review

Expired autonomy session state cleanup is explicit/manual only. The local
operator CLI can invoke cleanup when SQLite is enabled and connected. JSONL and
SQLite-disabled modes return safe unsupported/no-op metadata.

Dry-run cleanup counts expired rows that would be deleted and always reports
`deleted_count=0`. It returns safe metadata such as `operation_id`,
`operation_type`, `sqlite_path_fingerprint`, `sqlite_path_present`,
`would_delete_count`, `deleted_count`, degradation status, error category,
attempt time, and cutoff time.

Cleanup deletes only expired autonomy session state rows. It does not execute
autonomy decisions, change provider routing, or change runtime responses.

## 9. Cockpit Visibility Review

Cockpit autonomy visibility is read-only. The Autonomia tab can show current
decision metadata, controller stats, decision timeline, session-state source,
hydration/upsert/degradation status, and cleanup lifecycle diagnostics.

Cockpit must not expose destructive cleanup controls, raw persisted session
records, raw prompts, raw responses, raw provider payloads, stack traces,
stdout/stderr, secrets, file contents, or command arguments.

Current Cockpit visibility is sufficient for review and operator awareness, not
for action execution.

## 10. Security/Redaction Review

The autonomy stack is designed around metadata-only evidence. Redaction and
allowlists are required at persistence, diagnostics, Cockpit rendering, cleanup
output, and evidence-sharing boundaries.

Forbidden data includes:

- Raw prompts.
- Raw responses.
- Raw receipts.
- Stack traces and tracebacks.
- stdout/stderr.
- Command arguments.
- Headers and cookies.
- API keys, tokens, secrets, and provider credentials.
- File contents and `.env` contents.
- Raw database rows.
- Full provider payloads.

Dry-run planning must inherit these constraints.

## 11. Runtime Behavior Preservation Review

The implemented autonomy stack must not change runtime output strings, provider
routing, execution flow, or user-visible responses. Autonomy evaluation may
attach advisory diagnostics and evidence metadata, but it must not trigger
actions.

MemoryFacade failures, SQLite failures, corrupt rows, cleanup failures, and
evidence read failures must degrade to safe empty/no-op/degraded metadata.

## 12. CI/Test Validation Review

Recent autonomy stack work has used focused validation for memory contracts,
runtime autonomy behavior, control CLI behavior, security regression checks,
and diff hygiene.

The expected validation model before implementation work is:

- Focused backend tests for the changed module.
- Existing autonomy tests.
- Existing memory tests.
- Security regression checks when behavior or output safety changes.
- `git diff --check`.
- `git status --short`.

This review branch is documentation-only, so no test suite is required.

## 13. Known Validation Caveats

Known caveats:

- Broad local `python -m pytest tests/` has timed out in recent local runs and
  should be treated as inconclusive when it exceeds the local budget.
- CI remains the stronger source for full-suite validation.
- Documentation-only changes still require diff and status checks.
- Safety scans can produce expected hits in docs/tests that intentionally name
  forbidden examples; the risk is unredacted runtime output, not the existence
  of forbidden terms in governance docs.

## 14. Remaining Risks

Remaining risks before dry-run RETRY/REPLAN planning include:

- Operators may confuse dry-run planning with execution permission.
- Persisted advisory state could be over-trusted if not labeled clearly.
- Dry-run counts can become stale before cleanup.
- SQLite path fingerprints compare supplied paths but do not prove environment
  correctness.
- Future changes could accidentally widen evidence fields.
- Future UI changes could accidentally expose raw payloads.
- Multi-process SQLite state remains last-writer-wins advisory metadata.

## 15. Required Gates Before Dry-Run RETRY

Before dry-run RETRY planning begins:

- Define a dry-run RETRY plan contract that cannot execute provider calls.
- Define allowed inputs and outputs as metadata only.
- Require `advisory=true` and a separate `dry_run=true` marker.
- Prohibit raw prompt/response/provider payload persistence.
- Add tests proving no RETRY action is executed.
- Add tests proving runtime response strings are unchanged.
- Add Cockpit/read-only visibility only if safe and non-destructive.

## 16. Required Gates Before Dry-Run REPLAN

Before dry-run REPLAN planning begins:

- Define a dry-run REPLAN plan contract that cannot mutate plans or tasks.
- Require safe plan metadata only, with bounded strings and counts.
- Prohibit command execution, file writes, provider switching, patching, and PR
  automation.
- Add tests proving no REPLAN action is executed.
- Add tests proving no runtime output changes occur.
- Add review evidence showing how stale session state is handled.

## 17. Required Gates Before Real RETRY Execution

Before real RETRY execution:

- Complete dry-run RETRY implementation and review.
- Add explicit human approval or governance gate.
- Define retry budgets, rate limits, stop conditions, and evidence retention.
- Prove provider routing is not changed unintentionally.
- Prove retries cannot loop indefinitely.
- Add security and regression tests for no secret/payload leakage.
- Obtain manual approval through the established governance process.

## 18. Required Gates Before Real REPLAN Execution

Before real REPLAN execution:

- Complete dry-run REPLAN implementation and review.
- Add explicit human approval or governance gate.
- Define mutation boundaries and rollback behavior.
- Prove plan changes are bounded, explainable, and auditable.
- Prove no code, config, or runtime behavior changes occur without approval.
- Add tests for stale evidence, corrupt state, and degraded planning paths.

## 19. Required Gates Before SELF_REPAIR

Before SELF_REPAIR:

- Define a separate design and threat model.
- Require human approval before patches are applied.
- Require patch previews, tests, rollback plans, and safety evidence.
- Prohibit secret, environment, deploy, and CI credential changes.
- Prove no autonomous commit/push/PR happens.
- Prove failed repair degrades without cascading into provider switching or CI
  repair.

## 20. Required Gates Before Provider Switching

Before provider switching:

- Define a separate provider-routing design.
- Require explicit approval for any provider change.
- Define cost, safety, availability, and credential boundaries.
- Prove secrets and provider credentials are never surfaced.
- Prove advisory provider failure metadata cannot directly switch providers.
- Add tests for degraded provider state and no automatic switching.

## 21. Required Gates Before CI Repair

Before CI repair:

- Define a separate CI repair design and threat model.
- Keep CI diagnosis read-only until approved.
- Require bounded scope, explicit approval, and rollback behavior.
- Prohibit secret and CI settings mutation.
- Prove no autonomous rerun/fix/merge behavior occurs.
- Add tests for log redaction and failure degradation.

## 22. Required Gates Before Commit/Push/PR Automation

Before commit/push/PR automation:

- Define a separate repository automation governance model.
- Require explicit user approval for branch, staged files, commit message, push,
  and PR body.
- Prove unrelated files cannot be staged.
- Prove main is never pushed directly.
- Prove auto-merge remains disabled.
- Prove secrets, `.env`, deploy config, and CI secrets cannot be modified
  automatically.

## 23. Manual Merge Governance

Manual merge governance remains required.

Autonomy docs, evidence, dry-run outputs, cleanup results, and Cockpit
diagnostics do not approve merges. Misael or another authorized human must
review and merge PRs manually according to the repository governance process.

This review does not enable auto-merge and does not authorize direct pushes to
main.

## 24. Go/No-Go Checklist

| Gate | Result |
|------|--------|
| Advisory-only controller remains enforced | Go |
| Runtime output preservation remains required | Go |
| Provider routing unchanged | Go |
| Evidence payloads are metadata-only | Go |
| Session state persistence is SQLite opt-in | Go |
| Process-local fallback remains available | Go |
| Cleanup is explicit/manual only | Go |
| Dry-run cleanup deletes zero rows | Go |
| Cockpit autonomy surfaces are read-only | Go |
| Raw prompt/response/payload persistence remains forbidden | Go |
| Dry-run RETRY execution exists | No-go |
| Dry-run REPLAN execution exists | No-go |
| Real RETRY execution is approved | No-go |
| Real REPLAN execution is approved | No-go |
| SELF_REPAIR execution is approved | No-go |
| Provider switching is approved | No-go |
| CI repair is approved | No-go |
| Commit/push/PR automation is approved | No-go |

## 25. Final Recommendation

Approved only for dry-run planning work.

Not approved for autonomous execution.

The next phase may define and implement dry-run-only RETRY/REPLAN planning
contracts, provided the implementation cannot execute actions, cannot change
runtime output, cannot change provider routing, cannot persist raw payloads,
and remains clearly labeled as advisory dry-run metadata.
