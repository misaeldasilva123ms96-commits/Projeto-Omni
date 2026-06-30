# Dry-Run Historical Audit API Route Registration Implementation Planning Governance Review

## 1. Executive summary

This document reviews the implementation planning document added in PR #483 for governance readiness. The planning artifact is approved for documentation and approved for implementation planning. It is conditionally approved for future implementation branch preparation only.

It is not approved for route registration implementation yet, not approved for route registration yet, not approved for route exposure yet, and not approved for public exposure. Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL/SQLite/SQL access, direct API-to-`MemoryFacade` access, prompt rewrite, provider/model retry or replan execution, persisted evidence as execution input, and autonomous execution remain not approved.

## 2. Scope

This review covers the governance status of the route registration implementation planning document at `docs/runtime/autonomy-dry-run-historical-audit-api-route-registration-implementation-planning.md`.

The review decides which planning elements are approved, which are conditionally approved for future preparation, and which runtime or exposure behaviors remain blocked.

## 3. Non-goals

This review does not implement route registration, expose endpoints, modify handlers, add auth/authz code, add rate limiter code, add frontend/Cockpit/detail drawer behavior, add copy/export, or change runtime/provider/prompt/execution behavior.

It does not modify `MemoryFacade`, `HistoricalDryRunAuditQueryService`, storage, provider routing, prompts, CI secrets, deploy configuration, production settings, or billing-related settings.

## 4. Reviewed materials

Reviewed material:

- `docs/runtime/autonomy-dry-run-historical-audit-api-route-registration-implementation-planning.md`
- Prior route exposure, route registration controls, and governance review posture represented in the current `docs/runtime` history.

The review assumes PR #483 is merged and this branch starts from updated `main`.

## 5. Current implementation state

Internal contract handlers exist, but handlers remain unregistered. They fail closed by default with `internal_enabled=False`, and `internal_enabled=False` is not authentication.

Delegation remains only to `HistoricalDryRunAuditQueryService`. No public route, internal route, Cockpit/frontend/detail drawer, copy/export flow, or route exposure exists.

## 6. Current governance state

Governance currently permits documentation, planning, and review. It does not permit implementation of route registration or route exposure.

Route registration remains blocked until explicit implementation approval from Misael and until real authentication, authorization, caller identity, limits, logging, observability, rollback, security review, abuse review, and tests are selected or planned.

## 7. Governance decision summary

Required governance conclusions:

- Approved for documentation.
- Approved for implementation planning.
- Conditionally approved for future implementation branch preparation only.
- Not approved for route registration implementation yet.
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

Approved:

- Documentation.
- Implementation planning.

Conditionally approved:

- Future implementation branch preparation only.

Not approved:

- Route registration implementation.
- Route registration.
- Route exposure.
- Public exposure.
- Cockpit/detail drawer consumption.
- Copy/export.
- Retention/cleanup.
- Raw JSONL/SQLite/SQL access.
- Direct API-to-`MemoryFacade` access.
- Prompt rewrite.
- Provider/model retry or replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 8. Planning safety review

The planning document is safe as a governance artifact because it keeps runtime behavior blocked, names the missing controls, and separates future preparation from implementation approval.

The planning document must not be interpreted as implicit approval to register routes or expose endpoints.

## 9. Future implementation objective review

The future objective is acceptable only as a planning target: an internal-only read/query route that delegates to `HistoricalDryRunAuditQueryService` and returns a sanitized response envelope.

The objective is not approved for implementation until the required conditions are met and explicitly approved.

## 10. Candidate route review

Candidate routes are acceptable as placeholders for future planning. They are not approved route names and must not be registered.

A future branch must inspect real internal route conventions before choosing any path.

## 11. Implementation phase review

The phased plan is approved as a preparation framework. The required sequencing correctly places route convention discovery, auth/authz discovery, caller identity, limits, logging, observability, switch design, fail-closed behavior, rollback, and tests before registration.

No phase authorizes route registration in this PR.

## 12. Existing internal route convention review

The requirement to inspect existing internal route conventions is approved. A future implementation branch must identify real routing framework patterns before code changes.

If existing conventions cannot prove an internal-only boundary, route registration remains blocked.

## 13. Real authentication mechanism review

