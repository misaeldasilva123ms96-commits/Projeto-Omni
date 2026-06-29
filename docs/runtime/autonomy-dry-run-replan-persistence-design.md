# Autonomy Dry-Run Replan Persistence Design

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-replan-persistence-design`
**Base:** `main` after PR #446
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs a safe persistence layer for dry-run REPLAN plan
evidence. The proposed layer records sanitized audit metadata only, so
reviewers can inspect how a dry-run REPLAN plan was produced without exposing
prompts, rewritten prompts, responses, provider payloads, secrets, tool output,
or runtime internals.

Persistence must not execute REPLAN. Persistence must not rewrite prompts.
Persistence must not call a provider or model. Persistence must not change the
runtime response. Persistence must not change provider routing. Persistence
must not approve autonomous execution. Persistence is audit metadata only.

This document does not implement persistence or change runtime behavior.

**Contracts update:** `feature/autonomy-dry-run-replan-persistence-contracts`
adds a sanitized `DryRunReplanPlanEvidenceRecord`, forced event type
`dry_run_replan_plan_evidence`, allowlist-only serialization, bounded strings
and lists, MemoryFacade record/list contracts, and SQLite opt-in storage
contracts. Runtime persistence is not wired in this branch.

## 2. Current Status

The dry-run REPLAN stack currently includes:

- Design guidance for dry-run REPLAN planning.
- `DryRunReplanPlan` metadata contracts.
- `DryRunReplanPlanner` advisory planning.
- Runtime inspection metadata.
- Cockpit readonly display.
- Evidence interpretation notes.
- Governance review.

Governance status:

- Approved for documentation and readonly diagnostics.
- Approved for safe evidence persistence design after governance review.
- Not approved for prompt rewriting.
- Not approved for provider/model retry or replan execution.
- Not approved for autonomous execution.

## 3. Problem Statement

Dry-run REPLAN evidence is visible in Runtime Inspector and Cockpit, but there
is no persistence design that defines which fields may be recorded, where they
may be stored, how they must be sanitized, or how failures should degrade.

Without a design, future persistence work could accidentally store raw prompts,
rewritten prompts, provider payloads, stack traces, tool output, secrets, or
raw runtime objects. It could also be misread as an execution approval path.

Omni needs a persistence design that preserves auditability while keeping the
dry-run REPLAN stack advisory-only and metadata-only.

## 4. Goals

- Persist only sanitized dry-run REPLAN plan evidence metadata.
- Preserve JSONL as the safe default audit behavior.
- Preserve SQLite as an opt-in MemoryFacade-backed storage target.
- Define an explicit allowlist of fields.
- Define explicit forbidden fields.
- Define sanitization and bounding rules before persistence.
- Define best-effort failure behavior.
- Preserve runtime output exactly.
- Preserve provider routing exactly.
- Preserve the original prompt exactly.
- Avoid prompt rewriting, provider/model calls, tool execution, command
  execution, file writes, CI repair, Git automation, and PR automation.
- Keep evidence useful for governance review and Cockpit/audit inspection.

## 5. Non-Goals

- Do not implement persistence in this change.
- Do not execute REPLAN.
- Do not execute RETRY.
- Do not rewrite prompts.
- Do not generate rewritten prompts.
- Do not call a provider/model again.
- Do not change runtime output.
- Do not change provider routing.
- Do not execute tools or commands.
- Do not write runtime files or patch code.
- Do not repair CI.
- Do not commit, push, or open PRs from runtime behavior.
- Do not add a scheduler, background persistence loop, or automatic cleanup
  loop.
- Do not approve autonomous execution.
- Do not persist raw prompts, rewritten prompts, responses, receipts, provider
  payloads, tool output, stack traces, secrets, credentials, or file contents.

## 6. Persistence Definition

Dry-run REPLAN persistence means recording a sanitized representation of a
`DryRunReplanPlan` as audit metadata.

It is:

- Metadata-only.
- Advisory-only.
- Best-effort.
- Safe to omit when storage is unavailable.
- A record of dry-run planning evidence, not an execution record.

It is not:

- A prompt rewrite.
- A provider/model call.
- A retry or replan execution.
- A provider routing instruction.
- A runtime response modifier.
- An action queue.
- An autonomous execution approval.

## 7. What Persistence Must Never Store

Persistence must never store:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys, tokens, or secrets.
- Headers or cookies.
- Stack traces or tracebacks.
- stdout/stderr.
- Command args.
- File contents.
- `.env` content.
- Full tool outputs.
- Raw receipts.
- Raw exception objects.
- Raw Python `repr` of context objects.

If a field is not explicitly allowed, it must be treated as forbidden.

## 8. Allowed Fields

Only the following fields may be persisted:

- `plan_id`
- `plan_type`
- `advisory`
- `would_replan`
- `replan_reason`
- `blocked`
- `block_reasons`
- `replan_eligibility_score`
- `risk_level`
- `source_decision`
- `fingerprint_id`
- `stagnation_score`
- `progress_score`
- `repeated_strategy_count`
- `suggested_strategy`
- `evidence_summary`
- `created_at`
- `session_id`, only if already sanitized and bounded
- `request_id`, only if already sanitized and bounded
- `trace_id`, only if already sanitized and bounded

All allowed string fields must still pass sanitization and length bounding.
Allowed list fields must be bounded and contain only safe categorical strings.
Allowed numeric fields must be finite and within expected ranges.

## 9. Forbidden Fields

The persistence layer must reject or omit:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys, tokens, or secrets.
- Headers or cookies.
- Stack traces.
- Tracebacks.
- stdout/stderr.
- Command args.
- File contents.
- `.env` content.
- Full tool outputs.
- Raw receipts.
- Raw exception objects.
- Raw Python `repr` of context objects.

The persistence layer must also reject nested objects that could carry raw
context, such as request objects, provider response objects, exception objects,
receipt objects, tool result objects, or arbitrary serialized runtime state.

## 10. Sanitization and Bounding Rules

Future implementation should apply these rules before writing any evidence:

- Use an allowlist serializer, not a denylist scrubber.
- Drop unknown keys by default.
- Convert plan type, reason, risk, source decision, and suggested strategy to
  safe bounded strings.
- Bound `plan_id`, `fingerprint_id`, `session_id`, `request_id`, and `trace_id`.
- Bound `evidence_summary` to a small review-safe string.
- Bound `block_reasons` by item count and item length.
- Accept only booleans for `advisory`, `would_replan`, and `blocked`.
- Accept only finite numeric values for scores and counts.
- Normalize timestamps to safe ISO-8601 strings.
- Redact secret-like patterns before storage even for allowed fields.
- Reject or omit values that contain newline-heavy logs, tracebacks, shell
  syntax, path dumps, provider payload fragments, or environment assignments.
- Treat malformed evidence as degraded metadata rather than as a runtime error.

## 11. Storage Targets

The design allows two storage targets:

- JSONL audit mirror for sanitized event metadata.
- SQLite-backed normalized metadata through MemoryFacade when SQLite memory is
  explicitly enabled.

No storage target may receive raw prompts, rewritten prompts, responses,
provider payloads, raw receipts, tool output, file contents, secrets, or raw
runtime objects.

## 12. JSONL Behavior

JSONL remains the default audit path.

Proposed behavior:

- Emit a sanitized event record when dry-run REPLAN plan evidence is available
  and the existing audit path supports safe metadata.
- Use event type `dry_run_replan_plan_evidence`.
- Store only the allowed fields.
- Preserve append-only evidence semantics.
- Keep the runtime response unchanged.
- Degrade to no-op/debug metadata if JSONL writing fails.

JSONL default behavior must remain safe. A JSONL write failure must not fail
the user request, change provider routing, trigger retry/replan execution, or
surface raw errors to the user.

## 13. SQLite Behavior

SQLite persistence remains opt-in.

Proposed behavior:

- Write dry-run REPLAN evidence only when SQLite MemoryFacade storage is
  explicitly enabled and connected.
- Store normalized sanitized metadata, not raw plan/context objects.
- Preserve the same field allowlist used by JSONL.
- Degrade to no-op/debug metadata if SQLite is disabled, unavailable,
  corrupted, locked, or returns an error.
- Reads must degrade to empty results.
- Writes must be best-effort.

SQLite storage must not become a runtime execution dependency. Runtime output,
provider routing, prompt handling, and advisory-only mode must remain
unchanged if SQLite persistence is unavailable.

## 14. MemoryFacade Contract Proposal

Future MemoryFacade support should use optional methods with safe degradation:

- `record_dry_run_replan_plan_evidence(record)`
- `get_dry_run_replan_plan_evidence(plan_id)`
- `list_dry_run_replan_plan_evidence(limit, session_id=None)`
- `cleanup_expired_dry_run_replan_plan_evidence(now)`

Contract requirements:

- Accept only a sanitized record/model, not arbitrary dictionaries.
- Return success/failure metadata without raw exception details.
- Return `None` or empty lists on read failure.
- Return zero deleted rows on cleanup failure.
- Keep all methods best-effort.
- Avoid raising into runtime execution paths.
- Avoid returning raw SQLite rows.
- Avoid returning raw serialized JSON blobs that include unknown fields.

The contract should be optional so JSONL default behavior and process-local
runtime behavior remain unchanged.

## 15. Event Type Proposal

Suggested event type:

`dry_run_replan_plan_evidence`

The event represents sanitized audit metadata for a dry-run REPLAN plan. It
does not represent a prompt rewrite, provider/model call, retry execution,
replan execution, provider switch, tool execution, command execution, file
write, patch, CI repair, commit, push, PR, or autonomous action.

## 16. Evidence Lifecycle

Proposed lifecycle:

1. Runtime produces a dry-run REPLAN plan as advisory metadata.
2. The plan is converted through an allowlist serializer.
3. Sanitization and bounding are applied.
4. A sanitized `dry_run_replan_plan_evidence` event is built.
5. JSONL audit mirror may record the event.
6. SQLite MemoryFacade may record the event only when explicitly enabled.
7. Cockpit/audit views may read bounded metadata.
8. Retention cleanup may remove expired metadata later.

At no stage may persisted evidence be used to execute a replan or rewrite a
prompt.

## 17. Retention and Cleanup

Retention should be time-bounded.

Future implementation should define:

- Default TTL for dry-run REPLAN evidence.
- Optional retention override through safe configuration if the repository
  already supports it.
- Explicit/manual cleanup only unless a later governance review approves
  scheduling.
- Cleanup that deletes only expired dry-run REPLAN evidence metadata.
- Cleanup result metadata that reports counts only, not raw rows.

Cleanup must not delete non-expired records. Cleanup must not expose raw rows,
session dumps, prompts, rewritten prompts, responses, provider payloads,
receipts, tool output, file contents, or secrets.

## 18. Read/Query Behavior

Read/query behavior should be bounded and safe:

- Query by `plan_id` when a specific plan is needed.
- Query by sanitized `session_id` only if already approved and bounded.
- List with a strict limit.
- Sort by `created_at` descending by default.
- Return only allowed fields.
- Return empty results on failure.
- Avoid raw SQL row dumps or arbitrary JSON payload dumps.

Read results are for audit and diagnostics only. They must not be consumed as
runtime instructions.

## 19. Cockpit/Audit Usage

Cockpit and audit views may display persisted dry-run REPLAN evidence as
readonly metadata.

Permitted display fields match the allowed field list. The UI should continue
to reinforce:

- Dry-run REPLAN does not rewrite prompts.
- Dry-run REPLAN does not execute replan.
- `would_replan=true` is not permission.
- `blocked=false` is not permission.
- `suggested_strategy` is categorical metadata only.
- Persistence is audit metadata only.

No Cockpit control should use persisted evidence to execute REPLAN, RETRY,
SELF_REPAIR, SWITCH_PROVIDER, ABORT_SAFE, tool execution, command execution,
patching, CI repair, Git automation, or PR automation.

## 20. Failure/Degradation Behavior

Persistence failure must degrade safely:

- JSONL write failure: no-op/debug metadata only.
- SQLite disabled: no-op.
- SQLite unavailable: no-op/debug metadata only.
- SQLite read failure: empty result.
- SQLite write failure: no-op/debug metadata only.
- Corrupt persisted row: omit or return degraded safe metadata.
- Unknown fields: drop.
- Unsafe values: redact, bound, or omit.

Failures must not crash runtime, change the response string, change provider
routing, rewrite prompts, call providers/models, execute tools, or trigger
autonomous actions.

## 21. Security/Privacy Considerations

The persistence design is privacy-first and metadata-only.

Security requirements:

- Allowlist serialization before persistence.
- Redaction before writes.
- Bounded strings and bounded lists.
- No raw prompts or rewritten prompts.
- No raw responses or provider payloads.
- No secrets, tokens, API keys, credentials, headers, or cookies.
- No stack traces, tracebacks, stdout/stderr, command args, or tool output.
- No file contents or `.env` content.
- No raw exception objects.
- No raw Python `repr` of context objects.
- No raw database rows in APIs, logs, UI, or audit exports.

Persisted evidence should be treated as operational metadata. It is safer than
raw runtime payloads, but it may still reveal timing, risk categories, decision
categories, or workflow shape.

## 22. Testing Plan

Future implementation should add tests for:

- Model accepts all allowed fields.
- Model drops or rejects unknown fields.
- Forbidden fields are not persisted.
- Raw prompt, rewritten prompt, response, provider payload, secret, stack
  trace, stdout/stderr, command args, file contents, and raw receipts are
  redacted or omitted.
- String and list bounds are enforced.
- JSONL event contains only sanitized metadata.
- SQLite disabled produces safe no-op behavior.
- SQLite enabled writes sanitized metadata only.
- SQLite reads return bounded allowed fields only.
- Corrupt rows degrade to empty or safe degraded metadata.
- MemoryFacade failures do not raise into runtime.
- Runtime response remains unchanged.
- Provider routing remains unchanged.
- No prompt rewrite/provider call/replan execution occurs.
- Cockpit/audit display does not render forbidden fields.

## 23. Rollout Plan

Recommended rollout:

1. Review and merge this design.
2. Add sanitized model/contracts for dry-run REPLAN evidence.
3. Add JSONL event emission as best-effort metadata only.
4. Add SQLite MemoryFacade support behind explicit opt-in.
5. Add read/query tests and corruption tests.
6. Add Cockpit/audit read-only usage only after storage contracts are stable.
7. Add retention/cleanup support with explicit tests.
8. Run governance review before any execution design.

Each step should preserve advisory-only behavior and runtime output.

## 24. Known Risks

- Operators may treat persisted `would_replan=true` as permission.
- Operators may treat persisted `blocked=false` as permission.
- Persisted metadata may be misread as an execution record.
- `evidence_summary` could accidentally include raw content if not strictly
  sanitized and bounded.
- Future SQLite queries could expose raw rows if adapter boundaries are weak.
- Retention policy may be too long for operational metadata.
- JSONL and SQLite records could drift if schemas are not aligned.
- Debug logs could leak raw exception details if failure handling is careless.

## 25. Open Questions

- What default TTL should dry-run REPLAN evidence use?
- Should JSONL and SQLite use identical record shapes or should SQLite use a
  normalized schema with derived columns?
- Should `session_id`, `request_id`, and `trace_id` be persisted by default or
  only when already present in an approved sanitized context?
- Should `evidence_summary` be optional until stronger automated redaction
  tests exist?
- Should Cockpit read persisted evidence immediately or continue to prefer
  live runtime inspection until persistence is proven stable?
- Should cleanup share the autonomy session state cleanup entrypoint or use a
  separate evidence cleanup command?

## 26. Go/No-Go Checklist

Before implementation, all answers must be yes:

- Is the implementation metadata-only?
- Is every persisted field on the allowlist?
- Are unknown fields dropped?
- Are forbidden fields rejected, redacted, or omitted?
- Are strings and lists bounded?
- Does JSONL remain the safe default behavior?
- Does SQLite remain opt-in?
- Do reads degrade to empty results?
- Do writes degrade to no-op/debug metadata?
- Does persistence avoid prompt rewriting?
- Does persistence avoid provider/model calls?
- Does persistence avoid runtime response mutation?
- Does persistence avoid provider routing changes?
- Does persistence avoid tool, command, file, CI, Git, and PR automation?
- Does persisted evidence remain advisory-only?
- Does the implementation include tests for forbidden data and degradation?

No-go if any answer is no.

## 27. Final Recommendation

Proceed only with safe persistence contract design and review after this
document. The next implementation phase may add sanitized models/contracts and
tests for dry-run REPLAN plan evidence persistence, but it must remain
metadata-only and best-effort.

This design does not approve prompt rewriting, provider/model retry or replan
execution, provider switching, CI repair, self-repair, Git/PR automation, or
autonomous execution.
