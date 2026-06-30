# Autonomy Dry-Run Historical Audit Internal API Endpoint Governance Review

**Date:** 2026-06-30
**Branch:** `feature/autonomy-dry-run-historical-audit-api-internal-endpoint-governance-review`
**Base:** `main` after PR #475
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

This review evaluates the future internal/private historical dry-run audit API
endpoint implementation design. The design is acceptable as documentation and
as a constrained future implementation direction, but it does not authorize any
endpoint, route, handler, schema, Cockpit UI, detail drawer, copy/export,
retention/cleanup, runtime behavior, provider behavior, prompt behavior,
retry/replan execution, or autonomous execution.

The only conditionally approved next step is a separate future internal
endpoint implementation branch with strict tests and controls. Any route
exposure remains blocked until real auth, authorization, rate limits, size
limits, audit logging, and safe observability are present.

## 2. Scope

This review covers:

- The internal/private endpoint design from PR #475.
- Candidate list and detail endpoints.
- Internal-only exposure assumptions.
- Route registration, handler responsibilities, and handler exclusions.
- Dependency boundaries and service-only delegation.
- Request parsing, validation, pagination, size limits, and rate limits.
- Auth, authorization, audit logging, and observability requirements.
- Response, detail, and error/degradation mapping.
- Safe field allowlists and forbidden field denylists.
- Required controls before implementation or exposure.
- Go/no-go decisions for future phases.

## 3. Non-Goals

This review does not:

- Implement API endpoints, HTTP routes, handlers, or code schemas.
- Modify runtime, persistence, MemoryFacade, internal query service, SQLite,
  frontend, Cockpit, provider, routing, prompt, or deployment behavior.
- Add copy/export, retention/cleanup, detail drawer, or Cockpit consumption.
- Expose raw JSONL, raw SQLite rows, raw SQL, prompts, rewritten prompts,
  provider/model responses, provider payloads, tool outputs, credentials,
  secrets, tokens, headers, cookies, `.env` content, stack traces, raw
  exceptions, tracebacks, stdout/stderr, command args, or file contents.
- Execute RETRY or REPLAN.
- Use persisted evidence as execution input.
- Enable autonomous execution or self-repair.

## 4. Reviewed Materials

Reviewed materials:

- `docs/runtime/autonomy-dry-run-historical-audit-query-contract-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-contract-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-contract-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-internal-endpoint-design.md`
- MemoryFacade historical dry-run audit query controls.
- `HistoricalDryRunAuditQueryService` internal query service controls.

## 5. Governance Decision Summary

Approved:

- Documentation.
- Internal endpoint design.

Conditionally approved:

- Future internal/private endpoint implementation only with strict tests,
  service-only delegation, validation, bounded pagination, sanitized response
  envelopes, categorical errors, and no raw storage exposure.

Not approved:

- Route exposure without real auth, authorization, rate, size, and audit
  controls.
- Public exposure.
- Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Raw JSONL read.
- Raw SQLite row read.
- Raw SQL filters.
- Direct API-to-MemoryFacade.
- Prompt rewrite.
- Provider/model retry execution.
- Provider/model replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 6. Internal Endpoint Safety Review

The internal endpoint design preserves the current safety posture because it is
readonly, metadata-only, and scoped to sanitized historical dry-run audit
evidence. It does not approve any route implementation in this branch.

Future implementation is safe to consider only if the endpoint:

- Calls `HistoricalDryRunAuditQueryService` only.
- Accepts only allowlisted query and path parameters.
- Enforces bounded pagination and size limits.
- Returns sanitized envelopes only.
- Preserves advisory warnings.
- Emits only categorical errors.
- Provides safe audit logging and observability.
- Proves through tests that no runtime, provider, retry, replan, raw storage,
  or SQL path exists.

## 7. Endpoint Candidate Review

The design proposes these candidates:

- `GET /internal/audit/dry-run`
- `GET /internal/audit/dry-run/{plan_id}`

These names are acceptable as design placeholders because they are explicitly
internal, readonly, and audit-specific. They are not approved for route
registration yet.

Future implementation must keep the routes under an internal/private boundary
and must not present them as public operational controls.

## 8. Internal-Only Exposure Review

Internal-only exposure is required. The endpoint must not be internet-public or
tenant-public by default.

Before any route exposure, the implementation must define:

- Who may call the route.
- Which environment may expose it.
- Which network boundary protects it.
- Which auth and authorization checks apply.
- How abuse, scraping, and repeated broad queries are rate-limited.

## 9. Route Registration Review

Route registration remains blocked. A future implementation may register routes
only after route-level tests prove:

- The route is readonly.
- The route is internal/private.
- The route has validation before service calls.
- The route cannot call MemoryFacade directly.
- The route cannot access raw JSONL, raw SQLite, or raw SQL.
- The route cannot call runtime or provider/model code.
- The route cannot trigger retry or replan execution.

## 10. Handler Responsibility Review

Future handlers may be responsible for:

- Parsing query and path parameters.
- Validating parameters against static allowlists.
- Enforcing bounded pagination.
- Enforcing size limits and rate-limit hooks.
- Calling `HistoricalDryRunAuditQueryService` only.
- Mapping service responses to sanitized API envelopes.
- Preserving required warnings.
- Mapping failures to categorical errors only.
- Recording safe audit and observability metadata.

## 11. Handler Non-Responsibility Review

Future handlers must not:

- Read JSONL directly.
- Read SQLite directly.
- Build SQL.
- Call MemoryFacade directly.
- Call runtime code.
- Call provider/model code.
- Rewrite prompts.
- Execute retry or replan.
- Use persisted evidence as execution input.
- Implement copy/export.
- Expose raw exception or traceback details.
- Expose prompt, response, provider payload, tool output, secrets, or file
  contents.

## 12. Dependency Boundary Review

The only approved dependency path for a future endpoint is:

API route -> handler -> `HistoricalDryRunAuditQueryService` -> MemoryFacade safe
query contracts

The handler must not bypass the service. The service remains the validation and
sanitization boundary between API-facing code and MemoryFacade contracts.

## 13. HistoricalDryRunAuditQueryService-Only Delegation Review

Service-only delegation is required because the service already centralizes:

- Typed request handling.
- Static filter and sort allowlists.
- Enum validation.
- Bounded pagination.
- Timestamp and sanitized ID validation.
- Safe response and detail shapes.
- Safe degradation categories.

A future endpoint must call only:

- `HistoricalDryRunAuditQueryService.query_historical_dry_run_audit(...)`
- `HistoricalDryRunAuditQueryService.get_historical_dry_run_audit_detail(...)`

## 14. Request Parsing Review

Request parsing must remain shallow and defensive. The future handler may parse
only known query/path parameters into the typed request model used by the
internal service.

The handler must not log raw request bodies, raw query strings with secrets, or
raw framework request objects. Unsupported inputs must be rejected or safely
ignored with warnings according to the existing service style.

## 15. Query Parameter Validation Review

Future query parameter validation must cover:

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
- `cursor` or `offset`, whichever remains approved by the implementation
  contract.

No free-form filters are approved.

## 16. Path Parameter Validation Review

The detail endpoint path parameter `{plan_id}` must be bounded and sanitized.
It must reject unsafe characters, overly long values, empty values, raw object
representations, paths, SQL-like fragments, and secret-like payloads.

Path validation must happen before any service call.

## 17. Filter Validation Review

The filter model is acceptable only if it remains static and allowlisted.
Future endpoint code must not:

- Accept arbitrary filter keys.
- Translate raw request input into SQL.
- Add storage-specific filters.
- Add prompt, response, payload, file, or tool-output filters.
- Treat filters as execution selectors.

## 18. Sort Validation Review

