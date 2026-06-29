# Autonomy Dry-Run Retry Persistence Governance Review

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-retry-persistence-governance-review`
**Base:** `main` after PR #452
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

This review defines governance requirements for future persisted dry-run
RETRY evidence before any RETRY persistence contracts or runtime opt-in wiring
are added.

The future RETRY persistence path may record sanitized audit metadata for
`dry_run_retry_plan_evidence` and expose readonly diagnostics through
`dry_run_retry_plan_persistence`, but only after the required controls in this
document are satisfied. The evidence must remain advisory-only, metadata-only,
allowlisted, bounded, best-effort, and separated from execution.

Governance conclusion:

- Approved for documentation.
- Approved for readonly diagnostics.
- Approved for future sanitized RETRY audit metadata persistence design.
- Approved for future RETRY persistence contracts only after this review.
- Approved for future RETRY runtime opt-in persistence only after contracts.
- Not approved for prompt rewriting.
- Not approved for provider/model retry execution.
- Not approved for automatic retry execution.
- Not approved for using persisted evidence as execution input.
- Not approved for autonomous execution.

## 2. Scope

This review covers governance requirements for future persisted dry-run RETRY
evidence.

It reviews:

- Current RETRY dry-run planning and readonly diagnostic evidence.
- The current RETRY persistence gap.
- Alignment with the persisted dry-run REPLAN evidence path.
- Alignment with the dry-run persistence consolidation design.
- Proposed RETRY event fields and diagnostic metadata.
- MemoryFacade, JSONL, and SQLite governance requirements.
- Redaction, privacy, auditability, operator interpretation, misuse, failure,
  degradation, and control requirements.

It does not implement persistence, add contracts, modify runtime behavior,
modify provider routing, rewrite prompts, execute RETRY, execute REPLAN, call
providers/models, change MemoryFacade, change SQLite, change Cockpit, or
approve autonomous execution.

## 3. Current RETRY Dry-Run Stack Inventory

The current dry-run RETRY stack includes:

- Dry-run RETRY planning design.
- `DryRunRetryPlan` contract.
- `DryRunRetryPlanner`.
- Metadata-only eligibility and blocking rules.
- Runtime inspection metadata at `autonomy_evaluation.dry_run_retry_plan`.
- Cockpit readonly diagnostics.
- Dry-run RETRY plan evidence interpretation notes.

The stack is advisory-only. It may explain whether a retry would be eligible
under safe metadata rules, but it must not perform a retry, repeat a model
call, change provider routing, change runtime output, execute tools, execute
commands, write files, repair CI, or automate Git/PR actions.

## 4. Current RETRY Persistence Gap

RETRY evidence is not yet governed as a persisted audit metadata stream.

Current gaps:

- No approved RETRY persistence governance review before this document.
- No approved `dry_run_retry_plan_evidence` persistence contract.
- No approved MemoryFacade record/list contract for RETRY evidence.
- No approved JSONL persistence event for RETRY evidence.
- No approved SQLite schema or table behavior for RETRY evidence.
- No approved runtime opt-in persistence wiring for RETRY evidence.
- No approved persistence diagnostic key for RETRY evidence.
- No approved retention or cleanup behavior for RETRY evidence.
- No approved Cockpit historical audit view for persisted RETRY evidence.

This gap must be closed through staged governance, contracts, tests, and
readonly diagnostics before any runtime wiring is added.

## 5. Relationship to REPLAN Persistence

The REPLAN persistence stack already includes a governance review, persistence
design, persistence contracts, runtime opt-in wiring, evidence notes, JSONL
default audit behavior, SQLite opt-in support, MemoryFacade record/list
contracts, and diagnostics at `dry_run_replan_plan_persistence`.

RETRY should follow the same safety posture:

- Sanitized metadata only.
- Allowlisted fields only.
- Best-effort writes.
- Safe read degradation.
- JSONL as the default audit mirror.
- SQLite as opt-in structured storage.
- MemoryFacade as the persistence boundary.
- Runtime output unchanged.
- Provider routing unchanged.
- No prompt rewriting.
- No provider/model calls.
- No execution path.

RETRY must not inherit REPLAN behavior by copy-paste if field semantics differ.
It needs its own retry-specific field review and tests.

## 6. Relationship to Dry-Run Persistence Consolidation

The dry-run persistence consolidation design defines a shared model for future
RETRY and existing REPLAN dry-run plan evidence.

This review adopts the consolidation direction for RETRY:

- Event type: `dry_run_retry_plan_evidence`.
- Diagnostic key: `dry_run_retry_plan_persistence`.
- Shared audit fields across RETRY and REPLAN.
- RETRY-specific fields for retry eligibility and strategy categories.
- JSONL default audit metadata.
- SQLite opt-in structured metadata.
- MemoryFacade as the only persistence boundary.
- Persisted evidence must never become execution input.

Consolidation is not implementation. This review approves governance direction
for RETRY persistence only; it does not change any runtime or storage code.

## 7. Proposed RETRY Evidence Event Governance

Future persisted RETRY evidence should use the forced event type:

`dry_run_retry_plan_evidence`

The event may describe sanitized metadata from a `DryRunRetryPlan`, including
whether RETRY would be eligible, why it is blocked or eligible, which safe
decision and fingerprint metadata informed the plan, and which retry-specific
score or strategy category was observed.

Required retry-specific governance fields:

- `would_retry`
- `retry_reason`
- `retry_eligibility_score`
- `suggested_retry_strategy`, or the project-conventional equivalent if an
  existing safe categorical name is selected before contracts are implemented

Required shared governance fields:

- `event_type`
- `plan_id`
- `plan_type`
- `advisory`
- `blocked`
- `block_reasons`
- `risk_level`
- `source_decision`
- `fingerprint_id`
- `progress_score`
- `stagnation_score`
- `evidence_summary`
- `created_at`
- `recorded_at`
- `session_id`, only if sanitized and bounded
- `request_id`, only if sanitized and bounded
- `trace_id`, only if sanitized and bounded

The event type must be forced by the record model or serializer. Callers must
not be able to supply arbitrary event types.

## 8. Proposed RETRY Diagnostic Metadata Governance

Future runtime diagnostics should use the key:

`dry_run_retry_plan_persistence`

Approved diagnostic fields:

- `attempted`
- `recorded`
- `degraded`
- `error_category`
- `event_type`
- `storage_mode`
- `sqlite_enabled`
- `recorded_at`

Diagnostics must be categorical, boolean, numeric, or safe timestamp metadata.
They must not expose raw exceptions, tracebacks, stack traces, file paths,
prompts, rewritten prompts, responses, provider payloads, tool output,
secrets, raw MemoryFacade reprs, raw database rows, raw JSONL lines, or raw
context reprs.

Warnings:

- `would_retry=true` is not retry execution.
- `recorded=true` would not be approval.
- `attempted=true` would not be execution.
- `blocked=false` is not approval.
- `retry_eligibility_score` is not permission.
- `suggested_retry_strategy` is not an instruction.
- Persisted evidence must never become execution input.
- Cockpit visibility is not operational authorization.
- JSONL/SQLite storage is audit metadata only.
- Omni remains advisory-only.

## 9. MemoryFacade Governance Review

MemoryFacade may become the future RETRY persistence boundary only after
contracts are approved.

Required MemoryFacade controls before RETRY contracts:

- Accept only a sanitized RETRY evidence record model.
- Force `event_type=dry_run_retry_plan_evidence` without caller override.
- Drop or reject unknown keys.
- Bound strings, lists, identifiers, scores, and timestamps.
- Store only allowlisted shared and retry-specific fields.
- Degrade write failures to safe diagnostics.
- Return safe bounded records for reads.
- Return empty results on read failure.
- Avoid raw object reprs, raw exceptions, raw rows, raw JSON blobs with unknown
  fields, storage paths, prompts, responses, provider payloads, command args,
  file contents, and secrets.

MemoryFacade must not become an executor, retry queue, provider routing input,
prompt rewrite source, action queue, CI repair input, or autonomous control
surface.

## 10. JSONL Governance Review

JSONL should remain the default audit mirror for future RETRY persistence.

Approved future JSONL behavior:

- Append sanitized `dry_run_retry_plan_evidence` metadata only.
- Use the shared field model and RETRY-specific field model.
- Degrade write failures without runtime impact.
- Store bounded metadata only.
- Preserve existing safe JSONL audit behavior.

JSONL must not store raw prompts, rewritten prompts, responses, provider
payloads, receipts, tool outputs, traces, command args, secrets, file
contents, `.env` content, raw exceptions, raw Python reprs, raw database rows,
or unknown nested runtime objects.

Raw JSONL lines must not be pasted into review unless they have been inspected
and redacted.

## 11. SQLite Governance Review

SQLite should remain opt-in for future RETRY evidence storage.

Approved future SQLite behavior:

- Store sanitized RETRY evidence only when SQLite memory is enabled.
- Preserve JSONL default audit behavior.
- Preserve runtime behavior when SQLite is disabled, unavailable, locked, or
  corrupt.
- Degrade read failures to empty results.
- Degrade write failures to safe diagnostics.
- Return safe records, not raw rows.

SQLite enabled/disabled must not change RETRY eligibility, runtime output,
provider routing, prompt handling, provider/model calls, or autonomy behavior.
SQLite is audit metadata storage only.

## 12. Redaction/Privacy Review

Persisted RETRY evidence must use allowlist serialization, not denylist
scrubbing.

Forbidden persisted or shared material:

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
- Raw Python reprs.
- Raw database rows.
- Raw JSONL lines if not reviewed/redacted.

Allowed evidence must remain bounded metadata: booleans, scores, counts, safe
categories, safe timestamps, sanitized identifiers, and sanitized summaries.

## 13. Auditability Review

Future RETRY persistence can improve auditability by recording whether
metadata-only retry evidence was attempted, recorded, degraded, and which
storage mode was involved.

Auditability requirements:

- Link persisted evidence to safe `plan_id` and `fingerprint_id` values.
- Include `created_at` and `recorded_at`.
- Include `event_type` and `plan_type`.
- Keep `evidence_summary` sanitized and bounded.
- Preserve storage diagnostics without raw error text.
- Make missing or degraded persistence visible as metadata.
- Ensure records can be reviewed without raw runtime material.

Audit evidence supports review only. It does not authorize retry execution.

## 14. Operator Interpretation Risks

Operator risks:

- Treating `would_retry=true` as a completed retry.
- Treating `recorded=true` as governance approval.
- Treating `attempted=true` as execution attempted.
- Treating `blocked=false` as approval.
- Treating `retry_eligibility_score` as permission.
- Treating `suggested_retry_strategy` as an instruction.
- Treating Cockpit visibility as operational authorization.
- Treating SQLite enabled as an autonomy mode.
- Treating persisted evidence as more current than runtime state.
- Pasting raw JSONL lines, database rows, prompts, payloads, logs, or traces
  into review.

Future evidence notes and UI labels must continue to state that no retry was
executed and Omni remains advisory-only.

## 15. Abuse/Misuse Cases

Abuse or misuse cases to block:

- Persisted RETRY evidence becomes execution input.
- A future executor reads `would_retry=true` and calls a provider/model again.
- A provider router reads persisted evidence and switches providers.
- A prompt builder reads persisted evidence and rewrites a prompt.
- A UI places a Retry button beside persisted evidence.
- A cleanup, replay, or export path treats evidence records as actions.
- A test fixture uses persisted evidence to simulate real provider/model
  retries.
- A reviewer pastes raw rows, raw JSONL lines, prompts, responses, provider
  payloads, tool outputs, or secrets.
- Future automation treats `blocked=false` as approval.

These cases require governance rejection, tests, and code review gates.

## 16. Failure Modes

Important failure modes:

- MemoryFacade unavailable.
- JSONL write failure.
- SQLite disabled.
- SQLite unavailable, locked, or corrupt.
- Invalid RETRY plan metadata.
- Missing `plan_id` or `event_type`.
- Redaction failure.
- Unknown field drift.
- Diagnostic field drift.
- Stale persisted evidence.
- Operator confusion about recorded or attempted status.

Expected behavior is safe degradation: no crash, no runtime response mutation,
no provider routing change, no prompt rewrite, no provider/model call, no tool
execution, and no retry execution.

## 17. Storage Degradation Requirements

Storage degradation is acceptable only when it is safe and visible as
metadata.

Required degradation behavior:

- Write failure returns safe diagnostics.
- Read failure returns empty results.
- Invalid records are rejected or omitted safely.
- Corrupt rows are skipped or degraded safely.
- Raw errors are not exposed.
- Runtime output is unchanged.
- Provider routing is unchanged.
- Prompt handling is unchanged.
- Autonomy remains advisory-only.

`degraded=true` is a persistence diagnostic. It must not trigger RETRY,
REPLAN, ABORT_SAFE, SELF_REPAIR, SWITCH_PROVIDER, CI repair, provider calls,
tool calls, command execution, file writes, commits, pushes, PRs, or autonomous
execution.

## 18. Required Controls Before RETRY Persistence Contracts

Before RETRY persistence contracts are implemented:

- Approve the `dry_run_retry_plan_evidence` event type.
- Approve the `dry_run_retry_plan_persistence` diagnostic key.
- Define exact shared and RETRY-specific fields.
- Decide whether `suggested_retry_strategy` or a project-conventional
  equivalent is the contract field.
- Define string, list, identifier, score, and timestamp bounds.
- Force event type in the record model or serializer.
- Drop or reject unknown fields.
- Add tests proving forbidden fields are not serialized.
- Add tests proving raw prompts, responses, provider payloads, secrets, rows,
  JSONL lines, exceptions, reprs, command args, stdout/stderr, and file
  contents are excluded.
- Confirm persisted evidence cannot be consumed by any execution path.

## 19. Required Controls Before RETRY Runtime Opt-In Wiring

Before runtime opt-in persistence wiring:

- Complete and test RETRY persistence contracts.
- Add MemoryFacade record/list behavior with safe degradation.
- Add JSONL default audit behavior.
- Add SQLite opt-in behavior, if approved by contracts.
- Ensure runtime output remains unchanged.
- Ensure provider routing remains unchanged.
- Ensure no prompt rewrite occurs.
- Ensure no provider/model call occurs.
- Ensure no RETRY or REPLAN execution occurs.
- Ensure persistence failures degrade to diagnostics only.
- Add tests proving `dry_run_retry_plan_persistence` is diagnostics only.
- Add tests proving persisted evidence is not read back into execution.

Runtime wiring may record sanitized evidence only after a dry-run RETRY plan
already exists. It must not create a retry executor.

## 20. Required Controls Before Cockpit Historical Audit View

Before any Cockpit historical audit view:

- Define readonly query limits.
- Define safe filters such as event type, blocked state, risk level, plan id,
  source decision, fingerprint id, and timestamp range.
- Use sanitized IDs only.
- Define empty and degraded states without raw storage errors.
- Render records as metadata only.
- Confirm no raw rows or raw JSONL lines are rendered.
- Confirm no prompts, responses, provider payloads, logs, traces, command
  args, tool outputs, file contents, or secrets are rendered.
- Confirm no Retry, provider switch, prompt rewrite, patch, CI repair, commit,
  push, PR, cleanup, or destructive control is added.
- Confirm Cockpit labels state no retry was executed.
- Add frontend tests for redaction and readonly behavior.

This review does not approve Cockpit historical audit implementation.

## 21. Required Controls Before Retention/Cleanup Implementation

Before retention or cleanup implementation:

- Create a retention/cleanup design.
- Define default retention windows.
- Define cleanup eligibility.
- Define explicit/manual cleanup invocation before any scheduler.
- Define dry-run cleanup counts and diagnostics.
- Delete only eligible expired sanitized RETRY audit metadata.
- Preserve unrelated memory records.
- Return safe counts and categories only.
- Do not expose raw rows, raw JSONL lines, storage paths, exceptions, or file
  paths.
- Add tests for expired/non-expired records, corruption, unavailable storage,
  and safe failure.

Cleanup must not affect autonomy decisions, runtime responses, prompt
handling, provider routing, or execution.

## 22. Required Controls Before Any Execution Design

Before any RETRY execution design:

- Complete a separate go/no-go governance review.
- Define explicit human approval gates.
- Define bounded authority, budgets, and stop conditions.
- Define provider/model call boundaries.
- Define runtime response guarantees.
- Define provider routing guarantees.
- Define prompt handling and prompt rewrite rules if prompt changes are
  proposed.
- Define protected file, secret, CI, security, and rollback gates.
- Prove persisted evidence is never the sole authority for execution.
- Prove persisted evidence is not directly consumed as executable input.
- Add tests proving no execution occurs without approval.

Persisted dry-run RETRY evidence is insufficient for execution design.

## 23. Required Controls Before Autonomous Execution

Before autonomous execution:

- Complete separate governance approval.
- Define operator approval, revocation, pause, and kill-switch controls.
- Define bounded action limits and budgets.
- Define provider routing controls.
- Define prompt rewrite controls.
- Define tool, command, file, CI, Git, PR, and deployment controls.
- Define audit, rollback, and incident response requirements.
- Prove secrets, prompts, responses, provider payloads, and raw logs remain
  protected.
- Pass security, runtime, persistence, and governance validation.

This review does not approve autonomous execution.

## 24. Explicit Non-Approval Statement

This review does not approve:

- Prompt rewriting.
- Provider/model retry execution.
- Automatic retry execution.
- Replan execution.
- Using persisted evidence as execution input.
- Provider switching.
- Self-repair.
- CI repair.
- Tool or command execution.
- File writes or runtime patches.
- Commit, push, merge, or PR automation.
- Retention/cleanup implementation.
- Cockpit historical audit implementation.
- Autonomous execution.

Omni remains advisory-only.

## 25. Open Risks

- Operators may overinterpret `would_retry=true` as execution approval.
- `recorded=true` may be mistaken for governance approval.
- `attempted=true` may be mistaken for retry execution.
- `blocked=false` may be mistaken for permission.
- `retry_eligibility_score` may be over-trusted.
- `suggested_retry_strategy` may be mistaken for an instruction.
- Future UI work may add action controls beside persisted evidence.
- Future contracts may allow schema drift from REPLAN.
- Stale evidence may be reviewed without enough runtime context.
- Raw JSONL lines or SQLite rows may be copied into review without redaction.

## 26. Open Questions

- Should `suggested_retry_strategy` be the final field name, or should an
  existing project-conventional equivalent be reused?
- Should RETRY and REPLAN evidence share one SQLite table or separate tables?
- What exact string and list bounds should apply to retry reason, block
  reasons, and evidence summary?
- Should `session_id`, `request_id`, and `trace_id` be omitted by default
  unless already present in sanitized context?
- What retention window should apply to persisted dry-run RETRY evidence?
- Should Cockpit historical audit views wait for both RETRY and REPLAN
  persistence to share a common query model?
- What review cadence should apply to persisted advisory evidence schemas?

## 27. Go/No-Go Table

| Area | Decision | Conditions |
|------|----------|------------|
| Documentation | Go | This review is documentation-only. |
| Readonly diagnostics | Go | Metadata-only; no execution controls. |
| Future sanitized RETRY audit metadata persistence design | Go | Must use allowlisted bounded fields and preserve advisory-only behavior. |
| `dry_run_retry_plan_evidence` event taxonomy | Go | Event type must be forced by the record model or serializer. |
| `dry_run_retry_plan_persistence` diagnostics | Go | Diagnostics only; no raw errors or execution state. |
| MemoryFacade RETRY contracts | Go after controls | Requires field bounds, forced event type, redaction tests, and safe degradation. |
| JSONL RETRY evidence | Go after contracts | Default audit metadata only; no raw material. |
| SQLite RETRY evidence | Go after contracts | Opt-in audit metadata only; no behavior change when enabled or disabled. |
| RETRY runtime opt-in persistence wiring | Go after contracts | Best-effort only; no runtime output, prompt, provider, or execution changes. |
| Cockpit historical audit view design | Go after persistence model | Readonly design only with query limits and redaction controls. |
| Cockpit historical audit view implementation | No-go for now | Requires separate branch, tests, and approval. |
| Retention/cleanup design | Go later | Requires separate design with safe TTL and diagnostics. |
| Retention/cleanup implementation | No-go for now | Requires separate branch, tests, and approval. |
| Prompt rewriting | No-go | Not approved. |
| Provider/model retry execution | No-go | Not approved. |
| Automatic retry execution | No-go | Not approved. |
| Persisted evidence as execution input | No-go | Explicitly forbidden. |
| Autonomous execution | No-go | Explicitly not approved. |

## 28. Final Recommendation

Proceed with this documentation-only RETRY persistence governance review.

Recommended next branch: a RETRY persistence contracts branch that implements
only sanitized record contracts, safe serializers, MemoryFacade boundaries,
JSONL/SQLite audit metadata shapes as approved, and tests proving no runtime
behavior changes.

Do not implement RETRY runtime persistence wiring until contracts are complete.
Do not implement Cockpit historical audit views until the query model,
redaction rules, and readonly UI controls are approved. Do not implement
retention/cleanup until a separate retention design is approved. Do not use
persisted RETRY evidence for prompt rewriting, provider/model retry execution,
automatic retry execution, provider routing, or autonomous execution.

Omni remains advisory-only. Persisted RETRY evidence, if implemented later, is
audit metadata only.
