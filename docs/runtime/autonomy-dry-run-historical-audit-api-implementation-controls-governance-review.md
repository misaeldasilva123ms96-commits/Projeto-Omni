# Dry-Run Historical Audit API Implementation Controls Governance Review

## 1 Executive summary
This governance review approves PR #487 for documentation and dormant implementation controls only. The reviewed controls are fail-closed, disabled by default, and unregistered. Route registration, endpoint exposure, public exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, direct raw storage access, prompt rewrite, provider/model execution, persisted evidence as execution input, autonomous execution, and self-repair remain blocked.

## 2 Scope
Scope is limited to reviewing the dormant historical dry-run audit route controls added in PR #487 and documenting the resulting governance posture. This review covers authorization helper shape, caller identity extraction, route switch behavior, bounded config, query complexity guards, safe audit and observability schemas, tests, and remaining blockers.

## 3 Non-goals
This review does not implement or modify route registration, endpoint exposure, handler wiring, MemoryFacade behavior, HistoricalDryRunAuditQueryService behavior, storage behavior, runtime behavior, provider routing, prompts, frontend/Cockpit UI, copy/export, retention/cleanup, deploy settings, CI secrets, production settings, or billing-related settings.

## 4 Reviewed materials
- `backend/python/brain/memory/historical_audit_route_controls.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_route_controls.py`
- `docs/runtime/autonomy-dry-run-historical-audit-api-implementation-controls.md`
- `backend/python/brain/memory/historical_audit_internal_api.py`
- `backend/python/brain/memory/historical_audit_query_models.py`
- `backend/python/brain/memory/historical_audit_query_service.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_internal_api.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_query_contracts.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_query_service.py`

## 5 Current implementation state
The current implementation contains dormant Python route controls and tests. The controls define pre-route decisions but are not wired into any router or endpoint. Existing internal endpoint helpers remain disabled by default through `internal_enabled=False`, and the Rust router does not register `/internal/audit/dry-run`.

## 6 Current governance state
Governance approves the PR #487 control surface only as dormant preparatory infrastructure. Governance does not approve route registration, route exposure, public exposure, Cockpit consumption, copy/export, retention/cleanup, runtime execution, provider/model activity, or any use of audit evidence as execution input.

## 7 Governance decision summary
Approved: documentation, dormant implementation controls, unregistered/unexposed status, disabled-by-default switch, and fail-closed control decisions. Conditionally approved: future route registration design review only. Not approved: route registration implementation, endpoint exposure, public exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw storage/SQL access, direct API-to-MemoryFacade access, prompt rewrite, provider/model retry or replan execution, persisted evidence as execution input, autonomous execution, and self-repair.

## 8 Implementation controls safety review
The implementation controls are safety-positive because they add a pre-route authorization and validation layer without enabling a route. They reuse existing historical audit bounds and sanitizers where possible, and they default to denied or disabled states when input, caller, config, or capability data is missing or invalid.

## 9 Dormant control module review
`historical_audit_route_controls.py` is explicitly documented as dormant and intentionally not imported by any router. That module may be referenced by future route-registration work, but this review does not approve that integration yet.

## 10 Readonly authorization model review
The readonly authorization helper requires an accepted caller identity, an enabled route switch, and the exact `historical_audit:read` capability. The model is approved for dormant control use. It is not approved as a complete production auth/authz integration until a future route-registration design review validates caller capability source, propagation, and enforcement.

## 11 Supabase-sub caller identity review
Caller identity extraction accepts only a safe Supabase `sub` string and rejects empty, non-string, path-like, token-like, or otherwise unsafe identities. This is conditionally acceptable as a caller identity helper. Future route registration must verify that the identity is sourced only from authenticated middleware and cannot be supplied by request input.

## 12 Disabled-by-default route switch review
The route switch defaults disabled through `HISTORICAL_AUDIT_ROUTE_SWITCH_DEFAULT = False`. Disabled state returns a fail-closed decision before readonly capability authorization can pass. This is approved and must remain the rollback posture until a separate reviewed route-registration branch exists.

## 13 Rate limit config review
The config includes bounded rate limit fields with deterministic clamping. This is approved as configuration modeling only. It is not approved as live rate limiter behavior until a future branch wires it to an actual route-level limiter and proves enforcement.

## 14 Size limit config review
The config includes bounded query parameter count, parameter length, plan id length, page size, and offset limits. This is approved as pre-route control modeling and aligns with existing internal API bounds.

## 15 Query complexity guard review
The query complexity guard rejects unsupported parameters, excessive parameter count, excessive filters, oversized values, invalid pagination, unsupported sort fields, unsupported sort directions, and invalid detail plan ids. This is approved for dormant use. Future route registration must prove the guard executes before service access.

## 16 Safe audit event schema review
The safe audit event builder emits route id, operation, caller id/source, decision result, status, query keys, page size, logging flag, warnings, and timestamp only. It does not emit request bodies, raw storage data, prompts, provider payloads, tool outputs, secrets, headers, cookies, stacks, stdout, stderr, command args, file contents, raw exceptions, or raw reprs.

