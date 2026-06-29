# Autonomy Dry-Run Historical Audit API Boundary Governance Review

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-historical-audit-api-boundary-governance-review`
**Base:** `main` after PR #468
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

The future readonly API boundary design for historical dry-run RETRY and
REPLAN audit evidence is acceptable as a documentation artifact and as a
future implementation target only under strict controls. The design correctly
requires sanitized audit metadata only, access control before exposure,
rate/size limits, safe audit logging, and the dependency path:

API boundary -> internal query service -> MemoryFacade safe query contracts.

This review does not approve API implementation or exposure. API
implementation remains blocked until a separate implementation branch provides
typed request schemas, static allowlists, safe response envelopes, safe errors,
tests, and proof that no runtime/provider/model/execution path is introduced.

## 2. Scope

This review evaluates the API boundary design from PR #468. It covers:

- Candidate readonly endpoints.
- Request and response models.
- Error and degradation behavior.
- Authentication and authorization assumptions.
- Rate limiting and size limits.
- Filter, sort, pagination, timestamp, and ID validation.
- Safe audit logging.
- Field allowlists and denylists.
- Delegation and storage boundaries.
- Required controls before implementation, exposure, Cockpit consumption,
  copy/export, retention/cleanup integration, and execution design.

## 3. Non-Goals

- Do not implement API endpoints.
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

## 4. Reviewed Materials

Reviewed materials:

- `docs/runtime/autonomy-dry-run-historical-audit-query-contract-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-query-contract-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-internal-query-service-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-internal-query-service-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-internal-query-service-evidence-notes.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-boundary-design.md`
- MemoryFacade safe query contracts from PR #463.
- Internal readonly query service contracts from PR #466.

## 5. Governance Decision Summary

Approved:

- Documentation.
- API boundary design.
- API boundary governance review.

Blocked:

- API implementation until a separate implementation branch with strict tests.
- API exposure until authentication, authorization, rate limits, size limits,
  safe logging, abuse-case review, and security review exist.
- Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Direct API-to-MemoryFacade access.
- Raw JSONL, raw SQLite, and raw SQL access.
- Runtime calls.
- Provider/model calls.
- Prompt rewrite.
- Retry/replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 6. API Boundary Overview Review

The design correctly positions the API as a future readonly boundary that
adapts authorized HTTP requests into typed/sanitized internal service
requests. It requires authentication, authorization, request validation,
internal service-only delegation, sanitized response envelopes, and safe audit
logging.

This boundary is acceptable only if implemented as a narrow adapter. It must
not become a storage layer, query engine, runtime control plane, execution
selector, or export endpoint.

## 7. Candidate Endpoint Review

Candidate endpoints are design placeholders only:

- `GET /internal/audit/dry-run`
- `GET /internal/audit/dry-run/{plan_id}`

The naming is acceptable for design purposes because it signals internal,
readonly audit intent. Implementation remains blocked. Before implementation,
the path naming must be reviewed against existing route conventions and access
control patterns.

## 8. Request Model Review

The request model is acceptable because it is limited to safe filters, bounded
pagination, sort fields, timestamps, and sanitized IDs. It does not include
raw SQL, raw storage selectors, prompt selectors, response selectors, provider
payload selectors, command selectors, file selectors, or credential selectors.

Future implementation must convert HTTP inputs into typed request schemas
before calling the internal service.

## 9. Response Envelope Review

The response envelope is acceptable because it mirrors the internal service
and MemoryFacade safe response shapes:

- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category`, only when degraded
- `generated_at`

Detail responses must remain safe metadata details, not raw storage records.

## 10. Error/Degradation Model Review

The proposed error model is acceptable if implemented with categorical error
responses only. It should cover invalid request, unauthorized caller, rate
limit, service unavailable, storage unavailable through service, and not-found
states without leaking internal details.

Raw exception messages, tracebacks, stack traces, SQL strings, storage paths,
rows, JSONL lines, prompts, responses, payloads, tool outputs, headers,
cookies, credentials, and secrets must never be emitted.

## 11. Access-Control Requirements Review

Access control is mandatory before any implementation or exposure. The design
correctly states that only authorized callers may query historical dry-run
audit metadata and that unauthorized requests must be rejected before service
delegation.

Access must be explicit. Cockpit visibility, local operator access, or stored
audit metadata must not imply authorization.

## 12. Authorization Model Review

The design correctly separates readonly audit metadata access from runtime
execution, administrative maintenance, cleanup, and copy/export authority.

Any future permission should be scoped to readonly audit metadata. It must not
grant retry, replan, provider/model call, prompt rewrite, cleanup, copy/export,
or autonomous execution authority.

## 13. Authentication Assumptions Review

The authentication assumption is acceptable only as a placeholder. Future
implementation must reuse an existing safe authentication convention or stop
for a separate authentication design. An unprotected endpoint is not
acceptable.

