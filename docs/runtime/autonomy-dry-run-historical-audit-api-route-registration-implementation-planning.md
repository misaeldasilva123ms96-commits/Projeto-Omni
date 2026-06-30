# Dry-Run Historical Audit API Route Registration Implementation Planning

## 1. Executive summary

This document is an implementation planning artifact for a future branch that may register an internal dry-run historical audit query route.

Required conclusions:

- Approved for documentation/planning only.
- Future implementation planning allowed.
- Route registration implementation not approved in this PR.

Route registration remains blocked until explicit approval. Route exposure, public exposure, Cockpit/detail drawer consumption, copy/export behavior, retention/cleanup changes, raw storage access, direct `MemoryFacade` access, prompt rewrite behavior, provider execution, persisted evidence execution input, and autonomous execution remain blocked.

## 2. Scope

The scope is limited to planning a future implementation branch for internal route registration around the existing dry-run historical audit query boundary. The plan covers candidate internal routes, implementation phases, file candidates, security controls, test requirements, approval gates, risks, and go/no-go criteria.

This document does not alter runtime behavior. It does not register an endpoint, expose an API, add a handler, add authentication, add authorization, add rate limiting, add size limiting, change persistence, or connect frontend consumers.

## 3. Non-goals

This PR does not implement route registration. It does not expose internal or public routes. It does not modify handlers, provider calls, prompt construction, autonomous execution, runtime wiring, retention cleanup, Cockpit UI, detail drawers, copy/export flows, or storage adapters.

This PR does not select a final auth/authz/rate-limit implementation. It identifies the decisions and evidence required before a later implementation branch may proceed.

## 4. Current implementation state

The repository already contains governance and design material for dry-run historical audit querying and route registration controls. The current state treats the query service boundary as the only acceptable delegation point for future route code.

There is no approval in this PR to register a route or expose any endpoint. Any future route must be added only after confirming the real route framework, internal route conventions, authentication mechanism, authorization model, caller identity model, and fail-closed disablement path.

## 5. Current governance state

Current governance permits documentation and planning. It does not permit runtime exposure. Prior control documents require internal-only behavior, service-only delegation, safe response envelopes, logging denylist enforcement, query allowlists, pagination bounds, and explicit approval before implementation.

The governing posture remains blocked-by-default. A future implementation branch may be planned, but it must not be treated as pre-approved.

## 6. Why this is planning-only

Route registration changes the system boundary from stored internal data to callable runtime API surface. That shift requires concrete authentication, authorization, rate limit, size limit, audit logging, observability, and rollback controls before code is safe to register.

Because those controls have not been implemented or verified in this PR, the correct artifact is a planning document. The plan preserves the blocked state while making the future implementation path reviewable.

## 7. Future implementation objective

The future objective is to register an internal-only read/query route that delegates only to `HistoricalDryRunAuditQueryService` and returns a sanitized response envelope for historical dry-run audit records.

The future objective excludes execution, replay, provider calls, prompt rewriting, raw persisted evidence use as execution input, retention management, and frontend display or export behavior.

## 8. Candidate routes

Candidate route names for a future branch may include an internal namespace such as `/internal/autonomy/dry-run-audit/history` for collection queries and `/internal/autonomy/dry-run-audit/history/{session_id}` for detail queries.

These names are placeholders only. A future branch must follow existing route naming conventions discovered in the actual internal route registry. No candidate route is approved for registration by this document.

## 9. Required implementation phases

A future implementation branch must proceed in controlled phases:

1. Inspect existing internal route conventions.
2. Identify real authentication and authorization mechanisms.
3. Define internal caller identity.
4. Define rate, size, and query complexity limits.
5. Define safe audit logging and observability.
6. Define the route registration switch and fail-closed behavior.
7. Define rollback.
8. Implement route registration only after approval.
9. Add focused tests before any endpoint is made callable.

## 10. Phase 1: inspect existing internal route conventions

The implementation branch must inspect the actual route framework and internal route registration patterns before adding any route. It must identify where internal-only routes are declared, how they are mounted, how route dependencies are injected, and how disabled routes behave.

No implementation may invent a parallel route registry when a repository convention already exists.

## 11. Phase 2: identify real auth mechanism

The implementation branch must identify the real authentication mechanism used by internal API routes. Acceptable evidence includes existing middleware, route decorators, dependency injection, service tokens, session validation, or internal gateway controls already present in the codebase.

