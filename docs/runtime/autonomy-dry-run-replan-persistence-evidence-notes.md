# Autonomy Dry-Run Replan Persistence Evidence Notes

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-replan-persistence-evidence-notes`
**Base:** `main` after PR #449
**Status:** Documentation only
**Runtime impact:** None

## 1. Purpose

This document explains how operators and reviewers should interpret persisted
dry-run REPLAN plan evidence and the
`dry_run_replan_plan_persistence` diagnostics exposed by runtime inspection.

The evidence helps reviewers understand that sanitized dry-run REPLAN plan
metadata was, or was not, recorded for audit. It does not authorize or record
autonomous execution.

## 2. Scope

This guidance applies to:

- `autonomy_evaluation["dry_run_replan_plan"]` metadata after runtime creates
  the dry-run plan.
- `DryRunReplanPlanEvidenceRecord` persisted through MemoryFacade.
- JSONL default audit mirror records for dry-run REPLAN plan evidence.
- SQLite opt-in records for dry-run REPLAN plan evidence.
- `autonomy_evaluation["dry_run_replan_plan_persistence"]` diagnostics.

It does not define prompt rewriting, replan execution, retry execution,
provider/model calls, provider routing changes, tool execution, command
execution, file writes, runtime patches, CI repair, Git automation, PR
automation, provider switching, self-repair, or autonomous execution approval.

## 3. What Persisted Dry-Run REPLAN Evidence Means

Persisted dry-run REPLAN evidence means Omni recorded sanitized audit metadata
about a dry-run REPLAN plan after the plan was created.

It may show:

- Which dry-run REPLAN plan was observed.
- Whether advisory rules would consider REPLAN eligible.
- Whether the plan was blocked by safety or governance rules.
- Which safe block categories were present.
- Which safe risk category, source decision, fingerprint, and tracker scores
  informed the plan.
- Whether MemoryFacade attempted and recorded the evidence.
- Whether recording degraded safely.
- Which safe audit storage mode was used.

Persisted evidence is an audit trail for review. It is not an action queue.

## 4. What Persisted Dry-Run REPLAN Evidence Does NOT Mean

Persisted dry-run REPLAN evidence does not mean:

- A prompt was rewritten.
- A rewritten prompt was generated.
- REPLAN was executed.
- RETRY was executed.
- A provider/model was called again.
- Runtime response changed.
- Provider routing changed.
- A tool, command, file write, patch, CI repair, commit, push, or PR was
  executed.
- Autonomous execution is approved.
- Human approval gates are bypassed.
- Persisted evidence may be used as execution input.

`recorded=true` means evidence was stored; it does not approve execution.
`attempted=true` does not mean execution was attempted.

## 5. Evidence Lifecycle

The current evidence lifecycle is:

1. Runtime creates `autonomy_evaluation["dry_run_replan_plan"]`.
2. Runtime builds a `DryRunReplanPlanEvidenceRecord` from safe plan metadata.
3. Runtime records through MemoryFacade as best-effort audit metadata.
4. JSONL default audit mirror may record sanitized metadata.
5. SQLite may record sanitized metadata only when SQLite memory is enabled.
6. Runtime exposes `dry_run_replan_plan_persistence` diagnostics.
7. Operators and reviewers inspect the metadata as read-only evidence.

At no point may persisted evidence execute REPLAN, execute RETRY, rewrite
prompts, call providers/models, change provider routing, or mutate runtime
responses.

## 6. Persistence Diagnostics Interpretation

`dry_run_replan_plan_persistence` describes the audit recording attempt.

It is safe diagnostic metadata only. It is not an execution result, permission
signal, or action status.

Expected fields:

- `attempted`
- `recorded`
- `degraded`
- `error_category`
- `event_type`
- `storage_mode`
- `sqlite_enabled`
- `recorded_at`

Diagnostics must not include raw exceptions, tracebacks, stack traces, file
paths, prompts, rewritten prompts, responses, provider payloads, tool output,
secrets, MemoryFacade object reprs, or context object reprs.

## 7. Field-by-Field Interpretation

| Field | Interpretation |
|-------|----------------|
| `plan_id` | Safe identifier for the dry-run REPLAN plan. Use it to reference the plan in review. |
| `plan_type` | Expected value is `dry_run_replan`. |
| `advisory` | Expected value is `true`. The evidence is advisory metadata only. |
| `would_replan` | Advisory eligibility only. It does not mean REPLAN executed. |
| `blocked` | Whether safe rules blocked the dry-run plan. |
| `block_reasons` | Safe bounded categories explaining blockers. |
| `replan_eligibility_score` | Advisory score for review context only, not permission. |
| `risk_level` | Safe risk category used by the planner. |
| `source_decision` | Advisory autonomy decision that informed the plan. |
| `fingerprint_id` | Safe identifier for related error/progress evidence. |
| `progress_score` | Safe progress score from tracker evidence. |
| `stagnation_score` | Safe stagnation score from tracker evidence. |
| `repeated_strategy_count` | Count of repeated safe strategy categories. |
| `suggested_strategy` | Safe categorical metadata only, not an executable instruction. |
| `event_type` | Expected value is `dry_run_replan_plan_evidence`. |
| `attempted` | Whether audit persistence was attempted. It does not mean execution was attempted. |
| `recorded` | Whether sanitized evidence was recorded. It does not approve execution. |
| `degraded` | Whether persistence degraded safely. It does not mean autonomy failed. |
| `error_category` | Safe categorical reason for persistence degradation, if any. |
| `storage_mode` | Audit storage metadata only, such as JSONL or SQLite mode. |
| `sqlite_enabled` | Whether SQLite memory was enabled for storage. It does not change autonomy behavior. |
| `created_at` | Timestamp from the dry-run REPLAN plan metadata. |
| `recorded_at` | Timestamp for the persistence diagnostic, if available. |

## 8. How to Interpret `recorded=true`

`recorded=true` means sanitized dry-run REPLAN evidence was stored through the
MemoryFacade path.

It does not mean:

- REPLAN was executed.
- RETRY was executed.
- A prompt was rewritten.
- A provider/model was called again.
- Runtime output changed.
- Provider routing changed.
- Autonomous execution is approved.

Treat `recorded=true` as audit evidence only. It can support review and
traceability, but it must never be used as execution input.

## 9. How to Interpret `degraded=true`

`degraded=true` means persistence degraded safely.

It may indicate that MemoryFacade was unavailable, the plan was invalid for
recording, or recording failed. It does not mean autonomy evaluation failed. It
does not mean runtime output changed. It does not trigger fallback execution,
RETRY, REPLAN, SELF_REPAIR, SWITCH_PROVIDER, ABORT_SAFE, provider/model calls,
or prompt rewriting.

When `degraded=true`, review `error_category` and surrounding safe diagnostics.
Do not paste raw logs, exceptions, stack traces, prompts, provider payloads, or
database rows into review notes.

## 10. How to Interpret `error_category`

`error_category` is a safe categorical persistence diagnostic.

Examples may include:

- `memory_unavailable`
- `invalid_plan`
- `record_failed`

The category should help reviewers understand why persistence did not produce
a stored audit record. It must not contain raw exception text, stack traces,
file paths, command arguments, prompts, responses, provider payloads, secrets,
or object reprs.

An empty `error_category` means no persistence error category was reported.

## 11. How to Interpret `storage_mode`

`storage_mode` is audit storage metadata only.

It may indicate the MemoryFacade backend mode, such as JSONL default behavior
or SQLite-backed behavior when enabled. It is not an autonomy mode. It does
not change provider routing, prompt handling, response generation, or action
execution.

SQLite enabled or disabled does not change autonomy behavior. It only affects
whether opt-in structured audit storage may be available in addition to JSONL
default behavior.

## 12. JSONL Interpretation Notes

JSONL remains the default audit mirror behavior.

When JSONL records dry-run REPLAN evidence:

- The record should contain sanitized metadata only.
- The event type should be `dry_run_replan_plan_evidence`.
- The record should not include raw prompts, rewritten prompts, responses,
  provider payloads, secrets, tool output, stack traces, or raw receipts.
- A JSONL record is audit evidence, not an execution record.

Do not paste raw JSONL lines into review unless they have been inspected and
confirmed to contain only safe metadata.

## 13. SQLite Interpretation Notes

SQLite remains opt-in.

When SQLite records dry-run REPLAN evidence:

- It stores sanitized metadata through MemoryFacade contracts.
- It does not change runtime behavior.
- It does not change provider routing.
- It does not rewrite prompts.
- It does not execute REPLAN or RETRY.
- It must not expose raw database rows in review or UI output.

`sqlite_enabled=true` means SQLite audit storage was enabled. It does not mean
autonomy behavior changed or autonomous execution was approved.

## 14. What Evidence Can Be Shared in Review

The following fields are safe to paste into review when they appear exactly as
sanitized metadata:

- `plan_id`
- `plan_type`
- `advisory`
- `would_replan`
- `blocked`
- `block_reasons`
- `replan_eligibility_score`
- `risk_level`
- `source_decision`
- `fingerprint_id`
- `progress_score`
- `stagnation_score`
- `repeated_strategy_count`
- `suggested_strategy`
- `event_type`
- `attempted`
- `recorded`
- `degraded`
- `error_category`
- `storage_mode`
- `sqlite_enabled`
- `created_at`
- `recorded_at`

Include `evidence_summary` only if it has already been reviewed and confirmed
to be sanitized and bounded.

## 15. What Evidence Must Never Be Shared

Do not paste or share:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys, tokens, or secrets.
- Stack traces.
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

If evidence contains any forbidden material, treat it as a redaction failure
and do not include it in review.

## 16. Operator Checklist

Before using persisted dry-run REPLAN evidence in review:

- Confirm `event_type` is `dry_run_replan_plan_evidence`.
- Confirm `advisory` is `true`.
- Confirm `plan_type` is `dry_run_replan`.
- Confirm evidence is sanitized metadata only.
- Confirm `recorded=true` is treated as audit storage only.
- Confirm `attempted=true` is not interpreted as attempted execution.
- Confirm `degraded=true` is treated as safe persistence degradation only.
- Confirm `storage_mode` is treated as storage metadata only.
- Confirm SQLite enabled/disabled is not treated as autonomy behavior.
- Confirm no forbidden raw content is pasted.
- Confirm Omni remains advisory-only.

## 17. Security/Privacy Considerations

Persisted dry-run REPLAN evidence is safer than raw runtime payloads, but it is
still operational metadata. It may reveal timing, risk categories, decision
categories, fingerprints, score patterns, and repeated-strategy counts.

Security expectations:

- Persisted evidence must remain allowlisted and bounded.
- Diagnostics must remain categorical, boolean, numeric, or safe timestamp
  values.
- Raw exception text must not be exposed.
- Raw JSONL lines and database rows must not be pasted without review.
- Review notes must not add raw prompts, rewritten prompts, provider payloads,
  tool outputs, file contents, or secrets.

## 18. Abuse/Misuse Cases

Misuse cases to guard against:

- Treating `recorded=true` as execution approval.
- Treating `attempted=true` as an attempted replan.
- Treating `blocked=false` as permission to execute.
- Treating `would_replan=true` as permission to execute.
- Treating `suggested_strategy` as an instruction.
- Treating `storage_mode=sqlite` as a stronger autonomy mode.
- Feeding persisted evidence back into an executor.
- Expanding safe metadata with raw prompts, responses, stack traces, provider
  payloads, or database rows in review.

These are governance failures. The evidence exists for review and audit only.

## 19. Known Risks

- Operators may overinterpret persistence as approval.
- Operators may overinterpret `recorded=true` as an execution signal.
- Stale persisted evidence may be compared against a newer runtime condition.
- JSONL and SQLite records may be reviewed out of context.
- Raw JSONL lines or database rows may be pasted before redaction review.
- `evidence_summary` may be misunderstood as complete evidence.
- SQLite opt-in may be confused with autonomy opt-in.

## 20. Final Warning

Persisted dry-run REPLAN evidence is audit metadata only.

Persistence does not rewrite prompts. Persistence does not execute REPLAN or
RETRY. Persistence does not call a provider/model. Persistence does not change
provider routing. Persistence does not change runtime response. Persisted
evidence must never be used as execution input.

Omni remains advisory-only and is not approved for autonomous execution.
