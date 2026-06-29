# Autonomy Dry-Run Historical Audit API Boundary Design

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-historical-audit-api-boundary-design`
**Base:** `main` after PR #467
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs a future readonly API boundary for historical dry-run
RETRY and REPLAN audit evidence. The API boundary would expose sanitized audit
metadata to authorized callers only, through the internal historical dry-run
audit query service implemented in PR #466.

This design does not approve API implementation or exposure. It does not add
routes, handlers, schemas, frontend components, Cockpit behavior, runtime
behavior, persistence behavior, provider/model calls, prompt rewriting, retry
execution, replan execution, or autonomous execution.

The API must remain readonly, metadata-only, allowlisted, access-controlled,
rate-limited, size-limited, and delegated only to the internal query service.

## 2. Scope

This design covers:

- Future API boundary principles.
- Candidate readonly endpoint shapes.
- Request and response models.
- Error and degradation behavior.
- Access-control, authentication, and authorization requirements.
- Rate limiting, size limits, pagination, filters, sorting, and ID validation.
- Safe audit logging.
- Safe field allowlists and forbidden field denylists.
- Delegation rules and storage boundaries.
- Required controls before implementation and downstream exposure.

## 3. Non-Goals

- Do not implement API endpoints.
- Do not add route handlers.
- Do not add API schemas in code.
- Do not add frontend or Cockpit UI.
- Do not add detail drawer consumption.
- Do not add copy/export.
- Do not modify runtime code.
- Do not modify persistence code.
- Do not modify MemoryFacade code.
- Do not modify internal query service code.
- Do not modify SQLite code.
- Do not call runtime.
- Do not call providers/models.
- Do not rewrite prompts.
- Do not execute RETRY or REPLAN.
- Do not use persisted evidence as execution input.
- Do not approve autonomous execution.

## 4. Relationship To MemoryFacade Query Contracts

PR #463 introduced the safe MemoryFacade historical dry-run audit query
contracts:

- `DryRunAuditQueryRequest`
- `DryRunAuditQueryResponse`
- `DryRunAuditPageInfo`
- `DryRunAuditEvidenceItem`
- `DryRunAuditEvidenceDetail`
- `query_historical_dry_run_audit_evidence(...)`
- `get_historical_dry_run_audit_evidence_detail(...)`

The future API layer must not call these MemoryFacade methods directly. The
API must depend on the internal query service boundary so validation, safe
delegation, degradation, and logging remain centralized.

## 5. Relationship To Internal Query Service Contracts

PR #466 introduced the internal readonly query service:

- `HistoricalDryRunAuditQueryService`
- `query_historical_dry_run_audit(...)`
- `get_historical_dry_run_audit_detail(...)`

The future API boundary should adapt HTTP requests into typed, sanitized
service requests and call only these service contracts. The API should not
widen the service response shape or expose fields absent from the service's
safe models.

## 6. API Boundary Overview

The future API boundary should follow this flow:

1. Authenticate caller.
2. Authorize caller for readonly historical dry-run audit access.
3. Validate method, path, query parameters, route parameters, and size limits.
4. Normalize filters, sort, pagination, timestamps, and IDs into typed request
   objects.
5. Call only the internal query service.
6. Return sanitized response envelopes.
7. Log safe audit metadata only.
8. Never expose raw request bodies, raw response bodies, exceptions,
   tracebacks, raw rows, raw JSONL lines, raw SQL, prompts, responses,
   provider payloads, tool outputs, headers, cookies, tokens, or secrets.

## 7. Endpoint Design Principles

Endpoints must be:

- Readonly.
- Internal or protected by default.
- Explicitly access-controlled before exposure.
- Metadata-only.
- Strictly allowlisted.
- Rate-limited and size-limited.
- Paginated with bounded limits.
- Backed only by the internal query service.
- Non-authoritative for execution decisions.
- Separated from runtime and provider/model code.

Endpoint names in this document are placeholders only.

## 8. Candidate Readonly List Endpoint

Placeholder:

`GET /internal/audit/dry-run`

Purpose:

- Return a paginated list of sanitized historical dry-run RETRY/REPLAN audit
  evidence items.

Allowed request inputs:

- Supported filters.
- Supported sort field and direction.
- Bounded pagination.
- Sanitized request/session/trace IDs.
- Safe timestamp ranges.

Forbidden request inputs:

- Raw SQL.
- Raw JSONL paths or line selectors.
- Raw SQLite paths, table names, row IDs, or SQL fragments.
- Prompt, response, provider payload, tool output, command, file, secret,
  header, cookie, or credential selectors.

## 9. Candidate Readonly Detail Endpoint

Placeholder:

`GET /internal/audit/dry-run/{plan_id}`

Purpose:

- Return one sanitized historical dry-run audit detail by safe `plan_id`.

The detail endpoint must not return raw storage records. It must return only
the safe detail model from the internal query service.

## 10. Request Model

The API request model should include:

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
- `limit`
- `offset` or future opaque cursor
- `sort_field`
- `sort_direction`

The API must convert accepted query parameters into the typed internal request
model. It must not pass arbitrary request bodies or raw query dictionaries to
storage code.

## 11. Response Envelope Model

The list endpoint should return the service-safe envelope:

- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category`, only when degraded
- `generated_at`