The branch must not add placeholder authentication. If the real mechanism cannot be identified, the route must remain unregistered.

## 12. Phase 3: identify real authorization mechanism

The implementation branch must identify how internal callers are authorized for sensitive operational reads. It must determine whether authorization is role-based, capability-based, service-account-based, tenant-scoped, environment-scoped, or enforced by gateway policy.

If authorization cannot be proven, the route must fail closed or remain absent.

## 13. Phase 4: define internal caller identity

The route must have a concrete internal caller identity model before registration. The caller identity must be suitable for audit logging, rate limiting, authorization decisions, and operational traceability.

Anonymous internal requests are not acceptable. A route that cannot identify the caller must not return audit records.

## 14. Phase 5: define route-level rate limits

The future route must have route-level rate limits based on caller identity and route class. The limits must prevent broad historical scraping, accidental high-volume queries, and repeated expensive filter combinations.

Rate limit failures must be deterministic, safe, and logged without exposing sensitive request or response content.

## 15. Phase 6: define route-level size limits

The future route must enforce request and response size limits. Query parameters, request bodies if any, page sizes, cursor sizes, and response payloads must have bounded maximums.

Oversized requests must fail closed before invoking the query service.

## 16. Phase 7: define query complexity limits

The future route must limit query complexity through allowlisted filters, bounded pagination, bounded sort fields, and constrained date/session ranges. Complexity limits must be applied before service invocation.

The route must not permit arbitrary predicates, unbounded scans, raw SQL fragments, raw storage path selection, or query language pass-through.

## 17. Phase 8: define safe audit logging

The future route must audit access attempts, access denials, and successful query classes without logging raw evidence, prompts, provider payloads, secrets, stdout/stderr, stack traces, or storage paths.

Audit events should include route id, caller identity, authorization result, sanitized filter summary, page size bucket, request id, and outcome.

## 18. Phase 9: define safe observability

Observability must focus on operational health and control effectiveness. Metrics may include request counts, denied counts, rate-limit counts, validation failure counts, latency buckets, and degraded service responses.

Observability must not contain raw records, raw prompt text, provider payloads, persisted evidence, tokens, secrets, or raw storage identifiers.

## 19. Phase 10: define route registration switch

The future implementation must include a route registration switch that defaults to disabled unless explicitly enabled for the intended internal environment. The switch must be named, documented, tested, and owned.

Disabling the switch must remove or deny route access without changing storage, service behavior, provider behavior, or execution behavior.

## 20. Phase 11: define fail-closed route behavior

The future route must fail closed when authentication, authorization, caller identity, rate limiting, size limiting, query validation, service construction, or route switch evaluation is unavailable.

Fail-closed responses must use sanitized errors and must not leak whether specific sessions, records, storage files, SQL tables, prompts, or evidence exist.

## 21. Phase 12: define rollback path

Rollback must be possible by disabling the route registration switch and redeploying or reloading configuration according to repository conventions. Rollback must not require storage migration or data deletion.

The rollback plan must include how to verify the route is no longer callable and how to monitor denied or absent-route behavior after rollback.

## 22. Implementation file candidates

Candidate files for a later branch may include the internal route registry, route module, dependency injection module, request/response schema module, and focused route tests. Exact files must be selected by inspecting current conventions.

This document does not authorize edits to those files. It only identifies likely areas for future investigation.

## 23. Test file candidates

Candidate tests may live near existing internal route tests, runtime autonomy tests, memory/query service tests, or API boundary tests. The future branch should prefer focused unit and integration tests over broad unrelated suites.

Test candidates must cover disabled-by-default behavior, auth fail-closed behavior, service-only delegation, validation, logging safety, and non-execution guarantees.

## 24. Route registration constraints

Route registration must be internal-only, disabled by default, covered by tests, and gated by explicit approval. It must not be registered on public routers, frontend-facing routers, or general API namespaces.

Registration must not create a route that can be reached without the required internal caller controls.

## 25. Internal-only route boundary

The route boundary must be documented and enforced in code. Internal-only means more than an internal-looking path; it requires the route to be mounted only in internal contexts and protected by the real internal access controls.

If internal-only enforcement cannot be proven, registration must not proceed.

## 26. Authentication requirements

The future route must authenticate every request before validation reaches the query service. Missing, malformed, expired, or unverifiable authentication must fail closed.

