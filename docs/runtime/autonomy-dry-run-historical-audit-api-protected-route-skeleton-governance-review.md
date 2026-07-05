# Dry-Run Historical Audit API Protected Route Skeleton Governance Review

## 1 Executive summary

This governance review approves PR #512 for documentation and protected route skeleton only. The Rust Axum skeleton is isolated, protected by Supabase JWT middleware inside its own router builder, disabled by default, and not merged into the production app router.

The skeleton is not approved for production route wiring, route enablement, endpoint exposure beyond isolated skeleton tests, public exposure, Cockpit consumption, copy/export, retention/cleanup, raw storage access, direct API-to-MemoryFacade access, prompt/provider/runtime changes, retry or replan execution, persisted evidence as execution input, autonomous execution, or self-repair.

## 2 Scope

Scope is limited to reviewing the protected historical dry-run audit route skeleton added in PR #512 and documenting the resulting governance posture. The review covers skeleton isolation, protected candidate paths, `main.rs` module declaration, production router merge absence, Supabase JWT authentication, readonly authorization modeling, fail-closed guards, safe audit/observability envelopes, placeholder behavior, tests, and remaining blockers.

## 3 Non-goals

This review does not modify route code, wire a router, enable a route, expose an endpoint, add a server-side capability source, add cross-language delegation, change auth/authz behavior, modify MemoryFacade, modify HistoricalDryRunAuditQueryService behavior, change storage behavior, change runtime/provider/prompt/execution behavior, add Cockpit/detail drawer UI, add copy/export, add retention/cleanup, change CI/deploy settings, or alter secrets.

## 4 Reviewed materials

- `backend/rust/src/main.rs`
- `backend/rust/src/protected_historical_audit.rs`
- `docs/runtime/autonomy-dry-run-historical-audit-api-protected-route-skeleton.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-route-registration-design-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-implementation-controls.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-implementation-controls-governance-review.md`
- `backend/python/brain/memory/historical_audit_route_controls.py`
- `backend/python/brain/memory/historical_audit_internal_api.py`
- `backend/python/brain/memory/historical_audit_query_service.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_route_controls.py`

## 5 Current implementation state

PR #512 added `backend/rust/src/protected_historical_audit.rs`, declared the module in `backend/rust/src/main.rs`, and documented the skeleton. The module defines an isolated `protected_historical_audit_router(...)` builder with two candidate protected routes, route-local guards, safe envelope builders, and focused tests.

The production app router does not merge `protected_historical_audit_router(...)`. No public route, no no-auth `/internal/*` route, no Cockpit consumer, no copy/export feature, and no runtime/provider/prompt/execution path was added.

## 6 Current governance state

Governance approves the skeleton as an isolated protected route skeleton only. Route registration and endpoint exposure remain blocked. Server-side capability source design, cross-language delegation, production route wiring, route enablement, Cockpit consumption, copy/export, and retention/cleanup all require separate future review and explicit approval.

## 7 Governance decision summary

Approved: documentation, protected route skeleton, isolated skeleton status, production router unwired status, disabled/fail-closed default switch, protected-only candidate route paths, rejection of no-auth `/internal/*`, and blocked public exposure.

Conditionally approved: future capability-source design review only and future cross-language delegation design review only.

Not approved: production route wiring, route enablement, endpoint exposure beyond isolated skeleton tests, public exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL/SQLite/SQL access, direct API-to-MemoryFacade access, prompt rewrite, provider/model retry execution, provider/model replan execution, persisted evidence as execution input, autonomous execution, and self-repair.

## 8 Protected skeleton safety review

The skeleton is safety-positive because it adds a compiled and tested protected route shape without making it reachable in production. Its default config is disabled, authorization has no production caller source yet, successful guarded calls return only a degraded `501 service_delegation_unavailable` placeholder, and the response envelope is metadata-only.

## 9 Rust Axum skeleton review

The Rust module defines route constants, config, route state, guard decisions, validation helpers, envelope structs, and two GET handlers. The router builder applies `require_supabase_auth` and route-local extension state. The design follows Axum routing patterns but remains isolated from the production app router.

