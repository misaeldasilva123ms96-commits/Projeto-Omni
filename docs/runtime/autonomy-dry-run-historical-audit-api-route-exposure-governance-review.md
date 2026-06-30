# Autonomy Dry-Run Historical Audit API Route Exposure Governance Review

**Date:** 2026-06-30
**Branch:** `feature/autonomy-dry-run-historical-audit-api-route-exposure-governance-review`
**Base:** `main` after PR #479
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

This governance review evaluates the future controlled route exposure design
for internal historical dry-run audit API handlers. The design is acceptable as
documentation and as a future implementation direction, but it does not approve
route registration, route exposure, public exposure, Cockpit consumption,
copy/export, retention/cleanup, raw storage access, provider/model execution,
or autonomous execution.

Future route registration is conditionally approvable only after real
authentication, real authorization, internal-only caller boundaries,
route-level rate limits, route-level size limits, query complexity limits,
safe audit logging, safe observability, regression tests, security review,
abuse review, and explicit internal route registration approval.

## 2. Scope

This review covers:

- The route exposure design from PR #479.
- The existing internal endpoint contract handlers from PR #477.
- Current blocked state and future preconditions.
- Authentication, authorization, caller boundary, local-only constraints.
- Rate, size, and query complexity limits.
- Safe logging and observability.
- Service-only delegation and raw storage exclusions.
- Request/path/filter/sort/pagination validation.
- Error/degradation mapping and response allowlists.
- Required tests, rollback, monitoring, controls, risks, and go/no-go
  decisions.

## 3. Non-Goals

This review does not:

- Register API routes.
- Expose public or internal routes.
- Modify handlers.
- Modify MemoryFacade, storage, runtime, provider routing, or prompts.
- Add frontend, Cockpit, or detail drawer consumption.
- Add copy/export.
- Add retention/cleanup behavior.
- Read raw JSONL/SQLite/storage.
- Construct SQL from request input.
- Execute retry or replan.
- Call provider/model code.
- Enable autonomous execution or self-repair.

## 4. Reviewed Materials

Reviewed materials:

- `docs/runtime/autonomy-dry-run-historical-audit-api-route-exposure-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-internal-endpoint-evidence-notes.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-internal-endpoint-governance-review.md`
- `backend/python/brain/memory/historical_audit_internal_api.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_internal_api.py`

## 5. Current Implementation State

Current implementation state:

- Internal contract handlers exist.
- Handlers are unregistered.
- Handlers fail closed by default with `internal_enabled=False`.
- `internal_enabled=False` is not authentication.
- Delegation is only to `HistoricalDryRunAuditQueryService`.
- No direct MemoryFacade access exists at the route/handler contract layer.
- No raw JSONL, raw SQLite, raw storage, or SQL access exists.
- No public route exposure exists.
- No Cockpit/frontend/detail drawer exists.
- No copy/export exists.
- No runtime/provider/prompt/retry/replan/autonomous behavior exists.

## 6. Current Blocked State

Currently blocked:

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

## 7. Governance Decision Summary

Approved:

- Documentation.
- Route exposure design.

Conditionally approved:

- Future route registration implementation only after real controls and tests.

Not approved:

- Route registration now.
- Route exposure now.
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

## 8. Route Exposure Safety Review

The route exposure design is directionally safe because it keeps route
registration blocked until protective controls exist. The central safety
decision is that readonly metadata is still sensitive enough to require real
auth, real authorization, bounded queries, safe logging, and tests before any
route exists.

This review approves the route exposure design only. It does not approve
implementation.

## 9. Candidate Route Review

Candidate routes:

- `GET /internal/audit/dry-run`
- `GET /internal/audit/dry-run/{plan_id}`

The names are acceptable as internal route candidates. They are not approved
for registration yet.

## 10. Internal-Only Route Registration Review

The internal-only registration model is required. Future routes must be
private, explicitly gated, and separate from public runtime or chat surfaces.

Internal-only cannot mean "unguarded." It must include real auth,
authorization, deployment boundary review, rate limits, size limits, safe
logging, and observability.

## 11. Route Registration Precondition Review

Route registration preconditions are adequate and required:

- Real authentication.
- Real authorization.
- Internal caller boundary.
- Rate limits.
- Size limits.
- Query complexity limits.
- Safe audit logging.
- Safe observability.
- Forbidden-field tests.
- No raw storage tests.
- No runtime/provider/execution tests.
- Service-only delegation tests.

## 12. Authentication Requirement Review

