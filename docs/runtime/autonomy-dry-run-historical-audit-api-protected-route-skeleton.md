# Dry-Run Historical Audit API Protected Route Skeleton

## 1 Executive summary

This branch adds a narrow Rust Axum protected route skeleton for the future historical dry-run audit API. The skeleton is compiled and tested, but it is not wired into the production app router. It remains fail-closed by default and returns only safe metadata envelopes.

## 2 Scope

Scope is limited to an isolated protected router builder, skeleton handlers, route-specific guard logic, focused Rust tests, and this documentation.

## 3 Non-goals

This branch does not expose a production endpoint, add a public route, use the no-auth `/internal/*` group, add Cockpit UI, add detail drawers, add copy/export, add retention/cleanup, modify runtime behavior, modify provider routing, modify prompts, execute retry/replan, call providers/models, enable autonomous execution, or enable self-repair.

## 4 Files inspected

- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs`
- `backend/rust/src/run_control.rs`
- `backend/python/brain/memory/historical_audit_route_controls.py`
- `backend/python/brain/memory/historical_audit_internal_api.py`
- `backend/python/brain/memory/historical_audit_query_models.py`
- `backend/python/brain/memory/historical_audit_query_service.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_route_controls.py`
- `docs/runtime/autonomy-dry-run-historical-audit-api-implementation-controls.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-implementation-controls-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-route-registration-design-review.md`

## 5 Files changed

- `backend/rust/src/main.rs`
- `backend/rust/src/protected_historical_audit.rs`
- `docs/runtime/autonomy-dry-run-historical-audit-api-protected-route-skeleton.md`

## 6 Protected route skeleton overview

The new Rust module defines an isolated `protected_historical_audit_router(...)` builder. The builder applies Supabase JWT middleware and route-specific historical audit guards, but the production app router does not merge it.

## 7 Candidate route paths

- `GET /protected/internal/audit/dry-run`
- `GET /protected/internal/audit/dry-run/{plan_id}`

## 8 Production wiring status

Production wiring is blocked. `main.rs` declares the module for compilation only and does not merge the skeleton router into the app. Tests assert the candidate paths are not wired into the production router source.

## 9 Fail-closed behavior

The default route config has `route_enabled=false` and no authorized callers. The skeleton denies by default and returns safe degraded envelopes without storage, runtime, provider, prompt, retry, or replan access.

## 10 Supabase JWT authentication boundary

The router builder uses the existing `require_supabase_auth` Axum middleware. Missing, malformed, expired, or invalid bearer tokens return `401` before handler access.

## 11 Readonly historical-audit authorization boundary

The skeleton defines the route-specific capability constant `historical_audit:read`. Because there is no production capability source yet, test-only configuration maps authorized caller ids server-side. Missing capability fails closed with `403`.

## 12 Caller identity boundary

Caller identity comes only from the authenticated Supabase `sub` inserted into request extensions by `require_supabase_auth`. The handler does not accept caller identity from query params, path params, request bodies, cookies, or arbitrary headers.

## 13 Disabled route switch behavior

The route switch defaults disabled. Even valid authenticated callers with configured authorization receive a fail-closed `route_disabled` denial while the switch is off.

## 14 Rate limit control boundary

The skeleton includes bounded process-local rate-limit metadata and tests. It is intentionally local to the isolated router state and does not alter global runtime rate limiting.

## 15 Size limit control boundary

The skeleton bounds query parameter count, parameter length, page size, offset, and detail plan id length before placeholder response construction.

## 16 Query complexity control boundary

List queries accept only the historical audit filter/control allowlist and reject unsupported parameters, excessive filters, invalid sort fields, invalid sort directions, invalid limits, invalid offsets, and oversized values.

## 17 Safe audit schema usage

Responses include only safe audit metadata: event type, caller id/source, decision status, decision reason, query keys, and page size. They exclude headers, cookies, tokens, secrets, raw request bodies, raw storage, prompts, provider payloads, tool outputs, stdout/stderr, command args, file contents, raw exceptions, and stack traces.

## 18 Safe observability schema usage

Responses include only safe observability metadata: route id, operation name, decision, status code, route enabled flag, and bounded rate-limit settings.

## 19 Handler invocation boundary

Handlers perform auth-dependent caller extraction, route switch validation, readonly authorization, rate limiting, and query/detail validation before returning a placeholder envelope.

## 20 HistoricalDryRunAuditQueryService-only delegation boundary

The skeleton does not call the service yet. The placeholder response explicitly records `delegation_boundary=HistoricalDryRunAuditQueryService`. A future branch must implement cross-language service delegation only through the existing safe internal API/query service boundary.

## 21 No direct MemoryFacade confirmation

The Rust skeleton does not import or call MemoryFacade. Direct API-to-MemoryFacade access remains blocked.

## 22 No raw JSONL/SQLite/SQL confirmation

The skeleton does not read JSONL, SQLite rows, or SQL. It does not construct SQL from request input.

## 23 No prompt/provider/tool output confirmation

The skeleton does not expose prompts, model responses, provider payloads, provider responses, tool outputs, or tool raw results.

## 24 No runtime/provider/prompt/execution confirmation

Runtime, provider routing, prompt behavior, retry execution, replan execution, autonomous execution, and self-repair remain unchanged.

## 25 No Cockpit/detail drawer/copy/export confirmation

No frontend, Cockpit detail drawer, copy flow, export flow, or download behavior was added.

## 26 Test evidence

Focused Rust tests cover default disabled denial, no `/internal/audit/dry-run` route, missing JWT, invalid JWT, missing caller identity, missing readonly capability, valid auth while disabled, unsupported query params, excessive page size, invalid sort/detail input, rate-limit denial, safe audit/observability fields, no storage/runtime/copy-export placeholder behavior, and no production wiring.

## 27 Validation evidence

Validation must include `git diff --check`, `git status --short`, Rust formatting, and focused Rust tests for the new module. Existing Python historical audit tests remain applicable because no Python files changed.

## 28 Remaining blockers before route registration exposure

- Production capability source for `historical_audit:read`.
- Explicit environment/config route enablement design.
- Final rate limiter integration review.
- Safe audit sink integration.
- Safe observability sink integration.
- Cross-language service delegation through the existing internal API boundary.
- Security review and abuse-case review.

## 29 Remaining blockers before Cockpit consumption

- Endpoint exposure approval.
- Frontend redaction tests.
- Warning visibility design.
- No execution affordance review.
- No copy/export review.
- Payload size and detail drawer governance.

## 30 Go/no-go table

| Area | Decision | Reason |
| --- | --- | --- |
| Protected route skeleton | Go | Added as isolated compiled router builder. |
| Production route wiring | No-go | Not wired; future approval required. |
| Public exposure | No-go | Prohibited. |
| No-auth `/internal/*` route | No-go | Not added. |
| Cockpit/detail drawer | No-go | Out of scope. |
| Copy/export | No-go | Out of scope. |
| Retention/cleanup | No-go | Out of scope. |
| Runtime/provider/prompt/execution | No-go | Unchanged and blocked. |

## 31 Final recommendation

Protected route skeleton added. Keep the route fail-closed by default. Production exposure remains blocked unless explicitly approved later. Public exposure remains blocked. Cockpit/detail drawer remains blocked. Copy/export remains blocked. Retention/cleanup remains blocked. Runtime/provider/prompt/execution remains unchanged. A future branch is still required for controlled route exposure and enablement.
