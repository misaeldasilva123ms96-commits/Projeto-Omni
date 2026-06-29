# Autonomy Dry-Run Historical Audit Query Contract Design

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-historical-audit-query-contract-design`
**Base:** `main` after PR #460
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document defines a safe readonly query contract for a future Cockpit
historical dry-run audit view. The contract covers persisted RETRY and REPLAN
dry-run evidence and is intentionally limited to sanitized audit metadata.

The contract is designed to prevent future MemoryFacade, API, or Cockpit work
from overexposing raw persisted evidence. Query results are readonly audit
metadata. Query results are not approval. Query results are not execution
input. Filters must not become execution selectors. Detail views must not
expose raw storage records. Copy/export remains disabled until separate
governance approval. Omni remains advisory-only.

This document does not implement APIs, UI, runtime behavior, MemoryFacade
queries, SQLite queries, persistence behavior, provider routing, prompt
rewriting, RETRY execution, REPLAN execution, or autonomous execution.

## 2. Scope

This design covers:

- Safe query/filter contracts for historical dry-run audit evidence.
- Allowlisted filters, enum values, booleans, IDs, timestamps, pagination, and
  sorting.
- Result and detail item shapes.
- Redaction and denylist requirements.
- JSONL, SQLite, MemoryFacade, API, and Cockpit boundaries.
- Error, degradation, and empty result models.
- Required controls before future implementation.

## 3. Non-Goals

- Do not add query implementation.
- Do not modify MemoryFacade.
- Do not modify SQLite.
- Do not modify JSONL recording.
- Do not add API endpoints.
- Do not add UI components.
- Do not modify frontend/Cockpit behavior.
- Do not modify runtime behavior.
- Do not rewrite prompts.
- Do not execute RETRY.
- Do not execute REPLAN.
- Do not call providers/models.
- Do not change provider routing.
- Do not change runtime output.
- Do not enable copy/export.
- Do not approve autonomous execution.

## 4. Relationship To Historical Audit View Design

The historical audit view design defines the future Cockpit experience for
readonly inspection of persisted dry-run evidence. This query contract narrows
that design into a safe backend-facing contract that the view must consume.

The view must not read raw JSONL lines or raw SQLite rows. It should consume a
future query result that has already passed MemoryFacade/API allowlisting,
bounding, and redaction.

## 5. Relationship To Dry-Run Persistence Governance

The dry-run persistence governance review approved documentation, readonly
diagnostics, sanitized audit metadata persistence, and future historical audit
view design. It did not approve execution, prompt rewriting, provider/model
calls, or use of persisted evidence as execution input.

This contract preserves that governance boundary by making every query
readonly, bounded, allowlisted, and metadata-only.

## 6. Query Contract Goals

- Provide a single safe query shape for RETRY and REPLAN dry-run evidence.
- Support predictable filters for operator and reviewer workflows.
- Bound all query sizes and date ranges.
- Return only safe fields.
- Degrade safely on storage or validation failures.
- Keep JSONL and SQLite behavior consistent at the contract boundary.
- Preserve advisory-only semantics.

## 7. Query Contract Non-Goals

- Do not provide raw storage inspection.
- Do not support arbitrary SQL, JSONPath, regex, or free-text search.
- Do not support prompt, response, payload, file, or command filters.
- Do not provide export.
- Do not provide mutation or cleanup controls.
- Do not provide execution selectors.
- Do not infer approval from query results.

## 8. Evidence Source Model

Supported sources are sanitized evidence records created by existing dry-run
RETRY and REPLAN persistence flows:

1. Runtime creates dry-run plan metadata.
2. Runtime records sanitized evidence best-effort through MemoryFacade.
3. JSONL remains the default audit path when available.
4. SQLite remains opt-in structured storage.
5. A future query boundary reads only sanitized, allowlisted fields.
6. Cockpit consumes the safe query response.

The query layer must treat storage records as untrusted until normalized.

## 9. Supported Evidence Types

Supported event types:

- `dry_run_retry_plan_evidence`
- `dry_run_replan_plan_evidence`

Supported plan types:

- `dry_run_retry`
- `dry_run_replan`

Unknown evidence types must be rejected or omitted safely.

## 10. Supported Filters

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
- `created_at_from`
- `created_at_to`
- `recorded_at_from`
- `recorded_at_to`

Unsupported filters must be rejected with a safe validation error or ignored
only if the API contract explicitly documents ignore behavior. Silent broad
queries should be avoided.

## 11. Filter Validation Rules

Validation requirements:

- Accept only allowlisted filter names.
- Reject unknown filter names by default.
- Reject arrays unless a specific filter is approved for multiple values.
- Bound all string values before storage lookup.
- Normalize enum casing only if documented.
- Reject empty strings for required filter values.
- Reject raw storage fragments, raw JSON, SQL snippets, file paths, command
  fragments, prompt text, response text, and provider payload fragments.
- Return safe validation errors without echoing unsafe input.

## 12. Safe ID Validation Rules

ID filters are optional and allowed only when already sanitized:

- `request_id`
- `trace_id`
- `session_id`

Safe ID constraints:

- Maximum length should be explicit, for example 128 characters.
- Allowed characters should be limited to alphanumeric, underscore, hyphen,
  colon, and period.
- Control characters must be rejected.
- Whitespace must be rejected or trimmed before validation.
- Raw object reprs must be rejected.
- IDs must not contain path separators, shell metacharacters, URL query
  strings, secrets, tokens, prompts, responses, or payload fragments.

## 13. Date Range Validation Rules

Date filters:

- `created_at_from`
- `created_at_to`
- `recorded_at_from`
- `recorded_at_to`

Validation requirements:

- Accept ISO 8601 timestamps only.
- Normalize to UTC or clearly document timezone handling.
- Reject invalid timestamps.
- Reject inverted ranges.
- Bound maximum range length before implementation, for example 30 or 90 days.
- Apply conservative defaults when no range is supplied.
- Do not allow unbounded historical scans.

## 14. Enum Validation Rules

Allowed `plan_type` values:

- `dry_run_retry`
- `dry_run_replan`

Allowed `event_type` values:

- `dry_run_retry_plan_evidence`
- `dry_run_replan_plan_evidence`

Allowed `source_decision` values:

- `CONTINUE`
- `RETRY`
- `REPLAN`
- `SELF_REPAIR`
- `SWITCH_PROVIDER`
- `PAUSE`
- `ESCALATE_TO_MISAEL`
- `ABORT_SAFE`
- `UNKNOWN`

Allowed `risk_level` values:

- `low`
- `medium`
- `high`
- `unknown`

Allowed `storage_mode` values:

- `jsonl`
- `sqlite`
- `unavailable`
- `unknown`

Unknown enum values must not pass through as display text.

## 15. Boolean Validation Rules

Boolean filters:

- `blocked`
- `recorded`
- `degraded`
- `sqlite_enabled`

Validation requirements:

- Accept real booleans in typed APIs.
- For query strings, accept only documented boolean encodings, for example
  `true` and `false`.
- Reject `1`, `0`, `yes`, `no`, or arbitrary truthy strings unless explicitly
  approved.
- Missing boolean filters mean no filtering on that field.
- Boolean values must never trigger mutation or execution.

## 16. Pagination Model

Pagination must be bounded.

Recommended contract:

- Default `limit`: 25.
- Maximum `limit`: 100.
- Minimum `limit`: 1.
- `offset` maximum: explicit and bounded, for example 10,000.
- Cursor pagination is preferred for SQLite implementation if stable ordering
  is available.
- No unbounded queries.
- No full table scans from Cockpit without limit.
- Total counts are optional and should be returned only when cheap and safe.

If using cursors, cursors must be opaque, bounded, and non-executable. Cursors
must not contain raw SQL, raw paths, raw row data, raw JSONL lines, or secrets.

## 17. Sorting Model

Allowed sort fields only:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`
- `plan_type`
- `event_type`