Authentication failures must return sanitized responses and must not reveal route internals or record existence.

## 27. Authorization requirements

Authorization must be explicit for this route class. A generally authenticated caller is not automatically authorized to query dry-run audit history.

Authorization failures must be denied before service invocation, must be logged safely, and must not reveal whether matching audit records exist.

## 28. Internal caller requirements

The route must resolve a stable internal caller identity. The identity must be usable for audit logs, rate limits, authorization, and support investigations.

The implementation must reject calls where identity is absent, ambiguous, spoofable, or derived only from untrusted request parameters.

## 29. Rate limit requirements

Rate limits must be scoped to caller identity and route class. They must cover both collection and detail queries, and they must protect against repeated pagination and filter enumeration.

Rate limit tests must prove that limited requests do not invoke `HistoricalDryRunAuditQueryService`.

## 30. Size limit requirements

The future route must bound request size, query parameter length, filter count, sort count, page size, cursor length, and response size. It must reject excessive requests before invoking the service.

Response size enforcement must not truncate in a way that creates misleading audit results. Pagination must be used for bounded retrieval.

## 31. Query complexity requirements

Allowed filters and sorts must be explicit. Date ranges, session ids, statuses, and other fields must be constrained according to the existing service contract.

The route must not accept raw query expressions, direct SQL, raw JSONL selectors, SQLite table names, filesystem paths, or arbitrary nested filter trees.

## 32. Audit logging requirements

Audit logging must capture the fact of access and control outcomes without capturing sensitive content. Required fields should include timestamp, route id, sanitized caller id, request id, decision, status class, limit class, and sanitized query summary.

The audit log must not include raw records, prompts, evidence, stdout/stderr, tracebacks, provider payloads, secrets, tokens, raw storage paths, or raw SQL.

## 33. Observability requirements

Metrics and traces must describe health and control outcomes. They may include latency buckets, request counts, denied counts, validation failure counts, rate-limit counts, size-limit counts, service degradation counts, and disabled-route counts.

Metrics and traces must not contain sensitive record fields or raw user/provider content.

## 34. Safe request logging rules

Request logs may include method, route id, request id, caller identity hash or safe id, sanitized filter names, page size bucket, and decision outcome.

Request logs must not include raw authorization headers, cookies, tokens, prompts, evidence, provider payloads, storage paths, raw SQL, full query strings, or unbounded user-controlled values.

## 35. Safe response logging rules

Response logs may include response status, result count bucket, pagination presence, degradation flags, warning codes, and latency buckets.

Response logs must not include response bodies, record ids if sensitive, prompt or evidence fragments, storage metadata, provider payloads, stack traces, or raw exception text.

## 36. Forbidden logging denylist

Forbidden logging fields include secrets, tokens, cookies, authorization headers, raw prompts, prompt rewrites, provider request/response payloads, persisted evidence, stdout, stderr, stack traces, tracebacks, raw JSONL lines, SQLite paths, SQL text, raw storage paths, and full serialized response bodies.

Future implementation must include tests or review evidence proving these fields are not logged.

## 37. Handler invocation rules

The route handler must perform control checks before invoking the query service. Authentication, authorization, caller identity, route switch, rate limits, size limits, and query validation must all succeed first.

The handler must be read-only and must not start, replay, mutate, or enqueue dry-run execution.

## 38. HistoricalDryRunAuditQueryService-only delegation

The only allowed data access boundary for future route code is `HistoricalDryRunAuditQueryService`. The route may adapt validated request parameters into the service contract and adapt the service result into a safe envelope.

The route must not bypass the service to reach memory, JSONL, SQLite, filesystem, or SQL layers.

## 39. No direct MemoryFacade rule

Future route code must not call `MemoryFacade` directly. If a needed query is not available through `HistoricalDryRunAuditQueryService`, the implementation must stop and propose a separate service-contract change.

Direct memory access from the API boundary remains blocked.

## 40. No raw storage rule

Future route code must not read raw JSONL files, SQLite files, filesystem paths, or storage adapter internals. Storage format details must remain behind the service boundary.

No API response may expose raw storage records or storage implementation details.

## 41. No SQL construction rule

Future route code must not construct SQL, accept SQL, log SQL, or expose SQL. Any database-backed lookup must be mediated by existing service and adapter abstractions.

SQL construction at the route boundary remains prohibited.

## 42. Request validation requirements

