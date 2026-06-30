# Autonomy Dry-Run Historical Audit API Route Registration Controls Governance Review

**Date:** 2026-06-30
**Branch:** `feature/autonomy-dry-run-historical-audit-api-route-registration-controls-governance-review`
**Base:** `main` after PR #481
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

This governance review evaluates the route registration controls design for
future historical dry-run audit API handlers. The design is sound as
documentation and as a control checklist, but route registration remains
blocked until real authentication, real authorization, internal-only caller
identity, explicit approval, route-level limits, safe logging, safe
observability, regression tests, security review, abuse review, and rollback
controls exist.

Approved: documentation and route registration controls design. Conditionally
approved: future implementation planning only. Conditionally approved: future
route registration implementation only after explicit approval and all
required controls/tests. Not approved: route registration, route exposure,
public exposure, Cockpit/detail drawer, copy/export, retention/cleanup, raw
storage/SQL access, direct API-to-MemoryFacade access, prompt rewrite,
provider/model retry or replan execution, persisted evidence as execution
input, or autonomous execution.

## 2. Scope

This review covers the governance posture of
`docs/runtime/autonomy-dry-run-historical-audit-api-route-registration-controls-design.md`.
It reviews route registration safety, candidate routes, auth/authz,
internal-only boundaries, rate/size/query limits, logging, observability,
handler invocation, service-only delegation, validation, fail-closed behavior,
required tests, rollback, monitoring, controls, open risks, and go/no-go
decisions.

## 3. Non-Goals

- Do not register routes.
- Do not expose internal or public routes.
- Do not modify endpoint handlers.
- Do not modify MemoryFacade.
- Do not modify `HistoricalDryRunAuditQueryService`.
- Do not modify storage, runtime, provider routing, or prompts.
- Do not add auth, authorization, or rate-limiter code.
- Do not add frontend/Cockpit/detail drawer behavior.
- Do not add copy/export, retention/cleanup, retry, replan, provider/model
  calls, self-repair, or autonomous execution.

## 4. Reviewed Materials

Reviewed materials:

- `docs/runtime/autonomy-dry-run-historical-audit-api-route-registration-controls-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-route-exposure-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-route-exposure-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-internal-endpoint-evidence-notes.md`
- PR #477 through PR #481 context.

## 5. Current Implementation State

Current state:

- Internal contract handlers exist.
- Handlers are unregistered.
- Handlers fail closed by default with `internal_enabled=False`.
- `internal_enabled=False` is not authentication.
- Delegation is only to `HistoricalDryRunAuditQueryService`.
- No public or internal route is exposed.
- No Cockpit/frontend/detail drawer exists.
- No copy/export exists.
- Route registration remains blocked.

## 6. Current Governance State

Governance currently permits documentation and route registration controls
design only. It does not permit route registration, route exposure, public
exposure, UI consumption, copy/export, retention/cleanup, raw storage access,
direct API-to-MemoryFacade access, prompt rewrite, provider/model execution,
persisted evidence as execution input, or autonomous execution.

## 7. Governance Decision Summary

- Approved for documentation.
- Approved for route registration controls design.
- Conditionally approved for future implementation planning only.
- Conditionally approved for future route registration implementation only
  after explicit approval and all required controls/tests.
- Not approved for route registration yet.
- Not approved for route exposure yet.
- Not approved for public exposure.
- Not approved for Cockpit/detail drawer consumption.
- Not approved for copy/export.
- Not approved for retention/cleanup.
- Not approved for raw JSONL/SQLite/SQL access.
- Not approved for direct API-to-MemoryFacade access.
- Not approved for prompt rewrite.
- Not approved for provider/model retry or replan execution.
- Not approved for persisted evidence as execution input.
- Not approved for autonomous execution.

## 8. Route Registration Control Safety Review

The design correctly treats route registration as a security boundary change,
not a mechanical router step. It requires real auth/authz, internal caller
identity, limits, safe logs, observability, tests, security review, abuse
review, and rollback before any route is registered.

Safety finding: the design is appropriate for governance documentation. It is
not sufficient by itself to approve implementation.

## 9. Candidate Route Review

Candidate routes are:

- `GET /internal/audit/dry-run`
- `GET /internal/audit/dry-run/{plan_id}`

These names are acceptable as design candidates only. They must not be
registered until all controls are implemented and explicitly approved.

## 10. Internal-Only Registration Boundary Review

The design correctly requires internal-only registration and blocks public
exposure. Future registration must prove the route is not internet-facing, not
part of public chat/runtime APIs, not reachable by arbitrary frontend clients,
and disabled outside approved environments.

## 11. Auth Control Review

The design correctly states that `internal_enabled` is not authentication.
Future route registration requires real authentication, verified caller
identity, fail-closed behavior for missing/malformed/expired credentials, and
tests proving unauthenticated calls fail closed.

## 12. Authorization Control Review

Authorization must be separate from authentication. Future callers need
explicit readonly historical-audit permission. Authorization failures must not
reveal record existence or raw policy/caller/token/storage details.

## 13. Internal Caller Identity Review

Approved future callers are narrow: local operator tooling in approved
environments, internal backend components with readonly audit permission, or a
future Cockpit backend bridge after separate governance. Public clients,
runtime execution paths, provider adapters, and retry/replan executors remain
forbidden.

## 14. Local/Developer-Only Constraint Review

The design appropriately recommends the first registration be local or
developer-only unless separately approved. Localhost-only and disabled-by-
default behavior should be required for any first implementation branch.

## 15. Route-Level Rate Limit Review

Route-level rate limiting is required before registration. Limits must cover
requests per caller, requests per route, bursts, repeated broad list queries,
detail lookups, invalid auth, and invalid queries. Rate-limit errors must be
categorical and safe.

## 16. Route-Level Size Limit Review

The design correctly requires limits for query string length, parameter count,
individual parameter length, path parameter length, and response item count.
Oversized inputs should fail before handler invocation when possible.

## 17. Query Complexity Limit Review

Query complexity controls must prevent broad or expensive reads. Required
controls include bounded limits, bounded offset/cursor, static filter and sort
allowlists, deterministic ordering, maximum filter count, no unbounded scans,
and no raw storage selectors or SQL filters.

## 18. Audit Logging Review

Audit logging may include only safe metadata such as operation name, route
name, safe caller category, safe IDs, filter keys, sort field/direction,
bounded pagination metadata, status category, degraded flag, error category,
and timestamp.

## 19. Observability Review

Observability must be aggregate and categorical: request counts, auth/authz
failures, rate/size/query rejections, error categories, degraded response
counts, latency buckets, returned item count buckets, and disabled-route access
attempts.

## 20. Safe Request Logging Review

Safe request logging must log route name, operation name, allowed filter keys,
bounded limit/offset, sanitized IDs only when already safe, and safe caller
category. It must not log raw URLs, query strings, headers, cookies, or auth
material.

## 21. Safe Response Logging Review

Safe response logging may include status category, degraded boolean, error
category, returned item count, and generated timestamp. It must not log
response bodies, detail payloads, raw records, or evidence summaries.

## 22. Forbidden Logging Denylist Review

Forbidden logs include raw JSONL, raw SQLite rows, raw SQL, raw prompts,
rewritten prompts, raw responses, provider/model responses, provider payloads,
tool outputs, secrets, tokens, API keys, credentials, headers, cookies, `.env`,
stack traces, tracebacks, exceptions, stdout/stderr, command args, file
contents, database rows, and Python reprs.

## 23. Handler Invocation Review

Handler invocation must occur only after route registration approval, real
authentication, real authorization, internal-only gate, rate limits, size
limits, query complexity limits, and request/path validation all pass.

## 24. HistoricalDryRunAuditQueryService-Only Delegation Review

The approved dependency path remains:

route -> internal contract handler -> `HistoricalDryRunAuditQueryService` ->
MemoryFacade safe query contracts.

Future route code must not bypass the internal contract handler or service.

## 25. No Direct MemoryFacade Review

Direct API-to-MemoryFacade access remains forbidden. Future tests must prove no
MemoryFacade imports, construction, or direct method calls exist in route code.

## 26. No Raw Storage Review