Allowed sort directions:

- `asc`
- `desc`

Default sort should be `recorded_at desc` or `created_at desc`. Sort fields
must be mapped through a static allowlist, never interpolated directly into SQL
or storage queries.

## 18. Result Item Shape

List results should contain compact safe metadata only:

```json
{
  "event_type": "dry_run_retry_plan_evidence",
  "plan_id": "bounded-plan-id",
  "plan_type": "dry_run_retry",
  "advisory": true,
  "would_retry": false,
  "would_replan": null,
  "blocked": true,
  "risk_level": "medium",
  "source_decision": "RETRY",
  "fingerprint_id": "bounded-fingerprint",
  "progress_score": 0.2,
  "stagnation_score": 0.8,
  "retry_eligibility_score": 0.4,
  "replan_eligibility_score": null,
  "repeated_strategy_count": 2,
  "suggested_retry_strategy": "same_provider_retry",
  "suggested_strategy": null,
  "evidence_summary": "bounded sanitized summary",
  "created_at": "2026-06-29T00:00:00Z",
  "recorded_at": "2026-06-29T00:00:01Z",
  "request_id": "optional-sanitized-id",
  "session_id": "optional-sanitized-id",
  "trace_id": "optional-sanitized-id",
  "persistence": {
    "recorded": true,
    "degraded": false,
    "storage_mode": "jsonl",
    "sqlite_enabled": false
  }
}
```

