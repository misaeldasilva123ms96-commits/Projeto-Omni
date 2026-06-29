# Autonomy Dry-Run Persistence Consolidation Design

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-persistence-consolidation-design`
**Base:** `main` after PR #451
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs a unified persistence model for dry-run autonomy
evidence across RETRY and REPLAN planning. The model consolidates event names,
shared fields, plan-specific fields, diagnostics, storage expectations, and
governance controls while keeping dry-run evidence strictly separated from
execution.

Consolidation is not execution. Persisted evidence is not permission.
`recorded=true` is not approval. `blocked=false` is not approval.
`would_retry=true` is not retry execution. `would_replan=true` is not replan
execution. Suggested strategy metadata is not an instruction. Cockpit
visibility is not operational authorization. JSONL and SQLite storage are
audit metadata only. Persisted evidence must never become execution input.
Omni remains advisory-only.

This document does not implement persistence, change runtime behavior, change
provider routing, rewrite prompts, change storage behavior, change
MemoryFacade, change SQLite, or change Cockpit.

## 2. Scope

This design covers a future consolidated persistence layer for dry-run autonomy
plan evidence:

- Dry-run RETRY plan evidence.
- Dry-run REPLAN plan evidence.
- Shared audit event taxonomy.
- Shared allowlisted metadata fields.
- Plan-specific allowlisted metadata fields.
- JSONL default audit behavior.
- SQLite opt-in audit behavior.
- MemoryFacade contract direction.
- Readonly audit and Cockpit implications.
- Retention, cleanup, degradation, and testing considerations.

It does not cover execution, prompt rewriting, provider/model calls, provider
routing changes, tool execution, command execution, file writes, CI repair,
Git automation, PR automation, autonomous patching, or autonomous execution
approval.

## 3. Current RETRY Stack Inventory

The dry-run RETRY stack includes:

- Dry-run RETRY planning design.
- `DryRunRetryPlan` contract.
- `DryRunRetryPlanner`.
- Metadata-only eligibility and blocking rules.
- Runtime inspection and Cockpit readonly diagnostics.
- Evidence interpretation notes.

Current RETRY evidence is visible as readonly diagnostics. It is not currently
part of the same persisted evidence path as REPLAN. Any future persistence
must keep RETRY advisory-only and must not trigger a second provider/model
call, provider switching, runtime response mutation, tool execution, command
execution, file writes, CI repair, Git automation, or PR automation.

## 4. Current REPLAN Stack Inventory

The dry-run REPLAN stack includes:

- Dry-run REPLAN planning design.
- `DryRunReplanPlan` contract.
- `DryRunReplanPlanner`.
- Runtime inspection metadata.
- Cockpit readonly display.
- Evidence interpretation notes.
- Governance review.
- Persistence design.
- Persistence contracts.
- Runtime opt-in persistence wiring.
- Persistence evidence notes.
- Persistence governance review.

Current REPLAN persistence status:

- Sanitized metadata only.
- Best-effort.
- JSONL default audit mirror.
- SQLite opt-in.
- MemoryFacade record/list contracts.
- Runtime diagnostic key: `dry_run_replan_plan_persistence`.
- Event type: `dry_run_replan_plan_evidence`.

REPLAN persistence is audit metadata only. It must not rewrite prompts, execute
REPLAN, execute RETRY, call providers/models, change runtime output, or change
provider routing.

## 5. Gap Analysis Between RETRY and REPLAN

RETRY and REPLAN share the same advisory dry-run safety posture, but their
persistence maturity is different.

Shared current capabilities:

- Plan contracts.
- Pure planners.
- Eligibility and blocking rules.
- Runtime inspection metadata.
- Cockpit readonly diagnostics.
- Evidence interpretation notes.
- Advisory-only status.

Current differences:

- REPLAN has governance review before persistence; RETRY does not yet have a
  persistence governance path.
- REPLAN has persistence design, contracts, runtime opt-in wiring, diagnostics,
  and evidence notes; RETRY does not yet have equivalent persistence.
- REPLAN has an established event type,
  `dry_run_replan_plan_evidence`; RETRY needs the matching
  `dry_run_retry_plan_evidence` event.
- REPLAN has a persistence diagnostic key,
  `dry_run_replan_plan_persistence`; RETRY needs the matching
  `dry_run_retry_plan_persistence` diagnostic key.

The consolidation design should prevent duplicate schema drift, inconsistent
diagnostics, and inconsistent operator interpretation between RETRY and
REPLAN.

## 6. Consolidation Goals

- Define one event taxonomy for dry-run autonomy plan evidence.
- Define one shared field model for common plan evidence.
- Define plan-specific field models for RETRY and REPLAN.
- Preserve JSONL as the default audit mirror.
- Preserve SQLite as opt-in structured storage.
- Preserve MemoryFacade as the persistence boundary.
- Require allowlist serialization for all persisted evidence.
- Keep all persistence best-effort.
- Degrade write failures to safe diagnostics.
- Degrade reads to empty results.
- Keep persisted evidence metadata-only and advisory-only.
- Preserve runtime output, prompt handling, provider routing, and action
  behavior exactly.
- Establish controls before implementation, historical audit UI, cleanup, or
  any future execution design.

## 7. Non-Goals

- Do not implement persistence in this design.
- Do not modify runtime code.
- Do not modify persistence code.
- Do not modify MemoryFacade code.
- Do not modify SQLite code.
- Do not modify frontend or Cockpit code.
- Do not execute RETRY.
- Do not execute REPLAN.
- Do not rewrite prompts.
- Do not call providers/models again.
- Do not change provider routing.
- Do not change runtime output.
- Do not execute tools or commands.
- Do not write runtime files.
- Do not repair CI.
- Do not enable provider switching or self-repair.
- Do not approve autonomous execution.

## 8. Unified Event Taxonomy

Future consolidated dry-run persistence should use these event types:

- `dry_run_retry_plan_evidence`
- `dry_run_replan_plan_evidence`

The event type must be forced by the record model or serializer. Callers must
not be allowed to supply arbitrary event types.

Event types are audit categories only. They must not map to executable action
handlers, job queues, retry queues, replan queues, provider routing commands,
or autonomous execution controls.

## 9. Retry Evidence Event Proposal

`dry_run_retry_plan_evidence` should represent sanitized metadata from a
`DryRunRetryPlan`.

The event may record whether RETRY would be considered under advisory rules,
why it was eligible or blocked, which safe decision and fingerprint evidence
informed the plan, and which retry-specific score or strategy category was
observed.

It must not record raw prompts, raw responses, provider payloads, receipts,
stack traces, stdout/stderr, command args, file contents, secrets, raw rows, or
raw JSONL lines.

It must not execute a retry, call a provider/model, change response strings,
change provider routing, execute tools, run commands, write files, patch code,
repair CI, commit, push, or open PRs.

## 10. Replan Evidence Event Proposal

`dry_run_replan_plan_evidence` should continue to represent sanitized metadata
from a `DryRunReplanPlan`.

The event may record whether REPLAN would be considered under advisory rules,
why it was eligible or blocked, which safe decision and fingerprint evidence
informed the plan, and which REPLAN-specific score or suggested strategy
category was observed.

It must not store prompts, rewritten prompts, generated prompt drafts,
responses, provider payloads, raw receipts, stack traces, stdout/stderr,
command args, file contents, secrets, raw rows, raw JSONL lines, raw exception
objects, or raw Python reprs.

It must not rewrite prompts, execute REPLAN, execute RETRY, call a
provider/model, change response strings, change provider routing, execute
tools, run commands, write files, patch code, repair CI, commit, push, or open
PRs.

## 11. Shared Field Model

The shared field model should apply to both RETRY and REPLAN evidence:

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

All shared fields must be metadata-only. Strings must be bounded and
sanitized. Lists must be bounded by item count and item length. Numeric values
must be finite and constrained to expected ranges. Timestamps must be safe
ISO-8601 strings or omitted.

Unknown keys must be dropped by default. If a field is not explicitly allowed,
it must be treated as forbidden.

## 12. Plan-Specific Field Model

RETRY-specific fields:

- `would_retry`
- `retry_reason`
- `retry_eligibility_score`
- `suggested_retry_strategy`, or the project-conventional equivalent if a
  different safe categorical name is already used

REPLAN-specific fields:

- `would_replan`
- `replan_reason`
- `replan_eligibility_score`
- `repeated_strategy_count`
- `suggested_strategy`

Plan-specific fields must remain categorical, numeric, boolean, or safe
timestamp metadata. Strategy fields must be categories only, not executable
instructions, prompt rewrites, commands, tool calls, provider routing hints, or
patch plans.

## 13. Shared Diagnostics Model

Future consolidated persistence diagnostics should use the same shape for
RETRY and REPLAN:

- `attempted`
- `recorded`
- `degraded`
- `error_category`
- `event_type`
- `storage_mode`
- `sqlite_enabled`
- `recorded_at`

Required diagnostic keys:

- `dry_run_retry_plan_persistence`
- `dry_run_replan_plan_persistence`

Diagnostics are audit storage metadata only. `attempted=true` does not mean
execution was attempted. `recorded=true` does not approve execution.
`degraded=true` means persistence degraded safely; it does not mean autonomy
failed. `storage_mode` must not be interpreted as autonomy mode.

## 14. JSONL Consolidation Design

JSONL should remain the default audit mirror.

Future JSONL consolidation should:

- Append sanitized `dry_run_retry_plan_evidence` events for RETRY.
- Continue appending sanitized `dry_run_replan_plan_evidence` events for
  REPLAN.
- Use the shared field model where possible.
- Include plan-specific fields only for the matching plan type.
- Avoid raw paths, raw rows, raw runtime objects, raw exceptions, raw prompts,
  raw responses, provider payloads, tool output, stdout/stderr, command args,
  or secrets.
- Degrade write failures to safe diagnostics or debug-only metadata.
- Never make JSONL writes user-visible runtime failures.

Raw JSONL lines must not be pasted into review unless reviewed and redacted.

## 15. SQLite Consolidation Design

SQLite should remain opt-in.

Future SQLite consolidation may use:

- One normalized dry-run plan evidence table with `event_type` and
  plan-specific nullable columns.
- Separate RETRY and REPLAN evidence tables if that better matches existing
  schema conventions.
- A shared safe JSON metadata column only if it is populated by an allowlist
  serializer and never stores unknown raw context.

The preferred direction is the least complex schema that preserves:

- Forced event type.
- Shared field indexing.
- Safe plan-specific fields.
- Efficient list/query by event type, plan id, created timestamp, recorded
  timestamp, blocked state, risk level, and storage mode.
- No raw rows returned to callers.

SQLite failures must degrade safely. SQLite enabled/disabled must not change
autonomy behavior.

## 16. MemoryFacade Consolidation Design

MemoryFacade should remain the persistence boundary.

Future contract options:

- Add `DryRunRetryPlanEvidenceRecord` and reuse existing
  `DryRunReplanPlanEvidenceRecord`.
- Add a shared base serializer for dry-run plan evidence.
- Add MemoryFacade methods that mirror the REPLAN pattern for RETRY.
- Optionally add generic list/query helpers by `event_type` only after
  governance approves the query shape.

Any MemoryFacade consolidation must:

- Accept allowlisted record models only.
- Drop or reject unknown keys.
- Return safe bounded records.
- Return empty results on read failures.
- Degrade writes to safe diagnostics.
- Avoid raw database rows, raw exceptions, raw object reprs, and raw JSON blobs
  with unknown fields.
- Never expose execution controls or action queues.

## 17. Cockpit Historical Audit View Implications

A future Cockpit historical audit view could show persisted dry-run RETRY and
REPLAN evidence side by side, but only as readonly metadata.

Safe view concepts:

- Filter by event type.
- Filter by blocked state.
- Filter by risk level.
- Show plan identifiers, scores, safe reason categories, timestamps, and
  storage diagnostics.
- Show clear labels that no retry or replan was executed.

The view must not include destructive controls, execution buttons, provider
switching controls, prompt rewrite controls, raw row dumps, raw JSONL lines,
raw prompts, raw responses, provider payloads, tool outputs, stack traces,
stdout/stderr, command args, secrets, or file contents.

## 18. Query/Filter Implications

Consolidated evidence should support only safe audit queries.

Candidate safe filters:

- `event_type`
- `plan_type`
- `plan_id`
- `blocked`
- `risk_level`
- `source_decision`
- `fingerprint_id`
- `created_at` range
- `recorded_at` range
- `storage_mode`

Query results must be bounded by limit. Sorting should use safe timestamps or
stable identifiers. Queries must never return raw rows, raw JSONL lines, raw
context objects, raw exceptions, prompts, responses, provider payloads, tool
output, command args, secrets, or file contents.

## 19. Retention/Cleanup Implications

Retention and cleanup should be designed separately before implementation.

Future retention policy should define:

- Default retention window.
- SQLite cleanup behavior.
- JSONL archival expectations.
- Manual cleanup hooks, if any.
- Dry-run cleanup behavior, if any.
- Safe diagnostics for cleanup attempts.
- Governance approval before destructive cleanup of evidence records.

Cleanup must never delete non-expired records. Cleanup must never execute
RETRY or REPLAN. Cleanup diagnostics must be metadata-only and must not expose
raw rows or storage paths.

## 20. Redaction/Privacy Rules

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
- Raw JSONL lines if not reviewed and redacted.

Required rules:

- Use allowlist serialization, not denylist scrubbing.
- Bound all strings and lists.
- Normalize categorical values.
- Omit unsafe or unknown fields.
- Store only finite numeric values.
- Store only safe timestamps.
- Keep identifiers bounded and sanitized.
- Never persist raw nested runtime objects.

## 21. Abuse/Misuse Cases

Operators or future code could misuse persisted evidence by treating it as
permission or execution input. The design must explicitly block that
interpretation.

Misuse cases:

- Treating `would_retry=true` as permission to retry.
- Treating `would_replan=true` as permission to replan.
- Treating `blocked=false` as approval.
- Treating `recorded=true` as governance approval.
- Treating `suggested_strategy` as an executable instruction.
- Treating Cockpit visibility as operational authorization.
- Feeding persisted evidence into an executor.
- Expanding evidence with raw logs, prompts, provider payloads, or tool output.
- Exposing raw SQLite rows or raw JSONL lines in review.

Controls must keep persisted evidence readonly, bounded, sanitized, and
separate from any action path.

## 22. Failure/Degradation Behavior

Persistence must be best-effort.

Required behavior:

- JSONL write failure degrades safely.
- SQLite unavailable degrades safely.
- MemoryFacade unavailable degrades safely.
- Invalid records are rejected or omitted safely.
- Reads degrade to empty results.
- Writes degrade to no-op diagnostics.
- Runtime output remains unchanged.
- Provider routing remains unchanged.
- Prompt handling remains unchanged.
- No fallback execution is triggered.

Failure diagnostics may include safe categories such as `memory_unavailable`,
`invalid_record`, `record_failed`, or `storage_unavailable`. Diagnostics must
not include raw exception text, stack traces, file paths, command args,
provider payloads, prompts, responses, secrets, raw rows, or raw reprs.

## 23. Testing Strategy

Future implementation should include tests for:

- RETRY evidence record accepts allowed fields.
- REPLAN evidence record continues accepting allowed fields.
- Unknown fields are dropped or rejected.
- Forbidden fields are not serialized.
- Strings and lists are bounded.
- Scores and counts are constrained.
- Event type is forced.
- JSONL default remains enabled and metadata-only.
- SQLite remains opt-in.
- MemoryFacade read failures return empty results.
- MemoryFacade write failures degrade safely.
- Diagnostics use the shared shape.
- `dry_run_retry_plan_persistence` is populated only as diagnostics.
- `dry_run_replan_plan_persistence` remains compatible.
- No runtime response mutation occurs.
- No provider/model calls occur.
- No prompt rewriting occurs.
- No tool, command, file, Git, CI, or PR operation occurs.
- Raw prompts, rewritten prompts, responses, provider payloads, secrets, raw
  rows, raw JSONL lines, and raw reprs are not persisted or rendered.

## 24. Rollout Plan

Recommended future rollout:

1. Complete this consolidation design.
2. Create a governance review for RETRY persistence parity.
3. Implement RETRY evidence contracts using the shared model.
4. Add MemoryFacade and SQLite support only behind existing opt-in storage
   behavior.
5. Add runtime best-effort RETRY persistence diagnostics without changing
   runtime output.
6. Add evidence notes for persisted RETRY evidence.
7. Review combined RETRY/REPLAN persistence governance.
8. Design historical Cockpit audit views only after governance approval.
9. Design retention and cleanup only after storage and audit query behavior are
   stable.

Each rollout step must remain advisory-only unless a future governance process
explicitly approves otherwise.

## 25. Required Controls Before Implementation

Before implementing consolidation:

- Approve the unified event taxonomy.
- Approve shared and plan-specific fields.
- Approve string/list/numeric bounds.
- Approve MemoryFacade method names and return shapes.
- Approve SQLite schema shape.
- Approve JSONL event shape.
- Approve degradation diagnostics.
- Confirm no runtime output changes.
- Confirm no provider routing changes.
- Confirm no prompt rewrite path.
- Confirm no execution path consumes persisted evidence.

## 26. Required Controls Before Cockpit Historical Audit

Before any Cockpit historical audit view:

- Define readonly query limits.
- Define safe filters.
- Define empty and degraded states.
- Define labels stating no retry or replan was executed.
- Confirm no destructive controls are added.
- Confirm no raw rows or raw JSONL lines are rendered.
- Confirm no `dangerouslySetInnerHTML` or equivalent unsafe rendering.
- Confirm redaction utilities handle all displayed strings.
- Confirm visibility is not presented as operational authorization.

## 27. Required Controls Before Retention/Cleanup

Before retention or cleanup:

- Define retention windows.
- Define cleanup eligibility.
- Define dry-run cleanup counts.
- Define explicit/manual cleanup invocation requirements.
- Define safe cleanup diagnostics.
- Confirm cleanup deletes only eligible expired audit records.
- Confirm cleanup never deletes unrelated memory records.
- Confirm cleanup never exposes raw rows.
- Confirm cleanup never triggers RETRY, REPLAN, provider calls, prompt
  rewriting, or runtime output changes.

## 28. Required Controls Before Execution Design

Before any execution design:

- Complete separate governance review.
- Define human approval requirements.
- Define runtime response guarantees.
- Define provider routing guarantees.
- Define protected file and secret gates.
- Define CI/security gates.
- Define audit requirements.
- Define rollback and kill-switch requirements.
- Prove persisted evidence is not used as executable input.
- Prove RETRY/REPLAN dry-run evidence remains readonly unless explicitly
  transformed by a separately approved execution design.

This consolidation design does not approve execution design.

## 29. Explicit Non-Approval Statement

This design is approved only as documentation for future persistence
consolidation.

It is not approval for:

- RETRY execution.
- REPLAN execution.
- Prompt rewriting.
- Provider/model calls.
- Provider switching.
- Runtime response mutation.
- Tool execution.
- Command execution.
- File writes.
- Patching.
- CI repair.
- Git automation.
- PR automation.
- Autonomous execution.
- Using persisted evidence as execution input.

Omni remains advisory-only.

## 30. Open Risks

- Operators may overinterpret persisted evidence as permission.
- RETRY and REPLAN schemas may drift if implemented separately.
- Historical audit views may accidentally expose too much context.
- Raw JSONL lines may be copied into review without redaction.
- SQLite schema changes may introduce query complexity or retention ambiguity.
- Strategy fields may be mistaken for executable instructions.
- `blocked=false` may be misread as approval.
- `recorded=true` may be misread as approval.

## 31. Open Questions

- Should RETRY and REPLAN use one shared SQLite table or separate tables?
- Should MemoryFacade expose generic dry-run evidence queries or plan-specific
  methods only?
- What exact string and list bounds should be shared across both plan types?
- Should `suggested_retry_strategy` be introduced or should an existing
  project-conventional field name be reused?
- What retention window should apply to persisted dry-run plan evidence?
- Should historical Cockpit audit views be designed before or after RETRY
  persistence parity?
- Should JSONL event shape exactly match SQLite records or include a smaller
  subset?

## 32. Go/No-Go Table

| Area | Status | Notes |
|------|--------|-------|
| Consolidation design | Go | Documentation-only design is safe for review. |
| Unified event taxonomy | Go | Uses `dry_run_retry_plan_evidence` and `dry_run_replan_plan_evidence`. |
| Shared field model | Go | Metadata-only and allowlisted. |
| RETRY persistence implementation | No-go | Requires separate contracts, tests, and governance. |
| REPLAN persistence changes | No-go | Existing behavior must remain unchanged by this design. |
| Cockpit historical audit implementation | No-go | Requires separate design and controls. |
| Retention/cleanup implementation | No-go | Requires separate design and controls. |
| Execution design | No-go | Requires separate governance and approval. |
| Autonomous execution | No-go | Explicitly not approved. |

## 33. Final Recommendation

Proceed only with documentation review of this consolidation design.

Recommended next phase: a RETRY persistence governance or contracts branch that
uses this shared model as guidance, while preserving advisory-only behavior,
JSONL default audit behavior, SQLite opt-in behavior, MemoryFacade safety,
runtime output preservation, prompt preservation, provider routing
preservation, and strict separation from execution.

Do not use this design to execute RETRY, execute REPLAN, rewrite prompts, call
providers/models, change runtime responses, change provider routing, expose
destructive Cockpit controls, or approve autonomous execution.