The requirement to identify a real authentication mechanism is approved. Placeholder authentication is not acceptable.

If the real mechanism is not selected, no route may be registered.

## 14. Real authorization mechanism review

The requirement to identify a real authorization mechanism is approved. Authentication alone must not be treated as authorization.

If authorization cannot be proven for this sensitive query class, route registration remains blocked.

## 15. Internal caller identity review

The requirement to select an internal-only caller identity model is approved. Caller identity must support authorization, audit logging, rate limiting, and support investigation.

Anonymous, spoofable, or request-parameter-derived identities are not acceptable.

## 16. Route-level rate limit review

The requirement to select a route-level rate limit strategy is approved. Rate limiting must protect collection queries, detail queries, pagination, and repeated filter enumeration.

Rate limiter code is not approved in this PR.

## 17. Route-level size limit review

The requirement to select a route-level size limit strategy is approved. Query strings, bodies, cursors, filters, page size, and response size must be bounded.

Size limit implementation is not approved in this PR.

## 18. Query complexity limit review

The requirement to select a query complexity limit strategy is approved. Allowed filters, sorts, date ranges, and pagination behavior must be constrained before service invocation.

Arbitrary predicates, raw SQL, raw JSONL selectors, storage paths, and query language pass-through remain prohibited.

## 19. Safe audit logging review

The requirement to select a safe audit logging strategy is approved. Audit logs may record access decisions and sanitized summaries only.

Audit logs must not include raw prompts, provider payloads, persisted evidence, secrets, headers, cookies, stack traces, stdout/stderr, command args, file contents, or `.env` content.

## 20. Safe observability review

The requirement to select a safe observability strategy is approved. Metrics may describe counts, denials, validation failures, rate-limit outcomes, size-limit outcomes, latency buckets, and degraded service states.

Observability must not contain raw records, raw storage identifiers, prompts, provider payloads, secrets, or execution material.

## 21. Route registration switch review

The route registration switch requirement is approved as a future control. The switch must default disabled and must be tested.

The switch is not approved as authentication and must not be used to replace auth/authz.

## 22. Fail-closed route behavior review

Fail-closed route behavior is required and approved as a condition. Missing auth, missing authorization, missing identity, invalid request, unavailable limits, unavailable service dependency, or disabled switch must deny before service invocation.

Fail-closed behavior must not leak record existence or storage internals.

## 23. Rollback path review

The rollback/disablement requirement is approved. Rollback must disable or remove route callability without storage migration, data deletion, runtime execution changes, or provider changes.

The future branch must include verification steps for disabled or absent-route behavior.

## 24. Implementation file candidate review

Implementation file candidates are acceptable as planning references only. They are not approval to edit routing, handlers, runtime, storage, auth, rate limiting, or frontend code in this PR.

Exact files must be selected only in a future approved implementation branch.

## 25. Test file candidate review

Test file candidates are acceptable as planning references. Future tests must focus on internal routing, fail-closed controls, validation, service-only delegation, logging safety, response safety, rollback, and non-execution.

No test code is required in this docs-only governance review.

## 26. Route registration constraint review

The registration constraints are approved as mandatory future controls. Registration must be internal-only, disabled by default unless explicitly enabled, service-only, and covered by tests.

Registration remains not approved.

## 27. Internal-only route boundary review

The internal-only boundary requirement is approved. Internal-looking path names are insufficient; mounting and access controls must prove internal-only behavior.

If internal-only enforcement is uncertain, the route must remain absent.

## 28. Authentication requirement review

Authentication requirements are approved as conditions. Missing, malformed, expired, invalid, or unverifiable authentication must fail closed before service invocation.

Authentication code is not approved in this PR.

## 29. Authorization requirement review

Authorization requirements are approved as conditions. Authenticated callers must still prove explicit permission for dry-run historical audit queries.

Authorization code is not approved in this PR.

## 30. Internal caller requirement review

Internal caller requirements are approved as conditions. The caller must be stable, auditable, rate-limitable, and suitable for support investigation.

No implementation may trust unverified request input as caller identity.

## 31. Rate limit requirement review

Rate limit requirements are approved as conditions. The future branch must prove limited requests do not invoke `HistoricalDryRunAuditQueryService`.