## 10 Candidate route path review

The candidate paths are:

- `GET /protected/internal/audit/dry-run`
- `GET /protected/internal/audit/dry-run/{plan_id}`

These paths are approved as protected-only skeleton candidate paths. They are not approved for production registration or endpoint exposure.

## 11 Production wiring review

Production wiring remains blocked. The production app router in `main.rs` merges existing protected observability, stream, operator, control, settings, and protected internal routers, but it does not merge the protected historical audit router.

## 12 main.rs module declaration review

`main.rs` declares `mod protected_historical_audit;` so the skeleton compiles and its tests can include source-level assertions. This declaration is approved because it does not register paths, expose endpoints, or change runtime behavior.

## 13 Router merge absence review

The production router does not call `protected_historical_audit_router(state...)`. PR #512 tests assert the production router source does not contain the candidate historical audit paths or a merge call for the skeleton router.

## 14 No public route exposure review

No public route was added. The candidate paths remain under `/protected/internal/...`, and no `/api/v1/public`, `/api/v1/status`, summary, or other public surface exposes historical dry-run audit data.

## 15 No no-auth /internal/* route review

No no-auth `/internal/audit/dry-run` route was added. The prior governance rejection of the no-auth `/internal/*` group remains intact, and PR #512 includes a test proving `/internal/audit/dry-run` is not served by the skeleton router.

## 16 Supabase JWT boundary review

The skeleton uses the existing Supabase JWT boundary through `require_supabase_auth`. Missing, malformed, expired, or invalid bearer tokens are denied by middleware before handler-owned authorization can succeed.

## 17 require_supabase_auth usage review

`protected_historical_audit_router(...)` applies `route_layer(from_fn_with_state(state, require_supabase_auth))`. This is approved for the skeleton because caller identity is sourced from trusted middleware extensions rather than query params, path params, bodies, cookies, or arbitrary request headers.

## 18 Capability constant review

The skeleton defines `historical_audit:read` as the route-specific readonly capability. The constant is approved for skeleton and test use. It is not sufficient for production until a server-side capability source and propagation model are reviewed.

## 19 Readonly authorization boundary review

Readonly authorization is represented by server-side skeleton/test config containing authorized caller ids. Authentication alone is insufficient: callers without authorization receive `missing_historical_audit_readonly_capability`. Production authorization remains blocked until the capability source is designed and reviewed.

## 20 Server-side capability source blocker

No production server-side capability source exists for `historical_audit:read`. A future branch must define the authority, data source, propagation path, tamper resistance, caching behavior if any, failure behavior, and tests before production wiring or route enablement can be considered.

## 21 Caller identity guard review

Caller identity is extracted from the Supabase `sub` extension added by authentication middleware. Missing or unsafe caller identity fails closed. The handler does not accept caller identity from user-controlled request fields.

## 22 Disabled-by-default switch review

`HistoricalAuditRouteConfig::default()` sets `route_enabled=false` and no authorized callers. A valid authenticated caller with configured authorization still receives `route_disabled` while the switch is off. This is the approved default and rollback posture.

## 23 Fail-closed order review

The skeleton fails closed before any placeholder response: missing caller, disabled route, missing readonly authorization, rate-limit excess, invalid list query, and invalid detail plan id each stop processing. No storage, runtime, provider, prompt, retry, replan, copy/export, or service delegation path is invoked after a failed guard.

## 24 Rate limit guard review

The skeleton includes route-local process memory rate limiting with bounded defaults. This is approved as skeleton guard behavior only. Production route wiring still requires a final rate-limit design review and operational abuse review.

## 25 Size/page guard review

The skeleton bounds query parameter count, parameter value length, detail plan id length, list limit, and offset. Page size defaults to a bounded maximum of 100 in the skeleton, and oversized requests fail closed with sanitized degraded envelopes.

## 26 Query parameter guard review

List queries accept only the reviewed control and filter allowlists. Unsupported parameters, excessive parameter count, oversized values, excessive filters, invalid limits, and invalid offsets are rejected before placeholder construction.

## 27 Sort/filter guard review

