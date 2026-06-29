# Autonomy Dry-Run Historical Audit API Contract Design

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-historical-audit-api-contract-design`
**Base:** `main` after PR #469
**Status:** Contract design only
**Runtime impact:** None

## 1. Executive Summary

This document defines placeholder API contracts for future readonly historical
dry-run RETRY and REPLAN audit endpoints. The contracts describe request
parameters, response envelopes, error categories, pagination, validation,
safe fields, forbidden fields, examples, and future test expectations.

This design does not approve API implementation or exposure. It does not add
endpoints, handlers, code schemas, frontend components, Cockpit behavior,
runtime behavior, provider/model calls, prompt rewriting, retry execution,
replan execution, or autonomous execution.

## 2. Scope

This contract design covers:

- Candidate readonly list/detail endpoint contracts.
- Query and path parameter contracts.
- Filter, sort, pagination, timestamp, and ID validation contracts.
- Response, warning, degradation, and error category contracts.
- Safe field allowlists and forbidden field denylists.
- Internal service delegation rules.
- Rate/size limits and safe audit logging expectations.
- Future implementation and security test matrices.
- Required controls before implementation and exposure.

## 3. Non-Goals

- Do not implement endpoints.
- Do not add route handlers.
- Do not add API schemas in code.
- Do not expose the API.
- Do not add frontend or Cockpit UI.
- Do not add detail drawer consumption.
- Do not add copy/export.
- Do not modify runtime, persistence, MemoryFacade, internal service, SQLite,
  or frontend code.
- Do not rewrite prompts.
- Do not execute RETRY or REPLAN.
- Do not call providers/models.
- Do not use persisted evidence as execution input.
- Do not approve autonomous execution.

## 4. Relationship To API Boundary Design

The API boundary design defines the safety architecture: future API callers
must be authenticated, authorized, rate-limited, size-limited, and delegated
only to the internal historical dry-run audit query service.

This contract design narrows that boundary into concrete placeholder request
and response contracts. It does not change the boundary decision that API
implementation remains blocked.

## 5. Relationship To API Boundary Governance Review

The API boundary governance review approved documentation and API boundary
design only. It kept API implementation and exposure blocked until separate
implementation work supplies strict validation, access control, rate limits,
logging controls, and tests.

This document follows that governance decision. It is a contract design
artifact, not implementation approval.

## 6. Candidate Endpoint Inventory

Candidate endpoints, design only:

- `GET /internal/audit/dry-run`
- `GET /internal/audit/dry-run/{plan_id}`

Endpoint names are placeholders. Future implementation must validate these
paths against existing API route conventions and protection patterns.

## 7. List Endpoint Contract

`GET /internal/audit/dry-run`

Purpose:

- Return a bounded, paginated list of sanitized historical dry-run RETRY and
  REPLAN audit evidence.

Contract rules:

- Readonly.
- Authenticated and authorized before service delegation.
- Query parameters only; no raw request body needed.
- Static filter and sort allowlists.
- Bounded pagination.
- Sanitized response envelope only.
- Delegates only to the internal query service.

## 8. Detail Endpoint Contract

`GET /internal/audit/dry-run/{plan_id}`

Purpose:

- Return a sanitized detail item for one historical dry-run audit plan ID.

Contract rules:

- `plan_id` must pass sanitized ID validation.
- Invalid `plan_id` must not call the internal service.
- Not-found responses must be safe and metadata-only.
- Detail responses must not expose raw storage records.
- Detail responses must not include raw diagnostic object dumps.

## 9. Authentication Requirement Placeholder

Authentication is required before implementation or exposure.

Placeholder requirement:

- Future routes must reuse an existing safe authentication convention when one
  exists.
- If no safe convention exists, implementation must stop for separate
  authentication design.
- Unauthenticated requests must be rejected before validation work that could
  call the internal service.

## 10. Authorization Requirement Placeholder

Authorization is required before implementation or exposure.

Placeholder requirement:

- Callers must have explicit readonly historical audit metadata permission.
- Permission must not imply runtime control, retry/replan execution,
  provider/model call authority, cleanup authority, or copy/export authority.
- Cockpit visibility must not be treated as authorization.

## 11. Query Parameter Contract

Supported list query parameters:

- `plan_type`
- `event_type`
- `source_decision`
- `risk_level`
- `blocked`
- `recorded`
- `degraded`
- `storage_mode`
- `sqlite_enabled`
- `request_id`
- `trace_id`
- `session_id`
- `created_at_from`
- `created_at_to`
- `recorded_at_from`
- `recorded_at_to`
- `sort_by`
- `sort_direction`
- `limit`
- `offset`

`cursor` is reserved for a future opaque cursor design. This contract uses
bounded `offset` to align with the current internal query model.

Unsupported parameters must be rejected or safely ignored with warnings,
following the internal request model behavior chosen during implementation.

## 12. Path Parameter Contract

Supported detail path parameter:

- `plan_id`

Validation rules:

- Maximum length must match the sanitized audit ID limit.
- Empty, redacted, path-like, or query-injection-like values are invalid.
- Invalid values must not be echoed raw.
- Invalid values must not trigger MemoryFacade or storage access.

## 13. Filter Allowlist Contract

Allowed filters:

- `plan_type`
- `event_type`
- `source_decision`
- `risk_level`
- `blocked`
- `recorded`
- `degraded`
- `storage_mode`
- `sqlite_enabled`
- `request_id`
- `trace_id`
- `session_id`
- `created_at_from`
- `created_at_to`
- `recorded_at_from`
- `recorded_at_to`

No other filter is allowed to influence query results.

## 14. Sort Allowlist Contract

Allowed `sort_by` values:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`

