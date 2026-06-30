# Autonomy Dry-Run Historical Audit API Route Exposure Design

**Date:** 2026-06-30
**Branch:** `feature/autonomy-dry-run-historical-audit-api-route-exposure-design`
**Base:** `main` after PR #478
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs a future controlled route exposure path for the internal
historical dry-run audit API handlers. It is documentation only. It does not
register routes, expose endpoints, modify handlers, add Cockpit/frontend
consumption, add copy/export, add retention/cleanup, or change runtime,
provider, prompt, retry/replan, or autonomous execution behavior.

Route exposure remains blocked. The next implementable step is only a future
route-registration branch after real authentication, real authorization,
internal-only caller boundaries, route-level rate limits, route-level size
limits, query complexity limits, safe audit logging, safe observability,
security review, abuse review, and regression tests exist.

## 2. Scope

This design covers:

- Controlled internal route exposure for historical dry-run audit reads.
- Preconditions before route registration.
- Preconditions before route exposure.
- Authentication and authorization requirements.
- Internal caller model and local/developer constraints.
- Rate, size, and query complexity limits.
- Safe audit logging and observability.
- Handler delegation and storage boundary rules.
- Required request validation and response mapping.
- Test strategy, rollback, monitoring, risks, and go/no-go decisions.

## 3. Non-Goals

This design does not:

- Register API routes.
- Expose public or internal routes.
- Modify existing handlers.
- Add frontend, Cockpit, or detail drawer consumption.
- Add copy/export.
- Add retention/cleanup behavior.
- Call MemoryFacade directly from route/handler code.
- Read raw JSONL, SQLite, or storage directly.
- Construct SQL from request input.
- Change runtime output, provider routing, prompts, retry/replan execution, or
  autonomous execution.

## 4. Current Implementation State

Current state:

- Internal contract handlers exist.
- Handlers are unregistered.
- Handlers fail closed by default with `internal_enabled=False`.
- `internal_enabled=False` is not authentication.
- Delegation is only to `HistoricalDryRunAuditQueryService`.
- There is no direct MemoryFacade access from the endpoint contract layer.
- There is no raw JSONL, raw SQLite, raw storage, or SQL access.
- There is no public route exposure.
- There is no Cockpit/frontend/detail drawer.
- There is no copy/export.
- There is no runtime/provider/prompt/retry/replan/autonomous behavior.

## 5. Current Blocked State

Blocked capabilities:

- Route registration.
- Route exposure.
- Public exposure.
- Cockpit/detail drawer consumption.
- Copy/export.
- Retention/cleanup integration.
- Raw JSONL/SQLite/SQL access.
- Direct API-to-MemoryFacade access.
- Prompt rewrite.
- Provider/model retry or replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 6. Route Exposure Risk Summary

Route exposure changes the risk profile even for readonly metadata. Risks
include:

- Treating audit results as approval or execution input.
- Exposing historical metadata to unauthorized callers.
- Enumerating audit records through broad queries.
- Leaking raw payloads through logs or errors.
- Treating `internal_enabled=True` as auth.
- Accidentally wiring raw storage or MemoryFacade access into the route layer.
- Enabling frontend consumption before UI safety controls exist.

## 7. Route Exposure Design Overview

Future exposure should use a staged model:

1. Keep contract handlers unregistered.
2. Add a protected internal route registration branch.
3. Gate route registration behind real auth and authorization.
4. Enforce rate, size, and query complexity limits at the route layer.
5. Delegate only to existing internal handlers.
6. Preserve safe response envelopes and required advisory warnings.
7. Validate with route-level negative tests before any exposure.

This branch approves only the design of that staged model.

## 8. Candidate Route Inventory

Required route candidates:

- `GET /internal/audit/dry-run`
- `GET /internal/audit/dry-run/{plan_id}`

These are design candidates only. They must not be registered in this branch.

## 9. Internal-Only Route Registration Model

Future route registration must be internal-only:

- Bound to localhost, private service mesh, or another explicitly approved
  internal boundary.
- Disabled by default outside approved environments.
- Protected by real auth and authorization.
- Separated from public chat/runtime routes.
- Not discoverable as a public API.

