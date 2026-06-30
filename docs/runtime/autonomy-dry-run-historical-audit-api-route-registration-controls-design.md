# Autonomy Dry-Run Historical Audit API Route Registration Controls Design

**Date:** 2026-06-30
**Branch:** `feature/autonomy-dry-run-historical-audit-api-route-registration-controls-design`
**Base:** `main` after PR #480
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs the controls required before any internal route
registration of the historical dry-run audit API handlers. It is documentation
only. It does not register routes, expose endpoints, modify handlers, add auth
code, add rate limiter code, add frontend/Cockpit/detail drawer consumption,
add copy/export, add retention/cleanup, or change runtime, provider, prompt,
retry/replan, or autonomous execution behavior.

Route registration remains blocked. A future implementation branch may be
considered only after real authentication, real authorization, internal-only
caller identity, explicit route registration approval, route-level rate
limits, route-level size limits, query complexity limits, safe audit logging,
safe observability, regression tests, security review, abuse review, and a
rollback plan are defined and testable.

## 2. Scope

This design covers:

- Required controls before route registration.
- Required controls before route exposure.
- Candidate internal audit routes.
- Authentication and authorization requirements.
- Internal caller identity and local/developer constraints.
- Rate, size, and query complexity requirements.
- Safe audit logging and observability requirements.
- Handler invocation and delegation boundaries.
- Request, path, filter, sort, pagination, error, and response requirements.
- Fail-closed behavior and internal flag requirements.
- Required tests, rollback, monitoring, risks, and go/no-go decisions.

## 3. Non-Goals

This design does not:

- Register API routes.
- Expose internal or public routes.
- Modify endpoint handlers.
- Modify MemoryFacade.
- Modify `HistoricalDryRunAuditQueryService`.
- Modify storage, runtime, provider routing, or prompts.
- Add frontend, Cockpit, or detail drawer consumption.
- Add copy/export.
- Add retention/cleanup.
- Read raw JSONL, SQLite, or storage directly.
- Construct SQL from request input.
- Execute retry or replan.
- Call provider/model code.
- Enable autonomous execution or self-repair.

## 4. Current Implementation State

Current state:

- Internal contract handlers exist.
- Handlers are unregistered.
- Handlers fail closed by default with `internal_enabled=False`.
- `internal_enabled=False` is not authentication.
- Delegation is only to `HistoricalDryRunAuditQueryService`.
- No public route is exposed.
- No internal route is exposed.
- No Cockpit/frontend/detail drawer exists.
- No copy/export exists.
- Route registration remains blocked.
- No runtime/provider/prompt/retry/replan/autonomous behavior exists.

## 5. Current Governance State

Current governance allows:

- Documentation.
- Route exposure design.
- Route exposure governance review.
- Route registration controls design.

Current governance does not allow:

- Route registration implementation.
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

## 6. Route Registration Risk Summary

Route registration changes the risk boundary even before public exposure.
Risks include:

- Mistaking `internal_enabled=True` for authentication.
- Registering routes before real authorization exists.
- Exposing readonly metadata to unauthorized internal callers.
- Allowing broad historical enumeration through list queries.
- Allowing detail lookups to leak existence or storage information.
- Logging raw query strings, raw errors, or sensitive payloads.
- Introducing direct MemoryFacade, raw storage, or SQL paths.
- Creating a route that later becomes public by deployment drift.
- Encouraging Cockpit consumption before UI governance.

## 7. Route Registration Control Model

The required control model is layered:

1. Keep handlers unregistered by default.
2. Require explicit approval for any route registration branch.
3. Require real authentication before handler invocation.
4. Require real authorization after authentication.
5. Require an internal-only caller boundary.
6. Enforce rate, size, and query complexity limits at the route layer.
7. Preserve handler and service-only delegation boundaries.
8. Return sanitized envelopes and categorical errors only.
9. Log and observe only safe metadata.
10. Prove all controls with focused tests before registration.

## 8. Candidate Routes

Required candidate routes:

- `GET /internal/audit/dry-run`
- `GET /internal/audit/dry-run/{plan_id}`

These are candidate route names only. They must not be registered by this
document.

