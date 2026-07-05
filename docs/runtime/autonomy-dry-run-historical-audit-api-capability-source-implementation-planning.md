# Dry-Run Historical Audit API Capability Source Implementation Planning

## 1 Executive summary

This document plans, but does not implement, the future server-side capability source for `historical_audit:read`. It inherits PR #514's design: authorization must be evaluated server-side for the authenticated Supabase `sub`, with a Supabase table-backed grant source as the preferred production authority.

This branch is approved for documentation/planning only. It does not add capability code, schema, migrations, Supabase queries, route wiring, route enablement, endpoint exposure, cross-language delegation, Cockpit consumption, copy/export, retention/cleanup, storage access, or runtime/provider/prompt/execution behavior.

## 2 Scope

Scope is limited to implementation planning for a future capability source. The plan covers the proposed grant model, table fields, indexes, uniqueness, revocation/expiration semantics, RLS and service-role boundaries, Rust resolver boundaries, config boundaries, cache/no-cache decision, failure modes, tests, abuse cases, monitoring, security review, phases, and go/no-go decisions.

## 3 Non-goals

This document does not implement a resolver, add DB schema, add migrations, add Supabase table/RPC/query code, modify `backend/rust/src/protected_historical_audit.rs`, modify `backend/rust/src/main.rs`, wire routers, enable routes, expose endpoints, add cross-language delegation, modify MemoryFacade, modify HistoricalDryRunAuditQueryService, alter storage, change runtime/provider/prompt/execution behavior, add Cockpit UI, add copy/export, or change secrets/deploy/CI settings.

## 4 Reviewed materials

- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-design-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-protected-route-skeleton-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-protected-route-skeleton.md`
- `backend/rust/src/protected_historical_audit.rs`
- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs`
- Existing Rust protected route, config, server state, and caller identity patterns
- Existing Supabase/security notes in backend and audit docs

## 5 Current implementation state

The skeleton defines `historical_audit:read`, uses `require_supabase_auth`, reads caller identity from Supabase `sub`, supports test-only static callers, defaults disabled, and remains unmerged from the production router. There is no production capability resolver, grant schema, migration, Supabase query, or cross-language delegation.

## 6 Current governance state

PR #514 approved server-side-only capability-source design and rejected client/header/request-param/environment-only production authorization. Production wiring, route enablement, endpoint exposure, public exposure, cross-language delegation, Cockpit/detail drawer, copy/export, retention/cleanup, raw storage, direct MemoryFacade access, and execution behaviors remain blocked.

## 7 Capability under implementation planning

The planned capability remains exactly `historical_audit:read`. It is read-only and route-specific. It does not authorize write operations, export, cleanup, provider calls, prompt changes, retry/replan, autonomous execution, self-repair, route enablement, or public exposure.

## 8 Design decision inherited from PR #514

The future implementation must evaluate authorization server-side, keyed by authenticated Supabase `sub`. Static capability config is permitted only for isolated tests. Production authorization must not trust client claims, headers, query params, request bodies, browser state, or environment-only allowlists.

## 9 Preferred production authority

The preferred production authority is a Supabase table-backed grant registry read only by the server-side Rust capability resolver through a service-role or narrowly scoped server-only RPC boundary. This plan does not create that table or RPC.

## 10 Supabase sub caller identity model

The resolver input should be the Supabase `sub` inserted into request extensions by `require_supabase_auth`. Missing, empty, unsafe, or unavailable `sub` must deny access before any capability lookup can allow.

## 11 Proposed grant data model

Plan a grant record representing one caller, one capability, lifecycle state, optional expiration, and safe audit metadata. The model should support active grants, revoked grants, expiration, grant provenance, and deterministic lookup for a single caller/capability pair.

## 12 Proposed table fields

Planned fields: `id`, `supabase_sub`, `capability`, `active`, `revoked_at`, `expires_at`, `created_at`, `updated_at`, `created_by`, `updated_by`, `reason`, `source`, and bounded `metadata`. Exact SQL types are deferred to the future schema branch.

## 13 Required indexes

