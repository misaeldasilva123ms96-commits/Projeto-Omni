# Dry-Run Historical Audit API Route Registration Implementation Preparation Governance Review

## 1. Executive summary

This document reviews the implementation-preparation artifact added in PR #485. It approves the document as governance evidence and confirms that preparation may continue toward a future implementation-controls branch.

Required governance conclusions:

- Approved for documentation.
- Approved for implementation-preparation.
- Approved that future route must not use the current no-auth /internal group.
- Conditionally approved to prepare a future implementation-controls branch.
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

## 2. Scope

The scope is a docs-only governance review of `docs/runtime/autonomy-dry-run-historical-audit-api-route-registration-implementation-preparation.md`.

This review decides which preparation findings are approved, which next-step preparation is conditionally approved, and which implementation and exposure actions remain blocked.

## 3. Non-goals

This review does not implement route registration, expose endpoints, modify handlers, add router wiring, add middleware, add auth/authz code, add rate limiter code, or change runtime/provider/prompt/execution behavior.

It also does not modify `MemoryFacade`, `HistoricalDryRunAuditQueryService`, storage, frontend/Cockpit/detail drawer, copy/export, retention/cleanup, CI secrets, deploy configs, production settings, or billing-related settings.

## 4. Reviewed materials

Reviewed material:

- `docs/runtime/autonomy-dry-run-historical-audit-api-route-registration-implementation-preparation.md`
- Prior governance posture in `docs/runtime` for route exposure, route registration controls, implementation planning, and implementation preparation.

This review assumes PR #485 has been merged into `main`.

## 5. Current implementation state

Internal contract handlers exist in Python and remain unregistered. They fail closed by default with `internal_enabled=False`, and `internal_enabled=False` is not authentication.

Delegation remains limited to `HistoricalDryRunAuditQueryService`. No internal route, public route, Cockpit/detail drawer, copy/export, retention/cleanup path, provider/model execution path, retry/replan path, or autonomous execution path is exposed by this work.

## 6. Current governance state

Documentation and implementation-preparation are approved. Route registration implementation remains blocked.

The preparation artifact selected real existing mechanisms where possible, but it also identified missing controls that must exist before any future implementation-controls branch can be treated as ready for route registration.

## 7. Governance decision summary

Approved:

- Documentation.
- Implementation-preparation.
- Selection of existing mechanisms for future design discussion.
- Rejection of the current no-auth `/internal/*` group for this sensitive API.

Conditionally approved:

- Future implementation-controls branch preparation, only after explicit Misael approval and selection of the required controls.

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

## 8. Preparation safety review

The preparation document is safe because it inspects existing architecture, selects candidate mechanisms, identifies missing controls, and preserves non-approval for implementation and exposure.

The preparation document must not be treated as route registration approval.

## 9. Files inspected review

The inspected file list is appropriate for preparation. It includes Rust Axum route composition and auth files, Python dry-run audit contract/service/model files, rate limit and redaction utilities, and relevant tests.

No additional code inspection is required for this docs-only governance review.

## 10. Rust Axum route architecture review

The preparation correctly identifies `backend/rust/src/main.rs` as the HTTP route registration owner. Rust Axum routers compose protected route groups and apply `route_layer(from_fn_with_state(..., require_supabase_auth))`.

The selected future direction should stay in Rust route composition rather than creating parallel Python HTTP exposure.

## 11. Python dry-run audit contract/service review

The preparation correctly identifies Python as the current dry-run audit contract/service owner. `historical_audit_internal_api.py` provides fail-closed handler functions and request parsing, while `HistoricalDryRunAuditQueryService` provides the readonly service boundary.

Future route code must not bypass this contract/service boundary.

## 12. Selected route registration approach review

The selected approach is approved for future planning: a protected Rust Axum router, disabled by default, with controls before service invocation.

This review does not approve implementing that router in this PR.

## 13. Supabase JWT auth approach review

Reuse of existing Supabase JWT authentication through `require_supabase_auth` is approved as the selected authentication approach for future controls.

Authentication alone is not sufficient authorization for historical dry-run audit access.

## 14. Missing route-specific authorization review

The preparation correctly identifies route-specific readonly historical-audit authorization as missing.