Sort fields and sort directions are allowlisted. Raw SQL-like sort values and unsupported filter keys are rejected. The skeleton does not create storage filters, SQL fragments, or provider/prompt/tool filters.

## 28 Plan ID guard review

The detail route validates `{plan_id}` with safe identifier rules and a maximum length. Empty, oversized, path-like, token-like, or forbidden-marker identifiers fail closed.

## 29 Safe audit envelope review

The audit metadata includes only route access event type, caller id/source, decision status, decision reason, query keys, and page size. It excludes headers, cookies, bearer tokens, secrets, raw request bodies, raw storage, prompts, provider payloads, tool outputs, stdout/stderr, command args, file contents, raw exceptions, raw reprs, and stack traces.

## 30 Safe observability envelope review

The observability metadata includes only route id, operation name, decision status, status code, route enabled state, and bounded rate-limit settings. It does not expose raw runtime payloads, provider data, prompts, tool outputs, request headers, cookies, secrets, exception internals, or raw storage.

## 31 Metadata-only response review

All skeleton responses are metadata-only envelopes. The placeholder data contains empty items, null detail, `delegation_boundary=HistoricalDryRunAuditQueryService`, `storage_accessed=false`, `runtime_invoked=false`, and `copy_export_enabled=false`.

## 32 501 service_delegation_unavailable placeholder review

Authorized and enabled skeleton test calls return `501 NOT_IMPLEMENTED` with `service_delegation_unavailable`. This is the correct placeholder because no capability source, cross-language delegation, production wiring, or service invocation is approved yet.

## 33 Cross-language delegation blocker

No Rust-to-Python delegation is implemented or approved. Future cross-language delegation requires a design review covering transport, timeout, failure mapping, redaction, service-only access, payload bounds, and tests proving no direct MemoryFacade or raw storage access.

## 34 HistoricalDryRunAuditQueryService-only delegation review

The only acceptable future delegation boundary remains the existing historical audit internal API and `HistoricalDryRunAuditQueryService`. Future route handlers must not bypass safe query models, call MemoryFacade directly, create alternate storage readers, or treat audit evidence as instructions.

## 35 No direct MemoryFacade review

The Rust skeleton does not import or call MemoryFacade. Direct API-to-MemoryFacade access remains not approved. MemoryFacade must remain behind `HistoricalDryRunAuditQueryService` if a future delegation branch is approved.

## 36 No raw JSONL/SQLite/SQL review

The skeleton does not read JSONL, SQLite rows, or SQL. It does not construct SQL from request input. Raw JSONL, raw SQLite rows, raw SQL query/filter, and direct storage access remain not approved.

## 37 No prompt/provider/tool output review

The skeleton does not expose prompts, responses, provider payloads, provider responses, tool outputs, or tool raw results. Tests assert forbidden output markers are absent from safe response serialization.

## 38 No runtime/provider/prompt/execution review

The skeleton does not change runtime behavior, provider routing, prompt behavior, execution behavior, retry execution, replan execution, autonomous execution, or self-repair behavior.

## 39 No retry/replan/self-repair/autonomous execution review

The skeleton is read-only metadata governance infrastructure. It does not execute retry, execute replan, use persisted evidence as execution input, trigger autonomous execution, or enable self-repair.

## 40 No Cockpit/detail drawer review

No Cockpit page, detail drawer, API consumer, frontend state, or rendering path was added. Cockpit/detail drawer consumption remains blocked until after route exposure and frontend redaction governance are separately approved.

## 41 No copy/export review

No copy, export, download, clipboard, or export-friendly raw payload behavior was added. Copy/export remains not approved, and the skeleton placeholder explicitly reports `copy_export_enabled=false`.

## 42 No retention/cleanup review

No retention policy, cleanup job, deletion logic, pruning behavior, storage migration, or evidence lifecycle behavior was added. Retention/cleanup remains blocked for a separate storage and governance review.

## 43 Test evidence review

PR #512 focused Rust tests cover disabled default denial, no no-auth `/internal/audit/dry-run`, missing JWT, invalid JWT, missing caller identity, missing readonly capability, valid auth while disabled, unsupported query params, excessive page size, invalid sort/detail input, rate-limit denial, safe audit/observability fields, no storage/runtime/copy-export placeholder behavior, no direct storage/execution markers, and no production router wiring.