## 17 Safe observability field schema review
The safe observability field builder emits route id, operation, decision result, status, route enabled state, rate limit bounds, observability flag, and bounded latency only. This schema is approved for dormant controls and remains insufficient by itself to approve endpoint exposure.

## 18 Forbidden field exclusion review
Tests assert forbidden markers are absent from audit and observability output. This includes secrets, tokens, raw JSONL, SQLite, raw SQL, MemoryFacade markers, prompts, provider payloads, tool output, stdout, stderr, stacks, command args, file contents, raw exceptions, raw reprs, provider calls, retry execution, and replan execution.

## 19 Forbidden logging/data denylist review
The route controls include a denylist for route-level sanitization, and existing query models include a broader historical audit forbidden-marker sanitizer. This layered posture is approved for dormant controls. Future route registration must preserve these denylist checks and add endpoint-level logging review.

## 20 Fail-closed behavior review
Fail-closed behavior is covered for missing caller identity, invalid caller identity, disabled route switch, absent capability, invalid query params, excessive query params, excessive filters, oversized values, unsupported sort, invalid pagination, and invalid detail plan ids. This is approved as a prerequisite control pattern.

## 21 Capability check review
The capability check only accepts `historical_audit:read` as a string, collection member, or explicitly true mapping entry. That is acceptable as dormant helper behavior. Future registration must define where capabilities originate and how they are protected from request tampering.

## 22 No route registration review
No route was registered. Search evidence shows `/internal/audit/dry-run` appears only as existing Python internal endpoint constants, not as a Rust route registration.

## 23 No endpoint exposure review
No endpoint was exposed. Existing Python internal endpoint helpers remain functions, and the PR #487 control module does not expose HTTP access.

## 24 No Rust router wiring review
`backend/rust/src/main.rs` does not include `/internal/audit/dry-run` or `historical_audit_route_controls`. Existing route registrations remain limited to previously registered health, chat, telemetry, internal runtime, observability, operator, control, and settings routes.

## 25 No handler wiring review
No handler was wired to a router. Existing historical audit internal endpoint helpers still require explicit direct function invocation and remain disabled by default unless `internal_enabled=True` is supplied by future reviewed code.

## 26 No Cockpit/detail drawer review
No Cockpit UI or detail drawer consumption was added. Cockpit/detail drawer consumption remains not approved.

## 27 No copy/export review
No copy or export capability was added. Existing warnings continue to state that copy/export remains disabled. Copy/export remains not approved.

## 28 No retention/cleanup review
No retention or cleanup behavior was added. Retention/cleanup remains not approved and requires a separate policy and implementation review.

## 29 No runtime/provider/prompt/execution review
No runtime, provider, prompt, retry, replan, autonomous execution, or self-repair behavior was changed. The controls produce decisions and safe telemetry fields only.

## 30 No direct MemoryFacade access review
The new route controls do not call MemoryFacade. Existing `HistoricalDryRunAuditQueryService` remains the service boundary that delegates to MemoryFacade, and no direct API-to-MemoryFacade path was added.

## 31 No raw JSONL/SQLite/SQL exposure review
The controls do not read raw JSONL, SQLite rows, or SQL. The safe schemas and tests reject raw storage and SQL markers. Raw JSONL read, raw SQLite row read, and raw SQL query/filter remain not approved.

## 32 No prompt/provider/tool output exposure review
The controls do not expose prompts, provider payloads, provider responses, or tool outputs. Tests explicitly assert those markers are absent from safe audit and observability payloads.

## 33 Test coverage review
The reviewed test set is focused and appropriate for dormant controls. It covers fail-closed behavior, bounded configuration, query complexity rejection, safe schemas, no route registration, no raw exposure, no direct MemoryFacade exposure, and no runtime/provider execution trigger.

## 34 New route-controls test review
`test_historical_dry_run_audit_route_controls.py` adds 17 tests covering the new dormant controls. The tests are approved as governance evidence for dormant controls only, not as approval for route registration.

## 35 Existing internal API test review
Existing internal API tests remain relevant because `historical_audit_internal_api.py` still controls the disabled internal endpoint helper behavior, safe parsing, degraded responses, and service call boundary.

## 36 Existing query-service test review
Existing query-service tests remain relevant because `HistoricalDryRunAuditQueryService` is still the readonly service boundary and continues to sanitize invalid requests, degraded responses, safe categories, and audit event fields.

## 37 Historical audit memory discovery review
Historical audit memory discovery across `test_historical_dry_run_audit*.py` is relevant because it exercises the contract, internal API, query service, and route control test files together. PR #487 reported this discovery suite as passing.

## 38 Runtime autonomy discovery review
Runtime autonomy discovery is relevant because it checks that the control additions did not trigger autonomous runtime, provider, retry, replan, or self-repair behavior. PR #487 reported runtime autonomy discovery as passing.