Plan indexes for lookup by `(supabase_sub, capability)`, active grants, expiration checks, and audit/review queries by `created_at` or `updated_at`. Indexes must not be designed around raw request input or historical audit storage.

## 14 Required uniqueness rules

Plan one effective active grant per `(supabase_sub, capability)` at a time. Historical revoked/expired records may exist for auditability, but the resolver must never treat multiple conflicting active grants as allow.

## 15 Required active/revoked semantics

Only an active, non-revoked grant can authorize access. Any revoked grant, missing `active=true`, malformed state, or conflicting state must deny.

## 16 Required expiration semantics

Expired grants must deny. Null expiration may be allowed only if governance approves non-expiring grants and audit metadata records why. Expiration comparisons must be server-side and based on trusted time.

## 17 Required created_by/updated_by semantics

`created_by` and `updated_by` should identify the trusted operator or process that changed the grant. They are audit metadata only and must not become authorization inputs for route requests.

## 18 Required audit metadata

Grant metadata may include safe reason, ticket/reference, source, reviewer, and timestamps. It must not include secrets, headers, cookies, bearer tokens, raw JWTs, prompts, provider payloads, raw storage rows, SQL, stack traces, stdout/stderr, command args, file contents, raw exceptions, or raw reprs.

## 19 RLS policy planning

Plan RLS so browser/anon/authenticated client roles cannot read or mutate grant records directly. Server-side access should be through service-role or a reviewed RPC that returns only a boolean decision and safe reason.

## 20 Service role boundary planning

If a service-role key is used, it must remain server-only, never exposed to frontend code, logs, responses, docs examples with real values, or request-derived payloads. Missing service-role configuration must fail closed.

## 21 JWT boundary planning

JWT validation remains authentication only. The resolver must run after JWT validation and use the middleware-owned `sub`; JWT custom claims are not the primary production grant source in this plan.

## 22 Rust resolver boundary planning

Plan a small Rust resolver boundary with inputs: safe caller id, required capability, and config. Output should be an allow/deny decision with safe reason. It must not know query filters, plan ids, MemoryFacade, HistoricalDryRunAuditQueryService, provider routing, or prompt/runtime state.

## 23 Rust config boundary planning

Plan config for source mode, timeout, optional RPC/table endpoint selection, and test-only static grants. Production config must reject static/environment-only allow mode as the final authorization source.

## 24 Cache/no-cache decision

Default plan: no cache for production authorization until revocation and freshness requirements are proven. If a later branch adds cache, TTL must be short, bounded, observable, and fail closed on stale or invalid entries.

## 25 Revocation freshness requirement

Revocation must take effect quickly enough for operational safety. The initial implementation should prefer live lookup or no-cache behavior so revoked grants stop authorizing without waiting for a long token refresh or process restart.

## 26 Failure mode model

Failure modes include missing config, source unavailable, DB timeout, malformed source response, duplicate active grants, expired grant, revoked grant, unknown caller, and invalid capability. All must deny.

## 27 Fail-closed behavior

The future resolver must default deny. Authorization can allow only on exact caller match, exact capability match, active state, non-revoked state, non-expired state, and successful trusted source lookup.

## 28 Missing grant behavior

A missing grant denies with a safe forbidden reason such as `missing_historical_audit_readonly_capability`. The response must not reveal table names, SQL, grant counts, or other available capabilities.

## 29 Expired grant behavior

An expired grant denies. Safe audit/observability may count expiration denials without exposing expiration timestamps in public responses.

## 30 Revoked grant behavior

A revoked grant denies even if the capability name matches. Revocation must override stale active-looking state when conflicts are detected.

## 31 Unknown caller behavior

Unknown callers deny. Unknown means the authenticated `sub` has no current active grant for `historical_audit:read`.

## 32 Supabase unavailable behavior

Supabase unavailability denies and should produce a safe degraded authorization error category. It must not fall back to environment production allowlists.

## 33 DB timeout behavior

DB timeout denies. Timeouts should be bounded and observable, but timeout details, connection strings, query text, and credentials must not appear in responses or logs.

## 34 Safe error mapping