Allowed `sort_direction` values:

- `asc`
- `desc`

Raw SQL, arbitrary column names, nested field paths, and storage-specific
ordering clauses are forbidden.

## 15. Pagination Contract

Pagination must be bounded:

- Default limit: conservative and aligned with internal query defaults.
- Maximum limit: explicit and aligned with internal query max page size.
- Offset: bounded and non-negative.
- Cursor: reserved for future opaque cursor design, not mixed with raw storage
  cursor values.
- Page info must not expose raw row IDs or storage cursors.
- Unbounded queries are forbidden.

## 16. Timestamp Validation Contract

Timestamp parameters:

- `created_at_from`
- `created_at_to`
- `recorded_at_from`
- `recorded_at_to`

Rules:

- Accept safe ISO-like timestamps only.
- Normalize to safe timestamp representation.
- Reject invalid ranges.
- Do not echo unsafe raw timestamp input.
- Do not accept SQL expressions, relative expressions, or natural-language
  date selectors in the API contract.

## 17. Sanitized ID Validation Contract

Sanitized ID parameters:

- `request_id`
- `trace_id`
- `session_id`
- `plan_id`

Rules:

- Bounded length.
- Safe characters only.
- No path separators.
- No query-string metacharacters.
- No quotes, pipes, shell metacharacters, or traversal tokens.
- Redacted values are treated as invalid.

## 18. Request Examples

Safe list request:

```text
GET /internal/audit/dry-run?plan_type=dry_run_retry&risk_level=low&blocked=false&sort_by=recorded_at&sort_direction=desc&limit=25&offset=0
```

Safe filtered request:

```text
GET /internal/audit/dry-run?event_type=dry_run_replan_plan_evidence&source_decision=REPLAN&created_at_from=2026-06-29T00:00:00Z&created_at_to=2026-06-30T00:00:00Z
```

Safe detail request:

```text
GET /internal/audit/dry-run/plan-abc-123
```

Forbidden examples:

```text
GET /internal/audit/dry-run?sort_by=recorded_at;select *
GET /internal/audit/dry-run?raw_sql=select * from evidence
GET /internal/audit/dry-run/../secrets
```

## 19. Success Response Envelope

List success envelope:

```json
{
  "items": [],
  "page_info": {
    "limit": 25,
    "offset": 0,
    "returned_count": 0,
    "has_more": false,
    "next_offset": null
  },
  "applied_filters": {},
  "warnings": [],
  "degraded": false,
  "generated_at": "2026-06-29T00:00:00Z"
}
```

`error_category` should appear only when `degraded=true`.

## 20. List Item Contract

Safe list item fields:

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
- sanitized `request_id`, `session_id`, and `trace_id` when present
- safe persistence diagnostics only

## 21. Detail Item Contract

Safe detail item fields are the list item fields plus bounded, allowlisted
diagnostic metadata from the internal service detail model.

Forbidden detail output:

- Raw storage record.
- Raw JSONL line.
- Raw SQLite row.
- Raw SQL.
- Raw diagnostic object dump.
- Raw exception or traceback.

## 22. Page Info Contract

`page_info` fields:

- `limit`
- `offset`
- `returned_count`
- `has_more`
- `next_offset`

Rules:

- Values must be numeric or boolean.
- `next_offset` must be bounded when present.
- Raw storage cursors, row IDs, SQL offsets, and file positions are forbidden.

## 23. Warning Contract

Warnings are safe strings only. Allowed warning categories should include:

- `unsupported_filter`
- `invalid_query_request`
- `invalid_service_request`
- `historical_audit_query_requires_sqlite`
- `historical_audit_service_query_failed`
- `invalid_memoryfacade_response`