The detail endpoint should return the service-safe detail model or a safe
not-found response. It must not return raw rows, raw JSONL, raw SQL, or raw
diagnostic object dumps.

## 12. Error/Degradation Model

Errors should degrade safely:

- Invalid request: safe 400-style response with categorical error.
- Unauthorized caller: safe 401/403-style response with no storage details.
- Rate limit exceeded: safe 429-style response.
- Internal service unavailable: safe degraded response.
- Storage unavailable through service: safe degraded response.
- Not found: safe not-found response.

Forbidden error output:

- Raw exception messages.
- Tracebacks.
- Stack traces.
- SQL strings.
- JSONL lines.
- SQLite paths or row dumps.
- Prompt, response, payload, tool output, command args, headers, cookies,
  credentials, or secrets.

## 13. Access-Control Requirements

API exposure requires access control before implementation:

- Only authorized callers may query historical dry-run audit metadata.
- Access must be read-only.
- Authorization must be explicit, not inferred from Cockpit visibility.
- Unauthorized requests must be rejected before service delegation.
- Access decisions must not rely on persisted evidence content.

## 14. Authorization Model

The authorization model should distinguish:

- Readonly audit metadata access.
- Administrative maintenance access.
- Runtime execution authority.
- Copy/export authority.

This API boundary may only request readonly audit metadata access. It must not
grant execution, copy/export, runtime control, cleanup, provider switching, or
prompt rewrite authority.

## 15. Authentication Assumptions

This design assumes a future implementation will reuse an existing
authentication convention if one exists. If no safe convention exists, API
implementation must stop for separate auth design rather than inventing an
unprotected endpoint.

Authentication must happen before request validation that could trigger deeper
service work.

## 16. Rate Limiting And Size Limits

Future implementation must define:

- Conservative default page size.
- Explicit maximum page size.
- Bounded offset or opaque cursor.
- Maximum query string size.
- Maximum timestamp range if needed.
- Rate limits per caller or session.
- Safe behavior for repeated invalid queries.

No unbounded scan or unbounded response is allowed.

## 17. Filter Validation Strategy

Filters must be static and allowlisted. Supported filters:

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

Unsupported filters should be rejected or safely ignored with warnings,
following the internal request model's behavior.

## 18. Sort Validation Strategy

Allowed sort fields should match the internal query contract:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`

Allowed sort directions:

- `asc`
- `desc`

Sort behavior must remain deterministic and must not accept raw SQL fragments,
field paths, nested selectors, or arbitrary column names.

## 19. Pagination Strategy

Pagination must be bounded:

- Use a conservative default limit.
- Enforce a maximum limit.
- Enforce bounded offset or an opaque cursor.
- Return safe `page_info`.
- Never expose storage cursors, SQL offsets, raw row IDs, or implementation
  internals.
- Never support unbounded list queries.

## 20. Timestamp And Sanitized ID Validation

Timestamp validation must:

- Accept safe ISO-like timestamps only.
- Normalize to a safe representation.
- Reject invalid ranges.
- Avoid echoing unsafe raw input.

ID validation must:

- Use sanitized request/session/trace/plan ID rules.
- Reject path traversal characters.
- Reject query-string injection characters.
- Reject redacted or empty IDs.
- Avoid logging raw rejected IDs.

## 21. Safe Audit Logging Model

API audit logging should include only:

- Operation name.
- Authenticated caller category or safe caller ID, if available.
- Safe request/session/trace ID, if present.
- Safe filter keys only, not raw filter values unless already sanitized.
- Sort field and direction.
- Bounded limit and pagination metadata.
- Generated timestamp.
- Degraded boolean.
- Categorical error category.
- Response status category.

API audit logging must not include raw request bodies, raw response bodies, raw
exceptions, tracebacks, prompts, responses, provider payloads, tool outputs,
headers, cookies, tokens, secrets, SQL, rows, or JSONL lines.

## 22. Safe Field Allowlist

Allowed response fields include:

- `event_type`
- `plan_id`
- `plan_type`
- `advisory`
- `would_retry`
- `would_replan`
- `blocked`
- `block_reasons`, bounded
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
- `evidence_summary`, bounded
- `created_at`
- `recorded_at`
- sanitized `request_id`, `session_id`, and `trace_id` when present
- persistence diagnostics booleans/categorical values
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category`
- `generated_at`