Map authorization failures to safe categories: missing caller, invalid caller, route disabled, missing capability, invalid capability source, capability source unavailable, capability source timeout, capability source conflict, and forbidden. Do not expose raw errors.

## 35 Safe audit logging requirements

Audit logs may include route id, operation, safe caller id/category, capability required, decision, reason, source mode, route enabled state, timestamp, and bounded latency. They must exclude secrets, headers, cookies, raw JWTs, SQL, raw grant rows, raw storage, prompts, provider payloads, tool outputs, stacks, stdout/stderr, command args, file contents, raw exceptions, and raw reprs.

## 36 Safe observability requirements

Observability should count allows, denials, missing grants, expired grants, revoked grants, unknown callers, source unavailable, source timeout, malformed source responses, and source conflicts. Metrics must stay aggregate and safe.

## 37 Forbidden fields

Responses, logs, metrics, fixtures, and docs examples must not expose raw JSONL, raw SQLite rows, raw SQL, prompts, responses, provider payloads, tool outputs, secrets, headers, cookies, stack traces, stdout/stderr, command args, file contents, `.env` content, raw exceptions, raw reprs, bearer tokens, JWTs, service-role keys, or raw grant rows.

## 38 No client capability acceptance

Future implementation must reject or ignore client-supplied capability data from local storage, browser Supabase metadata, request bodies, UI state, or frontend-computed roles.

## 39 No header capability acceptance

Headers such as `X-Capability`, `X-Role`, `X-User-Role`, or forwarded identity headers must not grant access.

## 40 No request-param capability acceptance

Query/path/body parameters such as `capability`, `role`, `authorized`, or `caller_id` must not influence authorization.

## 41 Static test-only capability handling

Static local capability grants may be used only in isolated tests, behind explicit test construction. They must not be enabled by production environment variables and must not become production fallback behavior.

## 42 Environment-only production rejection

Environment-only production allowlists are rejected. Environment config may select source mode and timeouts, but it must not be the final production authorization authority.

## 43 Migration planning

A later migration branch should define table/RPC shape, RLS, constraints, indexes, grant lifecycle fields, and rollback. This branch adds no migration.

## 44 Backfill planning

Initial backfill should be manual and minimal: create only explicitly approved `historical_audit:read` grants for known operators after security review. No automatic grant backfill from existing users, roles, or frontend metadata is approved.

## 45 Rollback planning

Rollback should be possible by disabling the route switch, disabling capability-source mode, or revoking grants. Rollback must not require deleting historical audit evidence or changing runtime/provider/prompt/storage behavior.

## 46 Local development planning

Local development can use test-only static grants or a local Supabase test project. Production-like table-backed testing must use fake users and fake secrets. Real service-role keys must not be committed or printed.

## 47 Test fixture planning

Fixtures should include active, missing, expired, revoked, duplicate/conflicting, malformed, unknown-caller, and wrong-capability grants. Fixture values must be synthetic and must not contain real tokens, service-role keys, or user data.

## 48 Negative test matrix

Required negative tests: missing JWT, invalid JWT, missing `sub`, unsafe `sub`, route disabled, unknown caller, missing grant, expired grant, revoked grant, wrong capability, duplicate active grant conflict, malformed source response, source unavailable, DB timeout, client capability, header capability, request-param capability, and production static/env allow attempt.

## 49 Positive test matrix

Required positive tests: authenticated `sub` with exact active `historical_audit:read` grant can pass the resolver; non-expired grant allows; safe audit/observability fields are emitted; test-only static grant works only in isolated tests; enabled test route still reaches only placeholder or approved future boundary.

## 50 Abuse case matrix

Abuse cases to test or review: valid user without grant probes route, caller sends forged headers, caller sends capability query param, caller reuses stale token after revocation, caller paginates aggressively after grant, source outage occurs during probing, duplicate grants create ambiguity, and denial messages reveal operational details.

## 51 Operational monitoring plan

Monitor safe counts for allows, denials, missing/expired/revoked grants, source errors, DB timeouts, conflicts, route-disabled denials, and unexpected allow spikes. Alerts should avoid raw identifiers where possible and must not include secrets or raw grant rows.