## 44 Rust fmt/clippy/test review

The PR #512 skeleton was added with Rust tests as evidence. This docs-only governance branch does not require rerunning Rust fmt, clippy, or tests because it does not modify Rust code. Before any future implementation branch, Rust fmt, clippy, and focused Rust tests must pass.

## 45 Python route-controls/internal-api/query-service test review

Existing Python route-control, internal API, and query-service tests remain relevant as boundary evidence. They cover dormant route controls, `internal_enabled=False`, safe degraded responses, service-only query boundaries, sanitizer behavior, and no raw storage/prompt/provider/tool exposure. This branch does not modify Python code.

## 46 Runtime autonomy test review

Runtime autonomy tests remain relevant before implementation phases because they prove historical audit work does not trigger runtime/provider/retry/replan/self-repair behavior. This docs-only branch does not require runtime autonomy tests.

## 47 OneDrive CARGO_TARGET_DIR environment note

On Windows/OneDrive worktrees, Rust validation may need an explicit `CARGO_TARGET_DIR` outside OneDrive to avoid filesystem lock or path churn. This branch is docs-only, so Rust build artifacts are not required.

## 48 Remaining blockers before capability source

- Define the authoritative server-side source for `historical_audit:read`.
- Prove capabilities cannot be supplied or forged through request input.
- Define failure behavior for missing, stale, unavailable, or malformed capability data.
- Add tests for authorized and unauthorized callers through the production-intended source.

## 49 Remaining blockers before cross-language delegation

- Design Rust-to-Python delegation through the existing internal API/query service boundary.
- Define transport, timeout, cancellation, and failure mapping.
- Prove no direct MemoryFacade, raw JSONL, raw SQLite, raw SQL, prompt, provider, tool, runtime, retry, or replan path is reachable.
- Add redaction, payload size, degraded response, and service response validation tests.

## 50 Remaining blockers before production route wiring

- Complete capability-source design review.
- Complete cross-language delegation design review if delegation is included.
- Define environment/config route enablement and rollback behavior.
- Finalize rate limit, safe audit sink, safe observability sink, request validation, and abuse/security reviews.
- Add production-router tests proving protected-only registration and no no-auth/public exposure.

## 51 Remaining blockers before route enablement

- Production route wiring must be separately approved first.
- Capability source and delegation must be implemented and tested.
- Route switch defaults, rollout controls, rollback controls, operational monitoring, and audit logging must be validated.
- Endpoint exposure and route enablement must remain separate approvals.

## 52 Remaining blockers before Cockpit consumption

- Route exposure must be approved and implemented first.
- Frontend redaction, payload bounds, warning visibility, empty/error/loading states, and no execution affordance tests are required.
- Cockpit must not render raw storage, prompts, provider payloads, tool outputs, secrets, stacks, stdout/stderr, or export-oriented payloads.

## 53 Remaining blockers before copy/export

- Copy/export remains not approved.
- Any future branch would need explicit export policy, redaction policy, permission checks, audit trail, rate/size limits, retention implications, denial tests for raw data, and UI review.

## 54 Security review checklist

- Protected-only route path is retained.
- No no-auth `/internal/*` route is added.
- Supabase JWT middleware is required.
- Caller identity comes only from authenticated middleware.
- `historical_audit:read` is enforced server-side before service access.
- Route switch defaults disabled and fails closed.
- Rate, size, query, sort, filter, and plan-id guards run before service access.
- Safe envelopes exclude forbidden data.
- No raw storage, prompt, provider, tool, runtime, retry, replan, autonomous execution, or self-repair path is reachable.

## 55 Abuse review checklist

- Missing/invalid JWT fails closed.
- Missing/invalid caller fails closed.
- Missing readonly capability fails closed.
- Disabled route fails closed.
- Excessive rate fails closed.
- Oversized requests fail closed.
- Unsupported filters and sorts fail closed.
- Invalid plan ids fail closed.
- Placeholder service delegation remains non-executable.
- Public and no-auth probing remain blocked by absent registration.