The design correctly states that `internal_enabled` is not authentication.
Future route registration must include a real identity check before handlers
can be invoked.

Unauthenticated requests must fail closed with categorical metadata and no raw
credential or request logging.

## 13. Authorization Requirement Review

Authorization must be separate from authentication. A caller identity must have
an explicit readonly historical-audit permission or equivalent internal-admin
guard.

Authorization failures must not reveal whether a plan ID exists or whether a
query would otherwise match records.

## 14. Internal Caller Boundary Review

The internal caller model is acceptable only if callers are narrow and
explicitly approved. Public clients, arbitrary frontend code, runtime execution
paths, provider adapters, and autonomous components are not approved callers.

Future Cockpit backend bridges require separate governance.

## 15. Local-Only/Developer-Only Constraint Review

The local/developer-only constraints are appropriate for any first exposure.
Local-only mode must still be disabled by default, require real auth controls,
and be blocked in production unless separately approved.

Developer-only exposure must not weaken response, logging, or storage
boundaries.

## 16. Rate Limit Review

Rate limits are required before exposure. They should cover caller-level,
route-level, burst, broad-list, and repeated-detail access patterns.

Rate-limit responses must be categorical and must not expose caller secrets,
raw query data, or storage internals.

## 17. Size Limit Review

Size limits are required for:

- Query string length.
- Parameter count.
- Individual parameter length.
- Path parameter length.
- Response item count.
- Warning/error metadata size.

Oversized input should fail before handler invocation when possible.

## 18. Query Complexity Limit Review

Query complexity controls are required because broad historical audit reads can
be used for enumeration or resource pressure. The design correctly requires
bounded limit/offset, static filter and sort allowlists, deterministic sorting,
and no unbounded scans.

## 19. Audit Logging Review

Audit logging is required before exposure, but it must be metadata-only.
Allowed logging should be limited to route name, operation name, safe caller
category, safe filter keys, sort key, bounded pagination, status category,
degraded flag, error category, and timestamp.

Raw request and response bodies must never be logged.

## 20. Observability Review

Observability should remain aggregate and categorical. Metrics such as request
count, auth denial count, rate-limit count, size-limit count, error category,
degraded count, latency bucket, and returned item count bucket are acceptable.

Raw payloads and raw rows are not acceptable observability content.

## 21. Safe Request Logging Review

Safe request logging rules are acceptable:

- Log route name instead of raw URL.
- Log allowlisted filter keys instead of full query strings.
- Log bounded limit/offset.
- Log sanitized IDs only when already safe.
- Never log auth material.

These rules must be covered by future tests.

## 22. Safe Response Logging Review

Safe response logging should include only status, degraded boolean, error
category, returned item count, and timestamp. Response body logging is not
approved.

Evidence summaries and detail payloads must not be logged without separate
governance approval.

## 23. Forbidden Logging Denylist Review

The denylist is appropriate and must remain enforced:

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

## 24. Handler Delegation Review

Future route handlers may parse and validate route input, enforce route-level
controls, call existing internal contract handlers, preserve warnings, and map
safe categorical errors.

Future route handlers must not call MemoryFacade, raw storage, runtime,
provider/model, retry/replan, or execution code.

## 25. HistoricalDryRunAuditQueryService-Only Review

The approved dependency chain remains:

route -> internal contract handler -> `HistoricalDryRunAuditQueryService` ->
MemoryFacade safe query contracts

Bypassing this chain is not approved.

## 26. No Direct MemoryFacade Review

Direct API-to-MemoryFacade access remains blocked. Future route tests must
prove no route imports, constructs, or calls MemoryFacade directly.

## 27. No Raw Storage Review

Raw storage access remains blocked. Future route code must not read JSONL
files, access SQLite adapters directly, read SQLite rows, use storage paths, or
return raw rows/lines.

## 28. No SQL Construction Review

Route code must never construct SQL from request input. SQL-like values should
be rejected by validation and omitted from logs.

## 29. Request Validation Review

Request validation requirements are appropriate:

- Static query key allowlist.
- Enum validation.
- Boolean validation.
- Timestamp range validation.
- Sanitized ID validation.
- Sort field/direction validation.
- Limit and offset bounds.
- Query string size checks.
- Parameter count and length checks.

## 30. Path Validation Review

Path validation must ensure `{plan_id}` is non-empty, bounded, sanitized, and
free from path traversal, slashes, SQL-like fragments, or secret-like payloads.

Invalid path values must not reach handlers.

## 31. Filter/Sort Allowlist Review

