# Dry-Run Historical Audit API Capability Source Implementation Preparation

## 1 Executive summary

This document prepares, but does not implement, the future server-side capability source for `historical_audit:read`. It converts the approved PR #514 design review and PR #515 implementation planning into a precise implementation-readiness artifact for a later narrow code branch.

This branch is approved for documentation/preparation only. It does not add capability implementation, DB schema, migrations, Supabase query/RPC code, route wiring, route enablement, endpoint exposure, cross-language delegation, Cockpit consumption, copy/export, retention/cleanup, raw storage access, or runtime/provider/prompt/execution behavior.

## 2 Scope

Scope is limited to preparing the future schema, resolver interface, RLS/service-role posture, JWT/Supabase `sub` mapping, failure model, safe audit and observability requirements, test matrices, rollback plan, monitoring plan, security checklist, readiness checklist, blockers, and go/no-go decisions.

## 3 Non-goals

This document does not modify `backend/rust/src/protected_historical_audit.rs`, modify `backend/rust/src/main.rs`, implement a resolver, add schema, add migrations, add Supabase table/RPC/query code, wire the production router, enable `protected_historical_audit_router`, expose endpoints, add public routes, add Python delegation, modify MemoryFacade, modify `HistoricalDryRunAuditQueryService`, alter storage, change runtime/provider/prompt/execution behavior, add Cockpit/detail drawer UI, add copy/export, add retention/cleanup, or alter CI, deploy, billing, production settings, or secrets.

## 4 Reviewed materials

- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-implementation-planning.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-design-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-protected-route-skeleton-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-protected-route-skeleton.md`
- `backend/rust/src/protected_historical_audit.rs`
- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs`
- `supabase/migrations/20260409_omni_schema_foundation.sql`
- `supabase/migrations/20260418120000_runtime_tool_events.sql`
- `backend/python/brain/memory/schema.sql`
- `docs/backend/operator-telemetry-api.md`
- `docs/governance/vault-sandbox-policy.md`

## 5 Current implementation state

The protected historical audit Rust skeleton defines `historical_audit:read`, uses `require_supabase_auth`, reads caller identity from the authenticated Supabase `sub`, supports test-only static callers, defaults disabled, and remains unmerged from the production router. No production capability source, grant table, migration, Supabase query, RPC, resolver, or cross-language delegation exists.

## 6 Current governance state

PR #513 approved the route skeleton only as isolated, protected, unwired, and fail-closed. PR #514 approved server-side-only capability-source design. PR #515 approved implementation planning for Supabase table-backed grants and a Rust resolver keyed by Supabase `sub`. Production router wiring, route enablement, endpoint exposure, public exposure, cross-language delegation, Cockpit/detail drawer, copy/export, retention/cleanup, raw storage, direct MemoryFacade access, and execution behavior remain blocked.

## 7 Capability under preparation

The prepared capability is exactly `historical_audit:read`. It is read-only and route-specific. It does not authorize route enablement, service delegation, public exposure, Cockpit consumption, copy/export, retention/cleanup, storage reads, prompt access, provider/model calls, retry/replan, autonomous execution, or self-repair.

## 8 Inherited decisions from PR #514 and PR #515

Inherited decisions: use server-side-only evaluation, key production authorization by authenticated Supabase `sub`, prefer Supabase table-backed grants, keep static grants isolated to tests, reject client/header/request-param capabilities, reject environment-only production allowlists, preserve fail-closed behavior, and keep the route switch disabled by default.

## 9 Future implementation objective

The future objective is a narrow Rust-side capability resolver that answers whether an authenticated Supabase `sub` has an active, non-revoked, non-expired `historical_audit:read` grant from a server-controlled Supabase source. The resolver must return only a safe allow/deny decision and reason.

## 10 Proposed Supabase grant table name

Prepare the table name `public.omni_capability_grants`. The name is intentionally capability-generic so future governance can add other narrow capabilities without creating route-specific tables, while the first approved capability remains only `historical_audit:read`.

## 11 Proposed table purpose

`public.omni_capability_grants` stores server-owned caller-to-capability grants. It is an authorization registry, not an audit-data table, storage index, prompt store, route enablement switch, or execution policy table.

## 12 Proposed columns

Proposed columns: `id`, `supabase_sub`, `capability`, `active`, `revoked_at`, `expires_at`, `created_at`, `updated_at`, `created_by`, `updated_by`, `grant_reason`, `grant_source`, `review_ticket`, and `metadata`.

