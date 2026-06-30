# Autonomy Dry-Run Historical Audit Internal API Endpoint Design

**Date:** 2026-06-30
**Branch:** `feature/autonomy-dry-run-historical-audit-api-internal-endpoint-design`
**Base:** `main` after PR #474
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs a future internal/private API endpoint implementation
for historical dry-run RETRY/REPLAN audit evidence. It is documentation only.
It does not implement endpoints, routes, handlers, schemas, frontend/Cockpit
UI, detail drawers, copy/export, retention/cleanup, runtime behavior,
provider behavior, prompt behavior, retry/replan execution, or autonomous
execution.

Future implementation is conditionally acceptable only for an internal/private
endpoint that calls `HistoricalDryRunAuditQueryService` exclusively, enforces
validation and bounded pagination, preserves required advisory warnings,
returns sanitized envelopes and categorical errors only, and proves through
tests that no provider/runtime/execution or raw storage path exists.

## 2. Scope

This design covers:

- Internal/private endpoint shape.
- Candidate list/detail routes.
- Handler responsibilities and non-responsibilities.
- Dependency and service-only delegation boundaries.
- Request parsing and validation.
- Size, rate, auth, authorization, audit logging, and observability design.
- Response, detail, and error mapping.
- Safe field allowlist and forbidden field denylist.
- Test strategy and required controls before implementation or exposure.

## 3. Non-Goals

- Do not add API endpoints, HTTP routes, handlers, or code schemas.
- Do not add frontend/Cockpit UI or detail drawer behavior.
- Do not add copy/export.
- Do not add retention/cleanup behavior.
- Do not modify runtime, persistence, MemoryFacade, internal query service,
  SQLite, provider, routing, or prompt behavior.
- Do not expose raw JSONL, raw SQLite rows, raw SQL, prompts, responses,
  provider payloads, tool outputs, credentials, secrets, tokens, headers,
  cookies, `.env` content, stack traces, exceptions, tracebacks, stdout,
  stderr, command args, or file contents.
- Do not execute RETRY or REPLAN.
- Do not enable autonomous execution or self-repair.

## 4. Current Approved Governance State

Approved:

- Documentation/design.
- API contract design.
- API contract governance review.

Conditionally approved:

- Future internal/private endpoint implementation with strict tests and
  internal-service-only delegation.

Not approved:

- Route exposure without auth, authorization, rate, size, and audit controls.
- Public exposure.
- Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Raw JSONL read.
- Raw SQLite row read.
- Raw SQL filters.
- Direct API-to-MemoryFacade.
- Prompt rewrite.
- Provider/model retry or replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 5. Internal Endpoint Design Overview

The future endpoint should be a narrow HTTP adapter:

1. Accept only GET requests for list/detail audit metadata.
2. Enforce internal/private boundary controls.
3. Parse query/path parameters.
4. Validate parameters before service delegation.
5. Build the internal query service request.
6. Call `HistoricalDryRunAuditQueryService` only.
7. Map service output to a sanitized API envelope.
8. Emit safe audit/observability metadata.

The endpoint is a reader of sanitized audit metadata, not a runtime control
surface.

## 6. Endpoint Candidates

Candidate endpoints:

- `GET /internal/audit/dry-run`
- `GET /internal/audit/dry-run/{plan_id}`

These are design placeholders. Future implementation must confirm route names
against existing backend route conventions before adding code.

## 7. Internal-Only Exposure Model

The endpoint should begin as internal/private only. Internal/private means:

- Not public internet exposed.
- Not available to unauthenticated callers.
- Not available to general user sessions by default.
- Not consumed by Cockpit until separate governance approval.

Public exposure remains blocked.

## 8. Route Registration Expectations

Future route registration must:

- Keep routes grouped under an internal/protected namespace.
- Attach authentication and authorization before non-local exposure.
- Attach request size limits before handler execution.
- Attach rate limits before service delegation.
- Avoid registering copy/export routes.
- Avoid registering destructive or execution routes.

This branch adds no routes.

## 9. Handler Responsibilities

Future handlers are responsible for:

- Method/path validation.
- Query and path parsing.
- Parameter validation.
- Size and rate limit enforcement.
- Auth and authorization enforcement before exposure.
- Calling `HistoricalDryRunAuditQueryService` only.
- Mapping service results to sanitized response envelopes.
- Returning categorical errors only.
- Preserving required advisory warnings.
- Emitting safe audit and observability metadata.

## 10. Handler Non-Responsibilities

Handlers must not:

- Call MemoryFacade directly.
- Read JSONL or SQLite directly.
- Build SQL from request input.
- Execute retry or replan.
- Rewrite prompts.
- Call providers/models.
- Call runtime.
- Trigger cleanup.
- Export data.
- Render Cockpit UI.
- Interpret audit metadata as approval or execution input.

## 11. Dependency Boundary

Allowed dependency direction:

API route -> handler -> `HistoricalDryRunAuditQueryService` -> MemoryFacade
safe query controls.

Forbidden dependency directions:

- API route -> MemoryFacade.
- API route -> SQLite.
- API route -> JSONL.
- API route -> runtime.
- API route -> provider/model.
- API route -> shell/tool/Git/CI execution.

## 12. HistoricalDryRunAuditQueryService-Only Delegation

Future endpoint implementation must call only `HistoricalDryRunAuditQueryService`
or its approved wrapper functions:

- `query_historical_dry_run_audit(...)`
- `get_historical_dry_run_audit_detail(...)`

The service is the policy boundary for validation, warnings, safe degradation,
categorical errors, and MemoryFacade-only access.

## 13. Request Parsing Design

The list handler should parse query parameters into a typed request object.
The detail handler should parse `plan_id` from the path and validate it before
service delegation.

Parsing must not preserve raw request objects in logs, errors, or responses.

## 14. Query Parameter Validation Design

Supported query parameters:

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

Unsupported parameters must be rejected or safely warned, following the
implementation policy selected for the route.

## 15. Path Parameter Validation Design

`plan_id` validation must reject:

- Empty values.
- Redacted values.
- Path traversal.
- Path separators.
- Query injection characters.
- Quotes, pipes, shell metacharacters, and wildcard-like selectors.
- Values exceeding the safe ID length.

Invalid `plan_id` must not reach the service or storage layer.

## 16. Filter Validation Design

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

Filters must remain metadata query filters only. They must not become
execution, cleanup, export, or provider-routing selectors.

## 17. Sort Validation Design

Allowed sort fields:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`

Allowed sort directions:

- `asc`
- `desc`

Raw SQL, arbitrary column names, nested fields, and storage-specific clauses
are forbidden.

## 18. Pagination Validation Design

Pagination must enforce:

- Conservative default limit.
- Explicit max page size.
- Non-negative bounded offset.
- Deterministic ordering.
- No unbounded list path.
- No raw storage cursor or row ID exposure.

Cursor support is not part of this implementation design unless separately
approved.

## 19. Size Limit Design

Future implementation must define route-level size limits for:

- Query string length.
- Number of query parameters.
- Individual ID length.
- Timestamp string length.
- Page size.
- Offset.

Oversized requests should fail before service delegation when possible.

## 20. Rate Limit Design

Rate limiting is required before exposure. Future implementation should define
per-caller or per-session limits and safe error behavior for repeated invalid
or expensive requests.

Rate-limit responses must not reveal storage state or internal details.

## 21. Auth Placeholder Design

Authentication is a placeholder until a concrete implementation branch chooses
an existing safe auth convention. If no safe convention exists, endpoint
implementation must stop for a separate auth design.

Unauthenticated requests must be rejected before service delegation.

## 22. Authorization Placeholder Design

Authorization must grant readonly historical audit metadata access only. It
must not grant runtime control, provider/model calls, cleanup, copy/export,
prompt rewriting, retry execution, replan execution, or autonomous execution.

## 23. Audit Logging Design

Safe audit logs may include:

- Operation name.
- Safe caller category or ID if approved.
- Safe filter keys.
- Sort field and direction.
- Limit and offset.
- Response status category.
- Degraded boolean.
- Categorical error category.
- Timestamp.

Logs must not include raw request bodies, raw response bodies, raw exceptions,
tracebacks, prompts, responses, payloads, tool outputs, headers, cookies,
tokens, secrets, SQL, rows, or JSONL lines.

## 24. Observability Design

Safe observability may include:

- Accepted request counts.
- Rejected request counts by category.
- Unauthorized counts.
- Rate-limit counts.
- Degraded counts by category.
- Latency buckets.
- Page-size buckets.

Observability must not include raw query strings, raw response bodies, raw
exceptions, prompts, responses, provider payloads, rows, SQL, JSONL lines,
headers, cookies, tokens, or secrets.

## 25. Response Mapping Design

List responses should preserve the safe service envelope:

- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category`
- `generated_at`

Response mapping must not add unsafe debug metadata.

## 26. Detail Response Mapping Design

Detail responses should map only safe detail fields from the service. Missing
details may return a safe not-found response. Degraded detail paths must use
categorical metadata only.