Sort fields must remain static and deterministic. Approved sort fields for the
contract family are:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`

Sort direction must be restricted to `asc` or `desc`. Unsupported sort fields
must be rejected or safely degraded with warnings and categorical errors only.

## 19. Pagination Validation Review

Pagination must be bounded. The future endpoint must enforce:

- Conservative default limit.
- Explicit maximum page size.
- No unbounded list queries.
- Deterministic ordering.
- Safe cursor or safe offset semantics.

Pagination metadata must not include raw storage pointers, raw SQL offsets, raw
row identifiers, or sensitive implementation details.

## 20. Size Limit Review

Route-level size limits are required before route exposure. They must cover:

- Query string size.
- Path parameter length.
- Number of filter parameters.
- Response item count.
- Warning count.
- Error metadata size.

Oversized requests should fail safely with categorical error metadata.

## 21. Rate Limit Review

Rate limits are required before exposure because historical audit queries can be
used for enumeration or resource exhaustion. Rate limits should be scoped by
caller identity, environment, and route.

Rate-limit failures must not expose raw request details, raw service state, or
storage internals.

## 22. Auth Placeholder Review

The current design includes auth as a placeholder. That is acceptable for
design only, but insufficient for route exposure.

Before exposure, the implementation must define and test real authentication.
Auth placeholder logic must not be treated as access control.

## 23. Authorization Placeholder Review

The current design includes authorization as a placeholder. That is acceptable
for design only, but insufficient for route exposure.

Before exposure, the implementation must require an explicit readonly audit
permission or equivalent internal-admin guard.

## 24. Audit Logging Review

Audit logging must be safe and minimal. Future logs may include:

- Operation name.
- Route name.
- Sanitized request/session/trace IDs if already safe.
- Safe filter keys only.
- Sort key and direction.
- Bounded limit.
- Generated timestamp.
- Degraded boolean.
- Categorical error category.

Logs must not include raw request body, raw response body, raw exception,
traceback, raw query string with secrets, raw rows, raw JSONL, raw SQL,
prompts, responses, payloads, tool outputs, credentials, headers, cookies, or
file contents.

## 25. Observability Review

Observability must remain categorical and aggregate. Acceptable signals include:

- Request count.
- Degraded count.
- Error category counts.
- Latency bucket.
- Limit bucket.
- Storage mode category when already safe.

Observability must not capture raw evidence records, raw service responses, raw
exceptions, raw storage paths, raw SQL, prompts, responses, provider payloads,
tool outputs, or secrets.

## 26. Response Mapping Review

Response mapping must preserve the safe service envelope:

- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category`
- `generated_at`

The handler may not add unsafe debug fields. It must preserve required advisory
warnings and may only return allowlisted item fields.

## 27. Detail Response Mapping Review

Detail mapping must remain allowlisted. Detail responses may include the safe
detail fields from the service, including bounded `block_reasons` and safe
diagnostic details.

Detail responses must not expose raw storage records, raw JSONL lines, raw
SQLite rows, raw SQL, raw exception objects, prompt/response content, provider
payloads, tool outputs, credentials, headers, cookies, stack traces, command
args, or file contents.

## 28. Error/Degradation Mapping Review

Errors must degrade safely. Future endpoint code must return categorical error
metadata only. It must not leak exception messages, traceback text, storage
paths, SQL text, framework request representations, or raw service objects.

Acceptable categories should remain aligned with the internal service categories
such as invalid request, invalid filter, invalid sort, storage unavailable,
query failed, and invalid service response.

## 29. Required Advisory Warnings Review

The endpoint must preserve these warnings:

- Query results are readonly audit metadata.
- Query results are not approval.
- Query results are not execution input.
- `would_retry` and `would_replan` are not execution.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- Copy/export remains disabled.
- Omni remains advisory-only.

Warnings must appear in safe response metadata and must not be hidden behind
frontend-only interpretation.

## 30. Safe Field Allowlist Review

Safe fields remain limited to sanitized audit metadata, including:

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
- Sanitized request/session/trace IDs when present.
- Safe persistence diagnostic booleans and categorical values.

## 31. Forbidden Field Denylist Review

Forbidden fields include:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider/model response.
- Provider payload.
- Provider credentials.
- API keys, tokens, and secrets.
- Headers and cookies.
- `.env` content.
- Stack traces, tracebacks, and raw exceptions.
- Stdout/stderr.
- Command args.
- File contents.
- Full tool outputs.
- Raw receipts.
- Raw Python reprs.
- Raw database rows.
- Raw JSONL lines.
- Raw SQL.
- Screenshots or logs exposing secrets or raw payloads.

## 32. Raw Storage Exposure Review

Raw storage exposure remains blocked. The future endpoint must not expose:

- Raw JSONL files or lines.
- Raw SQLite rows.
- Raw SQLite paths.
- Raw SQL queries.
- Raw storage errors.
- Raw adapter responses.

Only sanitized service envelopes may cross the API boundary.

## 33. No Direct API-to-MemoryFacade Review

Direct API-to-MemoryFacade access remains blocked. The internal query service is
the approved boundary for validation, sanitization, degradation, and safe
response shaping.