Future route code must not read JSONL files, SQLite rows, SQLite adapters,
storage paths, raw rows, raw lines, or storage exceptions. Storage remains
behind MemoryFacade and the internal service.

## 27. No SQL Construction Review

The design correctly forbids constructing SQL from request input. SQL-like
input must be rejected by validation and must not be logged.

## 28. Request Validation Review

Future route implementation must validate allowed query keys, enum values,
booleans, timestamps, IDs, sort field/direction, pagination, query string
size, parameter count, and parameter length before data access.

## 29. Path Validation Review

Detail `{plan_id}` must be non-empty, bounded, safe-character only, slash-free,
path-traversal-free, SQL-fragment-free, and secret-like-payload-free before
handler or service invocation.

## 30. Filter/Sort Allowlist Review

Filters and sorts must remain static. Free-form selectors, storage-specific
filters, regex, JSONPath, raw SQL filters, and arbitrary column names are
forbidden.

## 31. Pagination Review

Pagination must use conservative defaults, explicit maximum limits, bounded
offset or approved cursor, deterministic ordering, no unbounded list queries,
and no raw storage pointers.

## 32. Error/Degradation Mapping Review

Errors must map to safe categories only: auth failed, authorization failed,
rate limited, payload too large, invalid request/path/filter/sort/pagination,
not found, query failed, invalid internal service response, and route disabled.

## 33. Required Advisory Warnings Review

Future route responses must preserve:

- Query results are readonly audit metadata.
- Query results are not approval.
- Query results are not execution input.
- `would_retry` and `would_replan` are not execution.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- Copy/export remains disabled.
- Omni remains advisory-only.

## 34. Safe Response Envelope Review

List responses must preserve `items`, `page_info`, `applied_filters`,
`warnings`, `degraded`, `error_category` only when degraded, and
`generated_at`. Detail responses must remain safe, bounded, and free of debug
or raw storage fields.

## 35. Forbidden Field Denylist Review

Forbidden response fields and content include raw JSONL, raw SQLite rows, raw
SQL, prompts, rewritten prompts, raw responses, provider/model responses,
provider payloads, tool outputs, secrets, tokens, API keys, credentials,
headers, cookies, `.env`, stack traces, tracebacks, raw exceptions,
stdout/stderr, command args, file contents, database rows, and Python reprs.

## 36. Fail-Closed Behavior Review

Fail-closed behavior is required for disabled routes, missing/invalid auth,
missing/invalid authorization, non-internal callers, rate/size/complexity
limit failures, invalid request/path/filter/sort/pagination, and service
failure.

## 37. Feature Flag/Internal Flag Review

An internal flag may be a route activation gate only if separately approved.
It must be disabled by default, separate from authentication and authorization,
safe to disable without code rollback, and tested. It must never be treated as
auth.

## 38. Route Registration Precondition Review

Before route registration, all required controls must exist: real auth, real
authorization, internal-only caller identity, explicit approval, route-level
limits, query complexity limits, safe logging, safe observability, tests,
security review, abuse review, and rollback plan.

## 39. Route Exposure Precondition Review

Before route exposure, registration must be approved and tested, auth/authz
enabled, internal-only boundary verified, limits enabled, safe logging and
observability enabled, rollback tested, public exposure blocked, and security
and abuse reviews complete.

## 40. Public Exposure Prohibition Review

Public exposure is not approved. Any future public exposure requires separate
design, threat model, privacy review, auth review, authorization review,
rate-limit review, security review, abuse review, and explicit governance
approval.

## 41. Cockpit/Detail Drawer Prohibition Review

Cockpit/detail drawer consumption is not approved. Future UI work needs
separate design and governance, readonly labels, safe normalizers, safe states,
detail allowlists, forbidden rendering tests, and no execution controls.

## 42. Copy/Export Prohibition Review

Copy/export remains blocked. Future copy/export requires separate governance,
safe summary/export design, rate and size limits, audit logging, secret and
payload scan tests, and explicit approval.

## 43. Retention/Cleanup Exclusion Review

Retention and cleanup are excluded. Read routes must never trigger cleanup,
retention changes, deletion, or destructive behavior.

## 44. Execution Exclusion Review

