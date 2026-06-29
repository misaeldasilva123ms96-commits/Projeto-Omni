# Autonomy Dry-Run Retry Persistence Evidence Notes

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-retry-persistence-evidence-notes`
**Base:** `main` after PR #457
**Status:** Documentation only
**Runtime impact:** None

## 1. Executive Summary

Dry-run RETRY persistence records sanitized audit metadata after runtime
creates `autonomy_evaluation["dry_run_retry_plan"]`. The persisted evidence
helps operators and reviewers understand whether a dry-run RETRY plan was
recorded, where it was recorded, and whether recording degraded safely.

The diagnostic key is `dry_run_retry_plan_persistence`. The event type is
`dry_run_retry_plan_evidence`.

This evidence is audit metadata only. `would_retry=true` is not retry
execution. `recorded=true` is not approval. `attempted=true` is not execution.
`blocked=false` is not approval. `retry_eligibility_score` is not permission.
`suggested_retry_strategy` is not an instruction. Persisted evidence must
never become execution input. Omni remains advisory-only.

## 2. Scope

This document explains how to interpret persisted dry-run RETRY plan evidence
and runtime persistence diagnostics.

It covers:

- `autonomy_evaluation["dry_run_retry_plan"]` after runtime creates the plan.
- `DryRunRetryPlanEvidenceRecord` metadata.
- MemoryFacade best-effort recording.
- JSONL default audit recording.
- SQLite opt-in evidence storage.
- Runtime diagnostics under `dry_run_retry_plan_persistence`.
- Safe evidence sharing and forbidden evidence handling.

It does not define or approve retry execution, replan execution, prompt
rewriting, provider/model calls, provider routing changes, runtime response
changes, tool execution, command execution, file writes, CI repair, Git
automation, PR automation, provider switching, self-repair, or autonomous
execution.

## 3. What Was Persisted

When runtime persistence succeeds, Omni records sanitized dry-run RETRY plan
metadata as `dry_run_retry_plan_evidence`.

The evidence may include:

- Event type.
- Plan type.
- Advisory flag.
- RETRY advisory eligibility.
- Safe retry reason category.
- Blocked flag.
- Safe block reason categories.
- Retry eligibility score.
- Safe risk level.
- Safe source decision.
- Bounded fingerprint ID.
- Safe progress and stagnation scores.
- Safe suggested retry strategy category, if present.
- Bounded evidence summary.
- Safe timestamps.
- Sanitized and bounded session, request, or trace IDs if present.

All fields remain metadata-only. They are not action instructions.

## 4. What Was Not Persisted

Dry-run RETRY persistence must not store:

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

If a field is not explicitly allowlisted by the evidence record, reviewers
should treat it as forbidden.

## 5. Runtime Diagnostic Interpretation

`dry_run_retry_plan_persistence` describes the audit recording attempt for a
dry-run RETRY plan.

Expected diagnostic fields:

- `attempted`
- `recorded`
- `degraded`
- `error_category`
- `event_type`
- `storage_mode`
- `sqlite_enabled`
- `recorded_at`

The diagnostic is not an execution result. It is not permission. It is not an
action status. It must not include raw exceptions, tracebacks, stack traces,
file paths, prompts, rewritten prompts, responses, provider payloads, tool
output, secrets, raw MemoryFacade reprs, or raw context reprs.

Field interpretation:

| Field | Interpretation |
|-------|----------------|
| `attempted` | Whether runtime attempted audit persistence after a plan existed. It does not mean RETRY was attempted. |
| `recorded` | Whether sanitized evidence was recorded. It does not approve execution. |
| `degraded` | Whether persistence degraded safely. It does not mean autonomy failed. |
| `error_category` | Safe categorical reason for persistence degradation, if any. |
| `event_type` | Expected value is `dry_run_retry_plan_evidence`. |
| `storage_mode` | Safe audit storage category only. It is not autonomy mode. |
| `sqlite_enabled` | Whether SQLite memory was enabled for storage. It does not change autonomy behavior. |
| `recorded_at` | Safe timestamp for the persistence diagnostic, if available. |

## 6. Evidence Record Interpretation

`DryRunRetryPlanEvidenceRecord` is the sanitized audit record for dry-run
RETRY plan evidence.

Important fields:

| Field | Interpretation |
|-------|----------------|
| `event_type` | Expected value is `dry_run_retry_plan_evidence`. |
| `plan_id` | Safe identifier for the dry-run RETRY plan. |
| `plan_type` | Expected value is `dry_run_retry`. |
| `advisory` | Expected value is `true`. |
| `would_retry` | Advisory eligibility only. It does not mean RETRY executed. |
| `retry_reason` | Safe bounded category explaining the plan result. |
| `blocked` | Whether dry-run rules blocked retry planning. |
| `block_reasons` | Safe bounded categories explaining blockers. |
| `retry_eligibility_score` | Advisory score for review only. It is not permission. |
| `risk_level` | Safe risk category used by planning logic. |
| `source_decision` | Advisory decision that informed the plan. |
| `fingerprint_id` | Safe bounded identifier for related evidence. |
| `progress_score` | Safe tracker progress score. |
| `stagnation_score` | Safe tracker stagnation score. |
| `suggested_retry_strategy` | Safe category only, not an instruction. |
| `evidence_summary` | Bounded sanitized summary, if present. |
| `created_at` | Timestamp from plan creation metadata. |
| `recorded_at` | Timestamp from record creation or persistence metadata. |
| `session_id` | Safe bounded session ID, if present. |
| `request_id` | Safe bounded request ID, if present. |
| `trace_id` | Safe bounded trace ID, if present. |

## 7. JSONL Interpretation

JSONL remains the default audit mirror.

When JSONL records dry-run RETRY evidence:

- The event type should be `dry_run_retry_plan_evidence`.
- The record should contain sanitized metadata only.
- JSONL storage does not execute RETRY.
- JSONL storage does not call a provider/model.
- JSONL storage does not change provider routing.
- JSONL storage does not change runtime output.
- JSONL storage is not operational authorization.

Do not paste raw JSONL lines into review unless they have been inspected and
confirmed to contain only safe metadata.

## 8. SQLite Interpretation

SQLite remains opt-in.

When SQLite records dry-run RETRY evidence:

- It stores sanitized metadata through MemoryFacade contracts.
- It may support structured list/query behavior for audit review.
- It does not change runtime behavior.
- It does not change provider routing.
- It does not execute RETRY or REPLAN.
- It does not call a provider/model.
- It must not expose raw database rows in review or UI output.

`sqlite_enabled=true` means SQLite audit storage was enabled. It does not mean
autonomy behavior changed or autonomous execution was approved.

## 9. MemoryFacade Interpretation

MemoryFacade is the persistence boundary for dry-run RETRY evidence.

Expected behavior:

- Accept `DryRunRetryPlanEvidenceRecord`.
- Sanitize through allowlisted record serialization.
- Record to JSONL default audit mirror when available.
- Record to SQLite only when SQLite is enabled and connected.
- Degrade write failures safely.
- Return safe bounded records for list/read operations.
- Return empty results on read failure.

MemoryFacade is not an execution queue. It must not feed persisted evidence
into RETRY execution, REPLAN execution, provider routing, prompt rewriting,
tool execution, command execution, CI repair, Git automation, or PR automation.

## 10. Operator Checklist

Before sharing or acting on persisted dry-run RETRY evidence, operators should
confirm:

- The evidence is labeled `dry_run_retry_plan_evidence`.
- Diagnostics are under `dry_run_retry_plan_persistence`.
- `advisory` is `true`.
- `would_retry=true` is interpreted only as advisory eligibility.
- `recorded=true` is interpreted only as audit storage success.
- `blocked=false` is not treated as approval.
- `suggested_retry_strategy` is treated as category metadata only.
- No raw prompt, response, provider payload, stack trace, tool output, command
  args, file contents, secrets, raw rows, or raw JSONL lines are shared.

## 11. Reviewer Checklist

Reviewers should verify:

- The diagnostic contains only allowed fields.
- The event type is `dry_run_retry_plan_evidence`.
- The plan type is `dry_run_retry`.
- Storage mode is treated as audit metadata only.
- SQLite status is not interpreted as autonomy mode.
- `error_category` is safe and categorical.
- Shared evidence is bounded and sanitized.
- No evidence field is being used as execution input.
- No Cockpit visibility is being treated as operational authorization.

## 12. Safe Evidence To Share

Safe evidence examples include:

- Event type.
- Plan type.
- Advisory flag.
- `would_retry`.
- Blocked flag.
- Safe block reason categories.
- Categorical risk level.
- Categorical source decision.
- Bounded fingerprint ID.
- Bounded evidence summary.
- Bounded `created_at` and `recorded_at` timestamps.
- Sanitized request, session, or trace IDs if present.
- Persistence diagnostic booleans and categorical values.
- `storage_mode`, if safe and categorical.
- `sqlite_enabled`, as a boolean.

Only share these fields after confirming they appear as sanitized metadata.

## 13. Evidence That Must Never Be Shared

Never paste or share:

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

If deeper debugging is required, create a new sanitized summary instead of
copying raw runtime material.

## 14. Common Misinterpretations

Avoid these interpretations:

- `would_retry=true` means RETRY executed.
- `recorded=true` means RETRY is approved.
- `attempted=true` means execution was attempted.
- `blocked=false` means autonomous execution is allowed.
- `retry_eligibility_score` is permission.
- `suggested_retry_strategy` is an instruction.
- `storage_mode=sqlite` means SQLite changed runtime behavior.
- `sqlite_enabled=true` means autonomy mode changed.
- Cockpit visibility means an operator may execute the plan.
- JSONL or SQLite records may be used as execution input.

All of these interpretations are incorrect.

## 15. Abuse/Misuse Cases

Misuse cases include:

- Feeding persisted evidence into an executor.
- Treating persisted evidence as a retry queue.
- Treating `suggested_retry_strategy` as an executable instruction.
- Treating `blocked=false` as approval to bypass human review.
- Treating `recorded=true` as governance approval.
- Copying raw JSONL lines into review without redaction.
- Exposing raw SQLite rows in Cockpit or review notes.
- Expanding evidence with raw prompts, responses, provider payloads, logs,
  traces, command args, file contents, or secrets.

The correct use is readonly audit review only.

## 16. Failure/Degradation Interpretation

`degraded=true` means persistence degraded safely.

Possible safe categories include:

- `memory_unavailable`
- `invalid_plan`
- `record_failed`

Degradation does not mean:

- Runtime failed.
- Autonomy failed.
- RETRY executed.
- REPLAN executed.
- A provider/model was called.
- Provider routing changed.
- Runtime response changed.
- SELF_REPAIR, SWITCH_PROVIDER, or ABORT_SAFE executed.

When degradation occurs, review `error_category` and surrounding safe
diagnostics. Do not paste raw exceptions, stack traces, file paths, prompts,
responses, provider payloads, tool output, command args, raw rows, or secrets.

## 17. Relationship To REPLAN Persistence Evidence

RETRY persistence mirrors the REPLAN persistence pattern:

- Both are best-effort.
- Both are metadata-only.
- Both use MemoryFacade.
- Both support JSONL default audit recording.
- Both support SQLite opt-in storage.
- Both expose safe persistence diagnostics.
- Both preserve advisory-only behavior.
- Neither may be used as execution input.

The RETRY diagnostic key is `dry_run_retry_plan_persistence`.
The REPLAN diagnostic key is `dry_run_replan_plan_persistence`.

The RETRY event type is `dry_run_retry_plan_evidence`.
The REPLAN event type is `dry_run_replan_plan_evidence`.

## 18. Relationship To Dry-Run Persistence Consolidation

The dry-run persistence consolidation design defines a shared model for RETRY
and REPLAN evidence.

This document applies that model to RETRY evidence interpretation:

- Shared event taxonomy.
- Shared diagnostic shape.
- Shared allowlist and redaction expectations.
- Shared JSONL default behavior.
- Shared SQLite opt-in behavior.
- Shared non-execution posture.
- Shared controls before broader audit views, retention, cleanup, or execution
  design.

Any future consolidation work must preserve RETRY and REPLAN separation from
execution.

## 19. Relationship To Future Cockpit Historical Audit View

A future Cockpit historical audit view may display persisted dry-run RETRY
evidence, but only as readonly metadata.

Before any such view:

- Query results must be bounded.
- Filters must be safe and categorical.
- Empty and degraded states must be explicit.
- Labels must state that no retry was executed.
- No destructive controls may be added.
- No raw rows or raw JSONL lines may be displayed.
- No raw prompts, responses, provider payloads, tool outputs, stack traces,
  command args, secrets, or file contents may be rendered.
- Cockpit visibility must not be presented as authorization.

## 20. Relationship To Future Retention/Cleanup

Future retention and cleanup must be designed separately.

Required expectations:

- Cleanup must be explicit or governed by an approved retention design.
- Cleanup must delete only eligible expired audit records.
- Cleanup must not delete unrelated memory records.
- Cleanup diagnostics must be safe metadata only.
- Cleanup must not expose raw database rows or raw JSONL lines.
- Cleanup must not execute RETRY, execute REPLAN, call providers/models,
  rewrite prompts, change provider routing, or change runtime output.

## 21. Required Controls Before Broader Persistence Views

Before broader persistence views are added:

- Approve safe query filters.
- Approve result limits.
- Approve displayed field allowlists.
- Approve redaction handling.
- Approve empty/degraded UI states.
- Confirm no raw rows or raw JSONL lines are rendered.
- Confirm no prompts, responses, provider payloads, tool outputs, stack traces,
  command args, secrets, or file contents are displayed.
- Confirm views remain readonly.
- Confirm visibility is not treated as operational authorization.

## 22. Required Controls Before Any Execution Design

Before any execution design:

- Complete separate governance review.
- Define human approval gates.
- Define protected file and secret gates.
- Define provider routing guarantees.
- Define runtime response guarantees.
- Define CI/security gates.
- Define audit requirements.
- Prove persisted evidence is not execution input.
- Prove RETRY evidence remains readonly unless transformed by a separately
  approved execution design.

This evidence note does not approve execution design.

## 23. Explicit Non-Execution Statement

Persisted dry-run RETRY evidence does not execute RETRY.

It also does not:

- Execute REPLAN.
- Rewrite prompts.
- Call providers/models.
- Change provider routing.
- Change runtime output.
- Execute tools.
- Execute commands.
- Write files.
- Patch code.
- Repair CI.
- Commit, push, or open PRs.
- Enable provider switching.
- Enable self-repair.
- Approve autonomous execution.

`dry_run_retry_plan_persistence` is audit metadata only.
`dry_run_retry_plan_evidence` is audit metadata only.
Omni remains advisory-only.

## 24. Open Risks

- Operators may misread `would_retry=true` as execution.
- Reviewers may misread `recorded=true` as approval.
- `blocked=false` may be overinterpreted as permission.
- `suggested_retry_strategy` may be mistaken for an instruction.
- Raw JSONL lines may be copied into review without redaction.
- Raw SQLite rows may be exposed during manual debugging.
- Future audit views may accidentally show too much context.
- Evidence could be misused as execution input without governance controls.

## 25. Open Questions

- Should RETRY and REPLAN persistence evidence use a shared historical audit
  query API?
- Should future Cockpit audit views group RETRY and REPLAN evidence together
  or keep separate tabs?
- What retention window should apply to dry-run RETRY evidence?
- Should RETRY evidence cleanup share the REPLAN/session-state cleanup path or
  use a separate explicit hook?
- Should `suggested_retry_strategy` use a stricter categorical enum before
  broader views are built?

## 26. Final Recommendation

Use persisted dry-run RETRY evidence only for readonly audit review.

It is safe to review sanitized metadata, persistence diagnostics, JSONL audit
presence, and SQLite opt-in storage status. It is not safe to use persisted
evidence as execution input or approval.

Recommended next phase: a governance review for the combined RETRY and REPLAN
dry-run persistence stack before broader historical audit views, retention,
cleanup, or any execution design.