## 9. Internal-Only Registration Boundary

Future route registration must be internal-only:

- Not public internet exposed.
- Not part of public chat/runtime APIs.
- Not reachable by arbitrary frontend clients.
- Bound to localhost, private service mesh, or another approved internal
  boundary.
- Disabled by default outside approved environments.
- Protected by real auth and authorization.
- Covered by tests proving public exposure is absent.

## 10. Auth Control Requirements

Authentication requirements:

- Authentication must be real and explicit.
- `internal_enabled` must not be treated as authentication.
- Caller identity must be verified before handler invocation.
- Missing, malformed, expired, or invalid credentials must fail closed.
- Auth failures must return categorical errors only.
- Raw credentials, tokens, headers, and cookies must not be logged.
- Tests must prove unauthenticated calls fail closed.

## 11. Authorization Control Requirements

Authorization requirements:

- Authorization must be separate from authentication.
- Authenticated callers must have explicit readonly historical-audit
  permission or an approved internal-admin equivalent.
- Unauthorized calls must fail closed.
- Authorization failures must not reveal record existence.
- Authorization failures must not include raw policy, caller, token, or storage
  details.
- Tests must prove unauthorized callers fail closed.

## 12. Internal Caller Identity Model

Approved future caller identity should be narrow and explicit:

- Local operator tooling in approved environments.
- Internal backend components with readonly audit permission.
- Future Cockpit backend bridge only after separate governance.

Unapproved callers:

- Public clients.
- Arbitrary frontend code.
- Runtime execution paths.
- Provider adapters.
- Autonomous execution components.
- CI repair, self-repair, retry, or replan executors.

## 13. Local/Developer-Only Constraints

Any first registration should be local/developer-only unless separate
governance approves more:

- Localhost-only by default.
- Disabled unless explicitly enabled for tests or development.
- Blocked in production.
- Still protected by real auth and authorization.
- Still subject to rate, size, and query complexity limits.
- Still subject to safe logging and observability rules.

## 14. Route-Level Rate Limit Requirements

Route-level rate limits must cover:

- Requests per caller.
- Requests per route.
- Burst behavior.
- Repeated broad list queries.
- Repeated detail lookups.
- Repeated invalid-auth attempts.
- Repeated invalid-query attempts.

Rate-limit responses must be categorical and must not expose raw caller,
credential, request, route, or storage internals.

## 15. Route-Level Size Limit Requirements

Size limits must cover:

- Query string length.
- Number of query parameters.
- Individual parameter length.
- Path parameter length.
- Request header size if route framework exposes it safely.
- Response item count.
- Warning and error metadata size.

Oversized inputs should fail before handler invocation when possible.

## 16. Query Complexity Limit Requirements

Query complexity limits must prevent broad or expensive reads:

- Conservative default limit.
- Explicit maximum limit.
- Bounded offset or approved cursor.
- Static filter allowlist.
- Static sort allowlist.
- Deterministic ordering.
- Maximum filter count.
- No unbounded scans.
- No raw storage selectors.
- No raw SQL filters.

## 17. Audit Logging Requirements

Safe audit logs may include:

- Operation name.
- Route name.
- Caller category or sanitized caller ID.
- Sanitized request/session/trace IDs if already safe.
- Allowed filter keys only.
- Sort field and direction.
- Bounded limit and offset/cursor metadata when safe.
- Status category.
- Degraded boolean.
- Error category.
- Timestamp.

Audit logs must not include raw request bodies, raw response bodies, raw query
strings, raw exceptions, tracebacks, raw storage records, raw SQL, prompts,
responses, provider payloads, tool outputs, credentials, headers, cookies,
command args, file contents, or `.env` content.

## 18. Observability Requirements

Observability should be aggregate and categorical:

- Request count by route.
- Auth failure count.
- Authorization failure count.
- Rate-limit count.
- Size-limit count.
- Invalid request count.
- Error-category count.
- Degraded response count.
- Latency buckets.
- Returned item count buckets.

Observability must not include raw payloads, raw rows, SQL, prompts, responses,
provider payloads, tool outputs, credentials, headers, cookies, stack traces,
or file contents.