This missing control blocks route registration implementation, route registration, and route exposure until a concrete authorization design is selected and tested.

## 15. Supabase sub caller identity review

Using the authenticated Supabase `sub` claim from Axum request extensions is approved as the selected caller identity source for future controls.

Requests without a stable `sub` must fail closed before service invocation.

## 16. Rate limit approach review

The preparation approves a per-caller route-level rate limit concept modeled on existing bucket behavior, but no implementation exists yet.

Future controls must prove rate-limited requests do not invoke `HistoricalDryRunAuditQueryService`.

## 17. Size limit approach review

The preparation correctly selects route-level size bounds plus preservation of existing Python contract limits.

Future controls must reject oversized query count, query string, individual parameter, path parameter, and page size inputs before service invocation.

## 18. Query complexity approach review

The selected query complexity approach is approved: preserve existing filter and sort allowlists, bounded pagination, date validation, unsupported parameter rejection, and no raw query language pass-through.

Raw SQL, JSONL selectors, SQLite selectors, and storage paths remain blocked.

## 19. Audit logging approach review

The selected approach is approved for future controls: use the service audit callback for service events and add sanitized route-level audit events for auth/authz/rate/size/query decisions.

The route audit schema remains missing and must be selected before implementation-controls work can proceed.

## 20. Observability approach review

The selected approach is approved for future controls: use sanitized Rust tracing and categorical metrics/fields for route attempts, denials, validation failures, limit failures, degraded responses, and latency buckets.

Observability must not capture raw request or response bodies.

## 21. Rollback/disablement approach review

The selected rollback/disablement approach is approved: disabled-by-default route switch plus preservation of the Python `internal_enabled=False` guard.

Rollback must make the route absent or denied without storage migration, provider changes, retention changes, or execution changes.

## 22. Protected router requirement review

The future route must use a protected Rust Axum router that applies authentication and the future route-specific authorization control before query parsing and service invocation.

This requirement is approved as mandatory.

## 23. No-auth internal group rejection review

The preparation correctly rejects the current no-auth `/internal/*` group for this route. That rejection is approved.

Future route registration must not mount historical dry-run audit access under the current no-auth internal route group.

## 24. Handler invocation boundary review

Future handler invocation must occur only after route switch, authentication, authorization, caller identity extraction, rate limits, size limits, query validation, and safe audit/observability setup succeed.

The handler must remain readonly.

## 25. HistoricalDryRunAuditQueryService-only delegation review

Service-only delegation is mandatory. Future route code must call only the contract/service path backed by `HistoricalDryRunAuditQueryService`.

Bypassing the service boundary remains blocked.

## 26. No direct MemoryFacade review

Direct API-to-`MemoryFacade` access remains not approved. Future route code must not call `MemoryFacade` directly.

If a missing query capability is discovered, it requires separate service-contract governance.

## 27. No raw storage review

Raw JSONL, raw SQLite rows, raw storage files, filesystem paths, and adapter internals remain blocked.

Future route code must consume only sanitized service responses.

## 28. No SQL construction review

SQL construction from request input remains prohibited. Future route code must not accept, construct, log, or expose SQL.

Database-backed behavior must stay behind existing safe abstractions.

## 29. Request validation review

Request validation requirements are approved as mandatory. Unknown fields, invalid types, invalid enums, unsupported query parameters, and oversized values must fail before service invocation.

Validation must remain structured and deterministic.

## 30. Path validation review

Path validation requirements are approved as mandatory. `plan_id` and similar path values must be bounded, sanitized, and rejected when they contain traversal, slash, query, or control metacharacters.

Invalid path values must fail closed.

## 31. Filter/sort allowlist review

The existing dry-run audit filter and sort allowlists must be preserved. Unknown filters and sorts must be rejected rather than ignored.

Storage-specific fields must not become route inputs.

## 32. Pagination review

Pagination must remain bounded by existing default, maximum limit, and maximum offset controls.

Pagination must not become copy/export or bulk extraction.

## 33. Error/degradation mapping review

Disabled route, auth failure, authorization failure, rate limit, size limit, validation failure, service failure, invalid service response, and not-found states must map to sanitized categorical responses.

Raw exception text, stack traces, storage paths, SQL, provider payloads, stdout/stderr, command args, file contents, and `.env` content must not be returned.