The filter and sort model is acceptable because it remains static and
deterministic. Free-form storage selectors and raw SQL filters remain blocked.

Future implementation must not expand the allowlists without separate review.

## 32. Pagination Review

Pagination must remain bounded with conservative defaults and explicit maximum
limits. Bulk export through pagination loops is not approved.

Any cursor model must avoid raw storage pointers.

## 33. Error/Degradation Mapping Review

Error mapping must remain categorical. Acceptable categories include auth
failure, authorization failure, rate-limited, payload too large, invalid
request, invalid filter, invalid sort, not found, query failed, and invalid
internal service response.

Raw exceptions, tracebacks, SQL, storage paths, prompts, responses, provider
payloads, and tool outputs are not approved.

## 34. Required Advisory Warnings Review

Future route responses must preserve:

- Query results are readonly audit metadata.
- Query results are not approval.
- Query results are not execution input.
- `would_retry` and `would_replan` are not execution.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- Copy/export remains disabled.
- Omni remains advisory-only.

## 35. Safe Response Envelope Review

The safe response envelope review is acceptable. List and detail responses must
preserve the existing sanitized envelope shape and must not add raw debug
fields.

`error_category` should appear only when degraded.

## 36. Forbidden Field Denylist Review

The forbidden response denylist is appropriate and must remain enforced:

- Raw JSONL.
- Raw SQLite rows.
- Raw SQL.
- Raw prompt or rewritten prompt.
- Raw response.
- Provider/model response.
- Provider payload.
- Tool output.
- Secrets, tokens, keys, credentials.
- Headers, cookies, `.env`.
- Stack traces, tracebacks, raw exceptions.
- Stdout/stderr, command args, file contents.
- Raw database rows and Python reprs.

## 37. Abuse/Misuse Cases

Misuse cases remain material:

- Treating audit results as approval.
- Treating audit results as execution input.
- Treating `would_retry` or `would_replan` as execution.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Enumerating records through broad queries.
- Guessing plan IDs.
- Inferring storage internals from errors.
- Recovering sensitive payloads from logs.

## 38. Security Review Checklist

Security review must verify:

- Internal-only route boundary.
- Real authentication.
- Real authorization.
- Rate, size, and complexity limits.
- Safe request/response logging.
- Safe observability.
- Service-only delegation.
- No MemoryFacade bypass.
- No raw storage access.
- No SQL construction.
- Forbidden-field regression tests.
- No runtime/provider/execution path.

## 39. Test Strategy Review

The test strategy is sufficient as a design target. Future implementation must
include positive and negative route tests before registration or exposure.

Tests must prove both successful safe reads and failure behavior for auth,
authorization, rate limit, size limit, invalid input, service failure, and
forbidden-field attempts.

## 40. Required Tests Before Route Registration

Before route registration:

- Disabled-by-default tests.
- Internal-only gate tests.
- Authentication-required tests.
- Authorization-required tests.
- Rate-limit tests.
- Size-limit tests.
- Query complexity tests.
- Service-only delegation tests.
- No MemoryFacade bypass tests.
- No raw JSONL/SQLite/SQL exposure tests.
- No runtime/provider/execution tests.

## 41. Required Tests Before Route Exposure

Before route exposure:

- End-to-end internal route tests.
- Negative auth tests.
- Negative authorization tests.
- Abuse-case broad query tests.
- Safe logging tests.
- Safe observability tests.
- Service failure degradation tests.
- Forbidden-field regression tests.
- Rollback/disablement tests.

## 42. Required Tests Before Cockpit Consumption

Before Cockpit consumption:

- API contract tests.
- Frontend normalizer tests.
- Empty/loading/error state tests.
- Readonly label tests.
- Forbidden rendering tests.
- No copy/export controls tests.
- No execution controls tests.

## 43. Required Tests Before Copy/Export

Before copy/export:

- Separate export governance tests.
- Safe summary tests.
- Secret and payload scan tests.
- No raw JSONL/SQLite/SQL export tests.
- Export audit logging tests.
- Export rate/size tests.

## 44. Required Tests Before Public Exposure

Public exposure remains blocked. If ever proposed, required tests include:

- Public threat model validation.
- Strong auth/authorization tests.
- Caller isolation tests.
- Abuse/rate-limit tests.
- Privacy review tests.
- Security review tests.
- Forbidden payload regression tests.

## 45. Rollback Strategy Review

Rollback requirements are appropriate. Future route exposure must include:

- Feature flag or route registration gate.
- Disablement without code rollback.
- Safe degraded response while disabled.
- Safe audit entry for disablement.
- Operational playbook.