## 39 Validation evidence review
PR #487 reported passing validation for `git diff --check`, Python compilation of changed files, 17 route-control tests, 14 internal API tests, 18 query-service tests, 62 historical audit memory discovery tests, and 341 runtime autonomy discovery tests. This docs-only governance review requires only `git diff --check` and `git status --short`.

## 40 Remaining blockers before route registration
Route registration remains blocked pending a separate route-registration design review, authenticated middleware source review, capability source review, rate limiter enforcement design, request size enforcement design, query complexity pre-service enforcement proof, safe logging review, safe observability review, abuse review, security review, and endpoint-level validation plan.

## 41 Required controls before route registration
Before route registration, governance requires proof that Supabase authentication supplies caller identity, capabilities cannot be request-forged, the disabled switch remains the default rollback state, rate/size/query controls run before service access, audit/observability payloads remain safe, and no raw storage or execution behavior can be reached.

## 42 Required controls before route exposure
Before internal route exposure, governance requires final auth/authz enforcement, route-level rate limiting, request size enforcement, query complexity enforcement, safe response schemas, safe error schemas, safe logging, safe observability, abuse review, and rollback testing.

## 43 Required controls before public exposure
Public exposure is not approved. Any future public exposure would require a separate product/security decision, a public threat model, stronger abuse controls, privacy review, public API contract review, and explicit governance approval.

## 44 Required controls before Cockpit/detail drawer
Cockpit/detail drawer consumption remains blocked until endpoint exposure is approved, frontend redaction is designed, detail payload limits are reviewed, user-facing warnings are preserved, and no execution semantics can be inferred from persisted evidence.

## 45 Required controls before copy/export
Copy/export remains blocked until explicit export policy, redaction policy, audit trails, user permissions, rate limits, payload limits, and retention implications are reviewed.

## 46 Security review checklist
- Authenticated caller identity comes only from trusted middleware.
- Capability source is server-side and cannot be request-forged.
- Route switch defaults disabled and supports rollback.
- Rate, size, and query complexity controls execute before service access.
- Safe audit and observability schemas exclude forbidden fields.
- Raw JSONL, SQLite rows, and SQL are inaccessible.
- Prompts, provider payloads, provider responses, and tool outputs are inaccessible.
- Errors are degraded and sanitized.
- No provider/model/retry/replan/self-repair path is reachable.

## 47 Abuse review checklist
- Excessive filters are rejected.
- Excessive pagination is rejected.
- Oversized parameters are rejected.
- Unsupported sort fields and directions are rejected.
- Detail plan ids are sanitized and bounded.
- Rate limit configuration is bounded.
- Route disabled state prevents probing through the future route.
- Safe telemetry avoids leaking sensitive operational data.

## 48 Rollback/disablement review
Rollback posture is acceptable: the route switch defaults disabled, disabled state fails closed, and no route is registered. Until a future branch registers a route, rollback is also structural because no endpoint exists.

## 49 Open risks
- Capability source and propagation are not yet implemented.
- Rate limiter behavior is modeled but not wired to a route.
- Request size enforcement is modeled but not wired to HTTP extraction.
- Query complexity enforcement has not yet been proven in a live route path.
- Audit and observability schemas are safe helpers but not integrated.
- Future route registration could accidentally bypass the dormant controls unless explicitly tested.

## 50 Open questions
- Which server-side capability authority will issue `historical_audit:read`?
- Will the future route live under protected Supabase middleware or a separate internal-only layer?
- What exact route-level rate limit should be enforced for production?
- What operational audit sink should receive safe route access events?
- What observability dimensions are necessary without increasing data exposure?

## 51 Go/no-go table
| Area | Decision | Governance rationale |
| --- | --- | --- |
| Documentation | Go | Approved for documentation. |
| Dormant implementation controls | Go | Approved as unregistered controls. |
| Readonly authorization helper | Go | Approved as dormant helper only. |
| Caller identity helper | Go | Approved as dormant helper only. |
| Disabled route switch | Go | Approved; defaults disabled/fail-closed. |
| Rate/size/query controls | Go | Approved as dormant controls. |
| Safe audit schema | Go | Approved as dormant safe schema. |
| Safe observability schema | Go | Approved as dormant safe schema. |
| Route registration design review | Conditional go | Future design review may proceed. |
| Route registration implementation | No-go | Not approved yet. |
| Internal route registration | No-go | Not approved yet. |
| Internal endpoint exposure | No-go | Not approved yet. |
| Public endpoint exposure | No-go | Not approved. |
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

## 52 Final recommendation
Approve PR #487's outcome for documentation and dormant implementation controls only. Keep route registration and endpoint exposure blocked. The recommended next branch is a route-registration design review branch that remains documentation-only until it proves the exact auth, capability, rate, size, query, logging, observability, and rollback controls required before any handler is wired to a router.
