# Dry-Run Historical Audit API Route Registration Design Review

## 1 Executive summary
This design review approves documentation and route registration design review only. It reviews how a future internal historical dry-run audit route could be registered safely using the dormant controls from PR #487, but it does not register a route, expose an endpoint, or wire a handler. Candidate routes are design-only: `GET /protected/internal/audit/dry-run` and `GET /protected/internal/audit/dry-run/{plan_id}`.

## 2 Scope
Scope is limited to future route registration design. The review covers candidate protected Rust Axum paths, rejection of the current no-auth `/internal/*` group, Supabase JWT authentication, readonly historical-audit authorization, Supabase `sub` caller identity, dormant control integration, validation, safe response envelopes, safe audit and observability fields, rollback, and required future tests.

## 3 Non-goals
This PR does not register API routes, expose internal or public routes, wire handlers into a router, modify endpoint handlers, change dormant controls, add auth/authz behavior, add rate limiter behavior, modify MemoryFacade, modify HistoricalDryRunAuditQueryService behavior, change storage, change runtime/provider/prompt/execution behavior, add Cockpit/detail drawer UI, add copy/export, or add retention/cleanup.

## 4 Reviewed materials
- `backend/python/brain/memory/historical_audit_route_controls.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_route_controls.py`
- `backend/python/brain/memory/historical_audit_internal_api.py`
- `backend/python/brain/memory/historical_audit_query_models.py`
- `backend/python/brain/memory/historical_audit_query_service.py`
- `docs/runtime/autonomy-dry-run-historical-audit-api-implementation-controls.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-implementation-controls-governance-review.md`
- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs`
- `backend/python/brain/runtime/rate_limiter.py`
- `backend/python/brain/runtime/observability/public_runtime_payload.py`

## 5 Current implementation state
Dormant controls exist and remain unregistered. The route switch defaults disabled and fail-closed. The current Rust router has protected groups using `require_supabase_auth`, a no-auth `/internal/*` group, and no `/internal/audit/dry-run` registration. The historical audit internal API helpers remain Python functions, disabled by default through `internal_enabled=False`.

## 6 Current governance state
Route registration remains blocked. Endpoint exposure remains blocked. Public exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL/SQLite/SQL access, direct API-to-MemoryFacade access, prompt rewrite, provider/model retry or replan execution, persisted evidence as execution input, autonomous execution, and self-repair are not approved.

## 7 Design review decision summary
Approved for documentation and route registration design review. Approved to continue using dormant controls as route preconditions. Approved that any future route must use a protected Rust Axum path and must not use the no-auth `/internal/*` group. Conditionally approved for a future narrow route registration implementation branch only after explicit Misael approval. Not approved for route registration or endpoint exposure in this PR.

## 8 Route registration design review
Future route registration should add a new protected Rust Axum route group, apply Supabase JWT middleware, extract authenticated caller identity from middleware-owned request extensions, enforce route-specific readonly historical-audit authorization, validate request complexity before service access, call the historical audit service boundary only, and return safe envelopes with required advisory warnings.

## 9 Candidate route paths
Candidate design-only routes are `GET /protected/internal/audit/dry-run` for list queries and `GET /protected/internal/audit/dry-run/{plan_id}` for detail lookup. These names are not registered in this PR and must remain candidates until a future approved implementation branch.

## 10 Protected Rust Axum route requirement
Future registration must use a protected Rust Axum route path with Supabase JWT middleware. It must follow the protected-router pattern currently used for observability, operator, control, and settings routes.

## 11 Rejection of no-auth /internal/* route group
The future route must not use the current `/internal/*` group because that group is explicitly documented in `backend/rust/src/main.rs` as internal with no auth middleware. The existing Python `internal_enabled` flag is not authentication and must not be treated as an exposure control.

## 12 Supabase JWT authentication review
Existing Rust middleware validates Supabase JWTs, rejects missing or invalid bearer tokens, and inserts `claims.sub` into request extensions when present. Future route registration must require this middleware and must fail closed when no authenticated `sub` is available.

## 13 Route-specific readonly authorization review
Future route registration must enforce `historical_audit:read` through the dormant readonly authorization helper or an equivalent reviewed server-side capability check. Authentication alone is insufficient.

## 14 Supabase sub caller identity review
The future route must derive caller identity only from the authenticated Supabase `sub` placed into request extensions by trusted middleware. It must not accept caller id, caller source, user id, or capability claims from query params, path params, request bodies, or headers outside the auth middleware.

## 15 Dormant route-control module integration review
The future handler should call dormant route controls in this order: route enabled switch, caller extraction, readonly authorization, list/detail query complexity validation, safe audit event construction, safe observability field construction, then service-only delegation. This PR does not perform that integration.

## 16 Disabled-by-default switch review
The route switch must default disabled. A disabled switch must return a fail-closed response and must not call the historical audit internal API, HistoricalDryRunAuditQueryService, MemoryFacade, storage, provider, runtime, retry, or replan logic.

## 17 Route enabled switch review
Future enablement must be explicit, reviewed, environment-controlled or config-controlled, and reversible. Enabling a route must not also approve public exposure, Cockpit consumption, copy/export, retention/cleanup, or execution behavior.

## 18 Rate limit control review
The dormant config models bounded rate limits. Future route registration must wire a route-level rate limiter before service access and add tests proving deterministic denial after the configured threshold. This PR does not add live rate limiter behavior.

## 19 Size limit control review
The future route must enforce query parameter count, query parameter length, plan id length, page size, and offset bounds before constructing service requests. Oversized requests should fail closed with sanitized degraded responses.

## 20 Query complexity control review
Future list and detail handlers must call the dormant complexity guards before service access. Excessive filters, unsupported query params, oversized values, invalid pagination, unsupported sort fields, unsupported sort directions, and invalid detail plan ids must be rejected.

## 21 Request validation review
Future request validation must accept only query params in the existing historical audit allowlists, must ignore or reject unsupported input, and must never parse request bodies for this read-only route. Request validation failures must not leak raw input.

## 22 Path validation review
The future detail route must validate `{plan_id}` using the dormant detail complexity guard and the existing safe audit id rules. Path traversal, query metacharacters, path separators, token-like strings, and oversized identifiers must fail closed.

## 23 Filter/sort allowlist review
Future list route filtering and sorting must preserve `ALLOWED_FILTERS`, `ALLOWED_SORT_FIELDS`, and `ALLOWED_SORT_DIRECTIONS`. It must not add ad hoc filters, raw SQL filters, storage-specific filters, or provider/prompt/tool filters.

## 24 Pagination review
Future pagination must preserve bounded `limit` and `offset`, default to safe values, and reject values outside configured bounds. Pagination must not scan arbitrary storage directly from the route.

## 25 Error/degradation mapping review
Future route errors must map to safe degraded categories such as unauthorized, forbidden, route disabled, invalid request, payload too large, rate limited, not found, query failed, and invalid service response. Raw exceptions, stack traces, stdout/stderr, command args, file contents, and raw reprs must not appear in responses or logs.

## 26 Safe response envelope review
Future responses must use safe envelopes from the existing internal API/query model patterns: list responses include sanitized items, page info, applied filters, warnings, degraded state, and generated time; detail responses include sanitized detail, warnings, degraded state, and generated time.

## 27 Required advisory warnings review
Future responses must preserve required advisory warnings that results are readonly audit metadata, not approval, not execution input, that would_retry/would_replan are not execution, scores are not permission, suggested strategies are not instructions, copy/export remains disabled, and Omni remains advisory-only.

## 28 Safe audit event review
Future route access logging must use the safe route audit event schema only. It may include route id, operation name, caller id/source, decision, status, query keys, page size, safe logging flag, warnings, and timestamp. It must not include raw request bodies, raw storage data, prompts, provider payloads, tool outputs, secrets, headers, cookies, stacks, stdout/stderr, command args, file contents, raw exceptions, or raw reprs.

## 29 Safe observability field review
Future observability fields must use the safe route observability schema only: route id, operation name, decision, status, route enabled state, bounded rate-limit values, safe observability flag, and bounded latency. They must not include raw runtime payloads, provider data, prompts, tool outputs, secrets, headers, cookies, stacks, stdout/stderr, command args, file contents, or raw exceptions.

## 30 Forbidden field denylist review
Future route implementation must preserve denylist coverage for authorization, bearer tokens, cookies, secrets, passwords, tokens, API keys, JWTs, raw JSONL, SQLite, raw SQL, MemoryFacade markers, prompts, provider payloads, tool output, stdout, stderr, traceback, stack, command args, file contents, `.env`, raw exceptions, raw reprs, retry execution, replan execution, and provider calls.

## 31 Forbidden logging/data denylist review
Future logging must use sanitized URI logging and safe audit/observability events. It must redact token-like query values and must not emit request headers, cookies, bearer tokens, raw query payloads, storage rows, SQL, prompt/provider/tool payloads, or exception internals.

## 32 Handler invocation boundary review
Future handlers must run auth/authz, route switch, rate limit, size checks, and query complexity checks before invoking the historical audit internal endpoint/service boundary. A failed control decision must stop handler execution.

## 33 HistoricalDryRunAuditQueryService-only delegation review
Future route handlers must delegate through the historical audit internal endpoint contract and `HistoricalDryRunAuditQueryService`. They must not create alternate storage readers, bypass safe query models, or use audit evidence as instructions.

## 34 No direct MemoryFacade review
Direct API-to-MemoryFacade access remains not approved. MemoryFacade must remain behind `HistoricalDryRunAuditQueryService`, and future route tests must prove handlers do not call MemoryFacade directly.

## 35 No raw JSONL/SQLite/SQL review
Future routes must not read raw JSONL, raw SQLite rows, or raw SQL. They must not construct SQL from request input, and they must not expose storage implementation details beyond safe metadata fields already present in sanitized audit records.

## 36 No prompt/provider/tool output review
Future routes must not expose prompts, responses, provider payloads, provider responses, tool outputs, tool raw results, or provider/tool diagnostic details. The endpoint remains audit metadata only.

## 37 No runtime/provider/prompt/execution review
Future route registration must not change runtime behavior, provider routing, prompts, retry, replan, autonomous execution, or self-repair. Persisted evidence must remain advisory and must not become execution input.

## 38 No Cockpit/detail drawer review
Cockpit/detail drawer consumption is not approved. No frontend consumer should be added until endpoint exposure is separately approved and frontend redaction, warnings, and UX boundaries are reviewed.

## 39 No copy/export review
Copy/export is not approved. Future route registration must preserve warnings that copy/export remains disabled and must not add export-friendly raw payloads.

## 40 No retention/cleanup review
Retention/cleanup is excluded from this design review. Any cleanup policy or implementation requires a separate branch with storage, audit, and governance review.

## 41 Rollback/disablement design review
Rollback requires the route switch to default disabled, fail closed when disabled, and be reversible without code changes where possible. A route disabled response must occur before service access and must generate only safe audit/observability fields.

## 42 Security review checklist
- Protected Rust Axum route, not no-auth `/internal/*`.
- Supabase JWT required.
- Caller identity from authenticated `sub` only.
- Server-side `historical_audit:read` capability required.
- Route switch defaults disabled.
- Rate, size, and query complexity controls run before service access.
- Safe response envelopes only.
- Safe audit and observability fields only.
- No direct MemoryFacade, raw storage, SQL, prompts, provider payloads, tool outputs, or execution paths.

## 43 Abuse review checklist
- Missing/invalid auth fails closed.
- Missing/invalid caller fails closed.
- Missing readonly capability fails closed.
- Disabled route fails closed.
- Rate limit excess fails closed.
- Oversized queries and path ids fail closed.
- Excessive filters and pagination fail closed.
- Unsupported sort and filters fail closed.
- Logs and telemetry remain bounded and sanitized.

## 44 Required tests before route registration
Before route registration, tests must prove auth is required, invalid JWT fails, missing Supabase `sub` fails, unauthorized caller fails, missing capability fails, disabled route fails, enabled route with capability reaches only the service boundary, no `/internal/*` registration exists for this API, and the candidate protected routes are behind Supabase middleware.

## 45 Required tests before endpoint exposure
Before endpoint exposure, tests must prove rate limiting, request size limits, query complexity rejection, path validation, filter/sort allowlists, pagination bounds, safe degraded errors, required advisory warnings, safe response envelopes, safe audit events, safe observability fields, and no direct MemoryFacade or raw storage access.

## 46 Required tests before public exposure
Public exposure is prohibited. If future governance reopens that question, tests would need public threat-model coverage, unauthenticated denial, abuse limits, privacy redaction, payload minimization, and public contract compatibility. This review does not approve that path.

## 47 Required tests before Cockpit consumption
Before Cockpit consumption, tests must prove frontend redaction, warning visibility, no execution affordances, no copy/export controls, no raw payload rendering, detail drawer payload bounds, empty/error/loading states, and no provider/prompt/tool leakage.

## 48 Required tests before copy/export
Copy/export is prohibited. Any future branch would need explicit permission tests, payload redaction tests, audit trail tests, rate/size tests, retention implications, and denial tests for raw storage or prompt/provider/tool data.

## 49 Observability monitoring requirements
Future route observability should track safe counts for allowed/denied decisions, disabled-route denials, auth failures, capability failures, rate-limit denials, validation denials, degraded service responses, and bounded latency. It must not include raw request values or sensitive payloads.

## 50 Audit logging requirements
Future route audit logging should record safe route access events with caller id/source, operation, decision, status, safe query key summary, page size, warnings, and generated time. Audit logging must fail closed or degrade safely without interrupting denial logic and must not leak forbidden fields.

## 51 Operational rollback requirements
Operations must be able to disable the route quickly through the route switch. Rollback must not require changing provider/runtime behavior, modifying prompts, altering storage, deleting evidence, or disabling unrelated protected routes.

## 52 Route registration implementation preconditions
Implementation requires explicit Misael approval, a narrow branch, protected Rust Axum routing, Supabase JWT middleware, server-side readonly capability source, route switch config, rate limiter integration, request size enforcement, query complexity enforcement, safe audit logging, safe observability, and focused tests.

## 53 Route exposure preconditions
Internal endpoint exposure requires all route registration preconditions plus validation of response envelopes, degraded errors, advisory warnings, observability, audit logging, operational rollback, abuse review, and security review. Endpoint exposure is not approved in this PR.

## 54 Public exposure prohibition
Public exposure is prohibited. The route is historical audit metadata for internal protected use only and must not be registered under public paths or public telemetry summary endpoints.

## 55 Cockpit/detail drawer prohibition
Cockpit/detail drawer consumption is prohibited in this PR and remains blocked after this design review. Future UI work requires a separate approved branch after endpoint exposure is approved.

## 56 Copy/export prohibition
Copy/export is prohibited. Future route design must preserve copy/export disabled warnings and must not add export-oriented response shapes.

## 57 Retention/cleanup exclusion
Retention/cleanup is excluded. Future route registration must not add cleanup workflows, mutate evidence, or change storage lifecycle policy.

## 58 Explicit non-approval statement
This PR does not approve route registration, endpoint exposure, public exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL/SQLite/SQL access, direct API-to-MemoryFacade access, prompt rewrite, provider/model retry execution, provider/model replan execution, persisted evidence as execution input, autonomous execution, or self-repair.

## 59 Open risks
- Future capability source is not yet implemented.
- Future protected route shape is not yet coded or tested.
- Rate limiter enforcement is not yet wired.
- Request size enforcement is not yet wired at HTTP extraction.
- Query complexity enforcement is not yet proven in a live handler path.
- Audit and observability helpers are not yet integrated.
- A future implementation could accidentally choose the no-auth `/internal/*` group unless tests block it.

## 60 Open questions
- What server-side authority will issue `historical_audit:read`?
- Should the protected path remain `/protected/internal/audit/dry-run` or align with an existing protected prefix?
- Where should route enabled config live?
- What exact rate limit should production use?
- Which audit sink should receive safe route access events?
- Which observability dashboard should monitor denied decisions and degraded responses?

## 61 Go/no-go table
| Area | Decision | Rationale |
| --- | --- | --- |
| Documentation | Go | Approved for docs-only design review. |
| Route registration design review | Go | Approved as design only. |
| Candidate protected route paths | Go | Approved as candidate names only. |
| Dormant controls as route preconditions | Go | Approved for future precondition design. |
| Future route registration implementation branch | Conditional go | Requires explicit Misael approval. |
| Route registration in this PR | No-go | Not approved and not implemented. |
| Endpoint exposure in this PR | No-go | Not approved and not implemented. |
| Internal endpoint exposure | No-go | Requires future approved branch. |
| Public endpoint exposure | No-go | Prohibited. |
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
| Self-repair | No-go | Not approved. |

## 62 Final recommendation
Approve this PR for documentation and route registration design review only. Keep all route registration and endpoint exposure blocked in this branch. The recommended next branch is a narrow route registration implementation preparation branch only after explicit Misael approval, with tests proving protected Rust Axum routing, Supabase JWT authentication, route-specific readonly authorization, dormant control enforcement, service-only delegation, safe envelopes, safe telemetry, and no no-auth `/internal/*` exposure.