Rate limiting remains a required future control, not a current implementation.

## 32. Size limit requirement review

Size limit requirements are approved as conditions. Oversized requests must be rejected before service invocation and must produce sanitized errors.

Size limiting remains a required future control, not a current implementation.

## 33. Query complexity requirement review

Query complexity requirements are approved as conditions. Unknown fields, excessive ranges, excessive filter counts, arbitrary expressions, and storage-aware selectors must be rejected.

Query complexity limiting remains a required future control.

## 34. Audit logging requirement review

Audit logging requirements are approved as conditions. Logs should include route id, caller identity, decision, request id, sanitized filter summary, and outcome class.

Logs must not include denylisted sensitive content.

## 35. Observability requirement review

Observability requirements are approved as conditions. Metrics and traces should show control outcomes and health without leaking data.

Observability must remain operational, not evidentiary.

## 36. Safe request logging review

Safe request logging rules are approved as mandatory. Logs may include route id, request id, safe caller identifier, method, sanitized filter names, page size bucket, and outcome.

Raw headers, cookies, tokens, full query strings, prompts, evidence, provider payloads, SQL, and storage paths remain forbidden.

## 37. Safe response logging review

Safe response logging rules are approved as mandatory. Logs may include status, count bucket, warning codes, degradation flags, and latency bucket.

Response bodies, raw records, stack traces, provider payloads, evidence, prompts, SQL, and storage internals remain forbidden.

## 38. Forbidden logging denylist review

The forbidden logging denylist is approved as mandatory. Secrets, headers, cookies, raw prompts, prompt rewrites, provider payloads, persisted evidence, stdout/stderr, command args, file contents, `.env` content, raw JSONL, raw SQLite rows, raw SQL, storage paths, stack traces, and tracebacks must not be logged.

A future branch must include review evidence or tests for the denylist.

## 39. Handler invocation review

Handler invocation rules are approved as mandatory. Controls must run before service invocation.

Handlers must remain read-only and must not start, retry, replan, mutate, enqueue, replay, or execute dry-run behavior.

## 40. HistoricalDryRunAuditQueryService-only delegation review

Service-only delegation is approved as mandatory. Future route code may delegate only to `HistoricalDryRunAuditQueryService`.

If needed data is not available through the service contract, the implementation must stop rather than bypass the boundary.

## 41. No direct MemoryFacade review

The no direct API-to-`MemoryFacade` rule is approved as mandatory. Route code must not call `MemoryFacade` directly.

Direct API-to-`MemoryFacade` access remains not approved.

## 42. No raw storage review

The no raw storage rule is approved as mandatory. Route code must not read JSONL files, SQLite rows, filesystem storage paths, or adapter internals.

Raw JSONL and raw SQLite row reads remain not approved.

## 43. No SQL construction review

The no SQL construction rule is approved as mandatory. Route code must not accept, construct, log, or expose SQL from request input.

Raw SQL filters and queries remain not approved.

## 44. Request validation review

Request validation requirements are approved as mandatory. Typed or structured validation must reject unknown fields, invalid types, invalid enums, invalid combinations, and unbounded input.

Validation must occur before service invocation.

## 45. Path validation review

Path validation requirements are approved as mandatory. Path parameters must be bounded, canonicalized, typed, and never interpreted as filesystem paths or storage keys by route code.

Invalid path parameters must fail closed.

## 46. Filter/sort allowlist review

Filter/sort allowlist requirements are approved as mandatory. Unknown filters and sorts must be rejected, not ignored.

Storage-specific or implementation-specific fields must not become public route inputs.

## 47. Pagination review

Pagination requirements are approved as mandatory. Collection queries must have conservative defaults and maximums.

Pagination must not become a bulk export mechanism.

## 48. Error/degradation mapping review

Error and degradation mapping requirements are approved as mandatory. Disabled route, auth failure, authorization failure, rate limit, size limit, validation failure, service unavailable, and degraded data states must map to sanitized responses.

Errors must not leak record existence, stack traces, raw exception text, SQL, storage paths, or provider payloads.

## 49. Required advisory warnings review

Required advisory warnings are approved as mandatory for partial, degraded, redacted, paginated, stale, or retention-limited data.