## 34. Required advisory warnings review

The existing required advisory warnings must be preserved. Warnings must continue to state that query results are readonly audit metadata, not approval, not execution input, and that copy/export remains disabled.

Warnings must not imply route exposure approval.

## 35. Safe response envelope review

The safe response envelope approach is approved. Future responses should preserve sanitized list/detail shapes, pagination metadata, applied filters, warnings, degraded state, generated time, and safe error categories.

Response envelopes must not expose raw evidence or storage internals.

## 36. Forbidden field denylist review

The forbidden response denylist is approved and mandatory. Raw JSONL, raw SQLite rows, raw SQL, prompts, rewritten prompts, provider payloads, tool outputs, secrets, headers, cookies, stack traces, stdout/stderr, command args, file contents, `.env` content, execution inputs, and raw storage paths must not be returned.

Future tests must include representative denylisted fields.

## 37. Forbidden logging denylist review

The forbidden logging denylist is approved and mandatory. Authorization headers, cookies, Bearer tokens, JWTs, secrets, API keys, raw prompts, provider payloads, tool outputs, raw evidence, stdout/stderr, command args, file contents, `.env` content, stack traces, raw JSONL, raw SQLite rows, raw SQL, and storage paths must not be logged.

Future route logs must use safe categorical fields only.

## 38. Auth fail-closed test review

Auth fail-closed tests are required before any route registration implementation. Missing, malformed, expired, invalid, and unverifiable Supabase JWTs must return unauthorized without invoking query parsing or service code.

These tests are not implemented in this PR.

## 39. Unauthorized fail-closed test review

Unauthorized fail-closed tests are required. Authenticated users without the future readonly historical-audit capability/scope must be denied before service invocation.

Because authorization is missing, this is a blocker.

## 40. Internal-only boundary test review

Internal-only boundary tests are required. They must prove the route is not mounted in public routers and not mounted under the current no-auth `/internal/*` group.

The selected protected router must be the only route location.

## 41. Rate limit test review

Rate limit tests are required. Excessive per-caller requests must be denied and must not invoke `HistoricalDryRunAuditQueryService`.

Logs and observability for rate-limited attempts must remain sanitized.

## 42. Size limit test review

Size limit tests are required. Excessive query count, query string length, individual parameter length, path parameter length, and page size must be rejected before service invocation.

Responses must be categorical and sanitized.

## 43. Query complexity test review

Query complexity tests are required. Unsupported filters, unsupported sorts, invalid ranges, excessive ranges, arbitrary expressions, SQL-like input, JSONL selectors, SQLite selectors, and storage paths must be rejected.

Rejected requests must not invoke the service.

## 44. Service-only delegation test review

Service-only delegation tests are required. They must prove the route only reaches the `HistoricalDryRunAuditQueryService` path.

They must also prove no direct `MemoryFacade`, raw storage, filesystem, or SQL helper access occurs.

## 45. No raw JSONL/SQLite/SQL exposure test review

Tests must prove responses, errors, logs, and traces do not expose raw JSONL, raw SQLite rows, SQL strings, table names, storage paths, or adapter implementation details.

This remains mandatory before route registration.

## 46. No runtime/provider/execution behavior test review

Tests must prove the route cannot start dry runs, retry, replan, enqueue work, mutate sessions, rewrite prompts, call providers/models, self-repair, or pass persisted evidence into execution inputs.

The route must remain read-only audit metadata access.

## 47. Rollback/disablement test review

Rollback/disablement tests are required. Disabling the route switch must make requests absent or denied and must prevent service invocation.

The Python `internal_enabled=False` guard must remain fail-closed.

## 48. Regression test matrix review

The regression matrix from the preparation document is approved as the baseline for a future implementation-controls branch. It covers auth, authorization, internal boundary, rate limits, size limits, query complexity, delegation, exposure, non-execution, and rollback.

The matrix must be approved again when concrete implementation code is proposed.

## 49. Missing controls review

Missing controls remain:

- Route-specific readonly historical-audit authorization capability/scope.
- Rust route-level rate-limit control.
- Rust route-level size-limit control.
- Rust route-level query complexity adapter.
- Route-level audit event schema.
- Route-level observability counters/fields.
- Explicit route registration switch name and ownership.
- Security review owner.
- Abuse review owner.