## 52 Security review checklist

- Supabase JWT validates before resolver input.
- Resolver uses only authenticated `sub`.
- Capability exact match is `historical_audit:read`.
- Client/header/request-param capabilities are rejected.
- Production source is server-side.
- RLS blocks browser/anon direct access.
- Service-role secret stays server-only.
- Source failure denies.
- Audit/observability are safe.
- No route wiring, storage reads, MemoryFacade, HistoricalDryRunAuditQueryService, provider, prompt, retry, replan, autonomous execution, or self-repair behavior is added.

## 53 Implementation phases

Phase 1: docs-only schema/RLS/RPC design. Phase 2: docs-only implementation preparation with exact Rust module and tests. Phase 3: narrow implementation of resolver and tests without route wiring. Phase 4: separate route integration review. Phase 5: separate route wiring and enablement reviews if explicitly approved.

## 54 Required future branch boundaries

Future branches must stay narrow: schema planning does not implement Rust; resolver implementation does not wire production routes; route wiring does not enable the route; route enablement does not add Cockpit/export; Cockpit does not add copy/export; no phase changes runtime/provider/prompt/execution behavior.

## 55 Remaining blockers before implementation

- Schema/RLS/RPC design approval.
- Service-role secret handling design.
- Rust resolver interface design.
- Timeout and error mapping design.
- Test fixture and negative/positive matrix approval.
- Explicit Misael approval for a narrow implementation-preparation branch.

## 56 Remaining blockers before route wiring

- Capability resolver implemented and tested.
- Route disabled behavior verified.
- No client/header/request-param grant acceptance verified.
- No production static/env allow verified.
- Safe audit/observability verified.
- Production router wiring separately approved.

## 57 Remaining blockers before route enablement

- Production router wiring approved and implemented.
- Resolver source operational.
- Grants created through approved process.
- Monitoring and rollback ready.
- Abuse and security review completed.
- Route enablement separately approved.

## 58 Remaining blockers before Cockpit consumption

- Endpoint exposure and route enablement approved.
- Frontend redaction and safe rendering tests complete.
- No execution affordances added.
- Copy/export remains absent.
- Detail drawer payload bounds approved.

## 59 Go/no-go table

| Area | Decision | Rationale |
| --- | --- | --- |
| Documentation | Go | Approved for planning. |
| Implementation planning | Go | This branch is planning only. |
| Capability name historical_audit:read | Go | Approved readonly capability name. |
| Supabase table-backed grant source | Go | Approved to plan as preferred production authority. |
| Rust-side resolver planning | Go | Approved to plan, not implement. |
| Supabase sub caller identity | Go | Approved resolver key. |
| Static local test capability | Go | Approved for isolated tests only. |
| Client-provided capability | No-go | Rejected. |
| Header-provided capability | No-go | Rejected. |
| Request-param-provided capability | No-go | Rejected. |
| Environment-only production capability | No-go | Rejected. |
| Capability-source implementation | No-go | Not approved in this branch. |
| DB schema/migration | No-go | Not approved in this branch. |
| Supabase query code | No-go | Not approved in this branch. |
| Production router wiring | No-go | Not approved. |
| Route enablement | No-go | Not approved. |
| Endpoint exposure | No-go | Not approved. |
| Public exposure | No-go | Not approved. |
| Cross-language delegation design | No-go | Separate future design required. |
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

## 60 Final recommendation

Approve this branch for documentation/planning only. Plan a Supabase table-backed grant source and Rust-side resolver keyed by authenticated Supabase `sub`; keep `historical_audit:read` as the readonly capability name; keep static capability handling isolated to tests; preserve fail-closed behavior; and reject client/header/request-param capability sources.

The recommended next branch is a docs-only schema/RLS/RPC design branch. Capability implementation, DB schema/migration, Supabase query code, production router wiring, route enablement, endpoint exposure, public exposure, cross-language delegation implementation, Cockpit/detail drawer, copy/export, retention/cleanup, raw storage access, direct MemoryFacade access, prompt/provider/runtime/execution changes, autonomous execution, and self-repair remain not approved.