Warnings must be safe codes and must not imply public or frontend approval.

## 50. Safe response envelope review

The safe response envelope requirement is approved as mandatory. Responses may include sanitized data, pagination metadata, warning codes, request/correlation id, and degradation status.

The envelope must not include raw records, prompts, provider payloads, evidence execution inputs, secrets, logs, SQL, or storage metadata.

## 51. Forbidden field denylist review

The forbidden response field denylist is approved as mandatory. Raw prompts, rewritten prompts, provider payloads, raw persisted evidence, stdout/stderr, command args, file contents, `.env` content, stack traces, secrets, headers, cookies, raw JSONL, raw SQLite rows, SQL text, filesystem paths, and execution input material must not be returned.

A future branch must prove response serialization enforces the denylist.

## 52. Required test matrix review

The required test matrix is approved as a future condition. Tests must cover disabled-by-default behavior, auth fail-closed, unauthorized fail-closed, internal-only boundary, rate limits, size limits, query complexity, service-only delegation, no raw storage/SQL exposure, non-execution, and rollback/disablement.

The test matrix must be approved before route registration implementation.

## 53. Auth fail-closed test review

Auth fail-closed tests are required. Missing, malformed, expired, invalid, and unverifiable authentication must deny before service invocation.

These tests are conditions for a future branch, not changes in this PR.

## 54. Unauthorized fail-closed test review

Unauthorized fail-closed tests are required. Authenticated callers without the required capability or scope must be denied before service invocation.

The denial must not reveal record existence.

## 55. Internal-only boundary test review

Internal-only boundary tests are required. The route must be absent from public routers and callable only through the approved internal context.

If the repository supports route manifests, they should be checked.

## 56. Rate limit test review

Rate limit tests are required. They must prove repeated or excessive requests are denied and do not invoke the service.

They must also verify safe logging for rate-limited requests.

## 57. Size limit test review

Size limit tests are required. Oversized query strings, bodies, cursors, filter sets, and page sizes must be rejected before service invocation.

Sanitized errors must be verified.

## 58. Query complexity test review

Query complexity tests are required. Unknown fields, arbitrary expressions, excessive date ranges, excessive filter counts, storage-aware selectors, and SQL-like inputs must be rejected.

No raw JSONL selector, SQLite selector, SQL filter, or storage path may pass validation.

## 59. Service-only delegation test review

Service-only delegation tests are required. Mocks or spies should prove the route delegates only to `HistoricalDryRunAuditQueryService`.

The route must not call `MemoryFacade`, storage adapters, filesystem readers, or SQL helpers.

## 60. No raw JSONL/SQLite/SQL exposure test review

No raw JSONL/SQLite/SQL exposure tests are required. Responses and logs must not contain raw JSONL records, raw SQLite rows, SQL strings, table names, storage paths, or adapter implementation details.

Serialization tests should include denylisted fields.

## 61. No runtime/provider/execution behavior test review

No runtime/provider/execution behavior tests are required. The route must not start, retry, replan, mutate, enqueue, replay, prompt-rewrite, call providers/models, or pass persisted evidence into execution inputs.

Autonomous execution must remain impossible from this route.

## 62. Rollback/disablement test review

Rollback/disablement tests are required. Disabling the route switch must make the route absent or denied and must not invoke the service.

Safe observability for disabled or denied attempts must be verified.

## 63. Implementation approval checklist review

The implementation approval checklist is approved as a future gate. Before implementation branch work begins, the following must be true:

1. Explicit approval from Misael.
2. Real authentication design selected.
3. Real authorization design selected.
4. Internal-only caller identity selected.
5. Route-level rate limit strategy selected.
6. Route-level size limit strategy selected.
7. Query complexity limit strategy selected.
8. Safe audit logging strategy selected.
9. Safe observability strategy selected.
10. Rollback/disablement plan selected.
11. Test matrix approved.
12. Security review planned.
13. Abuse review planned.
14. No public exposure.
15. No Cockpit/detail drawer.
16. No copy/export.

## 64. Route registration approval checklist review

Route registration remains not approved. A future route registration approval must separately prove implementation controls, tests, internal-only mounting, disabled-by-default behavior, auth/authz, identity, limits, logging safety, observability safety, rollback, and service-only delegation.

