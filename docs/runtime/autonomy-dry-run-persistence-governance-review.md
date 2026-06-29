# Autonomy Dry-Run Persistence Governance Review

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-persistence-governance-review`
**Base:** `main` after PR #458
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

The dry-run autonomy persistence stack is suitable for documentation, readonly
diagnostics, and sanitized audit metadata persistence across both RETRY and
REPLAN. Both plan types now have metadata-only evidence records, MemoryFacade
record/list contracts, JSONL default audit recording, SQLite opt-in storage,
runtime best-effort persistence wiring, and evidence interpretation notes.

Governance conclusions:

- Approved for documentation.
- Approved for readonly diagnostics.
- Approved for sanitized audit metadata persistence.
- Approved for future Cockpit historical audit view design.
- Approved for future retention/cleanup design.
- Not approved for prompt rewriting.
- Not approved for provider/model retry execution.
- Not approved for provider/model replan execution.
- Not approved for automatic retry execution.
- Not approved for automatic replan execution.
- Not approved for using persisted evidence as execution input.
- Not approved for autonomous execution.

Required warnings remain in force: `would_retry=true` is not retry execution.
`would_replan=true` is not replan execution. `recorded=true` is not approval.
`attempted=true` is not execution. `blocked=false` is not approval.
`retry_eligibility_score` and `replan_eligibility_score` are not permission.
`suggested_retry_strategy` and `suggested_strategy` are not instructions.
Cockpit visibility and JSONL/SQLite storage are not operational
authorization. Omni remains advisory-only.

## 2. Scope

This review covers the complete current dry-run persistence stack for RETRY
and REPLAN evidence.

It reviews:

- Runtime readonly plan metadata.
- Runtime best-effort persistence wiring.
- MemoryFacade evidence contracts.
- JSONL default audit recording.
- SQLite opt-in evidence storage.
- Persistence diagnostics.
- Evidence record safety.
- Cross-plan consistency.
- Operator and reviewer interpretation risks.
- Required controls before Cockpit historical audit views.
- Required controls before retention/cleanup.
- Required controls before any execution design or autonomous execution.

It does not implement code, modify runtime behavior, change provider routing,
rewrite prompts, call providers/models, execute RETRY or REPLAN, modify
MemoryFacade, modify SQLite, modify frontend/Cockpit, run CI repair, or
approve autonomous execution.

## 3. Current Stack Inventory

The current dry-run persistence stack includes both RETRY and REPLAN.

RETRY stack:

- Dry-run RETRY design.
- Dry-run RETRY contracts and planner.
- Runtime readonly inspection metadata.
- Cockpit readonly diagnostics.
- RETRY evidence notes.
- RETRY persistence governance review.
- Dry-run persistence consolidation design.
- `DryRunRetryPlanEvidenceRecord`.
- MemoryFacade record/list contracts.
- JSONL default audit recording.
- SQLite opt-in evidence storage.
- Runtime best-effort opt-in persistence wiring.
- RETRY persistence evidence notes.
- Runtime diagnostic key: `dry_run_retry_plan_persistence`.
- Event type: `dry_run_retry_plan_evidence`.

REPLAN stack:

- Dry-run REPLAN design.
- Dry-run REPLAN contracts and planner.
- Runtime readonly inspection metadata.
- Cockpit readonly diagnostics.
- REPLAN evidence notes.
- REPLAN governance review.
- REPLAN persistence design.
- `DryRunReplanPlanEvidenceRecord`.
- MemoryFacade record/list contracts.
- JSONL default audit recording.
- SQLite opt-in evidence storage.
- Runtime best-effort opt-in persistence wiring.
- REPLAN persistence evidence notes.
- REPLAN persistence governance review.
- Runtime diagnostic key: `dry_run_replan_plan_persistence`.
- Event type: `dry_run_replan_plan_evidence`.

## 4. RETRY Persistence Review

RETRY persistence records sanitized `DryRunRetryPlanEvidenceRecord` metadata
after runtime creates `autonomy_evaluation["dry_run_retry_plan"]`.

Approved RETRY behavior:

- Record metadata only.
- Use event type `dry_run_retry_plan_evidence`.
- Expose diagnostics at `dry_run_retry_plan_persistence`.
- Use MemoryFacade as the persistence boundary.
- Preserve JSONL as default audit recording.
- Preserve SQLite as opt-in storage.
- Degrade failures safely.
- Preserve runtime response, provider routing, and prompt handling.

Not approved:

- RETRY execution.
- Provider/model retry execution.
- Automatic retry execution.
- Treating `would_retry=true` as execution or approval.
- Treating `suggested_retry_strategy` as an instruction.
- Using persisted RETRY evidence as execution input.

## 5. REPLAN Persistence Review

REPLAN persistence records sanitized `DryRunReplanPlanEvidenceRecord` metadata
after runtime creates `autonomy_evaluation["dry_run_replan_plan"]`.

Approved REPLAN behavior:

- Record metadata only.
- Use event type `dry_run_replan_plan_evidence`.
- Expose diagnostics at `dry_run_replan_plan_persistence`.
- Use MemoryFacade as the persistence boundary.
- Preserve JSONL as default audit recording.
- Preserve SQLite as opt-in storage.
- Degrade failures safely.
- Preserve runtime response, provider routing, and prompt handling.

Not approved:

- Prompt rewriting.
- Rewritten prompt generation.
- REPLAN execution.
- Provider/model replan execution.
- Automatic replan execution.
- Treating `would_replan=true` as execution or approval.
- Treating `suggested_strategy` as an instruction.
- Using persisted REPLAN evidence as execution input.

## 6. Cross-Plan Consistency Review

RETRY and REPLAN are now aligned on the core governance model:

- Both are dry-run and advisory-only.
- Both produce readonly runtime inspection metadata.
- Both expose Cockpit readonly diagnostics.
- Both have sanitized evidence records.
- Both persist through MemoryFacade.
- Both write JSONL audit metadata by default when available.
- Both use SQLite only as opt-in evidence storage.
- Both expose safe persistence diagnostics.
- Both degrade failures without changing runtime output.
- Neither may feed an executor.

The required diagnostic keys are:

- `dry_run_retry_plan_persistence`
- `dry_run_replan_plan_persistence`

The required event types are:

- `dry_run_retry_plan_evidence`
- `dry_run_replan_plan_evidence`

## 7. Runtime Wiring Review

Runtime wiring is approved only as best-effort audit recording after dry-run
plan metadata exists.

Required runtime guarantees:

- No prompt rewrite.
- No provider/model call.
- No retry execution.
- No replan execution.
- No provider routing mutation.
- No runtime response mutation.
- No tool execution.
- No command execution.
- No file write.
- No CI repair.
- No provider switching.
- No self-repair.

Persistence failures must not crash runtime and must not become user-visible
runtime failures.

## 8. MemoryFacade Review

MemoryFacade is approved as the persistence boundary for sanitized dry-run
evidence.

Required MemoryFacade behavior:

- Accept only allowlisted record models.
- Sanitize and bound strings, lists, identifiers, scores, counts, and
  timestamps.
- Record JSONL default audit metadata when available.
- Record SQLite metadata only when SQLite is enabled and connected.
- Degrade writes safely.
- Return bounded records for list/read paths.
- Return empty results on read failure.
- Never expose raw rows, raw JSONL lines, raw exception objects, raw Python
  reprs, prompts, responses, provider payloads, command args, or secrets.

MemoryFacade must not become an execution dependency, action queue, retry
queue, replan queue, or provider routing input.

## 9. JSONL Review

JSONL is approved as the default audit recording path for sanitized dry-run
evidence.

Approved JSONL events:

- `dry_run_retry_plan_evidence`
- `dry_run_replan_plan_evidence`

JSONL storage is not operational authorization. Raw JSONL lines must not be
pasted into review unless reviewed and redacted. JSONL must not store raw
prompts, rewritten prompts, raw responses, provider payloads, stack traces,
stdout/stderr, command args, file contents, `.env` content, tool output,
receipts, secrets, raw exceptions, or raw object reprs.

## 10. SQLite Review

SQLite is approved only as opt-in structured audit storage for sanitized
evidence.

Approved SQLite behavior:

- Store sanitized RETRY evidence when SQLite memory is enabled.
- Store sanitized REPLAN evidence when SQLite memory is enabled.
- Preserve JSONL default behavior.
- Degrade write failures safely.
- Degrade read failures to empty results.
- Avoid raw row exposure.

SQLite enabled/disabled must not change autonomy behavior, provider routing,
prompt handling, response generation, or action execution.

## 11. Diagnostic Metadata Review

Approved diagnostic fields for both RETRY and REPLAN persistence:

- `attempted`
- `recorded`
- `degraded`
- `error_category`
- `event_type`
- `storage_mode`
- `sqlite_enabled`
- `recorded_at`

Diagnostics must be boolean, categorical, numeric, or safe timestamp metadata.
They must not include raw exceptions, tracebacks, stack traces, file paths,
prompts, rewritten prompts, responses, provider payloads, tool output,
secrets, raw MemoryFacade reprs, raw context reprs, or database rows.

## 12. Evidence Record Review

Evidence records are approved as sanitized audit metadata only.

Shared expectations:

- Forced event type.
- Advisory flag.
- Bounded plan ID.
- Bounded plan type.
- Safe blocked flag and block reason categories.
- Safe risk level and source decision.
- Bounded fingerprint ID.
- Safe progress and stagnation scores.
- Bounded evidence summary.
- Safe timestamps.
- Sanitized session, request, and trace IDs if present.

Plan-specific fields remain metadata:

- RETRY: `would_retry`, `retry_reason`, `retry_eligibility_score`,
  `suggested_retry_strategy`.
- REPLAN: `would_replan`, `replan_reason`, `replan_eligibility_score`,
  `suggested_strategy`.

Strategy fields are categories only, not executable instructions.

## 13. Redaction/Privacy Review

Persisted dry-run evidence must never include:

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
- Screenshots exposing secrets or raw payloads.

All serialization must be allowlist-first. Unknown keys must be dropped or
rejected.

## 14. Auditability Review

The current stack provides useful auditability without approving execution.

Auditable signals:

- Plan IDs.
- Event types.
- Plan types.
- Advisory flags.
- Blocked flags.
- Safe block categories.
- Safe risk levels.
- Safe source decisions.
- Fingerprint IDs.
- Progress and stagnation scores.
- Bounded evidence summaries.
- Persistence diagnostics.
- JSONL/SQLite storage modes.
- Safe timestamps.

Auditability is readonly. It must not become operational authorization.

## 15. Operator Interpretation Risks

Operators may misinterpret:

- `would_retry=true` as retry execution.
- `would_replan=true` as replan execution.
- `recorded=true` as approval.
- `attempted=true` as execution.
- `blocked=false` as approval.
- `storage_mode=sqlite` as an autonomy mode.
- Cockpit visibility as operational authorization.

Runbooks, evidence notes, and UI labels must keep these warnings visible.

## 16. Reviewer Interpretation Risks

Reviewers may misinterpret:

- Scores as permission.
- Suggested strategy categories as instructions.
- JSONL/SQLite presence as approval.
- Raw storage rows as safe review evidence.
- Missing evidence as evidence that no plan existed.
- Degraded persistence as autonomy failure.

Reviews must distinguish planning, persistence, diagnostics, and execution.

## 17. Abuse/Misuse Cases

Misuse cases include:

- Feeding persisted evidence into an executor.
- Treating persisted evidence as a retry/replan queue.
- Treating `blocked=false` as authorization.
- Treating scores as approval.
- Treating suggested strategies as instructions.
- Exposing raw SQLite rows or JSONL lines.
- Expanding evidence with raw prompts, responses, provider payloads, logs,
  command args, file contents, or secrets.
- Adding Cockpit destructive controls without governance.

All are explicitly not approved.

## 18. Failure/Degradation Behavior

Approved degradation behavior:

- Missing plan returns no-attempt diagnostics.
- Missing MemoryFacade degrades safely.
- Invalid records degrade safely.
- Write failure degrades safely.
- Read failure returns empty results.
- JSONL failure does not crash runtime.
- SQLite failure does not crash runtime.
- Diagnostics use safe categories such as `memory_unavailable`,
  `invalid_plan`, or `record_failed`.

Failures must not change runtime response, provider routing, prompt handling,
or action behavior.

## 19. Storage-Mode Consistency

Storage mode is audit metadata only.

Governance requirements:

- JSONL remains default.
- SQLite remains opt-in.
- SQLite enabled/disabled does not change autonomy behavior.
- `storage_mode` must be safe and categorical.
- `sqlite_enabled` must be boolean.
- Storage diagnostics must not include paths, raw exceptions, rows, prompts,
  responses, provider payloads, command args, or secrets.

## 20. Query/Filter Implications

Future query/filter behavior may be designed for audit views only.

Safe candidate filters:

- Event type.
- Plan type.
- Plan ID.
- Blocked flag.
- Risk level.
- Source decision.
- Fingerprint ID.
- Created/recorded timestamp range.
- Storage mode.

Queries must be bounded, readonly, and sanitized. They must not expose raw
rows, raw JSONL lines, raw context objects, prompts, responses, provider
payloads, logs, command args, file contents, or secrets.

## 21. Cockpit Historical Audit View Readiness

The stack is approved for future Cockpit historical audit view design, but not
implementation yet.

Readiness strengths:

- Stable event types.
- Shared diagnostic shape.
- Metadata-only evidence records.
- Existing readonly Cockpit patterns.
- Existing evidence interpretation notes.

Implementation is not yet approved because it needs explicit UI allowlists,
query limits, degraded states, security review, and no destructive controls.

## 22. Retention/Cleanup Readiness

The stack is approved for future retention/cleanup design, but not
implementation yet.

Design must define:

- Retention window.
- Eligible records.
- Dry-run cleanup counts.
- Explicit/manual cleanup behavior if needed.
- Safe cleanup diagnostics.
- JSONL archival expectations.
- SQLite deletion boundaries.

Cleanup must not delete unrelated memory records and must not expose raw rows.

## 23. Execution-Design Readiness

The stack is not approved for execution design beyond future governance
analysis.

Before execution design, Omni must prove:

- Persisted evidence is not execution input.
- Human approval gates are defined.
- Secret/protected-file gates are defined.
- Runtime output guarantees are defined.
- Provider routing guarantees are defined.
- CI/security gates are defined.
- Audit and rollback controls are defined.

No current persistence artifact may be used as an executor contract.

## 24. Autonomous-Execution Readiness

Omni is not approved for autonomous execution.

Current dry-run persistence evidence supports review only. It does not approve
automatic retry execution, automatic replan execution, prompt rewriting,
provider/model calls, provider switching, self-repair, CI repair, file writes,
patching, commits, pushes, PRs, or autonomous operations.

## 25. Required Controls Before Cockpit Historical Audit View

Before a Cockpit historical audit view:

- Approve readonly query APIs.
- Approve result limits.
- Approve displayed fields.
- Approve redaction paths.
- Define empty and degraded states.
- Label all views as readonly audit metadata.
- Show that no retry or replan was executed.
- Exclude raw rows and raw JSONL lines.
- Exclude prompts, responses, payloads, logs, command args, file contents, and
  secrets.
- Prohibit destructive controls.

## 26. Required Controls Before Retention/Cleanup

Before retention or cleanup implementation:

- Approve retention policy.
- Approve cleanup eligibility.
- Approve dry-run cleanup mode.
- Approve manual or governed invocation path.
- Approve diagnostics.
- Prove only eligible expired audit records are deleted.
- Prove unrelated memory records are not deleted.
- Prove cleanup does not trigger execution.
- Prove cleanup does not expose raw rows or raw JSONL lines.

## 27. Required Controls Before Execution Design

Before any execution design:

- Complete separate governance review.
- Define human approvals.
- Define safety gates.
- Define protected-file gates.
- Define secret detection gates.
- Define provider routing constraints.
- Define runtime response constraints.
- Define audit/evidence requirements.
- Define rollback and kill-switch behavior.
- Prove persisted evidence is never consumed directly as execution input.

## 28. Required Controls Before Autonomous Execution

Before autonomous execution:

- Complete execution design.
- Complete security review.
- Complete privacy review.
- Complete operational review.
- Complete CI/security gate review.
- Complete Cockpit authorization review.
- Define explicit user approval and revocation.
- Define bounded authority.
- Define monitoring and audit trails.
- Define rollback and emergency stop.
- Obtain explicit governance approval.

No current dry-run persistence work satisfies these controls.

## 29. Explicit Non-Approval Statement

This review does not approve:

- Prompt rewriting.
- Provider/model retry execution.
- Provider/model replan execution.
- Automatic retry execution.
- Automatic replan execution.
- Provider switching.
- Self-repair.
- CI repair.
- Tool execution.
- Command execution.
- File writes.
- Patching.
- Commit, push, or PR automation.
- Using persisted evidence as execution input.
- Autonomous execution.

Approved scope is documentation, readonly diagnostics, and sanitized audit
metadata persistence only.

## 30. Open Risks

- Operators may overinterpret persisted evidence as permission.
- Reviewers may paste raw JSONL or SQLite rows.
- Future audit views may accidentally expose raw context.
- Storage-mode metadata may be mistaken for autonomy mode.
- Suggested strategy categories may be mistaken for instructions.
- Degraded persistence may be mistaken for autonomy failure.
- Future execution work may attempt to reuse persisted evidence directly.

## 31. Open Questions

- Should RETRY and REPLAN share one historical audit view or separate views?
- Should query APIs be plan-specific or event-type based?
- What retention window should apply to dry-run evidence?
- Should cleanup be shared with other memory cleanup hooks?
- Should strategy fields become strict enums before broader views?
- Should JSONL audit lines have a separate redacted export command for review?

## 32. Go/No-Go Table

| Area | Decision | Notes |
|------|----------|-------|
| Documentation | Go | Approved. |
| Runtime readonly diagnostics | Go | Approved as metadata only. |
| Sanitized RETRY evidence persistence | Go | Approved as audit metadata only. |
| Sanitized REPLAN evidence persistence | Go | Approved as audit metadata only. |
| JSONL audit recording | Go | Approved as default sanitized audit path. |
| SQLite opt-in evidence storage | Go | Approved as opt-in sanitized audit storage. |
| Cockpit historical audit view design | Go | Approved for design only. |
| Cockpit historical audit view implementation | No-go | Requires separate controls and review. |
| Retention/cleanup design | Go | Approved for design only. |
| Retention/cleanup implementation | No-go | Requires separate controls and review. |
| Prompt rewrite | No-go | Not approved. |
| Provider/model retry execution | No-go | Not approved. |
| Provider/model replan execution | No-go | Not approved. |
| Automatic retry execution | No-go | Not approved. |
| Automatic replan execution | No-go | Not approved. |
| Persisted evidence as execution input | No-go | Explicitly forbidden. |
| Autonomous execution | No-go | Not approved. |

## 33. Final Recommendation

The dry-run persistence stack is approved for continued documentation,
readonly diagnostics, and sanitized audit metadata persistence across RETRY and
REPLAN.

The next safe phase may design Cockpit historical audit views or
retention/cleanup behavior, but implementation must wait for explicit controls
and separate review. Any execution design requires a separate governance
process and must prove persisted evidence cannot become execution input.

Final governance position: Omni remains advisory-only and is not approved for
autonomous execution.