## 13 Proposed column types

Proposed types: `id uuid`, `supabase_sub uuid`, `capability text`, `active boolean`, `revoked_at timestamptz null`, `expires_at timestamptz null`, `created_at timestamptz`, `updated_at timestamptz`, `created_by text`, `updated_by text`, `grant_reason text`, `grant_source text`, `review_ticket text`, and `metadata jsonb`.

## 14 Required primary key

The required primary key is `id uuid primary key default gen_random_uuid()`, matching existing Supabase migration style. The primary key is an internal row identifier only and must not be accepted from route requests as an authorization input.

## 15 Required uniqueness constraints

The future schema should enforce at most one active, non-revoked row per `(supabase_sub, capability)`. Historical revoked or expired rows may remain for auditability, but duplicate effective active grants must be impossible or treated as a resolver conflict and deny.

## 16 Required indexes

Required indexes: `(supabase_sub, capability)` for resolver lookup, a partial active-grant index for active and non-revoked rows, `expires_at` for review/cleanup visibility, `updated_at desc` for operations review, and `capability` for capability-scoped audits.

## 17 Required active/revoked semantics

Only `active=true` and `revoked_at is null` can authorize. `active=false`, a non-null `revoked_at`, contradictory state, or missing state denies.

## 18 Required expiration semantics

Expired grants deny. A null `expires_at` may be allowed only if the future implementation branch explicitly preserves governance approval for non-expiring grants and includes safe audit metadata explaining the grant.

## 19 Required created_by/updated_by semantics

`created_by` and `updated_by` identify the trusted operator or process that changed the grant. They are audit metadata only. They must not be derived from request parameters and must not authorize route access.

## 20 Required audit metadata fields

Required safe metadata fields are `grant_reason`, `grant_source`, `review_ticket`, `created_by`, `updated_by`, `created_at`, and `updated_at`. Optional `metadata` may hold bounded JSON such as review reference or migration batch id, but must never hold secrets, JWTs, service-role keys, raw storage, SQL, prompts, provider payloads, tool outputs, stack traces, command args, file contents, raw exceptions, or raw reprs.

## 21 Required RLS posture

The table must enable row level security. Browser roles, `anon`, and normal `authenticated` clients must have no direct select, insert, update, or delete policy for capability grants. The posture should match the runtime-tool-events pattern: RLS enabled and no PostgREST client policies unless a future reviewed admin path is explicitly approved.

## 22 Required service-role posture

The Rust backend may use a server-only service-role boundary or a tightly scoped server-only RPC. The service-role key must remain outside frontend code, browser bundles, logs, responses, docs examples with real values, tests with real values, and request-derived data. Missing or invalid service-role configuration must deny.

## 23 Required JWT boundary

Supabase JWT validation remains authentication only. `require_supabase_auth` must validate bearer token, expiry, issuer, and then insert the `sub` extension. The future resolver starts only after that middleware boundary succeeds.

## 24 Required Supabase sub mapping

The resolver must use the middleware-owned Supabase `sub` as the lookup key. The prepared table should store `supabase_sub uuid` to align with `auth.users.id` when possible; any future conversion from extension string to UUID must reject missing, empty, malformed, oversized, or unsafe values.

## 25 Required Rust resolver interface

Prepare a small Rust resolver boundary such as `authorize_historical_audit_read(caller_sub, source_config) -> CapabilityDecision`. The exact name is deferred, but the interface must remain route-agnostic enough to unit test and narrow enough to avoid storage, Python, runtime, provider, prompt, or UI dependencies.

## 26 Required Rust resolver inputs

Inputs: authenticated caller `sub`, required capability literal `historical_audit:read`, resolver source configuration, bounded timeout, and a clock for expiration comparison. Inputs must not include request query filters, plan ids, caller-provided roles, headers, cookies, request bodies, MemoryFacade, HistoricalDryRunAuditQueryService, provider state, or prompt state.

## 27 Required Rust resolver outputs

Outputs: `allowed: bool`, safe reason code, safe source mode, optional safe latency/diagnostic category, and no raw source record. The caller should receive only safe denial categories, not table names, SQL, grant counts, connection details, stack traces, or Supabase error bodies.

## 28 Required resolver error categories