Implementation approval and route registration approval must remain separate decisions.

## 65. Route exposure approval checklist review

Route exposure remains not approved. Internal route exposure requires separate approval after route registration controls are implemented and verified.

Public route exposure remains prohibited.

## 66. Public exposure prohibition review

Public exposure prohibition is approved and remains mandatory. The route must not be added to public APIs, frontend-facing routers, public docs, browser-accessible flows, or unauthenticated paths.

Changing this prohibition requires a separate governance decision.

## 67. Cockpit/detail drawer prohibition review

Cockpit/detail drawer consumption remains not approved. No frontend integration may be inferred from planning or governance review.

A future UI branch would require separate governance after internal route safety is proven.

## 68. Copy/export prohibition review

Copy/export remains not approved. The route must not support downloading, copying, exporting, or bulk extraction.

Any future copy/export work requires separate governance, redaction, rate limiting, and abuse review.

## 69. Retention/cleanup exclusion review

Retention/cleanup remains not approved. The route must not change retention policies, cleanup jobs, compaction, deletion, archival behavior, or storage lifecycle.

Retention/cleanup work requires separate governance.

## 70. Execution exclusion review

Execution remains not approved. The route must not start dry runs, retry, replan, mutate sessions, enqueue jobs, replay records, rewrite prompts, call providers/models, or feed persisted evidence into execution inputs.

Autonomous execution remains not approved.

## 71. Explicit non-approval statement

This governance review does not approve route registration implementation, route registration, internal route exposure, public route exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL read, raw SQLite row read, raw SQL filter/query, direct API-to-`MemoryFacade`, prompt rewrite, provider/model retry execution, provider/model replan execution, persisted evidence as execution input, or autonomous execution.

Only documentation, implementation planning, and conditional future implementation branch preparation are approved.

## 72. Open risks

Open risks include treating planning approval as implementation approval, confusing `internal_enabled=False` with authentication, selecting incomplete auth/authz controls, overexposing query filters, allowing bulk extraction through pagination, logging sensitive material, leaking storage internals, or accidentally connecting frontend/export behavior.

These risks require explicit approval, security review, abuse review, and the approved test matrix before implementation.

## 73. Open questions

Open questions before a future implementation branch:

1. Which internal route registry is authoritative?
2. Which authentication design should be selected?
3. Which authorization capability or scope should govern access?
4. Which internal-only caller identity should be audited?
5. Which rate, size, and query complexity limits are acceptable?
6. Which safe audit logging and observability sinks should be used?
7. Which rollback/disablement mechanism is operationally preferred?
8. Who owns the security and abuse reviews?

## 74. Go/no-go table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | Approved. |
| Implementation planning | Go | Approved. |
| Future implementation branch preparation | Conditional go | Requires explicit approval and selected controls. |
| Route registration implementation | No-go | Not approved yet. |
| Internal route registration | No-go | Not approved yet. |
| Internal route exposure | No-go | Not approved yet. |
| Public route exposure | No-go | Not approved. |
| Cockpit/detail drawer consumption | No-go | Not approved. |
| Copy/export | No-go | Not approved. |
| Retention/cleanup | No-go | Not approved. |
| Raw JSONL read | No-go | Not approved. |
| Raw SQLite row read | No-go | Not approved. |
| Raw SQL filter/query | No-go | Not approved. |
| Direct API-to-MemoryFacade | No-go | Not approved. |
| Prompt rewrite | No-go | Not approved. |
| Provider/model retry execution | No-go | Not approved. |
| Provider/model replan execution | No-go | Not approved. |
| Persisted evidence as execution input | No-go | Not approved. |
| Autonomous execution | No-go | Not approved. |

## 75. Final recommendation

Approve this PR for documentation and governance review. Keep implementation planning approved, and conditionally approve future implementation branch preparation only after explicit approval from Misael and selection of real auth/authz, caller identity, route-level limits, safe logging, observability, rollback/disablement, test matrix, security review, and abuse review.

Do not approve route registration implementation, route registration, route exposure, public exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw storage/SQL access, direct API-to-`MemoryFacade`, prompt rewrite, provider/model retry or replan execution, persisted evidence as execution input, or autonomous execution.
