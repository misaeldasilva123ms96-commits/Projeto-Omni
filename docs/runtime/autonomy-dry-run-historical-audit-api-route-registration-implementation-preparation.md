# Dry-Run Historical Audit API Route Registration Implementation Preparation

## 1. Executive summary

This document prepares a future implementation branch for historical dry-run audit API route registration. It is approved for documentation/preparation only. Existing mechanisms may be selected and documented, and future implementation branch preparation is allowed.

Route registration implementation is not approved in this PR. Route registration, route exposure, public exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL/SQLite/SQL access, direct API-to-`MemoryFacade` access, prompt rewrite, provider/model retry or replan execution, persisted evidence as execution input, and autonomous execution remain blocked.

## 2. Scope

The scope is to inspect existing backend architecture and document selected future mechanisms for route registration, authentication, authorization, internal-only caller identity, rate limits, size limits, query complexity limits, audit logging, observability, rollback/disablement, security review, abuse review, and tests.

This document does not implement any of those mechanisms.

## 3. Non-goals

This PR does not register API routes, expose endpoints, modify handlers, add middleware, add auth/authz implementation, add rate limiter implementation, add router wiring, modify `MemoryFacade`, modify `HistoricalDryRunAuditQueryService`, modify storage, or change runtime/provider/prompt/execution behavior.

It also does not add Cockpit/detail drawer behavior, copy/export, retention/cleanup, autonomous execution, self-repair, CI secret changes, deploy changes, production setting changes, or billing-related changes.

## 4. Current implementation state

Internal contract handlers exist in Python, are unregistered, and fail closed by default with `internal_enabled=False`. That flag is not authentication.

The current contract delegates only to `HistoricalDryRunAuditQueryService`, and the service delegates to `MemoryFacade` safe query contracts. No public or internal route is exposed, no Cockpit/frontend/detail drawer exists, and no copy/export exists.

## 5. Current governance state

Governance allows documentation/preparation only. Future implementation branch preparation is allowed, but route registration implementation is not approved in this PR.

Route registration remains blocked until a later branch receives explicit approval and satisfies the missing authz, control, security, abuse, and test conditions documented here.

## 6. Preparation method

Preparation used targeted inspection of the existing backend route registration, auth, observability, rate limit, redaction, dry-run audit contract, service, query model, and test files.

The inspection intentionally avoided broad implementation changes and did not execute provider/model calls or runtime behavior.

## 7. Files inspected

Files inspected:

- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs`
- `backend/rust/src/observability.rs`
- `backend/rust/src/run_control.rs`
- `backend/rust/crates/runtime/src/permissions.rs`
- `backend/python/brain/memory/historical_audit_internal_api.py`
- `backend/python/brain/memory/historical_audit_query_service.py`
- `backend/python/brain/memory/historical_audit_query_models.py`
- `backend/python/brain/runtime/rate_limiter.py`
- `backend/python/brain/runtime/observability/public_runtime_payload.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_internal_api.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_query_service.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_query_contracts.py`
- `backend/python/tests/memory/test_runtime_integration.py`

## 8. Existing backend route architecture

HTTP route registration is owned by the Rust Axum server in `backend/rust/src/main.rs`. The app composes `Router::new()` instances, registers routes with `get`, `post`, `put`, and `delete`, merges protected routers into the app, and applies shared layers such as CORS and `TraceLayer`.

Python currently owns the dry-run historical audit contract and service logic, but it is not registered as an HTTP route.

## 9. Existing internal route conventions

The current route map in `backend/rust/src/main.rs` explicitly marks `/internal/*` as internal with no auth middleware. That convention is not sufficient for sensitive historical dry-run audit access.

Protected routes use separate routers such as `protected_observability`, `protected_control`, `protected_operator`, and `protected_settings`, each with `route_layer(from_fn_with_state(state.clone(), require_supabase_auth))`.

## 10. Existing auth mechanisms found

The real HTTP authentication mechanism found is Supabase JWT validation in `backend/rust/src/observability_auth.rs`. `require_supabase_auth` extracts a Bearer token, validates it with `SupabaseAuthConfig`, and stores the Supabase subject as a request extension.

Observability stream access also uses short-lived, opaque, single-use stream tickets, but that pattern is specific to SSE stream constraints and should not replace normal request authentication for this API.

## 11. Existing authorization mechanisms found

No existing route-level HTTP authorization mechanism was found that grants a specific readonly historical audit capability. Protected routes currently authenticate with Supabase JWT and then use the authenticated user id in some settings handlers.

The Rust runtime permission policy in `backend/rust/crates/runtime/src/permissions.rs` authorizes tool execution, not HTTP API access, and should not be reused as route authorization without a separate design.

## 12. Existing caller identity patterns found

The existing HTTP caller identity pattern is the Supabase JWT `sub` claim inserted into Axum request extensions by `require_supabase_auth`. Settings handlers retrieve it through `extract_user_id`.

This is the selected identity source for a future route, but it must be combined with a route-specific authorization decision.

## 13. Existing rate limit patterns found

`backend/python/brain/runtime/rate_limiter.py` provides a simple in-memory `RateLimiter` with per-key buckets, a request window, remaining-count inspection, reset support, and dictionary diagnostics.

No Axum route-level rate-limit middleware was found. A future route must either adapt this pattern carefully or add a Rust-side equivalent before registration.

## 14. Existing request size limit patterns found

The Python dry-run audit contract enforces bounded query shape through `INTERNAL_DRY_RUN_AUDIT_MAX_QUERY_PARAMS`, `INTERNAL_DRY_RUN_AUDIT_MAX_PARAM_LENGTH`, and `INTERNAL_DRY_RUN_AUDIT_MAX_PLAN_ID_LENGTH`.

Axum JSON extractors are used elsewhere, but no route-specific body size middleware was found for this future query route. The future route should remain GET/query-only unless explicitly redesigned.

## 15. Existing query validation patterns found

`DryRunAuditQueryRequest` provides the strongest existing query validation pattern. It clamps `limit` and `offset`, allowlists filters, allowlists sort fields and directions, validates booleans and timestamps, rejects invalid ids, and validates date range ordering.

`historical_audit_internal_api.py` rejects unsupported query parameters and oversized values before invoking the service.

## 16. Existing audit logging patterns found

`HistoricalDryRunAuditQueryService` accepts an optional `audit_logger` callback and emits sanitized query/detail events containing operation name, filter keys, sort information, limit, offset, selected safe ids, generated time, degraded state, and safe error category.

This is the selected audit logging pattern for service-level events. A route-level audit wrapper is still missing.

## 17. Existing observability patterns found

Rust uses `TraceLayer::new_for_http()` with sanitized URIs through `sanitize_uri_for_logs`. Python exposes public-safe runtime payload sanitization through `sanitize_public_runtime_payload`.

`backend/rust/src/observability.rs` exposes protected observability routes and bounded trace limits, but its error payloads can include operational messages from the CLI. The future audit route should use categorical metrics and sanitized events, not raw CLI-style error strings.

## 18. Existing fail-closed patterns found

The dry-run audit internal endpoint functions return 404 with `internal_route_disabled` when `internal_enabled=False`, before service invocation.

`require_supabase_auth` returns 401 on missing, malformed, expired, or invalid tokens. Observability stream tickets reject missing, unknown, expired, reused, or wrong-scope tickets.

## 19. Existing feature flag/internal flag patterns found

The dry-run audit contract has an explicit `internal_enabled` parameter defaulting to `False`. Observability stream tickets use `OMNI_OBSERVABILITY_STREAM_TICKET_STORE_MODE` and reject unsupported shared modes.

The selected future route switch should be a Rust-side explicit route registration or enablement flag, while preserving `internal_enabled=False` as the Python handler fail-closed guard. The flag is not authentication.

## 20. Existing rollback/disablement patterns found

The existing rollback pattern is configuration-based fail-closed disablement: unsupported observability ticket store modes fail closed, and dry-run audit endpoints remain unavailable unless `internal_enabled=True`.

The selected future rollback path is to disable the route switch and verify that requests are absent or denied before the Python service is invoked.

## 21. Candidate route registration location

The candidate registration location is `backend/rust/src/main.rs`, in a new protected router merged near `protected_operator` or `protected_control`.

The current no-auth `/internal/*` route group is not selected for this sensitive API.

## 22. Candidate middleware/control location

Authentication should reuse `require_supabase_auth` from `backend/rust/src/observability_auth.rs`. A future authorization control should live in Rust near auth middleware or in a new dedicated route-control module.

Route-level rate and size controls should be applied before calling any Python contract handler.

## 23. Candidate test locations

Candidate tests:

- Rust route/auth tests near `backend/rust/src/observability_auth.rs` and `backend/rust/src/run_control.rs`.
- Python contract tests in `backend/python/tests/memory/test_historical_dry_run_audit_internal_api.py`.
- Python service/query tests in `backend/python/tests/memory/test_historical_dry_run_audit_query_service.py` and `test_historical_dry_run_audit_query_contracts.py`.

## 24. Selected route registration approach

Selected approach: use a future Rust Axum protected router, not the current no-auth `/internal/*` group. The protected router should be merged into the app only behind an explicit route registration switch and must apply auth, authorization, identity, rate, size, and query controls before calling the Python contract boundary.

No route is registered by this PR.

## 25. Selected authentication approach

Selected authentication approach: reuse Supabase JWT validation through `require_supabase_auth`.

Missing, malformed, expired, invalid, or unverifiable Bearer tokens must fail closed before query parsing or service invocation.

## 26. Selected authorization approach

Selected authorization approach: do not rely on authentication alone. A future branch must add or select an explicit readonly historical-audit authorization capability/scope before route registration.

Because no existing route-level HTTP authorization mechanism was found, this remains a missing control and route registration remains blocked.

## 27. Selected internal caller identity approach

Selected caller identity approach: use the authenticated Supabase `sub` inserted into Axum request extensions as the internal caller id, then bind rate limits, authorization decisions, audit logs, and observability to that identity.

Requests without a stable `sub` must fail closed.

## 28. Selected route-level rate limit approach

Selected rate limit approach: implement a route-level per-caller bucket before service invocation, modeled on the existing `RateLimiter` behavior but placed at the Rust route boundary or equivalent shared control.

Rate-limited requests must not invoke `HistoricalDryRunAuditQueryService`.

## 29. Selected route-level size limit approach

Selected size limit approach: preserve Python contract limits and add route-bound checks for query count, query string size, individual parameter size, path parameter length, and response page size before service invocation.

Oversized requests must return sanitized categorical errors.

## 30. Selected query complexity limit approach

Selected query complexity approach: reuse `DryRunAuditQueryRequest` allowlists and enforce additional route-level bounds for filter count, allowed sort fields, allowed date ranges, pagination, and unsupported parameter rejection.

Raw query expressions, SQL, JSONL selectors, SQLite selectors, and storage paths remain blocked.

## 31. Selected audit logging approach

Selected audit logging approach: use `HistoricalDryRunAuditQueryService` audit callback for service events and add a future route-level sanitized audit event for auth/authz/rate/size/query decisions.

The route audit event should include route id, safe caller id, request id, decision, status class, filter key summary, page size bucket, and outcome category.

## 32. Selected observability approach

Selected observability approach: use Rust tracing with `sanitize_uri_for_logs` and add categorical counters or trace fields for route attempts, denials, validation failures, rate limits, size limits, degraded responses, and latency buckets.

Observability must not include response bodies, raw evidence, prompts, provider payloads, headers, cookies, secrets, stack traces, stdout/stderr, command args, file contents, or `.env` content.

## 33. Selected rollback/disablement approach

Selected rollback/disablement approach: an explicit disabled-by-default route registration switch plus preservation of the Python `internal_enabled=False` guard.

Rollback must disable route callability without storage migration, retention changes, provider changes, or runtime execution changes.

## 34. Handler invocation boundary

Future route code must run authentication, authorization, caller identity extraction, route switch evaluation, rate limiting, size limiting, query validation, and logging safety checks before invoking the Python contract handler.

The handler must remain readonly.

## 35. HistoricalDryRunAuditQueryService-only delegation rule

Future route code must delegate only to the existing contract handler/service path that reaches `HistoricalDryRunAuditQueryService`.

No route code may bypass this service or directly call `MemoryFacade`.

## 36. No direct MemoryFacade rule

Direct API-to-`MemoryFacade` access remains blocked. If the service contract lacks a needed query, the future implementation must stop and propose a separate service-contract change.

## 37. No raw storage rule

Raw JSONL, raw SQLite rows, raw storage files, adapter internals, and filesystem paths must not be read or exposed by route code.

The route must consume only sanitized service responses.

## 38. No SQL construction rule

Route code must not construct SQL from request input, accept SQL, log SQL, or expose SQL.

Any database-backed behavior must stay behind existing safe query abstractions.

## 39. Request validation preparation

Future implementation should convert Axum query parameters into the existing Python contract shape and reject unsupported fields before service invocation.

Validation must be structured and deterministic, not ad hoc string pass-through.

## 40. Path validation preparation

Path parameters such as `plan_id` must use the existing `safe_audit_id` semantics: bounded, sanitized, no path traversal, no slashes, and no query/control metacharacters.

Invalid path values must fail closed before service invocation.

## 41. Filter/sort allowlist preparation

Future route code must preserve `ALLOWED_FILTERS`, `ALLOWED_SORT_FIELDS`, and `ALLOWED_SORT_DIRECTIONS`.

Unknown filters and sorts must be rejected rather than ignored at the route boundary.

## 42. Pagination preparation

Future route code must preserve `DRY_RUN_AUDIT_DEFAULT_LIMIT`, `DRY_RUN_AUDIT_MAX_LIMIT`, and `DRY_RUN_AUDIT_MAX_OFFSET`, and must prevent repeated broad queries from becoming export behavior.

Pagination must remain bounded.

## 43. Error/degradation mapping preparation

Future route code must map disabled route, auth failure, authorization failure, rate limit, size limit, validation failure, service failure, invalid service response, and not-found states to sanitized categorical responses.

Raw exception text must not be returned.

## 44. Required advisory warnings preservation

Future route code must preserve `REQUIRED_AUDIT_QUERY_WARNINGS`, including warnings that results are readonly metadata, not approval, not execution input, and that copy/export remains disabled.

Warnings must remain advisory and safe.

## 45. Safe response envelope preparation

Future route responses must preserve the existing safe envelope: `items`, `page_info`, `applied_filters`, `warnings`, `degraded`, `generated_at`, and safe `error_category` when degraded.

Detail responses must not expose raw diagnostic or storage internals beyond already sanitized service fields.

## 46. Forbidden field denylist

Forbidden response fields and values include raw JSONL, raw SQLite rows, raw SQL, prompts, rewritten prompts, responses, provider payloads, tool outputs, secrets, headers, cookies, stack traces, stdout/stderr, command args, file contents, `.env` content, execution inputs, and raw storage paths.

Future tests must include representative denylisted payloads.

## 47. Forbidden logging denylist

Forbidden log content includes authorization headers, cookies, Bearer tokens, JWTs, secrets, API keys, raw prompts, provider payloads, tool outputs, raw evidence, stdout/stderr, command args, file contents, `.env` content, stack traces, raw JSONL, raw SQLite rows, raw SQL, and storage paths.

Use `sanitize_uri_for_logs` and safe categorical fields only.

## 48. Auth fail-closed test plan

Tests must prove missing, malformed, expired, invalid, and unverifiable Supabase JWTs return 401 and do not invoke query parsing, handler code, or service code.

Use Rust Axum route tests modeled on existing observability/control auth tests.

## 49. Unauthorized fail-closed test plan

Tests must prove authenticated callers without the future readonly historical-audit capability/scope are denied before service invocation.

Because this authorization mechanism is missing, these tests are also a blocker.

## 50. Internal-only boundary test plan

Tests must prove the route is absent from public routers and not mounted under the current no-auth `/internal/*` group.

Tests should verify the selected protected router is the only mounting path.

## 51. Rate limit test plan

Tests must prove per-caller route limits reject excessive requests and do not invoke `HistoricalDryRunAuditQueryService`.

Tests should verify safe logging and observability for rate-limited attempts.

## 52. Size limit test plan

Tests must prove excessive query parameter count, excessive query string length, excessive individual parameter length, excessive path id length, and excessive page sizes are rejected before service invocation.

Responses must be categorical and sanitized.

## 53. Query complexity test plan

Tests must prove unsupported filters, unsupported sorts, invalid date ranges, excessive ranges, arbitrary expressions, SQL-like inputs, JSONL selectors, SQLite selectors, and storage paths are rejected.

The service must not be invoked for rejected requests.

## 54. Service-only delegation test plan

Tests must prove the route calls only the Python contract/service path backed by `HistoricalDryRunAuditQueryService`.

Tests must also prove no direct `MemoryFacade`, raw storage, filesystem, or SQL helper access occurs.

## 55. No raw JSONL/SQLite/SQL exposure test plan

Tests must prove responses, errors, traces, and logs do not contain raw JSONL, raw SQLite rows, SQL strings, table names, storage paths, or adapter implementation details.

Reuse existing forbidden-field patterns from memory tests.

## 56. No runtime/provider/execution behavior test plan

Tests must prove the route cannot start dry runs, retry, replan, enqueue work, mutate sessions, rewrite prompts, call providers/models, or pass persisted evidence into execution inputs.

The route must stay read-only.

## 57. Rollback/disablement test plan

Tests must prove disabling the route switch makes requests absent or denied and prevents service invocation.

Tests must also verify the Python `internal_enabled=False` guard remains fail-closed.

## 58. Regression test matrix

Required matrix:

| Area | Required tests |
| --- | --- |
| Auth | Missing, malformed, expired, invalid, unverifiable JWTs fail closed. |
| Authorization | Authenticated but unauthorized caller fails closed. |
| Internal boundary | Route only mounted in selected protected context. |
| Rate limit | Excessive per-caller requests denied before service. |
| Size limit | Oversized query/path inputs denied before service. |
| Query complexity | Unsupported filters/sorts/ranges/selectors denied. |
| Delegation | Only `HistoricalDryRunAuditQueryService` path is used. |
| Exposure | No raw JSONL/SQLite/SQL/storage details in responses/logs. |
| Non-execution | No retry/replan/provider/runtime execution behavior. |
| Rollback | Disabled route absent or denied before service. |

## 59. Implementation readiness checklist

Implementation is not ready until:

1. Misael gives explicit approval.
2. Rust protected route location is approved.
3. Supabase JWT auth is confirmed for this route.
4. Route-specific authorization capability/scope is designed.
5. Caller identity handling is finalized.
6. Route-level rate limit control is selected.
7. Route-level size limit control is selected.
8. Query complexity controls are finalized.
9. Route audit logging is designed.
10. Observability fields are designed.
11. Rollback/disablement switch is selected.
12. Security review is planned.
13. Abuse review is planned.
14. Test matrix is approved.

## 60. Missing controls

Missing controls:

- Route-specific readonly historical-audit authorization capability/scope.
- Rust route-level rate-limit middleware/control.
- Rust route-level size-limit control.
- Rust route-level query complexity adapter.
- Route-level audit event schema.
- Route-level observability counters/fields.
- Explicit route registration switch name and ownership.
- Security review owner.
- Abuse review owner.

## 61. Security review checklist

Security review must cover auth, authorization, caller identity spoofing, internal-only mounting, route switch behavior, logging denylist, response denylist, service-only delegation, no raw storage access, no SQL construction, and non-execution guarantees.

The review must also verify no CI secrets, deploy configs, production settings, or billing settings are changed.

## 62. Abuse review checklist

Abuse review must cover enumeration, broad historical scraping, repeated pagination, sensitive evidence inference, filter probing, route discovery, rate-limit bypass, copy/export pressure, and unauthorized operational insight.

The review must require no public exposure, no Cockpit/detail drawer, and no copy/export.

## 63. Future implementation branch constraints

A future implementation branch must remain narrow: route registration and required controls only, after explicit approval. It must not modify provider routing, prompts, runtime execution, retention/cleanup, Cockpit/detail drawer, copy/export, storage adapters, or raw query behavior.

Any missing service capability must be handled as a separate contract change.

## 64. Explicit non-approval statement

This PR does not approve route registration implementation, route registration, route exposure, public exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL/SQLite/SQL access, direct API-to-`MemoryFacade` access, prompt rewrite, provider/model retry or replan execution, persisted evidence as execution input, or autonomous execution.

Only documentation/preparation and mechanism selection are approved.

## 65. Open risks

Open risks include mistaking `/internal/*` for a secure boundary, treating `internal_enabled=True` as auth, missing route-level authorization, relying on process-local rate limits in multi-instance deployments, logging sensitive query content, enabling enumeration through pagination, and accidentally adding frontend/export behavior.

These risks keep route registration blocked.

## 66. Open questions

Open questions:

1. What exact route-specific authorization capability/scope should be introduced?
2. Should the future path use `/api/v1/operator/audit/dry-run` or another protected internal namespace?
3. What route switch name and owning environment should be used?
4. Should rate limiting be Rust-native or delegated to a shared service?
5. What concrete security and abuse reviewers should approve the implementation branch?
6. How should Rust call the Python contract handler without expanding runtime execution behavior?

## 67. Go/no-go table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation/preparation | Go | Approved for this PR. |
| Selecting existing auth/authz mechanisms | Conditional go | Auth selected; authz missing and must be designed. |
| Selecting route registration approach | Go | Protected Rust Axum router selected for future use. |
| Selecting logging/observability approach | Go | Safe service audit callback plus sanitized Rust tracing selected. |
| Selecting rollback/disablement approach | Go | Disabled-by-default route switch plus Python guard selected. |
| Future implementation branch | Conditional go | Requires explicit Misael approval and missing controls. |
| Route registration implementation | No-go | Not approved in this PR. |
| Internal route registration | No-go | Remains blocked. |
| Internal route exposure | No-go | Remains blocked. |
| Public route exposure | No-go | Remains blocked. |
| Cockpit/detail drawer consumption | No-go | Remains blocked. |
| Copy/export | No-go | Remains blocked. |
| Retention/cleanup | No-go | Remains blocked. |
| Raw JSONL read | No-go | Remains blocked. |
| Raw SQLite row read | No-go | Remains blocked. |
| Raw SQL query/filter | No-go | Remains blocked. |
| Direct API-to-MemoryFacade | No-go | Remains blocked. |
| Prompt rewrite | No-go | Remains blocked. |
| Provider/model retry execution | No-go | Remains blocked. |
| Provider/model replan execution | No-go | Remains blocked. |
| Persisted evidence as execution input | No-go | Remains blocked. |
| Autonomous execution | No-go | Remains blocked. |

## 68. Final recommendation

Approve this PR for documentation/preparation only. The future route should use a protected Rust Axum router with Supabase JWT authentication, explicit route-specific authorization, Supabase `sub` caller identity, per-caller route limits, route/query size bounds, existing dry-run audit query allowlists, service audit callbacks, sanitized Rust tracing, and disabled-by-default rollback.

Do not proceed to route registration implementation until Misael explicitly approves a future branch and the missing authorization, rate/size/query controls, route audit schema, observability fields, route switch, security review, abuse review, and regression test matrix are ready.