The future route must validate every incoming parameter against a typed schema or equivalent structured validator. Unknown fields, invalid types, invalid enum values, and invalid combinations must fail before service invocation.

Validation errors must be sanitized and must not echo unbounded user input.

## 43. Path validation requirements

Path parameters such as session identifiers must be bounded, typed, canonicalized, and free of path traversal semantics. They must not be interpreted as filesystem paths or storage keys by route code.

Invalid path parameters must fail closed before service invocation.

## 44. Filter/sort allowlist requirements

Filters and sort fields must be allowlisted. Disallowed fields must be rejected, not ignored. Sort direction must be bounded to approved values.

The route must not expose implementation-specific storage fields or raw internal keys as filter/sort inputs.

## 45. Pagination requirements

Pagination must be mandatory for collection queries and must have a conservative default page size and maximum page size. Cursors or offsets must be bounded and validated.

Pagination must not allow unbounded historical export through repeated oversized pages.

## 46. Error/degradation mapping requirements

The future route must map service results and failures to sanitized API responses. Degraded storage, unavailable service dependencies, disabled route state, validation failure, authentication failure, authorization failure, rate-limit failure, and size-limit failure must have distinct safe outcomes.

Errors must not leak stack traces, raw exception text, storage paths, SQL details, or record existence.

## 47. Required advisory warnings

Responses must include advisory warnings when data is partial, degraded, redacted, paginated, stale, or limited by retention. Warnings must be code-based and safe for internal API consumers.

Advisory warnings must not imply the route is approved for public exposure or frontend display.

## 48. Safe response envelope requirements

The response envelope must include sanitized data, pagination metadata, warning codes, request id or correlation id, and degradation status. It must avoid raw storage structures and implementation-specific fields.

The envelope must not include prompt rewrites, provider payloads, raw evidence, execution inputs, secrets, tokens, raw logs, or direct storage metadata.

## 49. Forbidden field denylist

Forbidden response fields include raw prompts, rewritten prompts, provider request payloads, provider response payloads, raw persisted evidence, stdout, stderr, stack traces, tracebacks, secrets, tokens, raw JSONL records, SQLite paths, SQL text, filesystem paths, and execution input material.

Future implementation must prove these fields cannot be returned by route serialization.

## 50. Required tests before implementation

Before route registration implementation is approved, tests must cover disabled-by-default behavior, auth fail-closed behavior, authorization fail-closed behavior, internal-only mounting, rate limits, size limits, query complexity limits, service-only delegation, logging safety, and non-execution.

The test plan must be reviewed before code registers a route.

## 51. Required tests for auth fail-closed

Tests must prove missing, malformed, expired, invalid, and unverifiable authentication fail closed. They must also prove the query service is not invoked in these cases.

The tests must verify sanitized errors and safe logging behavior.

## 52. Required tests for unauthorized fail-closed

Tests must prove authenticated but unauthorized callers are denied before service invocation. They must cover insufficient role, missing capability, wrong environment, and wrong tenant/scope where applicable.

The response must not reveal record existence.

## 53. Required tests for internal-only boundary

Tests must prove the route is mounted only in the internal route context and is absent or denied from public/frontdoor contexts.

If the repository has route listing tests, they should verify the route does not appear in public route manifests.

## 54. Required tests for rate limits

Tests must prove rate limits are enforced per caller and route class. They must also prove rate-limited requests do not invoke the service and do not log sensitive content.

Tests should include repeated detail requests and repeated collection pagination.

## 55. Required tests for size limits

Tests must prove oversized query strings, bodies, cursors, filters, and page sizes are rejected before service invocation.

Tests must verify sanitized size-limit errors and no response body leakage.

## 56. Required tests for query complexity limits

Tests must prove unknown filters, unknown sorts, excessive filter counts, invalid date ranges, excessive date ranges, and arbitrary query expressions are rejected.

Tests must verify that no raw SQL, raw JSONL selector, or storage path can pass through validation.

## 57. Required tests for service-only delegation

Tests must prove route code delegates only to `HistoricalDryRunAuditQueryService`. They should use mocks or spies to verify the route does not call memory facade, storage adapters, filesystem readers, or SQL helpers.

Any missing service capability must become a separate service contract discussion, not a route bypass.

## 58. Required tests for no raw JSONL/SQLite/SQL exposure

Tests must prove responses and logs do not expose raw JSONL records, SQLite paths, SQL strings, table names, storage paths, or adapter implementation details.