Future tests must prove the handler delegates through the service and does not
instantiate or call MemoryFacade directly.

## 34. No SQL Construction Review

The API layer must never construct SQL from request input. It must not expose
SQL fragments, accept SQL-like filters, pass raw SQL through query parameters,
or log SQL.

SQL construction, if any exists below the service, must remain isolated behind
existing MemoryFacade/adapter contracts and their allowlisted query controls.

## 35. Copy/Export Exclusion Review

Copy/export remains blocked. The endpoint design is not an export API.

Future implementation must not include:

- CSV export.
- JSON export.
- Bulk dump endpoints.
- Copy-safe summary generation.
- Raw JSONL download.
- Raw SQLite download.

Any copy/export capability requires separate governance.

## 36. Cockpit/Detail Drawer Exclusion Review

Cockpit consumption and detail drawer consumption remain blocked. A future
endpoint implementation must not imply frontend approval.

Before Cockpit consumption, a separate governance step must approve safe UI
labels, empty states, warning display, detail drawer fields, abuse handling,
and forbidden field tests.

## 37. Retention/Cleanup Exclusion Review

Retention and cleanup integration remain blocked. The endpoint must not delete,
expire, mutate, compact, migrate, or reconcile evidence records.

Historical audit reads must remain readonly. Retention/cleanup requires a
separate design and governance path.

## 38. Execution Exclusion Review

The endpoint must never become an execution path. Query results are audit
metadata only and must not feed:

- Prompt rewriting.
- Retry execution.
- Replan execution.
- Provider/model calls.
- Provider switching.
- Tool execution.
- File writes.
- CI repair.
- Git commit/push/PR automation.
- Autonomous execution.

## 39. Abuse/Misuse Cases

Abuse cases include:

- Treating `would_retry=true` or `would_replan=true` as permission.
- Treating `blocked=false` as approval.
- Treating eligibility scores as operational authorization.
- Treating suggested strategies as instructions.
- Using filters as execution selectors.
- Using list/detail responses as bulk export.
- Querying broad ranges repeatedly for enumeration.
- Attempting to recover raw prompts or provider payloads through detail views.
- Using error responses to infer storage paths or SQL behavior.

## 40. Security Review Checklist

Before future implementation is approved, reviewers must verify:

- Endpoint is readonly.
- Route remains internal/private.
- Auth and authorization are real before exposure.
- Rate and size limits exist.
- Handler calls only `HistoricalDryRunAuditQueryService`.
- No direct MemoryFacade access exists.
- No raw storage access exists.
- No SQL construction exists in the API layer.
- Request parameters are allowlisted and validated.
- Responses contain only safe fields.
- Errors are categorical only.
- Required warnings are preserved.
- Logs and observability exclude raw payloads and secrets.
- Tests prove no runtime/provider/execution path exists.

## 41. Required Controls Before Implementation

Before future implementation:

- Endpoint must call `HistoricalDryRunAuditQueryService` only.
- Endpoint must not call MemoryFacade directly.
- Endpoint must not call raw storage directly.
- Endpoint must not construct SQL from request input.
- Endpoint must preserve required warnings.
- Endpoint must return sanitized envelopes only.
- Endpoint must return categorical errors only.
- Endpoint must validate query parameters.
- Endpoint must validate path parameters.
- Endpoint must enforce filter allowlist.
- Endpoint must enforce sort allowlist.
- Endpoint must enforce bounded pagination.
- Endpoint must include forbidden-field exclusion tests.
- Endpoint must include tests proving no provider/runtime/execution behavior.
- Endpoint must include tests proving no raw JSONL/SQLite/SQL exposure.

## 42. Required Controls Before Route Exposure

Before any route exposure:

- Route-level size limit must exist.
- Rate limit must exist.
- Real auth must exist.
- Real authorization must exist.
- Safe audit logging must exist.
- Safe observability must exist.
- Abuse-case review must pass.
- Security review must pass.
- Route must remain internal/private.

## 43. Required Controls Before Public Exposure

Public exposure is not approved. If ever proposed, it requires a separate
design, governance review, threat model, auth and authorization model, abuse
review, rate-limit review, privacy review, and explicit approval.

This review recommends no public exposure.

## 44. Required Controls Before Cockpit Consumption

Before Cockpit consumption:

- Separate Cockpit design must be approved.
- Readonly warning labels must be visible.
- Detail views must remain allowlisted.
- Empty/loading/error states must be safe.
- No copy/export may be enabled.
- Frontend tests must prove forbidden fields are not rendered.
- Cockpit must not present results as approval or execution input.

## 45. Required Controls Before Detail Drawer Consumption

Before detail drawer consumption:

- Detail field allowlist must be frozen.
- `block_reasons` and diagnostic details must be bounded.
- Raw record display must be forbidden.
- Raw JSON/SQL/storage views must be forbidden.
- Required warnings must remain visible near detail content.
- Tests must cover blocked and eligible records.

## 46. Required Controls Before Copy/Export

Copy/export remains disabled. Before any future copy/export:

- Separate governance must approve the feature.
- Safe summary format must be defined.
- Raw JSON/CSV export must remain blocked unless separately approved.
- Secret and payload scans must cover exported content.
- Audit logging must record export attempts without raw content.

## 47. Required Controls Before Retention/Cleanup

Before retention/cleanup integration:

- Separate retention/cleanup design must be approved.
- Read endpoints must stay separate from destructive operations.
- Cleanup must be explicit, protected, and tested.
- Cleanup must not be triggered from list/detail reads.
- Audit metadata must not become execution input.

## 48. Required Controls Before Execution Design

Before any execution design:

- A separate governance review must approve the transition.
- Persisted evidence must remain non-executable by default.
- Human approval gates must be defined.
- Provider/model call boundaries must be redesigned and tested.
- Prompt rewrite, retry execution, replan execution, provider switching, CI
  repair, and Git automation must each have separate approval gates.

This review does not approve execution design.

## 49. Explicit Non-Approval Statement

This review does not approve:

- API endpoint implementation in this branch.
- Route exposure without real auth, authorization, rate, size, and audit
  controls.
- Public exposure.
- Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Raw JSONL read.
- Raw SQLite row read.
- Raw SQL filters.
- Direct API-to-MemoryFacade.
- Prompt rewrite.
- Provider/model retry execution.
- Provider/model replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 50. Open Risks

- Internal/private boundaries can drift into public exposure if deployment
  routing is not reviewed.
- Placeholder auth or authorization could be mistaken for real protection.
- Broad queries could create enumeration or resource pressure without rate and
  size limits.
- Detail endpoints may be expanded later unless the allowlist remains strict.
- Operators may misread audit metadata as permission to execute.
- Error mapping may leak implementation details if raw exceptions are surfaced.

## 51. Open Questions

- Which backend routing layer should own internal/private route registration?
- What concrete auth and authorization mechanism should protect the route?
- Should offset or cursor pagination be used in the future implementation?
- What maximum page size should be enforced?
- Which audit logging sink should record endpoint access?
- What observability counters are necessary without over-collecting metadata?

## 52. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | This governance review is approved as docs-only. |
| Internal endpoint design | Go | Design is approved. |
| Future internal endpoint implementation | Conditional Go | Separate branch, strict tests, and controls required. |
| Route exposure without auth/authorization/rate/size/audit controls | No-Go | Blocked. |
| Public exposure | No-Go | Blocked. |
| Cockpit consumption | No-Go | Separate governance required. |
| Detail drawer consumption | No-Go | Separate governance required. |
| Copy/export | No-Go | Separate governance required. |
| Raw JSONL read | No-Go | Forbidden. |
| Raw SQLite row read | No-Go | Forbidden. |
| Raw SQL filters | No-Go | Forbidden. |
| Direct API-to-MemoryFacade | No-Go | Forbidden. |
| Prompt rewrite | No-Go | Forbidden. |
| Provider/model retry execution | No-Go | Forbidden. |
| Provider/model replan execution | No-Go | Forbidden. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Forbidden. |

## 53. Final Recommendation

Approve this governance review and keep the project in a documentation-only
state for this branch. The internal endpoint design is sound enough to support
a future implementation proposal, but implementation is only conditionally
approved in a separate branch with strict tests and controls.

Do not expose any route until real auth, authorization, rate limits, size
limits, safe audit logging, safe observability, and security review are in
place. Do not approve public exposure, Cockpit/detail drawer consumption,
copy/export, raw storage access, direct API-to-MemoryFacade, prompt rewriting,
provider/model execution, persisted evidence as execution input, or autonomous
execution.

Omni remains advisory-only.