Required categories: `missing_caller_identity`, `invalid_caller_identity`, `missing_historical_audit_readonly_capability`, `expired_historical_audit_readonly_capability`, `revoked_historical_audit_readonly_capability`, `malformed_capability_grant`, `duplicate_capability_grant`, `capability_source_unavailable`, `capability_source_timeout`, `capability_source_misconfigured`, and `capability_source_forbidden`.

## 29 Required safe error mapping

Map unauthenticated cases to existing auth behavior, missing/invalid caller to `401` or safe unauthorized route envelope, missing/expired/revoked grants to `403`, disabled route to existing `404 route_disabled`, source unavailability/timeouts/malformed/duplicate state to safe fail-closed `403` or reviewed degraded authorization error. Never expose raw Supabase, SQL, HTTP client, or serialization errors.

## 30 Required fail-closed behavior

Authorization allows only when the route is enabled, caller identity is valid, source lookup succeeds, capability exactly matches `historical_audit:read`, grant is active, grant is not revoked, grant is not expired, and no conflict exists. Every other state denies.

## 31 Missing grant behavior

An authenticated caller without a grant denies with `missing_historical_audit_readonly_capability`. The response and logs must not disclose other grant rows, table structure, SQL, or which users have access.

## 32 Expired grant behavior

An expired grant denies even if it is otherwise active. Safe audit and metrics may count expiration denials without exposing raw timestamps in public responses.

## 33 Revoked grant behavior

A revoked grant denies even if `active=true` is stale. Revocation must dominate active state whenever a conflict is detected.

## 34 Unknown caller behavior

Unknown callers deny. Unknown means the authenticated `sub` is valid but no current effective `historical_audit:read` grant exists.

## 35 Supabase unavailable behavior

Supabase unavailable denies. The resolver must not fall back to static production allowlists, environment-only allows, JWT custom claims, or client-supplied data.

## 36 Supabase timeout behavior

Supabase timeout denies. Timeout duration must be bounded in config. Logs and metrics may record safe timeout category and latency bucket, but not connection strings, query text, credentials, or raw error bodies.

## 37 Malformed grant behavior

Malformed grants deny. Examples include missing capability, invalid capability, non-boolean active state if deserialized from RPC, invalid timestamps, unsafe metadata, wrong caller type, or unexpected source response shape.

## 38 Duplicate grant behavior

Duplicate effective active grants deny as a source conflict unless the schema makes the conflict impossible. The resolver must not pick the first row arbitrarily.

## 39 Static test-only capability behavior

Static capability grants remain allowed only in isolated Rust tests with explicit test construction. Static grants must not be enabled by production environment variables and must not become fallback behavior when Supabase is unavailable.

## 40 Client/header/request-param rejection behavior

Client, header, and request-param capability attempts must be ignored or rejected and must never authorize. Future negative tests must include `X-Capability`, `X-Role`, `capability=historical_audit:read`, `role=admin`, body-provided capability fields, and caller id spoofing.

## 41 Safe audit event requirements

Audit events may include route id, operation, safe caller category or bounded caller id, required capability, decision, reason code, source mode, route enabled state, timestamp, and bounded latency. They must exclude bearer tokens, headers, cookies, raw JWTs, raw grant rows, SQL, storage rows, prompts, provider payloads, tool outputs, stdout/stderr, stacks, command args, file contents, raw exceptions, raw reprs, and service-role material.

## 42 Safe observability requirements

Observability may count allows, denials, missing grants, expired grants, revoked grants, unknown callers, malformed grants, duplicate conflicts, source unavailable, source timeout, route-disabled denials, and unexpected allow spikes. Metrics must be aggregate and safe.

## 43 Forbidden fields

Responses, logs, metrics, fixtures, and docs examples must not expose raw JSONL, raw SQLite rows, raw SQL, prompts, responses, provider payloads, tool outputs, secrets, headers, cookies, stack traces, stdout/stderr, command args, file contents, `.env` content, raw exceptions, raw reprs, bearer tokens, JWTs, service-role keys, connection strings, or raw grant rows.

## 44 No raw storage exposure

The capability source must not read historical audit JSONL, SQLite, SQL, or storage files. It only answers whether the caller may proceed to the future safe historical audit route flow.

## 45 No direct MemoryFacade boundary

The future resolver must not import or call MemoryFacade. Direct API-to-MemoryFacade access remains not approved.

## 46 No HistoricalDryRunAuditQueryService changes

The capability source preparation does not modify `HistoricalDryRunAuditQueryService`. Cross-language delegation and query-service consumption remain separate blockers.