## 10. Route Registration Preconditions

Before route registration:

- Real authentication exists.
- Real authorization exists.
- Internal-only caller boundary exists.
- Route-level rate limits exist.
- Route-level size limits exist.
- Query complexity limits exist.
- Audit logging excludes raw payloads.
- Observability excludes raw payloads.
- Service-only delegation tests exist.
- Forbidden-field regression tests exist.
- Security and abuse reviews pass.

## 11. Authentication Requirements

Authentication must be real and explicit. `internal_enabled=True` is not
authentication and must not be used as an auth substitute.

Future implementation must define:

- Caller identity source.
- Token/session verification behavior.
- Failure response category.
- No raw token logging.
- Tests proving unauthenticated calls fail closed.

## 12. Authorization Requirements

Authorization must be separate from authentication. A caller being authenticated
does not imply permission to read historical audit metadata.

Future implementation must require a readonly historical-audit permission or an
equivalent internal-admin permission. Unauthorized callers must receive safe
categorical denial without raw details.

## 13. Internal Caller Model

Approved callers should be narrow:

- Local operator tooling in approved environments.
- Internal backend components explicitly granted readonly audit access.
- Future Cockpit backend bridge only after separate Cockpit governance.

Unapproved callers include public clients, arbitrary frontend code, provider
adapters, runtime execution paths, and autonomous execution components.

## 14. Local-Only/Developer-Only Constraints

If first exposed for development, the route should be:

- Localhost-only.
- Disabled by default.
- Explicitly enabled per process or test fixture.
- Blocked in production unless a separate approval exists.
- Covered by tests proving it is not public by default.

Developer-only exposure must still use safe responses and must not log raw
payloads.

## 15. Rate Limit Design

Route-level rate limits must control:

- Requests per caller.
- Requests per route.
- Burst behavior.
- Repeated broad list queries.
- Repeated detail lookups.

Rate-limit responses must be categorical and must not expose raw request,
caller credential, storage, or route internals.

## 16. Size Limit Design

Route-level size limits must control:

- Query string length.
- Number of query parameters.
- Individual parameter length.
- Path parameter length.
- Response item count.
- Warning and error metadata size.

Oversized input should fail before handler invocation when possible.

## 17. Query Complexity Limit Design

Query complexity limits should prevent expensive or broad reads:

- Require bounded `limit`.
- Require bounded `offset`.
- Restrict sort fields to allowlisted fields.
- Restrict filters to allowlisted fields.
- Reject excessive filter count.
- Prefer conservative defaults.
- Forbid unbounded scans and raw storage selectors.

## 18. Audit Logging Design

Audit logs may include:

- Operation name.
- Route name.
- Caller category or safe caller ID.
- Safe request/session/trace IDs if already sanitized.
- Allowed filter keys only.
- Sort field and direction.
- Bounded limit/offset.
- Status category.
- Degraded boolean.
- Error category.
- Timestamp.

Audit logs must not include raw request bodies, raw response bodies, raw query
strings with secrets, raw exceptions, tracebacks, raw storage records, raw SQL,
prompts, responses, provider payloads, tool outputs, credentials, headers,
cookies, command args, file contents, or `.env` content.

## 19. Observability Design

Observability should be aggregate and categorical:

- Request count by route.
- Denied count by auth/authorization category.
- Rate-limit count.
- Size-limit count.
- Degraded count.
- Error-category count.
- Latency buckets.
- Returned item count buckets.

Observability must not include raw payloads, raw rows, SQL, paths, prompts,
responses, provider payloads, tool outputs, credentials, headers, cookies, or
stack traces.

## 20. Safe Request Logging Rules

Safe request logging rules:

- Log route name, not raw URL.
- Log allowlisted filter keys, not full raw query strings.
- Log bounded numeric limit/offset.
- Log sanitized request/session/trace IDs only when already safe.
- Log caller category only when safe.
- Never log raw auth material.

## 21. Safe Response Logging Rules

Safe response logging rules:

- Log status code.
- Log degraded boolean.
- Log error category.
- Log returned item count.
- Log generated timestamp.
- Do not log response body.
- Do not log evidence summaries unless separately approved as safe.
- Do not log detail payloads.