Warnings must not include raw user input, raw exceptions, stack traces, SQL,
rows, JSONL lines, prompts, responses, provider payloads, tool outputs,
headers, cookies, tokens, or secrets.

## 24. Degradation Contract

`degraded=true` means the request was handled safely but the API could not
return normal results. It does not mean autonomy failed, execution was
attempted, or approval changed.

Degraded responses must:

- Return safe metadata only.
- Include a categorical `error_category`.
- Preserve the response envelope where possible.
- Avoid raw exception or storage details.

## 25. Error Category Contract

Allowed error categories should include:

- `invalid_request`
- `invalid_filter`
- `invalid_sort`
- `unauthenticated`
- `unauthorized`
- `rate_limited`
- `payload_too_large`
- `storage_unavailable`
- `query_failed`
- `not_found`
- `invalid_memoryfacade_response`
- `unknown`

Error categories are categorical metadata only.

## 26. Safe Field Allowlist

Safe fields:

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
- sanitized `request_id`, `session_id`, and `trace_id` when present
- safe persistence diagnostics only
- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category`
- `generated_at`

## 27. Forbidden Field Denylist

Forbidden fields:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys.
- Tokens.
- Secrets.
- Headers.
- Cookies.
- Stack traces.
- Tracebacks.
- Stdout.
- Stderr.
- Command args.
- File contents.
- `.env` content.
- Full tool outputs.
- Raw receipts.
- Raw exception objects.
- Raw Python reprs.
- Raw DB rows.
- Raw SQL.
- Raw JSONL lines.
- Screenshots exposing secrets or raw payloads.

## 28. HTTP Status Design

Suggested status design:

- `200`: successful list/detail response.
- `400`: invalid request, invalid filter, invalid sort, invalid timestamp, or
  invalid ID.
- `401`: unauthenticated.
- `403`: unauthorized.
- `404`: safe not-found detail response.
- `413`: request or query exceeds size limits.
- `429`: rate limited.
- `503`: internal query service or storage unavailable through safe boundary.

Status codes are design placeholders and must be aligned with repo API
conventions before implementation.

## 29. Rate/Size Limit Contract

Future implementation must define:

- Default limit.
- Maximum limit.
- Maximum offset.
- Maximum query string length.
- Maximum number of filters.
- Maximum ID length.
- Maximum timestamp range if needed.
- Per-caller or per-session rate limits.

Exceeded limits must fail safely without service delegation when possible.

## 30. Safe Audit Logging Contract

Safe API access logs may include:

- Operation name.
- Safe caller category or safe caller ID if approved.
- Safe filter keys.
- Sort field and direction.
- Limit and offset.
- Response status category.
- Degraded boolean.
- Categorical error category.
- Generated timestamp.

Forbidden logs:

- Raw request body.
- Raw response body.
- Raw exception.
- Traceback.
- Prompt or response.
- Provider payload.
- Tool output.
- Headers or cookies.
- Tokens or secrets.
- Raw SQL.
- Raw row.
- Raw JSONL line.

## 31. Internal Delegation Contract

Required dependency path:

API boundary -> internal query service -> MemoryFacade safe query contracts.

The API layer must delegate only to:

- `query_historical_dry_run_audit(...)`
- `get_historical_dry_run_audit_detail(...)`

or an equivalent future internal service method approved by governance.

## 32. No Direct MemoryFacade Access Contract

The API contract must not allow direct MemoryFacade calls. Direct
API-to-MemoryFacade access would bypass the validation, degradation, and safe
logging boundary introduced by the internal service.

## 33. No Raw Storage/SQL Contract

The API contract must not permit:

- Raw JSONL access.
- Raw SQLite access.
- Raw SQL filters.
- Raw SQL sorting.
- Raw row selectors.
- Storage file paths.
- Storage cursor exposure.

Storage access remains below MemoryFacade and outside the API contract.

## 34. No Execution-Input Contract

API results are not execution input. They must not be used to select,
authorize, or trigger:

- RETRY.
- REPLAN.
- Prompt rewriting.
- Provider/model calls.
- Provider switching.
- Tool execution.
- Command execution.
- File writes.
- CI repair.
- Commit, push, or PR automation.
- Autonomous execution.

## 35. Copy/Export Exclusion Contract

The API contract does not include:

- Copy safe summary.
- CSV export.
- JSON export.
- Raw JSONL export.
- Raw SQLite row export.
- Bulk dump endpoint.

Copy/export remains disabled until separate governance approval.

## 36. Abuse/Misuse Cases

Misuse cases:

- Treating API results as approval.
- Treating API results as execution input.
- Treating `would_retry=true` as retry execution.
- Treating `would_replan=true` as replan execution.
- Treating `blocked=false` as permission.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Using filters as execution selectors.
- Attempting SQL injection through sort/filter fields.
- Attempting path traversal through `plan_id`.
- Scraping data through unbounded pagination.
- Exposing the endpoint without authorization.

## 37. Future Implementation Test Matrix

Future implementation tests must cover:

- Authorized list request.
- Authorized detail request.
- Unauthenticated rejection.
- Unauthorized rejection.
- Invalid filter rejection or safe warning.
- Invalid sort rejection.
- Invalid timestamp rejection.
- Invalid ID rejection.
- Limit clamping or rejection.
- Offset bounds.
- Safe not-found detail response.
- Internal service-only delegation.
- No direct MemoryFacade calls.
- No runtime calls.
- No provider/model calls.
- No copy/export route.

## 38. Security Test Matrix

Security tests must prove:

- No raw prompt exposure.
- No rewritten prompt exposure.
- No raw response exposure.
- No provider payload exposure.
- No credential, API key, token, secret, header, or cookie exposure.
- No stack trace or traceback exposure.
- No stdout/stderr exposure.
- No command args exposure.
- No file content or `.env` exposure.
- No raw tool output exposure.
- No raw receipt exposure.
- No raw exception object or Python repr exposure.
- No raw DB row exposure.
- No raw SQL exposure.
- No raw JSONL line exposure.
- No execution path can be triggered.

## 39. Required Controls Before Implementation

Required controls:

- Typed request schema.
- Static filter allowlist.
- Static sort allowlist.
- Enum validation.
- Bounded limit and max page size.
- Deterministic ordering.
- Timestamp range validation.
- Sanitized ID validation.
- Internal service-only delegation.
- No direct MemoryFacade access.
- No raw storage access.
- No raw SQL exposure.
- Safe response envelope only.
- Safe error categories only.
- No raw request/response logging.
- No raw exception/traceback logging.
- Negative tests for forbidden fields.
- Tests proving no runtime/provider execution path.

## 40. Required Controls Before Exposure

Required controls:

- Authentication.
- Explicit authorization.
- Readonly permission model.
- Rate limits.
- Size limits.
- Request validation.
- Safe audit logging.
- Abuse-case review.
- Security review.
- No public exposure without separate approval.
- Operational ownership.
- Confirmation copy/export remains absent.

## 41. Explicit Non-Approval Statement

This contract design does not approve:

- API implementation.
- API exposure.
- Frontend/Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Raw JSONL reads.
- Raw SQLite row reads.
- Raw SQL filters.
- Direct API-to-MemoryFacade access.
- Runtime calls.
- Provider/model calls.
- Prompt rewrite.
- Retry execution.
- Replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 42. Open Risks

- Contract fields may drift from future service model changes.
- Existing auth conventions may not fit the endpoint.
- Offset pagination may be insufficient for large audit volumes.
- Operators may misread advisory metadata as approval.
- API implementation could accidentally bypass the internal service.
- Error handling could leak details without negative tests.
- Copy/export pressure could expand scope.

## 43. Open Questions

- Should future implementation use offset initially or move directly to opaque
  cursor?
- Which authentication mechanism should protect the endpoints?
- Which authorization role should grant readonly audit metadata access?
- Should detail not-found return `404` or a degraded envelope with no item?
- Should storage unavailable return `503` or `200` with `degraded=true`?
- What rate limits are appropriate for local and deployed modes?
- Should safe caller metadata be logged as ID, role, or category?

## 44. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | Approved. |
| API contract design | Go | This document. |
| API implementation | No-Go | Requires separate implementation branch and tests. |
| API exposure | No-Go | Requires auth, authorization, limits, logging, and security review. |
| Frontend/Cockpit consumption | No-Go | Requires separate governance. |
| Detail drawer consumption | No-Go | Requires separate governance. |
| Copy safe summary | No-Go | Copy/export remains disabled. |
| Export JSON/CSV | No-Go | Requires separate governance. |
| Raw JSONL read | No-Go | Forbidden. |
| Raw SQLite row read | No-Go | Forbidden. |
| Raw SQL filters | No-Go | Forbidden. |
| Direct MemoryFacade access from API | No-Go | API must use internal service only. |
| Runtime call | No-Go | Forbidden. |
| Provider/model call | No-Go | Forbidden. |
| Prompt rewrite | No-Go | Forbidden. |
| Provider/model retry execution | No-Go | Forbidden. |
| Provider/model replan execution | No-Go | Forbidden. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Forbidden. |

## 45. Final Recommendation

Approve this API contract design as documentation only. The next safe step may
be a governance review for these contracts. API implementation and exposure
remain blocked until typed schemas, auth, authorization, rate/size limits,
safe logging, safe errors, internal-service-only delegation, and focused
security tests are approved.

Omni remains advisory-only.
