# Autonomy Dry-Run Historical Audit View Design

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-historical-audit-view-design`
**Base:** `main` after PR #459
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs a future readonly Cockpit historical audit view for
persisted dry-run RETRY and REPLAN evidence. The view would help operators and
reviewers inspect sanitized audit metadata across
`dry_run_retry_plan_evidence` and `dry_run_replan_plan_evidence` without
exposing raw sensitive data and without implying approval, authorization, or
execution.

Required UX labels:

- "Historical dry-run audit"
- "Readonly audit metadata"
- "No retry executed"
- "No replan executed"
- "Not an approval"
- "Not execution input"
- "Advisory-only"

This design does not implement UI, APIs, runtime behavior, persistence
behavior, MemoryFacade behavior, SQLite behavior, provider routing, prompt
rewriting, RETRY execution, REPLAN execution, or autonomous execution.

## 2. Scope

This design covers a future Cockpit view that reads persisted dry-run audit
metadata and displays it safely.

It includes:

- Data source expectations.
- Readonly access model.
- Safe filters.
- Sorting and pagination.
- Evidence cards.
- Detail drawer behavior.
- Diagnostic display.
- Safe field allowlist.
- Forbidden field denylist.
- Redaction and privacy requirements.
- JSONL, SQLite, and MemoryFacade considerations.
- Copy/export policy.
- Testing and rollout guidance.
- Required controls before implementation.

## 3. Non-Goals

- Do not implement the view in this branch.
- Do not add UI components.
- Do not add API endpoints.
- Do not modify runtime code.
- Do not modify persistence code.
- Do not modify MemoryFacade code.
- Do not modify SQLite code.
- Do not modify frontend/Cockpit code.
- Do not rewrite prompts.
- Do not execute RETRY.
- Do not execute REPLAN.
- Do not call providers/models.
- Do not change provider routing.
- Do not change runtime output.
- Do not enable copy/export.
- Do not approve autonomous execution.

## 4. Current Persisted Evidence Inventory

Current dry-run autonomy persistence includes:

- `dry_run_retry_plan_evidence`
- `dry_run_replan_plan_evidence`
- `dry_run_retry_plan_persistence` diagnostics
- `dry_run_replan_plan_persistence` diagnostics
- JSONL default audit recording
- SQLite opt-in evidence storage
- MemoryFacade record/list contracts
- Runtime best-effort opt-in persistence wiring for RETRY and REPLAN
- Evidence notes for RETRY and REPLAN
- Consolidated dry-run persistence governance review

All evidence is sanitized audit metadata only. It is not an execution surface.

## 5. User Personas

Primary personas:

- Operator: checks whether dry-run evidence was recorded and whether
  persistence degraded safely.
- Reviewer: validates governance posture, redaction, and interpretation.
- Misael: reviews branches and decides whether future implementation is safe.
- Security reviewer: verifies that raw sensitive material is not exposed.

No persona receives authorization to execute RETRY, execute REPLAN, rewrite
prompts, switch providers, or trigger autonomous behavior from this view.

## 6. Primary Use Cases

Supported future use cases:

- Inspect recent persisted dry-run RETRY and REPLAN evidence.
- Filter by plan type, event type, source decision, risk level, blocked state,
  recorded state, degraded state, storage mode, SQLite enabled state, safe IDs,
  and timestamp ranges.
- Compare RETRY and REPLAN evidence at the same safety level.
- Review persistence diagnostics without raw storage access.
- Confirm audit metadata exists without treating it as approval.
- Identify safe degradation categories.

## 7. Forbidden Use Cases

Forbidden use cases:

- Execute RETRY.
- Execute REPLAN.
- Rewrite prompts.
- Call providers/models.
- Change provider routing.
- Change runtime output.
- Execute tools or commands.
- Repair CI.
- Switch providers.
- Self-repair.
- Display raw JSONL lines.
- Display raw SQLite rows.
- Copy/export raw evidence.
- Use persisted evidence as execution input.
- Treat Cockpit visibility as operational authorization.

## 8. Data Source Model

The future view should read from a safe backend query layer that uses
MemoryFacade contracts, not direct JSONL or SQLite access from the frontend.

Conceptual source flow:

1. Runtime produces dry-run plan metadata.
2. Runtime records sanitized evidence best-effort.
3. MemoryFacade records JSONL default audit metadata and SQLite opt-in records
   when enabled.
4. A future readonly query boundary returns bounded sanitized records.
5. Cockpit renders only allowlisted fields.

The view must not read raw database rows or raw JSONL lines.

## 9. Readonly Access Model

Access must be readonly.

Required properties:

- No mutation controls.
- No destructive buttons.
- No retry/replan action controls.
- No prompt rewrite controls.
- No provider routing controls.
- No cleanup controls.
- No copy/export controls until separately approved.
- Read failures degrade to empty or degraded states.

The view should be framed as "Readonly audit metadata" and "Advisory-only".

## 10. Query/Filter Model

Required supported filters:

- `plan_type`
- `event_type`
- `source_decision`
- `risk_level`
- `blocked`
- `recorded`
- `degraded`
- `storage_mode`
- `sqlite_enabled`
- `request_id`, if sanitized
- `trace_id`, if sanitized
- `session_id`, if sanitized
- `created_at` range
- `recorded_at` range

Filters must accept only bounded values. Unknown filters should be ignored or
rejected safely. Filters must not accept raw prompts, raw responses, provider
payloads, command args, file paths, raw row fragments, or raw JSONL snippets.

## 11. Sorting/Pagination Model

Sorting should be limited to safe fields:

- `created_at`
- `recorded_at`
- `event_type`
- `plan_type`
- `risk_level`
- `blocked`
- `degraded`

Pagination requirements:

- Use bounded page sizes.
- Prefer stable cursor or timestamp pagination.
- Avoid unbounded result sets.
- Show total counts only if cheaply and safely available.
- Degrade safely if counts are unavailable.

## 12. Detail Drawer Model

The detail drawer should show one selected evidence record as sanitized
metadata.

Allowed detail behavior:

- Show safe fields only.
- Group fields by plan metadata, scores, diagnostics, and IDs.
- Include warnings that the record is not execution input.
- Show degradation category if present.
- Show empty values as unavailable, not as failure.

Forbidden detail behavior:

- Raw JSON view.
- Raw SQLite row view.
- Raw JSONL line view.
- Prompt, response, provider payload, command args, file content, or secret
  display.
- Execution buttons.
- Copy/export buttons until separately approved.

## 13. Evidence Card Model

Evidence cards should provide compact, scan-friendly summaries.

Recommended fields:

- Event type.
- Plan type.
- Advisory flag.
- Blocked flag.
- Risk level.
- Source decision.
- Fingerprint ID.
- Created/recorded timestamps.
- Persistence status.
- Safe warning labels.

Card labels should include "No retry executed" for RETRY and
"No replan executed" for REPLAN.

## 14. Diagnostic Display Model

Diagnostics should show persistence state without raw failure details.

Allowed diagnostic values:

- `attempted`
- `recorded`
- `degraded`
- `error_category`
- `event_type`
- `storage_mode`
- `sqlite_enabled`
- `recorded_at`

Diagnostic labels must clarify:

- `recorded=true` is not approval.
- `attempted=true` is not execution.
- `degraded=true` is safe persistence degradation, not autonomy failure.

## 15. Safe Field Allowlist

Required visible safe fields:

- `event_type`
- `plan_id`
- `plan_type`
- `advisory`
- `would_retry`
- `would_replan`
- `blocked`
- `block_reasons`
- `risk_level`
- `source_decision`
- `fingerprint_id`
- `progress_score`
- `stagnation_score`
- `retry_eligibility_score`
- `replan_eligibility_score`
- `repeated_strategy_count`
- `suggested_retry_strategy`
- `suggested_strategy`
- `evidence_summary`
- `created_at`
- `recorded_at`
- Sanitized request, session, and trace IDs when present.
- Persistence diagnostic booleans and categorical values.

All visible strings must be sanitized and bounded before rendering.

## 16. Forbidden Field Denylist

Required forbidden UI fields:

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

Forbidden fields must not be rendered, copied, exported, logged by the UI, or
stored in client-side state for this view.

## 17. Redaction/Privacy Requirements

The view must use allowlisted display models rather than denylist cleanup of
raw records.

Requirements:

- Sanitize before API response.
- Sanitize again before display where existing frontend utilities allow it.
- Bound all strings.
- Bound all lists.
- Avoid raw object rendering.
- Avoid `dangerouslySetInnerHTML`.
- Avoid raw error text in UI.
- Avoid path, stack trace, or exception leakage.
- Avoid screenshots that contain raw payloads or secrets.

## 18. JSONL Display Considerations

JSONL is the default audit mirror, but the view must not display raw JSONL
lines.

Allowed behavior:

- Show storage mode as safe metadata.
- Show whether evidence came from audit storage if safely available.
- Show sanitized records returned by a server-side allowlist.

Forbidden behavior:

- Raw JSONL line viewer.
- JSONL download.
- JSONL copy button.
- Displaying unreviewed JSON blobs.

## 19. SQLite Display Considerations

SQLite is opt-in structured storage, but the view must not display raw rows.

Allowed behavior:

- Show `sqlite_enabled` as a boolean.
- Show safe storage mode.
- Show sanitized records returned by MemoryFacade.
- Show degraded state if SQLite is unavailable.

Forbidden behavior:

- Raw SQL row viewer.
- SQLite path display.
- SQL query console.
- Raw database export.

## 20. MemoryFacade Access Considerations

Future implementation should use MemoryFacade as the backend access boundary.

Requirements:

- Query via safe list/read methods.
- Enforce limits server-side.
- Return sanitized record DTOs.
- Return empty results on read failure.
- Return safe degraded diagnostics.
- Avoid exposing backend paths, raw exceptions, raw rows, or raw JSONL lines.

MemoryFacade must remain a storage boundary, not an action queue.

## 21. Error/Degradation Display Model

Errors and degraded states should be visible but safe.

Safe states:

- Memory unavailable.
- SQLite unavailable.
- Query failed.
- No records.
- Invalid filter.
- Partial results.

Display only safe categories. Do not display raw exception messages,
tracebacks, paths, command args, payloads, prompts, responses, or secrets.

## 22. Empty/Loading/Error States

Required states:

- Loading: neutral state, no raw request details.
- Empty: "No dry-run audit records found" or equivalent.
- Filtered empty: safe message that no matching metadata was found.
- Degraded: safe category and advisory-only warning.
- Error: safe generic message with no raw exception.

All states must preserve the labels "Readonly audit metadata" and
"Advisory-only".

## 23. UX Warnings And Labels

Required visible labels:

- "Historical dry-run audit"
- "Readonly audit metadata"
- "No retry executed"
- "No replan executed"
- "Not an approval"
- "Not execution input"
- "Advisory-only"

Required warnings:

- `would_retry=true` is not retry execution.
- `would_replan=true` is not replan execution.
- `recorded=true` is not approval.
- `attempted=true` is not execution.
- `blocked=false` is not approval.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- Persisted evidence must never become execution input.
- Cockpit visibility is not operational authorization.
- Copy/export must be disabled until separate governance approval.
- Omni remains advisory-only.

## 24. Copy/Export Policy

Copy/export must be disabled until separate governance approval.

Initial implementation should not include:

- Copy record.
- Copy raw JSON.
- Export JSON.
- Export CSV.
- Download JSONL.
- Download SQLite data.
- Screenshot helper that may expose secrets.

Future copy/export design may allow a safe summary only after separate
approval, display allowlists, redaction tests, and security review.

## 25. Auditability Requirements

The view should improve auditability by showing:

- Which plan evidence exists.
- Whether records are RETRY or REPLAN.
- Whether persistence recorded or degraded.
- Which safe risk/source categories applied.
- Which safe fingerprint and scores were recorded.
- Which sanitized IDs link related evidence.
- When records were created and recorded.

Auditability must remain readonly and metadata-only.

## 26. Abuse/Misuse Cases

Misuse cases to prevent:

- Treating the view as approval.
- Treating a record as an execution queue item.
- Treating suggested strategy as an instruction.
- Treating `blocked=false` as authorization.
- Copying raw JSONL lines.
- Displaying raw SQLite rows.
- Using records to trigger provider/model calls.
- Adding retry/replan buttons.
- Adding cleanup buttons without governance.

## 27. Security Review Checklist

Before implementation, security review must verify:

- No raw prompt display.
- No rewritten prompt display.
- No raw response display.
- No provider payload display.
- No credentials or secrets display.
- No stack trace or traceback display.
- No stdout/stderr display.
- No command args display.
- No file contents display.
- No raw JSONL line display.
- No raw SQLite row display.
- No dangerous HTML rendering.
- No copy/export without approval.
- No execution controls.

## 28. Testing Strategy

Future implementation should test:

- Safe filters render and query correctly.
- Unsupported filters are rejected or ignored safely.
- Pagination is bounded.
- Detail drawer shows only allowlisted fields.
- Evidence cards show required labels.
- Diagnostics render safe categories only.
- Empty/loading/error states render safely.
- Forbidden fields are not rendered.
- Copy/export controls are absent.
- No retry/replan controls appear.
- No raw rows or JSONL lines appear.
- Security tests pass.

## 29. Rollout Plan

Recommended rollout:

1. Complete this design.
2. Review query/API design separately.
3. Review UI allowlist separately.
4. Implement backend readonly query boundary.
5. Implement Cockpit readonly view.
6. Add security and UI tests.
7. Validate no execution controls exist.
8. Keep copy/export disabled.
9. Review retention/cleanup integration separately.

## 30. Required Controls Before Implementation

Before implementation:

- Approve backend query shape.
- Approve UI field allowlist.
- Approve filter allowlist.
- Approve pagination limits.
- Approve degraded/error states.
- Approve security checklist.
- Confirm copy/export is disabled.
- Confirm no execution controls.
- Confirm no raw storage exposure.

## 31. Required Controls Before Enabling Copy/Export

Before copy/export:

- Separate governance approval.
- Safe summary schema.
- Redaction tests.
- Security review.
- Explicit exclusion of raw JSONL and SQLite rows.
- Explicit exclusion of prompts, responses, payloads, logs, command args,
  file contents, and secrets.
- Clear labels that exported data is not approval or execution input.

## 32. Required Controls Before Retention/Cleanup Integration

Before retention/cleanup integration:

- Separate retention/cleanup design.
- Explicit/manual or governed invocation model.
- Dry-run cleanup behavior.
- Safe cleanup diagnostics.
- Proof that unrelated memory records are not deleted.
- No destructive Cockpit controls without admin/governance approval.
- No raw row exposure.

## 33. Required Controls Before Any Execution Design

Before any execution design:

- Separate governance review.
- Human approval gates.
- Secret/protected-file gates.
- Provider routing constraints.
- Runtime response constraints.
- CI/security gates.
- Audit and rollback plan.
- Proof persisted evidence is not execution input.
- Proof UI visibility is not authorization.

## 34. Explicit Non-Approval Statement

This design is not approval for:

- UI implementation.
- API implementation.
- Copy/export.
- Retention/cleanup implementation.
- Prompt rewriting.
- Provider/model retry execution.
- Provider/model replan execution.
- Automatic retry execution.
- Automatic replan execution.
- Provider switching.
- Self-repair.
- CI repair.
- Persisted evidence as execution input.
- Autonomous execution.

It approves only documentation/design for a future readonly historical audit
view.

## 35. Open Risks

- Operators may still infer authorization from visibility.
- Copy/export may be requested before governance is ready.
- Historical views may tempt raw-row debugging.
- Filtered results may be mistaken for complete evidence.
- Degraded storage may be mistaken for autonomy failure.
- Suggested strategies may be mistaken for instructions.
- Future implementation could accidentally expose raw JSON blobs.

## 36. Open Questions

- Should RETRY and REPLAN share one table view or use tabs?
- Should the initial view read SQLite only or also summarize JSONL audit
  availability?
- What default time range should the view use?
- Should IDs be partially masked even after sanitization?
- Should evidence summaries be collapsible by default?
- What retention status should be shown before cleanup integration exists?

## 37. Go/No-Go Table

| Area | Decision | Notes |
|------|----------|-------|
| Docs/design | Go | This branch only. |
| Readonly historical audit view implementation | No-go | Requires separate controls and implementation PR. |
| Safe filters | Go for design | Implementation requires query review. |
| Safe detail drawer | Go for design | Implementation requires UI allowlist review. |
| Copy safe summary | No-go | Requires separate governance approval. |
| Export JSON/CSV | No-go | Requires separate governance approval. |
| Raw JSONL display | No-go | Explicitly forbidden. |
| Raw SQLite row display | No-go | Explicitly forbidden. |
| Prompt rewrite | No-go | Not approved. |
| Provider/model retry execution | No-go | Not approved. |
| Provider/model replan execution | No-go | Not approved. |
| Persisted evidence as execution input | No-go | Explicitly forbidden. |
| Autonomous execution | No-go | Not approved. |

## 38. Final Recommendation

Proceed only with review of this design. A future implementation may be safe
only if it remains readonly, uses MemoryFacade-backed sanitized query
boundaries, displays allowlisted fields only, keeps copy/export disabled, and
contains no execution controls.

Recommended next phase: design the readonly backend query contract for
historical dry-run audit evidence, still without implementing Cockpit UI,
copy/export, retention/cleanup, or execution behavior.