## 19. Safe Request Logging Rules

Safe request logging rules:

- Log route name, not raw URL.
- Log safe operation name.
- Log allowlisted filter keys, not raw query strings.
- Log bounded numeric limit/offset.
- Log sanitized IDs only when already safe.
- Log caller category only when safe.
- Do not log auth material.
- Do not log raw headers or cookies.

## 20. Safe Response Logging Rules

Safe response logging rules:

- Log status category.
- Log degraded boolean.
- Log error category.
- Log returned item count.
- Log generated timestamp.
- Do not log response body.
- Do not log detail payloads.
- Do not log evidence summaries unless separately approved.

## 21. Forbidden Logging Denylist

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

## 22. Handler Invocation Rules

Future routes may invoke handlers only after:

- Route is explicitly registered in an approved branch.
- Real authentication succeeds.
- Real authorization succeeds.
- Rate limit checks pass.
- Size limit checks pass.
- Query complexity checks pass.
- Request/path validation passes.

Future routes must fail closed before handler invocation if any control fails.

## 23. HistoricalDryRunAuditQueryService-Only Delegation Rule

The approved dependency path remains:

route -> internal contract handler -> `HistoricalDryRunAuditQueryService` ->
MemoryFacade safe query contracts

Future route code must not bypass the internal contract handler or internal
query service.

## 24. No Direct MemoryFacade Rule

Direct API-to-MemoryFacade access remains forbidden. Future route registration
tests must prove:

- No MemoryFacade import in route code.
- No MemoryFacade construction in route code.
- No direct MemoryFacade method calls in route code.
- Only the internal handler/service path is used.

## 25. No Raw Storage Rule

Future route code must not:

- Read JSONL files.
- Read SQLite rows directly.
- Use SQLite adapters directly.
- Use raw storage paths.
- Return raw rows or raw lines.
- Return storage exceptions.

## 26. No SQL Construction Rule

Future route code must not construct SQL from request input. SQL-like input
must be rejected by validation and must not be logged.

All query behavior must remain inside governed MemoryFacade query contracts
through `HistoricalDryRunAuditQueryService`.

## 27. Request Validation Requirements

Future route implementation must validate:

- Allowed query keys.
- Enum values.
- Boolean values.
- Timestamp ranges.
- Sanitized ID values.
- Sort field and direction.
- Limit and offset/cursor bounds.
- Query string size.
- Parameter count.
- Parameter length.

Invalid input must fail safely before data access.

## 28. Path Validation Requirements

The detail route must validate `{plan_id}`:

- Non-empty.
- Bounded length.
- Safe characters only.
- No slashes.
- No path traversal.
- No SQL-like fragments.
- No secret-like payloads.

Invalid path values must not call handlers or service methods.

## 29. Filter/Sort Allowlist Requirements

Allowed filters must remain static:

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

Allowed sort fields must remain static and deterministic. Raw SQL filters,
free-form selectors, and storage-specific filters remain forbidden.

## 30. Pagination Requirements

Pagination requirements:

- Conservative default limit.
- Explicit maximum limit.
- Bounded offset or approved opaque cursor.
- Deterministic ordering.
- No unbounded list queries.
- No bulk export through pagination loops without separate governance.
- No raw storage pointers in cursors.

## 31. Error/Degradation Mapping Requirements

Errors must map to safe categories only:

- Authentication failed.
- Authorization failed.
- Rate limited.
- Payload too large.
- Invalid request.
- Invalid path.
- Invalid filter.
- Invalid sort.
- Invalid pagination.
- Not found.
- Query failed.
- Invalid internal service response.
- Route disabled.

Raw exceptions, tracebacks, SQL, storage paths, prompts, responses, provider
payloads, tool outputs, headers, cookies, and secrets must not be returned.

## 32. Required Advisory Warnings

Future route responses must preserve:

- Query results are readonly audit metadata.
- Query results are not approval.
- Query results are not execution input.
- `would_retry` and `would_replan` are not execution.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- Copy/export remains disabled.
- Omni remains advisory-only.

## 33. Safe Response Envelope Requirements

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