## 22. Forbidden Logging Denylist

Forbidden in logs:

- Raw JSONL.
- Raw SQLite rows.
- Raw SQL.
- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider/model response.
- Provider payload.
- Tool output.
- Secrets, tokens, API keys, credentials.
- Headers and cookies.
- `.env` content.
- Stack traces and tracebacks.
- Raw exceptions.
- Stdout/stderr.
- Command args.
- File contents.
- Raw database rows.
- Raw Python reprs.

## 23. Handler Delegation Rules

Future route handlers must:

- Parse and validate route input.
- Enforce route-level auth, authorization, rate, size, and complexity controls.
- Call existing internal contract handlers.
- Preserve handler envelopes and warnings.
- Return categorical errors only.

Future route handlers must not call MemoryFacade, raw storage, runtime,
provider/model, retry/replan, or execution code.

## 24. HistoricalDryRunAuditQueryService-Only Rule

The approved dependency path remains:

route -> internal contract handler -> `HistoricalDryRunAuditQueryService` ->
MemoryFacade safe query contracts

The route layer must not bypass the internal contract handler or the internal
query service.

## 25. No Direct MemoryFacade Rule

Direct route-to-MemoryFacade access is not approved. Future route tests must
prove:

- No MemoryFacade import in route code.
- No MemoryFacade construction in route code.
- No direct MemoryFacade method calls in route code.
- Only the internal contract handler/service path is used.

## 26. No Raw Storage Rule

Future route code must not:

- Read JSONL files.
- Read SQLite rows directly.
- Use SQLite adapters directly.
- Use filesystem storage paths.
- Return raw rows or raw lines.
- Surface storage exceptions.

## 27. No SQL Construction Rule

Future route code must not construct SQL from request input. SQL-like input
must be rejected by validation and must not be logged.

All query behavior must remain inside governed MemoryFacade query contracts.

## 28. Request Validation Requirements

Future route implementation must validate:

- Allowed query keys.
- Enum values.
- Boolean values.
- Timestamp ranges.
- Sanitized ID values.
- Sort field and direction.
- Limit and offset bounds.
- Query string size.
- Parameter count.
- Parameter length.

Invalid input must fail safely before accessing data.

## 29. Path Validation Requirements

The detail route must validate `{plan_id}`:

- Non-empty.
- Bounded length.
- Safe characters only.
- No slashes or path traversal.
- No SQL-like fragments.
- No secret-like payloads.

Invalid path values must not call handlers or service methods.

## 30. Filter/Sort Allowlist Requirements

Allowed filters must remain the historical audit allowlist:

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
- Created-at range.
- Recorded-at range.

Allowed sort fields must remain static and deterministic. Raw SQL filters and
free-form storage selectors remain forbidden.

## 31. Pagination Requirements

Pagination requirements:

- Conservative default limit.
- Explicit maximum limit.
- Bounded offset or approved cursor.
- Deterministic ordering.
- No unbounded list queries.
- No bulk export through pagination loops without separate governance.

## 32. Error/Degradation Mapping Requirements

Errors must map to safe categories only:

- Authentication failed.
- Authorization failed.
- Rate limited.
- Payload too large.
- Invalid request.
- Invalid filter.
- Invalid sort.
- Not found.
- Query failed.
- Invalid internal service response.

No raw exception, traceback, storage path, SQL, prompt, response, provider
payload, or tool output may be returned.

## 33. Required Advisory Warnings

Future route responses must preserve:

- Query results are readonly audit metadata.
- Query results are not approval.
- Query results are not execution input.
- `would_retry` and `would_replan` are not execution.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- Copy/export remains disabled.
- Omni remains advisory-only.

## 34. Safe Response Envelope Requirements

List responses must preserve:

- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category` only when degraded
- `generated_at`

Detail responses must preserve:

- `detail`
- `warnings`
- `degraded`
- `error_category` only when degraded
- `generated_at`

## 35. Forbidden Field Denylist

Forbidden response fields and content:

- Raw JSONL.
- Raw SQLite rows.
- Raw SQL.
- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider/model response.
- Provider payload.
- Tool output.
- Secrets, tokens, API keys, credentials.
- Headers and cookies.
- `.env` content.
- Stack traces and tracebacks.
- Raw exceptions.
- Stdout/stderr.
- Command args.
- File contents.
- Raw database rows.
- Raw Python reprs.

## 36. Abuse/Misuse Cases

Abuse and misuse cases:

- Treating audit results as approval.
- Treating audit results as execution input.
- Treating `would_retry` or `would_replan` as execution.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Scraping historical records through repeated broad queries.
- Guessing plan IDs through detail routes.
- Using route errors to infer storage internals.
- Using route logs to recover sensitive payloads.

## 37. Security Review Checklist

Before implementation:

- Verify route is internal-only.
- Verify real authentication.
- Verify real authorization.
- Verify rate and size limits.
- Verify query complexity limits.
- Verify service-only delegation.
- Verify no direct MemoryFacade access.
- Verify no raw storage access.
- Verify no SQL construction.
- Verify forbidden-field tests.
- Verify safe logging and observability.
- Verify no runtime/provider/execution behavior.

## 38. Test Strategy Before Implementation

Future tests should cover:

- Unauthenticated denial.
- Unauthorized denial.
- Rate-limit denial.
- Size-limit denial.
- Invalid query rejection.
- Invalid path rejection.
- Safe list success.
- Safe detail success.
- Service failure degradation.
- Forbidden-field exclusion.
- No raw storage access.
- No runtime/provider/execution path.

## 39. Required Tests Before Route Registration

Before route registration:

- Tests proving route stays disabled by default.
- Tests proving internal-only registration gate.
- Tests proving auth and authorization are required.
- Tests proving rate and size limits.
- Tests proving query complexity controls.
- Tests proving service-only delegation.
- Tests proving no MemoryFacade bypass.
- Tests proving no raw JSONL/SQLite/SQL exposure.

## 40. Required Tests Before Route Exposure

Before route exposure:

- End-to-end internal route tests.
- Negative auth tests.
- Negative authorization tests.
- Abuse-case tests for broad queries.
- Safe logging tests.
- Safe observability tests.
- Degradation tests for service failures.
- Regression tests for forbidden fields.

## 41. Required Tests Before Cockpit Consumption

Before Cockpit consumption:

- API contract tests.
- Frontend normalizer tests.
- Empty/loading/error state tests.
- Readonly label tests.
- Forbidden rendering tests.
- Tests proving no copy/export controls.
- Tests proving no execution controls.

## 42. Required Tests Before Copy/Export

Before copy/export:

- Export governance tests.
- Safe summary tests.
- Secret and payload scan tests.
- No raw JSONL/SQLite/SQL export tests.
- Audit logging tests for export attempts.
- Rate and size tests for export operations.

## 43. Required Tests Before Public Exposure

Public exposure is not approved. If ever proposed, tests must include:

- Public threat model validation.
- Strong auth and authorization tests.
- Tenant/caller isolation tests.
- Abuse and rate-limit tests.
- Privacy review tests.
- Security review tests.
- Forbidden payload regression tests.

## 44. Rollback Strategy

Future route exposure must include rollback:

- Feature flag or route registration gate.
- Ability to disable route without code rollback.
- Safe degraded response while disabled.
- Audit log entry for disablement without raw payloads.
- Operational playbook for reverting route exposure.

## 45. Operational Monitoring Requirements

Monitoring should include:

- Request counts.
- Denied auth/authorization counts.
- Rate-limit counts.
- Size-limit counts.
- Error-category counts.
- Degraded response counts.
- Latency buckets.
- Returned item count buckets.

Monitoring must not include raw payloads, raw rows, SQL, prompts, responses,
provider payloads, tool outputs, secrets, headers, cookies, stack traces, or
file contents.

## 46. Required Controls Before Implementation Branch

Before implementation branch:

- Approved design.
- Approved governance review.
- Auth approach selected.
- Authorization model selected.
- Internal-only route boundary selected.
- Test plan accepted.
- Logging and observability model accepted.
- Security and abuse review owners identified.

## 47. Required Controls Before Route Registration

Before route registration:

- Real authentication, not `internal_enabled`.
- Real authorization.
- Internal-only caller boundary.
- Route-level rate limits.
- Route-level size limits.
- Query complexity limits.
- Audit logging without raw payloads.
- Observability without raw payloads.
- Forbidden-field regression tests.
- Tests proving no raw JSONL/SQLite/SQL exposure.
- Tests proving no runtime/provider/execution behavior.
- Tests proving service-only delegation.
- Security review.
- Abuse review.
- Explicit approval for internal route registration.

## 48. Required Controls Before Route Exposure

Before route exposure:

- Internal route registration approved and tested.
- Real auth/authorization enabled.
- Rate and size limits enabled.
- Logging and observability enabled.
- Security review complete.
- Abuse review complete.
- Rollback switch tested.
- Route is disabled in public environments.

## 49. Required Controls Before Public Exposure

Public exposure remains blocked. Any future public exposure requires a separate
proposal, threat model, governance review, privacy review, auth review,
authorization review, rate-limit review, security review, and explicit
approval.

## 50. Required Controls Before Cockpit/Detail Drawer

Before Cockpit or detail drawer:

- Separate Cockpit design.
- Separate Cockpit governance review.
- Route exposure approved.
- UI warning labels.
- Readonly semantics.
- Safe detail allowlist.
- Forbidden rendering tests.
- No copy/export unless separately approved.

## 51. Required Controls Before Copy/Export

Before copy/export:

- Separate governance approval.
- Safe export format.
- Export rate and size limits.
- Export audit logging.
- Secret and payload scan tests.
- No raw JSONL/SQLite/SQL export unless separately approved.

## 52. Required Controls Before Retention/Cleanup

Before retention/cleanup:

- Separate retention/cleanup design.
- Separate governance review.
- Explicit/manual cleanup controls if destructive.
- Tests proving reads never trigger cleanup.
- Tests proving retention operations do not expose raw payloads.

## 53. Required Controls Before Execution Design

Before execution design:

- Separate execution design.
- Separate governance approval.
- Human approval gates.
- Proof persisted evidence is not execution input.
- Separate approval for prompt rewrite, retry execution, replan execution,
  provider/model calls, provider switching, CI repair, and Git automation.

## 54. Open Risks

Open risks:

- Internal routes can drift toward public exposure.
- `internal_enabled` can be misunderstood as auth.
- Broad queries can cause enumeration pressure.
- Logs can accidentally capture raw query strings.
- Future Cockpit consumption can imply operational authorization.
- Detail routes can leak more than list routes if allowlists drift.

## 55. Open Questions

Open questions:

- Which auth mechanism should protect internal audit routes?
- Which authorization permission should represent readonly audit access?
- Should the first route exposure be localhost-only?
- What exact route-level rate limits should apply?
- What maximum query string length should apply?
- Which monitoring sink should receive safe route metrics?

## 56. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation/design | Go | This branch is design-only. |
| Route exposure design | Go | Allowed as documentation. |
| Route registration | No-Go | Not approved yet. |
| Route exposure | No-Go | Not approved yet. |
| Public exposure | No-Go | Not approved. |
| Cockpit/detail drawer consumption | No-Go | Not approved. |
| Copy/export | No-Go | Not approved. |
| Retention/cleanup integration | No-Go | Not approved. |
| Raw JSONL/SQLite/SQL access | No-Go | Forbidden. |
| Direct API-to-MemoryFacade access | No-Go | Forbidden. |
| Prompt rewrite | No-Go | Forbidden. |
| Provider/model retry or replan execution | No-Go | Forbidden. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Forbidden. |

## 57. Final Recommendation

Approve this document as route exposure design only. Do not register or expose
routes in this branch. A future implementation branch may be considered only
after real authentication, real authorization, internal-only caller boundaries,
route-level rate limits, route-level size limits, query complexity limits, safe
audit logging, safe observability, forbidden-field regression tests, tests for
no raw storage exposure, tests for no runtime/provider/execution behavior,
service-only delegation tests, security review, abuse review, and explicit
internal route registration approval are in place.

Omni remains advisory-only.
