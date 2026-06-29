# Autonomy Dry-Run Replan Persistence Governance Review

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-replan-persistence-governance-review`
**Base:** `main` after PR #450
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

The persisted dry-run REPLAN evidence stack is suitable for documentation,
readonly diagnostics, and sanitized audit metadata persistence. It records
safe dry-run plan evidence through MemoryFacade after runtime creates
`autonomy_evaluation.dry_run_replan_plan`, while preserving advisory-only
behavior, JSONL default audit recording, SQLite opt-in storage, and
best-effort degradation.

This review does not approve prompt rewriting, provider/model retry,
provider/model replan execution, using persisted evidence as execution input,
or autonomous execution.

Governance conclusion:

- Approved for documentation.
- Approved for readonly diagnostics.
- Approved for sanitized audit metadata persistence.
- Approved for future readonly Cockpit historical audit view design.
- Approved for future dry-run persistence governance consolidation.
- Not approved for prompt rewriting.
- Not approved for provider/model retry or replan execution.
- Not approved for using persisted evidence as execution input.
- Not approved for autonomous execution.

## 2. Scope

This review covers persisted dry-run REPLAN evidence after runtime opt-in
persistence wiring and evidence notes.

It reviews:

- Runtime wiring governance boundaries.
- MemoryFacade recording and listing boundaries.
- JSONL default audit behavior.
- SQLite opt-in evidence storage.
- Persistence diagnostics.
- Evidence lifecycle.
- Redaction, privacy, auditability, and operator interpretation risks.
- Required controls before future audit views, persistence consolidation,
  retention/cleanup, execution design, or autonomous execution.

It does not implement code, modify runtime behavior, modify provider routing,
rewrite prompts, execute actions, change persistence code, change MemoryFacade
code, change SQLite code, change frontend/Cockpit code, or approve autonomous
execution.

## 3. Current Persisted REPLAN Evidence Stack Inventory

The current stack includes:

- Dry-run REPLAN plan design.
- `DryRunReplanPlan` model.
- `DryRunReplanPlanner`.
- Runtime inspection metadata at `autonomy_evaluation.dry_run_replan_plan`.
- Cockpit readonly display.
- Dry-run REPLAN plan evidence interpretation notes.
- Governance review before persistence.
- Persistence design.
- `DryRunReplanPlanEvidenceRecord`.
- MemoryFacade record/list contracts.
- JSONL default audit recording.
- SQLite opt-in support.
- SQLite schema/table support for sanitized evidence.
- Runtime best-effort persistence wiring.
- Persistence diagnostics at `dry_run_replan_plan_persistence`.
- Persistence evidence notes.

The stack is metadata-only and advisory-only. It is not an execution surface.

## 4. Runtime Wiring Governance Review

Runtime wiring records sanitized evidence only after
`dry_run_replan_plan` is already created. The wiring is best-effort and must
not affect response construction, prompt construction, provider routing, or
action execution.

Runtime guarantees:

- No prompt rewrite.
- No rewritten prompt generation.
- No provider/model call.
- No retry execution.
- No replan execution.
- No provider routing mutation.
- No runtime response mutation.
- No tool or command execution.
- No autonomous behavior patching.
- No CI repair.
- No provider switching or self-repair.

The persistence result may be exposed as diagnostics only. It must never be
consumed by an executor.

## 5. MemoryFacade Governance Review

MemoryFacade support is approved only as a safe audit metadata boundary.

Required MemoryFacade controls:

- Accept sanitized `DryRunReplanPlanEvidenceRecord` data only.
- Use allowlisted fields only.
- Bound strings, lists, scores, and identifiers.
- Degrade writes without raising into runtime.
- Return safe bounded records for reads.
- Return empty results on read failure.
- Avoid raw object reprs, raw rows, raw JSON blobs with unknown fields, raw
  exceptions, or storage paths in returned data.

MemoryFacade must not become an execution dependency or action queue.

## 6. JSONL Governance Review

JSONL remains the default audit mirror.

Approved JSONL behavior:

- Append sanitized `dry_run_replan_plan_evidence` metadata.
- Preserve existing safe default audit behavior.
- Degrade write failures without runtime impact.
- Store metadata only.

JSONL must not store raw prompts, rewritten prompts, responses, provider
payloads, receipts, tool outputs, traces, command args, secrets, file
contents, `.env` content, raw exceptions, or raw Python reprs.

Raw JSONL lines must not be pasted into review unless they have been inspected
and confirmed safe.

## 7. SQLite Governance Review

SQLite remains opt-in.

Approved SQLite behavior:

- Store sanitized dry-run REPLAN evidence through MemoryFacade only when
  SQLite memory is enabled.
- Preserve JSONL default behavior.
- Preserve process/runtime behavior when SQLite is disabled or unavailable.
- Degrade read failures to empty results.
- Degrade write failures to no-op diagnostics.

SQLite enabled/disabled must not change autonomy behavior. It is audit storage
metadata only.

## 8. Diagnostic Metadata Governance Review

Approved diagnostic fields:

- `attempted`
- `recorded`
- `degraded`
- `error_category`
- `event_type`
- `storage_mode`
- `sqlite_enabled`
- `recorded_at`

Diagnostics must be categorical, boolean, numeric, or safe timestamp values.
They must not include raw exceptions, tracebacks, stack traces, file paths,
prompts, rewritten prompts, responses, provider payloads, tool output,
secrets, raw MemoryFacade reprs, or raw context reprs.

Warnings:

- `recorded=true` is not permission.
- `attempted=true` is not execution.
- `degraded=true` is not autonomy failure.
- `storage_mode` is audit storage metadata only.

## 9. Evidence Lifecycle Governance Review

Approved lifecycle:

1. Runtime creates `dry_run_replan_plan`.
2. Runtime builds `DryRunReplanPlanEvidenceRecord` from safe plan metadata.
3. MemoryFacade records evidence best-effort.
4. JSONL records sanitized metadata by default when available.
5. SQLite records sanitized metadata only when opt-in storage is enabled.
6. Runtime exposes safe persistence diagnostics.
7. Operators review the evidence as readonly audit metadata.

No lifecycle step may trigger prompt rewriting, provider/model calls, retry,
replan, provider switching, self-repair, CI repair, command execution, file
writes, commits, pushes, PRs, or autonomous execution.

## 10. Redaction/Privacy Review

Persisted evidence must remain allowlisted and sanitized.

Forbidden material:

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
- Raw JSONL lines unless reviewed and redacted.

Allowed evidence must remain bounded metadata: booleans, scores, counts,
timestamps, IDs, safe categories, and sanitized summaries.

## 11. Auditability Review

The current stack improves auditability by linking dry-run plan metadata with
safe persistence diagnostics. Reviewers can determine whether evidence was
attempted, recorded, degraded, and which storage mode was involved.

Auditability limits:

- Persisted evidence may be stale.
- Persisted evidence may not include all runtime context.
- `evidence_summary` is a summary, not raw evidence.
- JSONL and SQLite records must be correlated carefully.
- Missing persistence does not mean missing autonomy evaluation.

Audit evidence supports review only. It does not authorize action.

## 12. Operator Interpretation Risks

Operator risks:

- Treating `recorded=true` as permission.
- Treating `attempted=true` as execution.
- Treating `degraded=true` as autonomy failure.
- Treating `would_replan=true` as approval.
- Treating `blocked=false` as approval.
- Treating `suggested_strategy` as an instruction.
- Treating Cockpit visibility as operational authorization.
- Treating SQLite enabled as an autonomy mode.
- Pasting raw JSONL lines, database rows, prompts, payloads, or logs into
  review.

Evidence notes mitigate these risks, but future UI and docs must continue to
make the non-execution boundary explicit.

## 13. Abuse/Misuse Cases

Abuse or misuse cases to block:

- Persisted evidence becomes execution input.
- A future executor reads `would_replan=true` and rewrites a prompt.
- A future provider router reads persisted evidence and changes routing.
- A UI adds a destructive REPLAN button beside persisted evidence.
- A cleanup or replay path treats JSONL/SQLite records as actions.
- A reviewer pastes raw database rows or JSONL lines with sensitive data.
- A future automation treats `blocked=false` as approval.
- A test fixture uses persisted evidence to simulate provider/model calls.

These cases require governance rejection, tests, and code review gates.

## 14. Failure Modes

Important failure modes:

- MemoryFacade unavailable.
- JSONL write failure.
- SQLite disabled.
- SQLite unavailable or locked.
- SQLite corrupt row.
- Invalid plan metadata.
- Redaction failure.
- Diagnostic field drift.
- Evidence stale relative to current runtime state.
- Operator confusion about storage mode or recorded status.

Expected behavior is safe degradation: no crash, no response mutation, no
provider routing change, no prompt rewrite, no action execution.

## 15. Storage Degradation Review

Storage degradation is acceptable only when it remains safe and visible as
metadata.

Required degradation behavior:

- Write failure returns safe diagnostics.
- Read failure returns empty results.
- Corrupt rows are skipped or degraded safely.
- Raw errors are not exposed.
- Runtime response is unchanged.
- Provider routing is unchanged.
- Autonomy remains advisory-only.

`degraded=true` is a persistence diagnostic. It is not autonomy failure and
must not trigger RETRY, REPLAN, ABORT_SAFE, SELF_REPAIR, or SWITCH_PROVIDER.

## 16. Required Controls Before Cockpit Historical Audit View

Before designing or implementing a readonly Cockpit historical audit view:

- Define safe query limits.
- Define time/session filters using sanitized IDs only.
- Define empty/error states that do not expose raw storage errors.
- Confirm no raw rows or raw JSONL lines are rendered.
- Confirm no destructive or execution controls are added.
- Confirm no `dangerouslySetInnerHTML` or unsafe HTML rendering.
- Add frontend tests for redaction and missing data.
- Add governance language that Cockpit visibility is not authorization.

This review approves future readonly Cockpit historical audit view design, not
implementation.

## 17. Required Controls Before Broader Dry-Run Persistence Consolidation

Before consolidating dry-run persistence across RETRY, REPLAN, cleanup, or
other advisory artifacts:

- Define a shared event taxonomy.
- Define common allowlist/forbidden-field rules.
- Define shared diagnostics with bounded categories.
- Define consistent JSONL and SQLite behavior.
- Define storage degradation semantics.
- Define shared evidence-note guidance.
- Confirm no persisted dry-run artifact can become execution input.
- Add cross-artifact tests for redaction and no runtime mutation.

This review approves future governance consolidation design, not execution.

## 18. Required Controls Before Retention/Cleanup Implementation

Before retention or cleanup implementation:

- Create a retention/cleanup design.
- Define TTL defaults.
- Define explicit/manual cleanup behavior first.
- Define dry-run cleanup behavior if deletion is introduced.
- Delete only expired sanitized audit metadata.
- Return counts and safe diagnostics only.
- Do not expose raw rows.
- Do not add uncontrolled schedulers.
- Add tests for expired/non-expired records, corruption, and failures.

Cleanup must not affect autonomy decisions or runtime responses.

## 19. Required Controls Before Any Execution Design

Before any execution design:

- Complete a separate go/no-go review.
- Prove persisted evidence is never the sole authority for execution.
- Define explicit human approval gates.
- Define prompt rewrite safety if prompt rewriting is proposed.
- Define provider/model call boundaries if calls are proposed.
- Define rollback and audit requirements.
- Add tests proving no execution occurs without approval.
- Review redaction, privacy, and operator-risk impacts.

Persisted evidence alone is insufficient for execution design.

## 20. Required Controls Before Autonomous Execution

Before autonomous execution:

- Complete separate governance approval.
- Define bounded authority, budgets, and action limits.
- Define operator approval and revocation mechanisms.
- Define safety kill switches.
- Define provider routing controls.
- Define prompt rewrite controls.
- Define tool, command, file, CI, Git, and PR controls.
- Define audit, rollback, and incident response.
- Prove secrets and raw payloads remain protected.
- Pass security, runtime, and governance validation.

This stack is not approved for autonomous execution.

## 21. Explicit Non-Approval Statement

This review does not approve:

- Prompt rewriting.
- Provider/model retry.
- Provider/model replan execution.
- Using persisted evidence as execution input.
- Provider switching.
- Self-repair.
- CI repair.
- Tool or command execution.
- File writes or runtime patches.
- Commit, push, or PR automation.
- Autonomous execution.

Omni remains advisory-only.

## 22. Open Risks

- Persisted evidence may be overinterpreted as permission.
- `recorded=true` may be mistaken for action success.
- `attempted=true` may be mistaken for attempted execution.
- `degraded=true` may be mistaken for autonomy failure.
- SQLite storage may be mistaken for a stronger autonomy mode.
- Stale evidence may be reviewed without enough context.
- Future UI may accidentally expose raw rows or add controls.
- Future consolidation may weaken per-artifact allowlists.

## 23. Open Questions

- What retention period should persisted dry-run evidence use?
- Should Cockpit historical audit view read from JSONL, SQLite, or an abstract
  read model?
- Should persisted evidence include `request_id` and `trace_id` by default, or
  only when already present in sanitized context?
- Should `evidence_summary` be hidden from historical views until additional
  redaction tests exist?
- Should dry-run RETRY and REPLAN persistence share a single governance
  document later?
- What review cadence should apply to persisted advisory evidence schemas?

## 24. Go/No-Go Table

| Area | Decision | Conditions |
|------|----------|------------|
| Documentation | Go | Keep docs/reviews explicit about advisory-only status. |
| Runtime readonly diagnostics | Go | Metadata-only; no execution controls. |
| Persisted sanitized evidence | Go | Allowlisted, bounded, best-effort audit metadata only. |
| JSONL audit mirror | Go | Default safe audit behavior; no raw payloads. |
| SQLite opt-in evidence storage | Go | Opt-in only; no behavior change when enabled/disabled. |
| Cockpit historical audit view design | Go | Readonly design only with redaction and query limits. |
| Cockpit historical audit view implementation | No-go for now | Requires separate implementation plan and tests. |
| Retention/cleanup design | Go | Design only; explicit TTL and safe cleanup semantics. |
| Retention/cleanup implementation | No-go for now | Requires separate approved branch and tests. |
| Prompt rewrite | No-go | Not approved. |
| Provider/model retry | No-go | Not approved. |
| Replan execution | No-go | Not approved. |
| Autonomous execution | No-go | Not approved. |

## 25. Final Recommendation

The persisted dry-run REPLAN evidence stack is approved for documentation,
readonly diagnostics, sanitized audit metadata persistence, future readonly
Cockpit historical audit view design, and future dry-run persistence governance
consolidation.

It is not approved for prompt rewriting, provider/model retry or replan
execution, using persisted evidence as execution input, provider switching,
self-repair, CI repair, Git/PR automation, or autonomous execution.

Omni remains advisory-only. Persisted evidence is audit metadata only.