Fields that do not apply to a plan type should be omitted or null, consistently
with the future API contract.

## 19. Detail Item Shape

Detail results may include the same safe fields as list items plus:

- `block_reasons`, bounded list of safe categorical strings.
- Allowlisted diagnostic details only.
- Safe storage metadata as categorical values only.

Detail responses must not include raw records, raw JSONL lines, raw SQLite rows,
raw exception objects, raw Python reprs, prompts, rewritten prompts, responses,
provider payloads, command args, file contents, or secrets.

## 20. Redaction/Allowlist Model

The query contract must use allowlisting, not best-effort denylisting.

Allowlisted categories:

- Known enum values.
- Booleans.
- Numeric scores and counts.
- Safe timestamps.
- Bounded sanitized identifiers.
- Bounded sanitized summaries.
- Bounded categorical block reasons.
- Safe persistence diagnostic booleans and categorical values.

Every string returned to Cockpit must be bounded and sanitized before it enters
the response shape.

## 21. Denylist Model

Forbidden fields and content:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys, tokens, or secrets.
- Headers or cookies.
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
- Raw JSONL lines.
- Screenshots exposing secrets or raw payloads.

The denylist is a final safety net. The primary control remains the allowlist.

## 22. Error/Degradation Response Model

Errors must be safe and categorical.

Recommended response fields:

- `items`: safe list, possibly empty.
- `degraded`: boolean.
- `error_category`: safe enum or null.
- `storage_mode`: `jsonl`, `sqlite`, `unavailable`, or `unknown`.
- `next_cursor`: safe opaque cursor or null.
- `limit`: applied bounded limit.

Forbidden error response data:

- Raw exception message.
- Traceback.
- Stack trace.
- SQL statement.
- File path.
- JSONL path.
- SQLite path.
- Raw object repr.
- Prompt, response, payload, command, or secret content.

## 23. Empty Result Model

Empty results are valid and should not be treated as failure.

Empty response shape should include:

- `items: []`
- `degraded: false` when the query succeeded.
- Applied filters, if safe and normalized.
- Pagination metadata with no next page.

If storage is unavailable, return empty safe results with degradation metadata
rather than crashing the caller.

## 24. Storage-Mode Behavior

`storage_mode` is audit storage metadata only. It must not change autonomy
behavior and must not imply authorization.

Supported values:

- `jsonl`
- `sqlite`
- `unavailable`
- `unknown`

The contract should allow callers to filter by storage mode only for audit
interpretation.

## 25. JSONL Behavior

JSONL remains the default audit recording path, but the future query contract
must not expose raw JSONL lines.

JSONL query behavior should:

- Return sanitized, normalized items only.
- Degrade safely if JSONL is unavailable or unreadable.
- Avoid unbounded file scans.
- Avoid returning file paths.
- Avoid returning raw line content.

If JSONL querying is not implemented initially, the response should make that
clear through safe `storage_mode` and `degraded` metadata.

## 26. SQLite Behavior

SQLite remains opt-in structured evidence storage.

SQLite query behavior should:

- Use parameterized queries only.
- Map sort fields through static allowlists.
- Enforce bounded limits and date ranges.
- Return empty results on read failure.
- Never expose raw rows.
- Never expose SQLite paths.
- Preserve JSONL default behavior.

SQLite enabled/disabled must not change autonomy behavior, provider routing,
prompt handling, runtime output, or execution behavior.

## 27. MemoryFacade Boundary

MemoryFacade should be the only future backend access boundary for historical
dry-run audit queries.

Required MemoryFacade controls before implementation:

- Query input model with allowlisted filters.
- Result model with allowlisted fields.
- Bounded pagination.
- Safe sort mapping.
- Sanitized ID validation.
- Read failure degradation to empty safe results.
- No raw JSONL or SQLite row exposure.
- No execution coupling.

MemoryFacade must not become a retry queue, replan queue, action queue, or
provider-routing input.

## 28. API Boundary Design

A future API endpoint, if approved separately, should expose only the
MemoryFacade query contract.

API requirements:

- Readonly method only.
- Auth/protection consistent with existing Cockpit runtime diagnostics.
- Strict schema validation.
- Safe validation errors.
- Bounded pagination.
- Static sort allowlist.
- No raw storage fields.
- No copy/export endpoint.
- No mutation endpoint.
- No execution endpoint.

The API must not accept filters that can select prompts, responses, provider
payloads, command args, file contents, raw rows, or raw JSONL lines.

## 29. Cockpit Consumption Model

Cockpit should consume normalized query responses and render only safe fields.

Consumption requirements:

- Preserve readonly labels.
- Show "Advisory-only" and "Not execution input".
- Show "No retry executed" for RETRY evidence.
- Show "No replan executed" for REPLAN evidence.
- Treat missing fields as unavailable.
- Render empty states safely.
- Do not use `dangerouslySetInnerHTML`.
- Do not expose raw storage details.
- Do not add execution controls.

## 30. Copy/Export Exclusion

Copy/export is excluded from this contract.

Copy/export remains disabled until separate governance approval. Future copy
or export design must define:

- Separate allowlist.
- Review-safe summaries.
- Redaction gates.
- Role/access controls.
- Evidence provenance.
- Explicit non-execution warnings.

Raw JSONL, raw SQLite rows, raw prompts, rewritten prompts, responses,
provider payloads, and secrets must never be export targets.

## 31. Abuse/Misuse Cases

Misuse cases to prevent:

- Treating `would_retry=true` as retry execution.
- Treating `would_replan=true` as replan execution.
- Treating `blocked=false` as approval.
- Treating scores as permission.
- Treating suggested strategies as instructions.
- Using filters as execution selectors.
- Scraping all historical evidence through unbounded queries.
- Searching for secrets through raw text filters.
- Displaying raw rows under a debug option.
- Exporting evidence without governance.
- Feeding persisted evidence into an executor.

## 32. Security Review Checklist

Before implementation, verify:

- Only allowlisted filters are accepted.
- Enum values are constrained.
- Booleans are strictly parsed.
- IDs are bounded and sanitized.
- Date ranges are bounded.
- Pagination is bounded.
- Sort fields use a static mapping.
- Responses omit forbidden fields.
- Error responses are categorical and safe.
- Raw JSONL lines are never returned.
- Raw SQLite rows are never returned.
- No prompts, responses, payloads, commands, files, receipts, or secrets are
  exposed.
- No execution controls are introduced.

## 33. Testing Strategy

Future implementation should test:

- Each supported filter.
- Unknown filter rejection.
- Enum validation.
- Boolean validation.
- Safe ID validation.
- Invalid and inverted date ranges.
- Pagination defaults and maximums.
- Sort field and direction validation.
- Empty results.
- Storage unavailable degradation.
- JSONL unavailable degradation.
- SQLite read failure degradation.
- Forbidden field exclusion.
- Raw row and raw JSONL exclusion.
- Cockpit rendering of missing/degraded data.
- No execution behavior.

## 34. Required Controls Before MemoryFacade Query Implementation