Route registration must never rewrite prompts, execute retry/replan, call
providers/models, change provider routing, change runtime output, execute
tools/commands, patch files, run CI repair, perform Git automation, use
persisted evidence as execution input, or enable autonomous execution.

## 45. Abuse/Misuse Cases

Misuse cases include treating audit results as approval or execution input,
treating `would_retry`/`would_replan` as execution, treating scores as
permission, treating strategies as instructions, scraping broad queries,
guessing plan IDs, inferring storage internals from errors, recovering
sensitive payloads from logs, and drifting internal routes toward public
exposure.

## 46. Security Review Checklist

Before implementation, verify internal-only route posture, real auth, real
authorization, internal caller identity, rate limits, size limits, query
complexity limits, safe logging, safe observability, service-only delegation,
no MemoryFacade bypass, no raw storage, no SQL construction, forbidden-field
tests, and no runtime/provider/execution behavior.

## 47. Required Tests Before Implementation

Required before implementation planning proceeds:

- Request validation tests or test plan.
- Path validation tests or test plan.
- Auth failure tests or test plan.
- Authorization failure tests or test plan.
- Rate-limit tests or test plan.
- Size-limit tests or test plan.
- Query complexity tests or test plan.
- Safe logging tests or test plan.
- Safe observability tests or test plan.
- Forbidden-field regression test plan.

## 48. Required Tests Before Route Registration

Required before route registration:

- Disabled-by-default tests.
- Internal-only gate tests.
- Authentication-required tests.
- Authorization-required tests.
- Invalid-auth fail-closed tests.
- Unauthorized-caller fail-closed tests.
- Rate-limit tests.
- Size-limit tests.
- Query complexity tests.
- Service-only delegation tests.
- No MemoryFacade bypass tests.
- No raw JSONL/SQLite/SQL exposure tests.
- No runtime/provider/execution behavior tests.

## 49. Required Tests Before Route Exposure

Required before route exposure:

- End-to-end internal route tests.
- Negative authentication and authorization tests.
- Abuse-case broad query tests.
- Plan ID guessing tests.
- Safe logging and observability tests.
- Service failure degradation tests.
- Forbidden-field regression tests.
- Rollback/disablement tests.
- Tests proving the route remains internal-only.

## 50. Required Tests Before Cockpit Consumption

Required before Cockpit consumption:

- API contract tests.
- Frontend normalizer tests.
- Empty/loading/error state tests.
- Readonly label tests.
- Forbidden rendering tests.
- No copy/export controls tests.
- No execution controls tests.
- Separate Cockpit governance approval.

## 51. Required Tests Before Copy/Export

Required before copy/export:

- Separate export governance tests.
- Safe summary tests.
- Secret and payload scan tests.
- No raw JSONL/SQLite/SQL export tests.
- Export audit logging tests.
- Export rate and size tests.
- Explicit approval.

## 52. Rollback Strategy Review

Future route registration must include a route registration gate or feature
flag, safe disabled response, disablement audit log, operational playbook,
tests proving disablement works, and monitoring for post-disable access
attempts.

## 53. Operational Monitoring Review

Monitoring should include request counts, auth/authz failure counts,
rate/size/query-complexity rejections, error-category counts, degraded
response counts, latency buckets, returned item count buckets, and disabled
route access attempts. It must remain payload-free.

## 54. Required Controls Before Implementation Branch

Before an implementation branch:

- This governance review accepted.
- Auth approach selected.
- Authorization model selected.
- Internal caller identity model selected.
- Route registration gate selected.
- Rate, size, and complexity limit strategy selected.
- Logging and observability model selected.
- Security and abuse review owners identified.

## 55. Required Controls Before Route Registration

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

## 56. Required Controls Before Route Exposure

Before route exposure:

- Route registration approved and tested.
- Route disabled-by-default behavior tested.
- Real auth and authorization enabled.
- Internal-only boundary verified.
- Rate, size, and complexity limits enabled.
- Safe audit logging enabled.
- Safe observability enabled.
- Rollback switch tested.
- Security and abuse reviews complete.
- Public environment exposure blocked.

## 57. Required Controls Before Public Exposure