Authentication must happen before expensive validation or service delegation.

## 14. Rate Limiting And Size Limits Review

Rate and size limits are required before exposure. The design properly calls
for conservative page sizes, maximum limits, bounded offsets or cursors,
maximum query sizes, safe behavior for repeated invalid queries, and no
unbounded scans.

API implementation must include tests for limit enforcement.

## 15. Filter Validation Review

The filter set is acceptable because it matches the safe query contract:

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

Unsupported or invalid filters must be rejected or safely warned according to
the internal model. Filters must never become execution selectors.

## 16. Sort Validation Review

The sort model is acceptable with these allowlisted fields:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`

Allowed directions must remain `asc` and `desc`. Raw SQL fragments, arbitrary
column names, nested selectors, and storage-specific order clauses are
forbidden.

## 17. Pagination Review

The pagination design is acceptable if implementation enforces:

- Default limit.
- Maximum limit.
- Bounded offset or opaque cursor.
- Deterministic ordering.
- Safe `page_info`.
- No unbounded query path.
- No raw storage cursor or row ID exposure.

## 18. Timestamp And Sanitized ID Validation Review

Timestamp and ID validation requirements are adequate. Future implementation
must accept only safe timestamp formats, reject invalid ranges, sanitize
request/session/trace IDs, sanitize `plan_id`, reject path traversal and query
injection characters, and avoid echoing rejected raw input.

## 19. Safe Audit Logging Review

The logging model is acceptable because it limits logs to metadata such as
operation name, safe caller category or ID, safe filter keys, sort key,
bounded limit, pagination metadata, generated timestamp, degraded boolean,
categorical error category, and response status category.

Forbidden logs include raw request bodies, raw response bodies, raw exception
objects, tracebacks, prompts, responses, provider payloads, tool outputs,
headers, cookies, tokens, secrets, SQL, rows, and JSONL lines.

## 20. Safe Field Allowlist Review

The safe field allowlist is acceptable and should remain closed by default.
Allowed fields include plan metadata, advisory flags, would_retry/would_replan,
blocked, bounded block reasons, risk/source categories, scores, bounded
evidence summaries, safe timestamps, sanitized IDs, persistence diagnostics,
page info, applied filters, warnings, degraded, error category, and
generated_at.

New fields require governance review before exposure.

## 21. Forbidden Field Denylist Review

The denylist is adequate and must remain enforced. Forbidden output includes
raw prompts, rewritten prompts, raw responses, provider payloads, credentials,
API keys, tokens, secrets, headers, cookies, stack traces, tracebacks,
stdout/stderr, command args, file contents, `.env` content, full tool outputs,
raw receipts, raw exception objects, raw Python reprs, raw database rows, raw
SQL, raw JSONL lines, storage paths, and sensitive screenshots.

## 22. Internal Service-Only Delegation Review

The service-only delegation rule is mandatory. The only approved dependency
direction for future implementation is:

API boundary -> internal query service -> MemoryFacade safe query contracts.

Any bypass requires a new governance review. Direct API-to-MemoryFacade,
API-to-SQLite, API-to-JSONL, API-to-runtime, or API-to-provider/model paths are
blocked.

## 23. No Direct MemoryFacade Access Review

Direct API-to-MemoryFacade access remains blocked. The internal service
centralizes request validation, safe degradation, and audit logging. Bypassing
it would duplicate or weaken safeguards.

## 24. No Raw Storage Access Review

The API must never read raw JSONL files, SQLite files, SQLite rows, database
paths, storage internals, or raw persistence records. Storage behavior must
remain hidden behind MemoryFacade and the internal service.

## 25. No Raw SQL Review

Raw SQL remains forbidden at the API boundary. The API must not accept, build,
log, return, or expose SQL. Filtering and sorting must use static allowlists.

## 26. No Copy/Export Review

Copy/export remains blocked. The API must not expose CSV export, JSON export,
raw row export, raw JSONL export, copy-to-clipboard summaries, or bulk dump
endpoints.

Copy/export requires separate governance because it changes the risk profile
of otherwise readonly metadata.

## 27. No Execution-Input Review

API results must never become execution input. They must not select,
authorize, or trigger RETRY, REPLAN, prompt rewriting, provider/model calls,
provider switching, tool execution, command execution, file writes, CI repair,
Git automation, PR automation, or autonomous execution.

## 28. Abuse/Misuse Cases

Primary misuse cases:

- Treating `would_retry=true` as retry execution or approval.
- Treating `would_replan=true` as replan execution or approval.
- Treating `blocked=false` as permission.
- Treating eligibility scores as authorization.
- Treating suggested strategies as instructions.
- Using filters as execution selectors.
- Scraping metadata through unbounded pagination.
- Injecting SQL through filter/sort fields.
- Traversing paths through `plan_id`.
- Retrieving raw JSONL or SQLite rows.
- Exposing the endpoint without auth.
- Logging sensitive request or response material.

## 29. Security Review Checklist

Before implementation, reviewers must confirm:

- API is readonly.
- Authentication is defined.
- Authorization is explicit.
- Request schema is typed.
- Static filter allowlist exists.
- Static sort allowlist exists.
- Enum validation exists.
- Bounded limit and max page size exist.
- Deterministic ordering exists.
- Timestamp range validation exists.
- Sanitized ID validation exists.
- API delegates only to internal service.
- API does not call MemoryFacade directly.
- API does not read raw storage.
- API does not expose raw SQL.
- Safe response envelope only.
- Safe error categories only.
- Safe audit logging only.
- Negative tests cover forbidden fields.
- Tests prove no runtime/provider execution path.

## 30. Required Controls Before API Implementation

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
- No prompts, responses, provider payloads, tool outputs, secrets, headers, or
  cookies.
- Focused tests for future list/detail routes.
- Negative tests for forbidden fields.
- Tests proving no runtime/provider execution path.

## 31. Required Controls Before API Exposure

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
- Operational ownership and incident response expectations.
- Verification that copy/export remains absent.

## 32. Required Controls Before Cockpit Consumption

Required controls:

- Separate Cockpit governance approval.
- API implementation and exposure approved first.
- Readonly warning labels.
- "Not approval" and "not execution input" labels.
- Empty/loading/error states.
- Forbidden field absence tests.
- No destructive controls.
- No execution controls.
- No `dangerouslySetInnerHTML`.
- No screenshots containing sensitive data.

## 33. Required Controls Before Detail Drawer Consumption

Required controls:

- Safe detail endpoint implemented and reviewed.
- Detail field allowlist approved.
- Bounded block reasons and summaries.
- No raw row, JSONL, SQL, or diagnostic object dump.
- Missing/degraded detail states.
- Readonly labels and warnings.
- Tests for forbidden field absence.

## 34. Required Controls Before Copy/Export

Required controls:

- Separate copy/export governance approval.
- Export-specific field allowlist.
- Export size limits.
- Redaction review.
- Authorization review.
- Audit trail for export if approved.
- No raw JSONL export.
- No raw SQLite row export.
- No secret/payload/prompt/response/tool-output screenshots or files.

## 35. Required Controls Before Retention/Cleanup Integration

Required controls:

- Separate retention/cleanup governance approval.
- Query endpoints remain readonly.
- Cleanup controls remain separate from query controls.
- No destructive API behavior through audit query routes.
- Safe lifecycle diagnostics only.
- Tests proving filters do not become cleanup selectors.

## 36. Required Controls Before Any Execution Design

Required controls:

- Separate execution governance approval.
- Persisted evidence remains non-execution input.
- Explicit user approval model.
- Runtime output preservation review.
- Provider/model call boundary review.
- Prompt rewrite boundary review.
- Tool/command/file/Git/CI boundary review.
- Tests proving query paths cannot trigger execution.

## 37. Explicit Non-Approval Statement

This review does not approve:

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
- Prompt rewriting.
- Retry execution.
- Replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 38. Open Risks

- Future implementation could bypass the internal service.
- Existing authentication conventions may not fit this endpoint.
- Operators may over-trust advisory values.
- Query filters may be mistaken for operational selectors.
- Copy/export pressure may expand the exposure surface.
- Large data volume may pressure pagination and rate limits.
- Error handling could leak implementation details if not tested.

## 39. Open Questions

- Which existing authentication mechanism should protect the endpoint?
- Which role should grant readonly audit metadata access?
- Should endpoints remain internal-only or admin-only?
- Should pagination use offset or opaque cursor?
- What rate limits are appropriate?
- Should safe audit logging include caller ID or only caller category?
- What exact status codes should represent degraded and not-found states?

## 40. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | Approved. |
| API boundary design | Go | Approved as design only. |
| API boundary governance review | Go | This document. |
| API implementation | No-Go | Blocked until separate implementation branch with strict tests. |
| API exposure | No-Go | Blocked until auth, authorization, limits, logging, and security review. |
| Frontend/Cockpit consumption | No-Go | Requires separate governance. |
| Detail drawer consumption | No-Go | Requires separate detail review and tests. |
| Copy safe summary | No-Go | Copy/export remains blocked. |
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

## 41. Final Recommendation

Approve the API boundary design and this governance review as documentation
only. Do not implement or expose API routes until a separate branch supplies
typed schemas, access-control integration, rate/size limits, safe logging,
safe errors, internal-service-only delegation, and focused tests proving no raw
data exposure and no runtime/provider/execution path.

Omni remains advisory-only.