- Approved query input model.
- Approved result/detail models.
- Allowlisted storage mappings.
- Bounded pagination.
- Bounded date range behavior.
- Safe error categories.
- Tests for corrupt or malformed stored records.
- Tests that raw rows and raw JSONL lines are not returned.
- Confirmation persisted evidence is not execution input.

## 35. Required Controls Before API Implementation

- MemoryFacade query implementation reviewed.
- API auth/protection pattern selected.
- Request schema validation.
- Response schema validation.
- Safe validation errors.
- Rate or size limits if needed.
- No copy/export route.
- No mutation route.
- No execution route.
- Security review for query abuse.

## 36. Required Controls Before Cockpit Implementation

- API contract approved.
- Frontend normalizer approved.
- Empty, loading, degraded, and error states designed.
- Readonly labels approved.
- No `dangerouslySetInnerHTML`.
- No raw storage rendering.
- No action controls.
- Tests for forbidden field suppression.

## 37. Required Controls Before Copy/Export Governance

- Separate governance review.
- Separate export allowlist.
- Safe summary format.
- Operator/reviewer warnings.
- Role or access model.
- Audit trail for export invocation.
- Explicit ban on raw JSONL, raw SQLite rows, prompts, responses, provider
  payloads, command args, file contents, and secrets.

## 38. Required Controls Before Retention/Cleanup Integration

- Separate retention/cleanup design.
- Proof that query filters cannot trigger cleanup.
- Proof that cleanup cannot use query result rows as execution input.
- Safe lifecycle diagnostics.
- Tests that cleanup deletes only approved expired metadata.
- No Cockpit destructive control without separate governance.

## 39. Required Controls Before Any Execution Design

- Separate governance review.
- Separate threat model.
- Explicit approval from Misael.
- Proof persisted evidence is not used as execution input.
- Prompt rewrite controls, if ever considered, reviewed separately.
- Provider/model call controls reviewed separately.
- Runtime output preservation reviewed separately.
- Human approval boundaries defined.

## 40. Explicit Non-Approval Statement

This design approves documentation only. It does not approve MemoryFacade query
implementation, API implementation, Cockpit implementation, copy/export,
retention/cleanup integration, prompt rewriting, provider/model retry
execution, provider/model replan execution, persisted evidence as execution
input, or autonomous execution.

## 41. Open Risks

- Operators may overinterpret historical evidence as approval.
- Filters could become too broad if not bounded.
- Future debug views could accidentally expose raw rows.
- JSONL querying could become expensive without limits.
- SQLite query implementation could introduce unsafe dynamic sorting if not
  mapped through an allowlist.
- Copy/export pressure could bypass review-safe summaries.

## 42. Open Questions

- Should cursor pagination be required from the first implementation, or is a
  bounded offset acceptable initially?
- What maximum date range should be allowed?
- Should total counts be omitted by default to avoid expensive scans?
- Which auth/protection pattern should gate a future API endpoint?
- Should JSONL querying be supported initially or treated as unavailable for
  historical view queries?

## 43. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Docs/design | Go | This document is approved as design-only work. |
| MemoryFacade query implementation | No-go | Requires controls in section 34. |
| API query endpoint implementation | No-go | Requires controls in section 35. |
| Cockpit query UI implementation | No-go | Requires controls in section 36. |
| Safe filters | Go for design | Implementation requires validation tests. |
| Safe detail drawer | Go for design | Must remain allowlisted and readonly. |
| Copy safe summary | No-go | Requires separate copy/export governance. |
| Export JSON/CSV | No-go | Requires separate governance. |
| Raw JSONL display | No-go | Forbidden. |
| Raw SQLite row display | No-go | Forbidden. |
| Prompt rewrite | No-go | Not approved. |
| Provider/model retry execution | No-go | Not approved. |
| Provider/model replan execution | No-go | Not approved. |
| Persisted evidence as execution input | No-go | Forbidden. |
| Autonomous execution | No-go | Omni remains advisory-only. |

## 44. Final Recommendation

Proceed only with documentation review for this query contract. The next safe
step is a MemoryFacade query implementation design or governance checkpoint,
not implementation, unless Misael explicitly approves moving beyond design.

The future query contract should remain readonly, bounded, allowlisted,
metadata-only, and disconnected from execution. Omni remains advisory-only.