These missing controls block route registration.

## 50. Security review checklist

Security review must cover auth, authorization, caller identity, internal-only mounting, route switch behavior, logging denylist, response denylist, service-only delegation, no raw storage, no SQL construction, and non-execution guarantees.

Security review must also confirm no CI secrets, deploy configs, production settings, or billing settings are changed.

## 51. Abuse review checklist

Abuse review must cover enumeration, broad historical scraping, repeated pagination, sensitive evidence inference, filter probing, route discovery, rate-limit bypass, copy/export pressure, and unauthorized operational insight.

Abuse review must require no public exposure, no Cockpit/detail drawer, and no copy/export.

## 52. Future implementation-controls branch constraints

A future implementation-controls branch may prepare the missing controls only after explicit Misael approval. It must remain narrow and must not register the route unless separately approved.

It must not modify provider routing, prompts, runtime execution, retention/cleanup, Cockpit/detail drawer, copy/export, storage adapters, raw query behavior, CI secrets, deploy configs, production settings, or billing-related settings.

## 53. Explicit non-approval statement

This governance review does not approve route registration implementation, route registration, internal route exposure, public route exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL read, raw SQLite row read, raw SQL query/filter, direct API-to-`MemoryFacade`, prompt rewrite, provider/model retry execution, provider/model replan execution, persisted evidence as execution input, autonomous execution, or self-repair.

Only documentation, implementation-preparation, rejection of the no-auth `/internal/*` group, and conditional future implementation-controls preparation are approved.

## 54. Open risks

Open risks include treating preparation approval as implementation approval, accidentally mounting under no-auth `/internal/*`, relying on authentication without authorization, adding weak process-local limits in a multi-instance context, leaking sensitive query content through logs, enabling enumeration through pagination, and creating frontend/export pressure.

These risks require the missing controls, security review, abuse review, and tests before implementation can proceed.

## 55. Open questions

Open questions:

1. What exact readonly historical-audit authorization capability/scope should be selected?
2. What protected Rust Axum path should be used?
3. What route switch name and owner should be selected?
4. Should rate limiting be Rust-native or shared?
5. What audit event schema should be adopted?
6. What observability metric names and labels are safe?
7. Who owns security review and abuse review?

## 56. Go/no-go table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | Approved. |
| Implementation-preparation | Go | Approved. |
| No-auth /internal group for future route | No-go | Must not be used. |
| Future implementation-controls branch preparation | Conditional go | Requires explicit Misael approval and selected controls. |
| Route registration implementation | No-go | Not approved yet. |
| Route registration | No-go | Not approved yet. |
| Route exposure | No-go | Not approved yet. |
| Public exposure | No-go | Not approved. |
| Cockpit/detail drawer consumption | No-go | Not approved. |
| Copy/export | No-go | Not approved. |
| Retention/cleanup | No-go | Not approved. |
| Raw JSONL read | No-go | Not approved. |
| Raw SQLite row read | No-go | Not approved. |
| Raw SQL query/filter | No-go | Not approved. |
| Direct API-to-MemoryFacade | No-go | Not approved. |
| Prompt rewrite | No-go | Not approved. |
| Provider/model retry execution | No-go | Not approved. |
| Provider/model replan execution | No-go | Not approved. |
| Persisted evidence as execution input | No-go | Not approved. |
| Autonomous execution | No-go | Not approved. |

## 57. Final recommendation

Approve this PR for documentation/governance review. Keep implementation-preparation approved and approve the finding that the future route must not use the current no-auth `/internal/*` group.

Conditionally approve preparation for a future implementation-controls branch only after explicit Misael approval and selection of route-specific authorization, protected Rust Axum path, Supabase JWT reuse confirmation, Supabase `sub` caller identity, route-level rate/size/query strategies, safe audit logging schema, safe observability schema, rollback/disablement switch, test matrix, security review, and abuse review.

Do not approve route registration implementation, route registration, route exposure, public exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL/SQLite/SQL access, direct API-to-`MemoryFacade` access, prompt rewrite, provider/model retry or replan execution, persisted evidence as execution input, autonomous execution, or self-repair.