No unsafe debug fields may be added.

## 34. Forbidden Field Denylist

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

## 35. Fail-Closed Behavior Requirements

Fail-closed behavior is required for:

- Route disabled.
- Missing auth.
- Invalid auth.
- Missing authorization.
- Invalid authorization.
- Caller outside internal boundary.
- Rate limit exceeded.
- Size limit exceeded.
- Query complexity exceeded.
- Invalid request/path/filter/sort/pagination.
- Internal service failure.

Fail-closed responses must be safe, categorical, and metadata-only.

## 36. Feature Flag / Internal Flag Requirements

Future route registration must use an explicit route registration gate.
Requirements:

- Disabled by default.
- Separate from authentication.
- Separate from authorization.
- Safe to disable without code rollback.
- Covered by tests proving disabled routes fail closed.
- Not sufficient on its own for exposure.

`internal_enabled=True` may be a route activation gate only if separately
approved; it must never be treated as authentication or authorization.

## 37. Route Registration Preconditions

Before route registration:

- Real authentication exists.
- Real authorization exists.
- Internal-only caller identity exists.
- Explicit route registration approval exists.
- Route-level rate limits exist.
- Route-level size limits exist.
- Query complexity limits exist.
- Safe audit logging exists.
- Safe observability exists.
- Forbidden-field regression tests exist.
- Service-only delegation tests exist.
- No raw storage/SQL tests exist.
- No runtime/provider/execution tests exist.
- Security and abuse reviews pass.

## 38. Route Exposure Preconditions

Before route exposure:

- Route registration has been approved and implemented.
- Route registration tests pass.
- Real auth and authorization are enabled.
- Rate, size, and complexity limits are enabled.
- Safe audit logging is enabled.
- Safe observability is enabled.
- Rollback switch is tested.
- Public environment exposure is blocked.
- Security and abuse reviews are complete.

## 39. Public Exposure Prohibition

Public exposure is not approved. Any future public exposure requires separate
design, threat model, privacy review, auth review, authorization review,
rate-limit review, security review, abuse review, and explicit governance
approval.

## 40. Cockpit/Detail Drawer Prohibition

Cockpit and detail drawer consumption are not approved. Future UI work requires
separate design and governance for:

- Readonly labels.
- Safe normalizers.
- Empty/loading/error states.
- Detail allowlists.
- Forbidden rendering tests.
- No copy/export controls unless separately approved.
- No execution controls.

## 41. Copy/Export Prohibition

Copy/export remains disabled. Future copy/export requires separate governance,
safe summary design, export rate/size limits, audit logging, secret/payload
scan tests, and explicit approval.

Raw JSONL, raw SQLite rows, raw SQL, prompts, responses, provider payloads, and
tool outputs must not be exported.

## 42. Retention/Cleanup Exclusion

Retention and cleanup integration are excluded from route registration. Future
retention/cleanup work requires separate design and governance.

Read routes must never trigger cleanup, retention changes, deletion, or
destructive behavior.

## 43. Execution Exclusion

Route registration must never:

- Rewrite prompts.
- Execute retry.
- Execute replan.
- Call provider/model.
- Change provider routing.
- Change runtime output.
- Execute tools.
- Execute commands.
- Patch files.
- Run CI repair.
- Commit, push, or open PRs.
- Use persisted evidence as execution input.
- Enable autonomous execution.

## 44. Abuse/Misuse Cases

Abuse and misuse cases:

- Treating audit results as approval.
- Treating audit results as execution input.
- Treating `would_retry` or `would_replan` as execution.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Scraping records through repeated broad queries.
- Guessing plan IDs.
- Inferring storage internals from errors.
- Recovering sensitive payloads from logs.
- Using internal routes as a bridge to public exposure.

## 45. Security Review Checklist

Before implementation:

- Verify route is internal-only.
- Verify real authentication.
- Verify real authorization.
- Verify internal caller identity.
- Verify rate limits.
- Verify size limits.
- Verify query complexity limits.
- Verify safe request/response logging.
- Verify safe observability.
- Verify service-only delegation.
- Verify no MemoryFacade bypass.
- Verify no raw storage access.
- Verify no SQL construction.
- Verify forbidden-field tests.
- Verify no runtime/provider/execution behavior.