Raw record dumps and raw diagnostic objects are forbidden.

## 27. Error/Degradation Mapping Design

Errors should map to safe categorical responses:

- invalid request
- invalid filter
- invalid sort
- unauthenticated
- unauthorized
- rate limited
- payload too large
- storage unavailable
- query failed
- not found
- invalid service response
- unknown

Raw exception messages, stack traces, tracebacks, storage paths, SQL, rows,
JSONL lines, prompts, responses, payloads, headers, cookies, command args,
tokens, and secrets are forbidden.

## 28. Required Advisory Warnings

Responses must preserve these warnings:

- Query results are readonly audit metadata.
- Query results are not approval.
- Query results are not execution input.
- `would_retry/would_replan` are not execution.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- Copy/export remains disabled.
- Omni remains advisory-only.

## 29. Safe Field Allowlist

Allowed fields:

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
- sanitized `request_id`, `session_id`, and `trace_id`
- safe persistence diagnostics
- safe envelope and page fields

## 30. Forbidden Field Denylist

Forbidden fields and values:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys, tokens, secrets.
- Headers, cookies.
- `.env` content.
- Stack traces, raw exceptions, tracebacks.
- Stdout, stderr.
- Command args.
- File contents.
- Full tool outputs.
- Raw receipts.
- Raw Python reprs.
- Raw JSONL lines.
- Raw SQLite rows.
- Raw SQL.
- Screenshots exposing secrets or raw payloads.

## 31. Raw Storage Exposure Prohibition

Future endpoint implementation must not expose or read raw JSONL, raw SQLite
rows, raw SQL, raw DB paths, storage cursors, or raw persistence records.

Storage remains behind MemoryFacade and the internal query service.

## 32. No Direct API-To-MemoryFacade Rule

The API endpoint must not call MemoryFacade directly. Direct calls would bypass
the internal service boundary and risk inconsistent validation, warnings,
error categories, and logging behavior.

## 33. No SQL Construction Rule

The endpoint must not construct SQL from request input. SQL construction is
not part of the API layer. Filtering and sorting must use static allowlisted
fields only.

## 34. Copy/Export Exclusion

Copy/export is excluded. The endpoint must not provide:

- Copy safe summary.
- CSV export.
- JSON export.
- Raw JSONL export.
- Raw SQLite row export.
- Bulk dump response.

## 35. Cockpit/Detail Drawer Exclusion

Cockpit and detail drawer consumption remain excluded. Future UI consumption
requires separate governance, UI warning labels, missing/degraded states, and
forbidden field tests.

## 36. Retention/Cleanup Exclusion

Retention and cleanup behavior remain excluded. Query filters must not become
cleanup selectors. No deletion, lifecycle mutation, or scheduled cleanup may
be introduced through this endpoint.

## 37. Execution Exclusion

The endpoint must never trigger or authorize:

- RETRY.
- REPLAN.
- Prompt rewriting.
- Provider/model calls.
- Provider switching.
- Tool execution.
- Command execution.
- File writes.
- CI repair.
- Git operations.
- Autonomous execution.

## 38. Abuse/Misuse Cases

Misuse cases:

- Treating query results as approval.
- Treating query results as execution input.
- Treating `would_retry=true` as retry execution.
- Treating `would_replan=true` as replan execution.
- Treating `blocked=false` as permission.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Using filters as execution selectors.
- Using filters as cleanup selectors.
- SQL injection through filter/sort parameters.
- Path traversal through `plan_id`.
- Scraping through unbounded pagination.
- Exposing routes without auth or rate limits.

## 39. Security Review Checklist

Before implementation, verify:

- Endpoint calls `HistoricalDryRunAuditQueryService` only.
- Endpoint does not call MemoryFacade directly.
- Endpoint does not call raw storage.
- Endpoint does not construct SQL from request input.
- Endpoint preserves required warnings.
- Endpoint validates parameters.
- Endpoint enforces bounded pagination.
- Endpoint enforces size limits.
- Endpoint uses categorical errors only.
- Endpoint returns sanitized envelopes only.
- Tests exclude forbidden fields.
- Tests prove no provider/runtime/execution behavior.
- Tests prove no raw JSONL/SQLite/SQL exposure.

## 40. Test Strategy

Future tests should be focused and route-level:

- Valid list request.
- Valid detail request.
- Invalid filter.
- Invalid sort.
- Invalid `plan_id`.
- Invalid timestamp range.
- Bounded limit and offset.
- Required warnings preserved.
- Forbidden fields absent.
- Service-only delegation.
- No MemoryFacade direct access.
- No raw storage access.
- No runtime/provider/execution calls.
- Safe degraded responses.