Serialization tests should include records containing denylisted fields to ensure they are excluded or redacted.

## 59. Required tests for no runtime/provider/execution behavior

Tests must prove the route cannot start, replay, enqueue, mutate, prompt-rewrite, call providers, or pass persisted evidence into execution inputs.

The route must remain a read/query boundary only.

## 60. Required tests for rollback/disablement

Tests must prove disabling the route switch makes the route absent or denied according to the selected convention. They must verify the disabled state does not invoke the service.

Rollback tests must also verify safe observability for disabled or denied route attempts.

## 61. Implementation approval checklist

Implementation may proceed only after:

1. Existing internal route conventions are identified.
2. Real authentication is identified.
3. Real authorization is identified.
4. Internal caller identity is defined.
5. Rate, size, and query complexity controls are specified.
6. Safe audit logging and observability are specified.
7. Disabled-by-default route switch is specified.
8. Required test plan is approved.
9. Explicit approval is granted for implementation.

## 62. Route registration approval checklist

Route registration may proceed only after the implementation branch proves all controls are present and tests pass. Registration must remain internal-only, disabled by default unless explicitly enabled, and service-only.

Registration approval must be distinct from route exposure approval.

## 63. Route exposure approval checklist

Route exposure remains blocked. Any future exposure approval must separately prove internal-only mounting, auth, authorization, caller identity, limits, logging, observability, response safety, rollback, and test coverage.

No route exposure is approved by this planning document.

## 64. Public exposure prohibition

Public exposure is prohibited. The route must not be added to public APIs, frontend-facing routers, public docs, browser-accessible flows, or unauthenticated paths.

Changing this prohibition requires a separate explicit governance decision.

## 65. Cockpit/detail drawer prohibition

Cockpit and detail drawer integration remain prohibited. No frontend consumer may be added by this PR or inferred from this planning document.

Any future UI consumption requires separate approval after the internal API has been implemented, tested, and reviewed.

## 66. Copy/export prohibition

Copy and export behavior remain prohibited. The route must not be used to support downloading, copying, exporting, or bulk extracting dry-run audit history.

Future copy/export work requires separate governance, redaction, rate limiting, and abuse review.

## 67. Retention/cleanup exclusion

Retention and cleanup behavior are excluded. The route must not change retention policies, cleanup jobs, storage compaction, deletion behavior, or archival behavior.

Retention work requires separate governance and implementation approval.

## 68. Execution exclusion

Execution behavior is excluded. The route must not start dry runs, replay dry runs, mutate sessions, enqueue jobs, rewrite prompts, call providers, or feed persisted evidence into execution inputs.

Autonomous execution remains blocked.

## 69. Open risks

Open risks include misidentifying the internal route boundary, assuming auth controls that are not present, logging sensitive evidence, enabling broad enumeration through pagination, leaking storage implementation details, or accidentally creating a frontend/public route.

These risks are why implementation remains blocked until explicit approval and focused tests exist.

## 70. Open questions

Open questions for a future branch:

1. Which route registry owns internal-only routes?
2. What authentication middleware is authoritative for this route class?
3. What authorization capability is required?
4. What caller identity should be audited?
5. What route switch naming convention should be used?
6. What rate, size, and query complexity limits match operational needs?
7. Which test suite should own route boundary coverage?

## 71. Go/no-go table

| Area | Status | Decision |
| --- | --- | --- |
| Documentation/planning | Ready | Go |
| Future implementation planning | Ready | Go |
| Route registration implementation in this PR | Blocked | No-go |
| Internal route exposure | Blocked | No-go |
| Public exposure | Blocked | No-go |
| Cockpit/detail drawer | Blocked | No-go |
| Copy/export | Blocked | No-go |
| Retention/cleanup | Blocked | No-go |
| Raw storage/direct MemoryFacade/SQL access | Blocked | No-go |
| Prompt rewrite/provider execution/autonomous execution | Blocked | No-go |

## 72. Final recommendation

Approve this PR for documentation/planning only. Allow future implementation planning to continue, but do not approve route registration implementation in this PR.

Route registration remains blocked until explicit approval. Route exposure, public exposure, Cockpit/detail drawer consumption, copy/export behavior, retention/cleanup changes, raw storage access, direct `MemoryFacade` access, prompt rewrite behavior, provider execution, persisted evidence execution input, and autonomous execution remain blocked.