## 46. Required Tests Before Implementation

Before implementation:

- Request validation unit tests.
- Path validation unit tests.
- Auth failure design tests or test plan.
- Authorization failure design tests or test plan.
- Rate-limit design tests or test plan.
- Size-limit design tests or test plan.
- Query complexity design tests or test plan.
- Safe logging tests or test plan.
- Safe observability tests or test plan.
- Forbidden-field regression test plan.

## 47. Required Tests Before Route Registration

Before route registration:

- Route disabled-by-default tests.
- Internal-only gate tests.
- Authentication-required tests.
- Authorization-required tests.
- Invalid auth fails-closed tests.
- Unauthorized caller fails-closed tests.
- Rate-limit tests.
- Size-limit tests.
- Query complexity tests.
- Service-only delegation tests.
- No MemoryFacade bypass tests.
- No raw JSONL/SQLite/SQL exposure tests.
- No runtime/provider/execution behavior tests.

## 48. Required Tests Before Route Exposure

Before route exposure:

- End-to-end internal route tests.
- Negative authentication tests.
- Negative authorization tests.
- Abuse-case broad query tests.
- Plan ID guessing tests.
- Safe logging tests.
- Safe observability tests.
- Service failure degradation tests.
- Forbidden-field regression tests.
- Rollback/disablement tests.
- Tests proving route remains internal-only.

## 49. Required Tests Before Cockpit Consumption

Before Cockpit consumption:

- API contract tests.
- Frontend normalizer tests.
- Empty/loading/error state tests.
- Readonly label tests.
- Forbidden rendering tests.
- No copy/export controls tests.
- No execution controls tests.
- Separate Cockpit governance approval.

## 50. Required Tests Before Copy/Export

Before copy/export:

- Separate export governance tests.
- Safe summary tests.
- Secret and payload scan tests.
- No raw JSONL/SQLite/SQL export tests.
- Export audit logging tests.
- Export rate and size tests.
- Explicit copy/export approval.

## 51. Rollback Strategy

Future route registration must include rollback:

- Route registration gate or feature flag.
- Ability to disable route without code rollback.
- Safe disabled response.
- Safe audit log entry for disablement.
- Operational playbook.
- Tests proving disablement works.
- Monitoring for post-disable traffic attempts.

## 52. Operational Monitoring Requirements

Operational monitoring should include:

- Request counts.
- Auth failure counts.
- Authorization failure counts.
- Rate-limit counts.
- Size-limit counts.
- Query complexity rejection counts.
- Error-category counts.
- Degraded response counts.
- Latency buckets.
- Returned item count buckets.
- Disabled-route access attempts.

Monitoring must not include raw payloads, raw rows, SQL, prompts, responses,
provider payloads, tool outputs, secrets, headers, cookies, stack traces, or
file contents.

## 53. Required Controls Before Implementation Branch

Before implementation branch:

- This design accepted.
- Route exposure governance accepted.
- Auth approach selected.
- Authorization model selected.
- Internal caller identity model selected.
- Route registration gate selected.
- Rate, size, and complexity limit strategy selected.
- Logging and observability model selected.
- Security and abuse review owners identified.

## 54. Required Controls Before Route Registration

Before route registration:

- Real authentication, not `internal_enabled`.
- Real authorization.
- Internal-only caller identity.
- Explicit route registration approval.
- Route-level rate limits.
- Route-level size limits.
- Query complexity limits.
- Safe audit logging without raw payloads.
- Safe observability without raw payloads.
- Forbidden-field regression tests.
- Tests proving no raw JSONL/SQLite/SQL exposure.
- Tests proving no runtime/provider/execution behavior.
- Tests proving service-only delegation.
- Tests proving invalid auth fails closed.
- Tests proving unauthorized caller fails closed.
- Tests proving route remains internal-only.
- Security review.
- Abuse review.
- Rollback plan.

## 55. Required Controls Before Route Exposure

Before route exposure:

- Route registration approved and tested.
- Route disabled-by-default behavior tested.
- Real auth and authorization enabled.
- Internal-only boundary verified.
- Rate, size, and complexity limits enabled.
- Safe audit logging enabled.
- Safe observability enabled.
- Rollback switch tested.
- Security review complete.
- Abuse review complete.
- Public environment exposure blocked.

## 56. Required Controls Before Public Exposure

Public exposure remains prohibited. Any future proposal requires:

- Separate public exposure design.
- Threat model.
- Privacy review.
- Authentication review.
- Authorization review.
- Rate-limit review.
- Security review.
- Abuse review.
- Explicit governance approval.

## 57. Required Controls Before Cockpit/Detail Drawer

Before Cockpit/detail drawer:

- Separate Cockpit design.
- Separate Cockpit governance review.
- Route exposure approved.
- UI readonly warning labels.
- Safe detail allowlist.
- Forbidden rendering tests.
- No copy/export unless separately approved.
- No execution controls.

## 58. Required Controls Before Copy/Export

Before copy/export:

- Separate copy/export governance.
- Safe export format.
- Export rate and size limits.
- Export audit logging.
- Secret and payload scan tests.
- No raw JSONL/SQLite/SQL export.
- Explicit approval.

## 59. Required Controls Before Retention/Cleanup

Before retention/cleanup:

- Separate retention/cleanup design.
- Separate governance review.
- Explicit/manual cleanup controls if destructive.
- Tests proving read routes do not trigger cleanup.
- Tests proving cleanup does not expose raw payloads.
- Tests proving retention does not change route response safety.

## 60. Required Controls Before Execution Design

Before execution design:

- Separate execution design.
- Separate governance approval.
- Human approval gates.
- Proof persisted evidence is not execution input.
- Separate approval for prompt rewrite, retry execution, replan execution,
  provider/model calls, provider switching, CI repair, and Git automation.

## 61. Open Risks

Open risks:

- Internal routes can drift into public exposure.
- `internal_enabled` can be misunderstood as auth.
- Auth placeholders can persist into implementation.
- Logs can accidentally capture raw query strings.
- Broad queries can create enumeration pressure.
- Detail route behavior can leak record existence.
- Future Cockpit consumption can imply authorization.
- Route registration can be approved before monitoring is ready.

## 62. Open Questions

Open questions:

- Which auth mechanism should protect internal routes?
- Which authorization permission should represent readonly audit access?
- Should initial route registration be localhost-only?
- What exact route-level rate limits should apply?
- What maximum query string length should apply?
- What maximum parameter count should apply?
- What query complexity scoring should apply?
- Which monitoring sink should receive safe metrics?
- Who owns security and abuse reviews?

## 63. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation/design | Go | This branch is docs-only. |
| Route registration controls design | Go | Allowed as documentation. |
| Route registration implementation | No-Go | Not approved yet. |
| Route exposure | No-Go | Not approved yet. |
| Public exposure | No-Go | Not approved. |
| Cockpit/detail drawer consumption | No-Go | Separate governance required. |
| Copy/export | No-Go | Separate governance required. |
| Retention/cleanup | No-Go | Separate governance required. |
| Raw JSONL/SQLite/SQL access | No-Go | Forbidden. |
| Direct API-to-MemoryFacade access | No-Go | Forbidden. |
| Prompt rewrite | No-Go | Forbidden. |
| Provider/model retry or replan execution | No-Go | Forbidden. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Forbidden. |

## 64. Final Recommendation

Approve this document as route registration controls design only. Do not
register routes in this branch. Do not expose internal or public routes.

A future route registration implementation should remain blocked until real
authentication, real authorization, internal-only caller identity, explicit
route registration approval, route-level rate limits, route-level size limits,
query complexity limits, safe audit logging without raw payloads, safe
observability without raw payloads, forbidden-field regression tests, tests
proving no raw JSONL/SQLite/SQL exposure, tests proving no runtime/provider
execution behavior, service-only delegation tests, invalid-auth fail-closed
tests, unauthorized-caller fail-closed tests, internal-only route tests,
security review, abuse review, and a rollback plan exist.

Omni remains advisory-only.