## 47 No production route wiring boundary

The production app router must remain unwired in this branch. `protected_historical_audit_router(...)` must not be merged into `main.rs`.

## 48 No route enablement boundary

The route switch must remain disabled by default. Capability preparation does not approve enablement.

## 49 No endpoint exposure boundary

No endpoint exposure is approved. The candidate paths remain isolated skeleton paths only.

## 50 No public exposure boundary

No public route, public summary, unauthenticated route, or public documentation implying availability is approved.

## 51 No Cockpit/detail drawer boundary

Cockpit/detail drawer consumption remains blocked until route exposure, endpoint payload, frontend redaction, and UI governance are separately approved.

## 52 No copy/export boundary

Copy/export remains blocked. `historical_audit:read` must not imply clipboard, download, export, or raw payload rights.

## 53 No retention/cleanup boundary

Retention/cleanup remains blocked. The capability does not authorize deletion, pruning, compaction, evidence lifecycle mutation, or cleanup jobs.

## 54 Migration preparation checklist

- Use a new timestamped file under `supabase/migrations/`.
- Create `public.omni_capability_grants`.
- Use `gen_random_uuid()` for `id`.
- Use `timestamptz` with UTC defaults for timestamps.
- Add exact `capability` check for approved values if governance wants a closed set.
- Add active/revoked/expiration checks.
- Add uniqueness for effective active grants.
- Add resolver lookup and operations-review indexes.
- Enable RLS.
- Add comments documenting anon/authenticated deny posture.
- Do not add broad client policies.
- Include rollback SQL or an explicit reversible migration plan.

## 55 Resolver implementation preparation checklist

- Add a narrow Rust resolver module or boundary.
- Keep resolver inputs limited to authenticated `sub`, exact capability, config, timeout, and clock.
- Parse and validate `sub` safely.
- Query only the approved server-side source.
- Return safe decision categories.
- Deny on missing config, unavailable source, timeout, malformed response, duplicate active grants, missing grant, expired grant, revoked grant, wrong capability, and unknown caller.
- Preserve test-only static grants as isolated test construction.
- Do not modify route wiring, runtime, provider, prompt, Python delegation, MemoryFacade, or storage.

## 56 Test fixture preparation checklist

- Synthetic caller UUIDs only.
- Synthetic grant rows only.
- No real JWTs, service-role keys, access tokens, emails, customer data, prompts, provider payloads, storage rows, SQL dumps, or `.env` content.
- Fixtures for active, missing, expired, revoked, duplicate, malformed, wrong-capability, unknown-caller, source-unavailable, timeout, and test-static paths.

## 57 Negative test matrix

Required negative tests: missing JWT, invalid JWT, expired JWT, missing `sub`, malformed `sub`, unknown caller, missing grant, expired grant, revoked grant, wrong capability, wildcard capability, duplicate active grant conflict, malformed grant row, missing Supabase config, missing service-role config, source unavailable, source timeout, client capability, header capability, request-param capability, caller spoofing, production static allow attempt, and environment-only production allow attempt.

## 58 Positive test matrix

Required positive tests: authenticated `sub` with exact active `historical_audit:read` grant allows resolver decision; non-expired active grant allows; unrelated capability does not allow; safe audit event emits approved metadata only; safe observability emits aggregate category only; static test grant works only in isolated tests; route-enabled skeleton still reaches only placeholder or separately approved future boundary.

## 59 Abuse case matrix

Abuse cases: authenticated user probes audit route without grant, user forges `X-Capability`, user forges `X-Role`, user sends capability query param, user sends spoofed caller id, user reuses token after grant revocation, user probes during Supabase outage, user induces duplicate grants, user tries raw SQL-like params, user paginates aggressively after grant, and user tries to infer access policy from denial details.

## 60 Rollback preparation

Rollback options: keep the route switch disabled, remove or disable the resolver source mode, revoke grants, rotate service-role credentials if exposed, revert the capability migration in a separate reviewed branch, or keep production router unwired. Rollback must not require deleting historical audit evidence or changing runtime/provider/prompt/storage behavior.

## 61 Operational monitoring preparation

Prepare safe counters for allow, deny, missing grant, expired grant, revoked grant, unknown caller, malformed grant, duplicate conflict, source unavailable, source timeout, resolver misconfig, route disabled, and unexpected allow spikes. Alerts must not include secrets, JWTs, service-role keys, raw caller tokens, raw grants, SQL, or storage rows.