## 41. Required Tests Before Implementation

Required tests:

- Parameter validation tests.
- Forbidden field exclusion tests.
- Required warnings tests.
- Categorical error tests.
- No provider/runtime/execution behavior tests.
- No raw JSONL/SQLite/SQL exposure tests.
- Service-only delegation tests.
- Bounded pagination tests.
- Size limit tests before exposure.
- Auth/authorization tests before non-local exposure.
- Rate limit tests before exposure.

## 42. Required Controls Before Route Exposure

Required controls before any route exposure:

- Route-level size limits.
- Authentication.
- Explicit authorization.
- Readonly permission model.
- Rate limits.
- Safe audit logging.
- Safe observability.
- Abuse-case review.
- Security review.
- Operational ownership.

## 43. Required Controls Before Public Exposure

Public exposure remains blocked. Before reconsideration:

- Separate governance approval.
- Production-grade auth and authorization.
- Rate limiting.
- Size limiting.
- Security review.
- Abuse-case review.
- Logging and observability review.
- Incident response owner.
- No copy/export.

## 44. Required Controls Before Cockpit Consumption

Required before Cockpit consumption:

- Separate governance approval.
- Approved route exposure.
- Readonly labels.
- "Not approval" and "not execution input" warnings.
- Missing/degraded UI states.
- No destructive or execution controls.
- No copy/export controls.
- No forbidden fields rendered.

## 45. Required Controls Before Copy/Export

Copy/export remains blocked. Required before reconsideration:

- Separate governance approval.
- Export allowlist.
- Export size limits.
- Redaction review.
- Authorization review.
- Audit trail.
- No raw JSONL or SQLite export.

## 46. Required Controls Before Retention/Cleanup

Required before retention/cleanup integration:

- Separate governance approval.
- Query endpoint remains readonly.
- Cleanup controls are separate.
- Query filters do not become cleanup selectors.
- Tests prove no destructive behavior through query routes.

## 47. Required Controls Before Execution Design

Required before execution design:

- Separate execution governance approval.
- Query results remain non-execution input.
- Persisted evidence remains non-execution input.
- Explicit user approval model.
- Runtime output preservation review.
- Provider/model boundary review.
- Prompt rewrite boundary review.
- Tool/command/file/Git/CI boundary review.

## 48. Open Risks

- Future implementation could bypass the internal query service.
- Auth/authorization conventions may not fit the endpoint.
- Internal/private route could be exposed too broadly.
- Query strings could leak in logs without strict controls.
- Offset pagination may not scale to large audit history.
- Operators may misread advisory metadata as permission.
- Copy/export requests may expand the scope.

## 49. Open Questions

- Which backend auth convention should protect the route?
- Which authorization role should grant readonly audit access?
- Should implementation start local-only or internal-only?
- Should pagination use offset initially or an opaque cursor?
- Which status code should represent safe degraded storage behavior?
- What rate limits are appropriate for local and deployed modes?
- What safe caller metadata should be logged?

## 50. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation/design | Go | This document. |
| Internal/private endpoint implementation | Conditional Go | Requires strict tests and service-only delegation. |
| Route exposure without auth/authorization/rate/size/audit controls | No-Go | Blocked. |
| Public exposure | No-Go | Requires separate governance. |
| Cockpit consumption | No-Go | Requires separate governance. |
| Detail drawer consumption | No-Go | Requires separate governance. |
| Copy/export | No-Go | Disabled. |
| Raw JSONL read | No-Go | Forbidden. |
| Raw SQLite row read | No-Go | Forbidden. |
| Raw SQL filters | No-Go | Forbidden. |
| Direct API-to-MemoryFacade | No-Go | Must use internal service. |
| Prompt rewrite | No-Go | Forbidden. |
| Provider/model retry execution | No-Go | Forbidden. |
| Provider/model replan execution | No-Go | Forbidden. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Forbidden. |

## 51. Final Recommendation

Approve this document as design only. A future internal/private endpoint
implementation may proceed only in a separate branch, with route-level tests,
strict validation, bounded pagination, safe categorical errors, required
warnings, safe logging, safe observability, and delegation only to
`HistoricalDryRunAuditQueryService`.

Do not approve route exposure without auth/authorization/rate/size/audit
controls. Do not approve public exposure, Cockpit consumption, detail drawer
consumption, copy/export, raw storage access, direct API-to-MemoryFacade,
prompt rewriting, provider/model execution, persisted evidence as execution
input, or autonomous execution.

Omni remains advisory-only.