## 46. Operational Monitoring Review

Operational monitoring should track aggregate safe metrics only:

- Request counts.
- Auth/authorization denial counts.
- Rate-limit counts.
- Size-limit counts.
- Error-category counts.
- Degraded response counts.
- Latency buckets.
- Returned item count buckets.

No raw payload observability is approved.

## 47. Required Controls Before Implementation Branch

Before an implementation branch:

- Route exposure design accepted.
- Governance review accepted.
- Auth approach selected.
- Authorization model selected.
- Internal-only route boundary selected.
- Test plan accepted.
- Logging and observability model accepted.
- Security and abuse review owners identified.

## 48. Required Controls Before Route Registration

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

## 49. Required Controls Before Route Exposure

Before route exposure:

- Route registration approved and tested.
- Real auth and authorization enabled.
- Rate, size, and complexity limits enabled.
- Safe audit logging enabled.
- Safe observability enabled.
- Security review complete.
- Abuse review complete.
- Rollback switch tested.
- Public environment exposure blocked.

## 50. Required Controls Before Public Exposure

Public exposure is not approved. Any future public exposure requires separate
design, threat model, privacy review, auth review, authorization review,
rate-limit review, security review, abuse review, and explicit governance
approval.

## 51. Required Controls Before Cockpit/Detail Drawer

Before Cockpit/detail drawer:

- Separate Cockpit design.
- Separate Cockpit governance review.
- Route exposure approved.
- Readonly UI labels.
- Safe detail allowlist.
- Forbidden rendering tests.
- No copy/export unless separately approved.

## 52. Required Controls Before Copy/Export

Before copy/export:

- Separate copy/export governance.
- Safe export format.
- Export rate and size limits.
- Export audit logging.
- Secret/payload scan tests.
- Explicit approval for any JSON/CSV export.

## 53. Required Controls Before Retention/Cleanup

Before retention/cleanup:

- Separate retention/cleanup design.
- Separate governance review.
- Explicit/manual cleanup controls if destructive.
- Tests proving read routes do not trigger cleanup.
- Tests proving no raw payload exposure.

## 54. Required Controls Before Execution Design

Before execution design:

- Separate execution design.
- Separate governance approval.
- Human approval gates.
- Proof persisted evidence is not execution input.
- Separate approval for prompt rewrite, retry execution, replan execution,
  provider/model calls, provider switching, CI repair, and Git automation.

## 55. Explicit Non-Approval Statement

This review does not approve:

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

## 56. Open Risks

Open risks:

- Internal routes may drift into public exposure.
- `internal_enabled` may be misread as auth.
- Logging may accidentally capture raw query strings.
- Broad queries may enable enumeration.
- Detail routes may leak more than list routes if allowlists drift.
- Cockpit consumption may imply operational authorization.

## 57. Open Questions

Open questions:

- Which auth mechanism should protect internal routes?
- Which authorization permission should represent readonly audit access?
- Should initial exposure be localhost-only?
- What exact rate limits should apply?
- What maximum query length should apply?
- Which monitoring sink should receive safe metrics?
- Who owns security and abuse reviews?

## 58. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | This governance review is docs-only. |
| Route exposure design | Go | Design is approved. |
| Future route registration implementation | Conditional Go | Requires real controls and tests. |
| Route registration now | No-Go | Not approved. |
| Route exposure now | No-Go | Not approved. |
| Public exposure | No-Go | Not approved. |
| Cockpit/detail drawer consumption | No-Go | Separate governance required. |
| Copy/export | No-Go | Separate governance required. |
| Retention/cleanup integration | No-Go | Separate governance required. |
| Raw JSONL/SQLite/SQL access | No-Go | Forbidden. |
| Direct API-to-MemoryFacade access | No-Go | Forbidden. |
| Prompt rewrite | No-Go | Forbidden. |
| Provider/model retry or replan execution | No-Go | Forbidden. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Forbidden. |

## 59. Final Recommendation

Approve this governance review as documentation. Approve the route exposure
design as a future direction only. Do not register or expose routes yet.

A future route registration implementation may proceed only after real
authentication, real authorization, an internal-only caller boundary,
route-level rate limits, route-level size limits, query complexity limits,
audit logging without raw payloads, observability without raw payloads,
forbidden-field regression tests, tests proving no raw JSONL/SQLite/SQL
exposure, tests proving no runtime/provider/execution behavior, tests proving
service-only delegation, security review, abuse review, and explicit internal
route registration approval.

Omni remains advisory-only.