## 62 Security review checklist

- Supabase JWT authentication happens before resolver lookup.
- Resolver uses only middleware-owned Supabase `sub`.
- Required capability is exact `historical_audit:read`.
- RLS is enabled.
- Browser/anon/authenticated direct access is denied.
- Service-role material is server-only.
- Client/header/request-param capabilities are rejected.
- Source failure denies.
- Duplicate or malformed grant state denies.
- Audit/observability are metadata-only.
- No route wiring, route enablement, endpoint exposure, storage read, MemoryFacade call, HistoricalDryRunAuditQueryService change, provider call, prompt change, retry/replan, autonomous execution, or self-repair is added.

## 63 Implementation readiness checklist

Before code is allowed, the next branch must have explicit Misael approval, exact migration/RLS/RPC shape, secret-handling plan, Rust resolver module boundary, timeout and safe error mapping, fixture plan, negative/positive test matrix, rollback plan, monitoring plan, and proof the production router remains unwired.

## 64 Remaining blockers before implementation

- Explicit Misael approval for a narrow implementation branch.
- Final SQL migration content.
- Final RLS and service-role/RPC design.
- Final Rust resolver interface and module placement.
- Final Supabase client/query mechanism.
- Final timeout and error mapping.
- Final test fixtures and negative/positive test coverage.
- Final secret handling review.

## 65 Remaining blockers before route wiring

- Capability source implemented and tested.
- Resolver denial order and fail-closed behavior verified.
- No client/header/request-param authorization verified.
- No static/environment-only production allow verified.
- Safe audit/observability verified.
- Cross-language delegation design/implementation separately approved if needed.
- Production router wiring separately approved.

## 66 Remaining blockers before route enablement

- Production router wiring approved and implemented.
- Capability source operational.
- Grants created through approved operator process.
- Monitoring and rollback ready.
- Abuse/security review completed.
- Route enablement separately approved.

## 67 Remaining blockers before Cockpit consumption

- Endpoint exposure approved and implemented.
- Route enablement approved.
- Frontend redaction and safe rendering tests complete.
- Detail drawer payload bounds approved.
- No execution affordances added.
- Copy/export remains absent or separately approved.

## 68 Go/no-go table

| Area | Decision | Rationale |
| --- | --- | --- |
| Documentation | Go | Approved for documentation/preparation. |
| Implementation preparation | Go | This branch prepares only. |
| Capability name historical_audit:read | Go | Approved readonly capability name. |
| Supabase grant table preparation | Go | Approved to prepare future table-backed grants. |
| Rust resolver preparation | Go | Approved to prepare, not implement. |
| Supabase sub caller identity | Go | Approved resolver key. |
| RLS/service-role preparation | Go | Required for future server-side source. |
| Static local test capability | Go | Approved for isolated tests only. |
| Client-provided capability | No-go | Rejected. |
| Header-provided capability | No-go | Rejected. |
| Request-param-provided capability | No-go | Rejected. |
| Environment-only production capability | No-go | Rejected. |
| Capability-source implementation | No-go | Not approved in this branch. |
| DB schema/migration | No-go | Not approved in this branch. |
| Supabase query/RPC code | No-go | Not approved in this branch. |
| Production router wiring | No-go | Not approved. |
| Route enablement | No-go | Not approved. |
| Endpoint exposure | No-go | Not approved. |
| Public exposure | No-go | Not approved. |
| Cross-language delegation design | No-go | Separate future review required. |
| Cross-language delegation implementation | No-go | Not approved. |
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

## 69 Final recommendation

Approve this branch for documentation/preparation only. Approve preparation of a Supabase table-backed grant implementation, a Rust-side resolver keyed by authenticated Supabase `sub`, the exact readonly capability name `historical_audit:read`, static capability only for isolated tests, fail-closed behavior, and rejection of client/header/request-param capabilities.

Conditionally approve a future narrow capability-source implementation branch only after explicit Misael approval. Capability implementation, DB schema/migration, Supabase query/RPC code, production router wiring, route enablement, endpoint exposure, public exposure, cross-language delegation implementation, Cockpit/detail drawer consumption, copy/export, retention/cleanup, raw JSONL/SQLite/SQL access, direct API-to-MemoryFacade access, prompt rewrite, provider/model retry or replan execution, persisted evidence as execution input, autonomous execution, and self-repair remain not approved.