## 56 Operational rollback checklist

- Keep route switch disabled by default.
- Keep production router unwired until separate approval.
- Ensure future enablement can be reversed without runtime/provider/prompt/storage changes.
- Ensure rollback does not require deleting evidence or disabling unrelated protected routes.
- Ensure disabled state returns only safe degraded metadata.

## 57 Required tests before next implementation branch

- Auth required, missing JWT denied, invalid JWT denied, expired JWT denied.
- Missing Supabase `sub` denied.
- Unauthorized caller denied.
- Missing `historical_audit:read` denied.
- Disabled route denied even for otherwise authorized callers.
- Query complexity, sort/filter, page size, and plan-id guards fail closed.
- Safe envelope tests for forbidden marker exclusion.
- No direct MemoryFacade, raw JSONL/SQLite/SQL, provider, prompt, retry, replan, Cockpit, copy/export, or runtime execution references.

## 58 Required tests before production wiring

- Production router contains only protected historical audit paths if approved.
- Production router does not contain `/internal/audit/dry-run` or public historical audit paths.
- Route merge is behind Supabase auth middleware.
- Capability source cannot be request-forged.
- Disabled route blocks service access.
- Rate, size, query, sort, filter, and plan-id guards execute before delegation.
- Safe audit and observability sinks receive only metadata.
- Service delegation failures degrade safely.

## 59 Required tests before route enablement

- End-to-end protected route tests with valid and invalid callers.
- Capability source availability and failure-mode tests.
- Delegation timeout and invalid service response tests.
- Abuse/rate-limit tests.
- Operational rollback tests.
- Monitoring and safe audit event tests.
- Regression tests proving no public/no-auth exposure.

## 60 Explicit non-approval statement

This review does not approve production route wiring, route enablement, endpoint exposure beyond isolated skeleton tests, public exposure, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL/SQLite/SQL access, direct API-to-MemoryFacade access, prompt rewrite, provider/model retry execution, provider/model replan execution, persisted evidence as execution input, autonomous execution, or self-repair.

## 61 Open risks

- The production capability source is not designed or implemented.
- Cross-language delegation is not designed or implemented.
- The isolated skeleton could be mistaken for production readiness unless the unwired/default-disabled posture remains explicit.
- Future route wiring could accidentally bypass guards unless source and integration tests are required.
- Process-local skeleton rate limiting may not match future production abuse-control requirements.

## 62 Open questions

- Which server-side authority will issue and store `historical_audit:read`?
- What exact protected route prefix should production use if the candidate paths are later approved?
- What transport should be used for Rust-to-Python service-only delegation?
- What audit and observability sinks should receive safe route access events?
- What rollout control separates production wiring from route enablement?

## 63 Go/no-go table

| Area | Decision | Governance rationale |
| --- | --- | --- |
| Documentation | Go | Approved for this governance review. |
| Protected route skeleton | Go | Approved as isolated protected skeleton only. |
| Candidate protected route paths | Go | Approved as protected-only candidate paths, not production exposure. |
| main.rs module declaration | Go | Approved for compilation only. |
| Production router wiring | No-go | Not approved; router remains unwired. |
| Route enablement | No-go | Not approved; switch remains disabled/fail-closed by default. |
| Server-side capability source | Conditional go | Design review only may proceed in a future branch. |
| Cross-language delegation design | Conditional go | Design review only may proceed in a future branch. |
| Cross-language delegation implementation | No-go | Not approved. |
| Internal endpoint exposure | No-go | Not approved beyond isolated skeleton tests. |
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

## 64 Final recommendation

Approve PR #512's outcome for documentation and protected route skeleton only. Keep the skeleton isolated, keep the production router unwired, keep the route switch disabled and fail-closed by default, keep candidate routes protected-only, keep no-auth `/internal/*` rejected, and keep public exposure blocked.

The recommended next branch is a documentation-only capability-source design review for `historical_audit:read`, followed separately by a cross-language delegation design review if Misael explicitly approves that phase. Production route wiring, route enablement, Cockpit consumption, copy/export, retention/cleanup, and execution-related behavior must remain blocked.