## 23. Forbidden Field Denylist

Forbidden output includes:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys, tokens, secrets.
- Headers or cookies.
- Stack traces or tracebacks.
- Stdout or stderr.
- Command args.
- File contents.
- `.env` content.
- Full tool outputs.
- Raw receipts.
- Raw exception objects.
- Raw Python reprs.
- Raw database rows.
- Raw SQL.
- Raw JSONL lines.
- SQLite file paths or internal storage paths.
- Screenshots exposing secrets or raw payloads.

## 24. Internal Service-Only Delegation Rule

The API must delegate only to the internal historical dry-run audit query
service. It must not bypass service validation or safe degradation.

Required dependency direction:

API boundary -> internal query service -> MemoryFacade safe query contracts.

Forbidden dependency direction:

API boundary -> MemoryFacade.
API boundary -> SQLite.
API boundary -> JSONL.
API boundary -> runtime.
API boundary -> provider/model.

## 25. No Direct MemoryFacade Access Rule

Direct MemoryFacade calls from the API layer are not allowed in this design.
The internal service exists to centralize validation, safe degradation, and
safe audit metadata logging. Direct API-to-MemoryFacade access would bypass
that boundary and requires separate governance if ever reconsidered.

## 26. No Raw Storage Access Rule

The API must never read JSONL files, SQLite files, SQLite rows, database paths,
or storage internals directly. It must never accept raw storage selectors.

Storage behavior remains hidden behind MemoryFacade and the internal query
service.

## 27. No Raw SQL Rule

The API must not accept, build, log, return, or expose raw SQL. Sorting and
filtering must be expressed only through static allowlisted fields.

Any future implementation that needs storage-specific query optimization must
remain below MemoryFacade and must not leak into API contracts.

## 28. No Copy/Export Rule

Copy/export remains disabled. The API must not provide:

- CSV export.
- JSON export.
- Raw row export.
- Raw JSONL export.
- Copy-to-clipboard summaries.
- Bulk dump endpoints.

Any copy/export proposal requires separate governance.

## 29. No Execution-Input Rule

API results must never become execution input. They must not be used to select,
approve, or trigger:

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

## 30. Abuse/Misuse Cases

The API boundary must defend against:

- Treating `would_retry=true` as retry approval.
- Treating `would_replan=true` as replan approval.
- Treating `blocked=false` as execution approval.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Scraping audit metadata through unbounded pagination.
- Using filters as execution selectors.
- Attempting raw SQL injection through sort/filter fields.
- Attempting path traversal through `plan_id`.
- Attempting to retrieve raw JSONL or SQLite rows.
- Logging sensitive request or response material.
- Exposing the endpoint without access control.

## 31. Security Review Checklist

Before implementation, reviewers must confirm:

- Endpoint is readonly.
- Endpoint is access-controlled.
- Authentication is defined.
- Authorization is explicit.
- Rate and size limits are defined.
- Request schema is allowlisted.
- Filters and sorts are static.
- Pagination is bounded.
- IDs and timestamps are sanitized.
- API delegates only to the internal service.
- API does not call MemoryFacade directly.
- API does not read raw storage.
- API does not emit raw SQL.
- Logs are metadata-only.
- Errors are categorical and safe.
- Copy/export is absent.
- Runtime/provider/model calls are absent.
- Execution-input usage is absent.

## 32. Testing Strategy For Future Implementation

Future API implementation tests must cover:

- Authorized readonly list query.
- Authorized readonly detail query.
- Unauthorized requests rejected before service delegation.
- Invalid filters rejected or safely warned.
- Invalid sort fields/directions rejected.
- Invalid IDs rejected.
- Invalid timestamp ranges rejected.
- Bounded limit enforcement.
- Rate/size limit behavior.
- Safe degraded responses.
- No raw exception/traceback exposure.
- No raw prompt/response/payload/tool output exposure.
- No raw SQL, raw JSONL, or raw row exposure.
- API delegates only to the internal service.
- API does not call MemoryFacade directly.
- API does not call runtime or providers/models.
- Copy/export endpoints do not exist.