Public exposure remains prohibited. Any future proposal requires separate
public exposure design, threat model, privacy review, auth review,
authorization review, rate-limit review, security review, abuse review, and
explicit governance approval.

## 58. Required Controls Before Cockpit/Detail Drawer

Before Cockpit/detail drawer:

- Separate Cockpit design.
- Separate Cockpit governance review.
- Route exposure approved.
- UI readonly warning labels.
- Safe detail allowlist.
- Forbidden rendering tests.
- No copy/export unless separately approved.
- No execution controls.

## 59. Required Controls Before Copy/Export

Before copy/export:

- Separate copy/export governance.
- Safe export format.
- Export rate and size limits.
- Export audit logging.
- Secret and payload scan tests.
- No raw JSONL/SQLite/SQL export.
- Explicit approval.

## 60. Required Controls Before Retention/Cleanup

Before retention/cleanup:

- Separate retention/cleanup design.
- Separate governance review.
- Explicit/manual cleanup controls if destructive.
- Tests proving read routes do not trigger cleanup.
- Tests proving cleanup does not expose raw payloads.
- Tests proving retention does not change route response safety.

## 61. Required Controls Before Execution Design

Before execution design:

- Separate execution design.
- Separate governance approval.
- Human approval gates.
- Proof persisted evidence is not execution input.
- Separate approval for prompt rewrite, retry execution, replan execution,
  provider/model calls, provider switching, CI repair, and Git automation.

## 62. Explicit Non-Approval Statement

This review does not approve route registration, route exposure, public
exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup,
raw JSONL/SQLite/SQL access, direct API-to-MemoryFacade access, prompt
rewrite, provider/model retry execution, provider/model replan execution,
persisted evidence as execution input, or autonomous execution.

## 63. Open Risks

- Internal routes can drift into public exposure.
- `internal_enabled` can be misunderstood as auth.
- Auth placeholders can persist into implementation.
- Logs can accidentally capture raw query strings.
- Broad queries can create enumeration pressure.
- Detail route behavior can leak record existence.
- Future Cockpit consumption can imply authorization.
- Route registration can be approved before monitoring is ready.

## 64. Open Questions

- Which auth mechanism should protect internal routes?
- Which authorization permission should represent readonly audit access?
- Should initial route registration be localhost-only?
- What exact route-level rate limits should apply?
- What maximum query string length should apply?
- What maximum parameter count should apply?
- What query complexity scoring should apply?
- Which monitoring sink should receive safe metrics?
- Who owns security and abuse reviews?

## 65. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | Approved for this branch. |
| Route registration controls design | Go | Approved as design documentation. |
| Future implementation planning | Conditional Go | Only planning, with controls defined. |
| Future route registration implementation | Conditional Go | Requires explicit approval and all tests/controls. |
| Internal route registration | No-Go | Not approved yet. |
| Internal route exposure | No-Go | Not approved yet. |
| Public route exposure | No-Go | Prohibited. |
| Cockpit/detail drawer consumption | No-Go | Separate governance required. |
| Copy/export | No-Go | Separate governance required. |
| Retention/cleanup | No-Go | Separate governance required. |
| Raw JSONL read | No-Go | Forbidden. |
| Raw SQLite row read | No-Go | Forbidden. |
| Raw SQL filter/query | No-Go | Forbidden. |
| Direct API-to-MemoryFacade | No-Go | Forbidden. |
| Prompt rewrite | No-Go | Forbidden. |
| Provider/model retry execution | No-Go | Forbidden. |
| Provider/model replan execution | No-Go | Forbidden. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Forbidden. |

## 66. Final Recommendation

Approve the route registration controls design for documentation and future
implementation planning only. Keep route registration blocked until real
authentication, real authorization, internal-only caller identity, explicit
route registration approval, route-level rate limits, route-level size limits,
query complexity limits, safe audit logging without raw payloads, safe
observability without raw payloads, forbidden-field regression tests, tests
proving no raw JSONL/SQLite/SQL exposure, no runtime/provider/execution tests,
service-only delegation tests, invalid-auth fail-closed tests, unauthorized
fail-closed tests, internal-only route tests, security review, abuse review,
and rollback plan all exist and pass.

Omni remains advisory-only.