## 33. Required Controls Before API Implementation

- Separate implementation approval.
- Existing auth convention identified or separate auth design completed.
- Typed request schema design approved.
- Static allowlists finalized.
- Response envelope finalized.
- Safe error categories finalized.
- Rate/size limits finalized.
- Safe audit logging design finalized.
- Tests planned for delegation, redaction, auth, and abuse cases.

## 34. Required Controls Before API Exposure

- Authentication enabled.
- Authorization enforced.
- Unauthorized behavior tested.
- Rate limiting enabled.
- Size limits enabled.
- Safe logging verified.
- Security review completed.
- No raw storage access verified.
- No runtime/provider/model calls verified.
- No copy/export verified.
- Operational owner identified.

## 35. Required Controls Before Cockpit Consumption

- Separate Cockpit governance approval.
- API exposure approved first.
- Frontend data contract reviewed.
- Readonly labels required.
- "Not approval" and "not execution input" warnings required.
- Empty/loading/error states reviewed.
- Forbidden fields tested as absent.
- No destructive controls.
- No execution controls.
- No `dangerouslySetInnerHTML`.

## 36. Required Controls Before Detail Drawer Consumption

- Detail endpoint approved and implemented safely.
- Detail drawer field allowlist approved.
- Bounded `block_reasons` and summaries.
- No raw row, JSONL, SQL, or diagnostic dump.
- Clear readonly labels.
- Missing/degraded detail states tested.

## 37. Required Controls Before Copy/Export

- Separate copy/export governance approval.
- Export-specific allowlist.
- Export size limits.
- Redaction review.
- User authorization review.
- Audit trail for export if approved.
- No raw JSONL or SQLite row export.
- No screenshots containing secrets or payloads.

## 38. Required Controls Before Retention/Cleanup Integration

- Separate retention/cleanup governance approval.
- Read-only API behavior preserved.
- Cleanup actions kept separate from query endpoints.
- No destructive API control introduced through this boundary.
- Safe lifecycle diagnostics only.
- Tests proving query filters do not become cleanup selectors.

## 39. Required Controls Before Any Execution Design

- Separate execution governance approval.
- Persisted evidence remains non-execution input.
- User approval model defined.
- Runtime output preservation reviewed.
- Provider/model call boundaries reviewed.
- Prompt rewrite boundaries reviewed.
- Tool/command/file/Git/CI boundaries reviewed.
- Tests proving query paths cannot trigger execution.

## 40. Explicit Non-Approval Statement

This document approves documentation only. It does not approve:

- API implementation.
- API exposure.
- Frontend/Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Raw JSONL reads.
- Raw SQLite row reads.
- Raw SQL filters.
- Direct MemoryFacade access from API.
- Runtime calls.
- Provider/model calls.
- Prompt rewriting.
- Retry execution.
- Replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 41. Open Risks

- Future API code could accidentally bypass the internal service.
- Access control patterns may be incomplete or inconsistent.
- Query filters could be misinterpreted as operational selectors.
- Operators may over-trust `would_retry`, `would_replan`, or eligibility
  scores.
- Copy/export pressure could widen the safe field set.
- Large audit volumes could create performance pressure unless pagination and
  rate limits are enforced.

## 42. Open Questions

- Which existing authentication convention should protect this endpoint?
- Which role or permission should authorize readonly audit metadata access?
- Should the API be internal-only, admin-only, or both?
- Should pagination use offset initially or an opaque cursor?
- What rate limits are appropriate for local and deployed environments?
- What safe operational audit event should record API access?
- What not-found response shape should detail reads use?

## 43. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | This design is approved. |
| API boundary design | Go | Design only. |
| API implementation | No-Go | Requires separate approval and tests. |
| API exposure | No-Go | Requires auth, authorization, limits, and security review. |
| Frontend/Cockpit consumption | No-Go | Requires separate governance. |
| Detail drawer consumption | No-Go | Requires detail allowlist and tests. |
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

## 44. Final Recommendation

Proceed only with documentation review of this API boundary design. The next
safe phase may be an API boundary governance review or an implementation plan,
but API implementation and exposure remain not approved until access control,
authorization, rate/size limits, safe logging, and security tests are reviewed
and explicitly approved.

Omni remains advisory-only.
