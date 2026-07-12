# Dry-Run Historical Audit API Capability Source Implementation

## 1 Executive Summary

This branch implements the narrow server-side capability source foundation for `historical_audit:read`.

The implementation adds a Supabase grant-table migration, a Rust capability resolver abstraction, fail-closed resolver tests, and safe route-envelope metadata. It keeps the protected historical audit route skeleton isolated and disabled. It does not wire the production router, enable the route, expose an endpoint, add public or no-auth `/internal/*` routes, add Cockpit/detail drawer UI, add copy/export, add cross-language delegation, modify `MemoryFacade`, modify `HistoricalDryRunAuditQueryService`, or change runtime/provider/prompt/retry/replan/autonomy/self-repair behavior.

## 2 Files Changed

- `supabase/migrations/20260711120000_omni_capability_grants.sql`
- `backend/rust/src/historical_audit_capability.rs`
- `backend/rust/src/protected_historical_audit.rs`
- `backend/rust/src/main.rs`
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-implementation.md`

## 3 Migration Result

The migration creates `public.omni_capability_grants` as a server-owned capability grant table.

The first and only approved capability is constrained to the exact value `historical_audit:read`. The table stores `supabase_sub`, active/revoked/expiration state, created/updated metadata, review metadata, and JSON metadata bounded by `omni_capability_grants_metadata_size_check`.

RLS is enabled. No anon/authenticated client policies are added. The table comments document that browser clients must not directly read or mutate capability grants.

The migration adds lookup, active lookup, capability, expiration, and updated-at indexes. It intentionally does not enforce uniqueness with a temporal predicate because expired historical grants must be able to coexist with one current effective grant. Duplicate current effective grants deny in the Rust resolver. The metadata size check limits `metadata::text` to 8192 bytes.

## 4 Resolver Result

`backend/rust/src/historical_audit_capability.rs` adds:

- `CapabilityGrantRepository` trait for server-controlled grant lookup.
- `HistoricalAuditCapabilityResolver` for exact `historical_audit:read` authorization.
- `CapabilityDecision` with safe allow/deny state, categorical reason, and source mode.
- `CapabilityGrantLookup` for safe source states: records, unavailable, timeout, misconfigured, and forbidden.
- `UnavailableCapabilityGrantRepository` as the production-safe default, which denies.
- `StaticTestCapabilityGrantRepository` under `#[cfg(test)]` only.

The resolver uses only the authenticated Supabase `sub` supplied by the existing auth middleware boundary. It does not accept client, header, query-param, request-body, cookie, or environment-only production authority.

## 5 Fail-Closed Behavior

The resolver allows only when:

- caller identity is present and safe;
- required capability is exactly `historical_audit:read`;
- source lookup succeeds;
- the returned grant matches the caller and exact capability;
- the grant is active;
- the grant is not revoked;
- the grant is not expired;
- no duplicate effective active grant exists.

It denies missing, empty, inactive, revoked, expired, malformed, duplicate, unavailable, timed-out, misconfigured, forbidden, or wrong-capability grant states.

## 6 Safe Error, Audit, and Observability Behavior

The route envelope now includes only safe categorical capability-source metadata:

- `audit.capability_source_mode`
- `observability.capability_source_mode`

It does not expose raw grant rows, SQL, Supabase responses, tokens, service-role material, authorization headers, cookies, secrets, stack traces, stdout, stderr, command arguments, file contents, prompts, provider payloads, raw exceptions, or raw reprs.

## 7 Route Exposure Status

Production route wiring remains blocked. `backend/rust/src/main.rs` only declares modules for compilation and does not merge `protected_historical_audit_router(...)` into the production Axum router.

No endpoint is exposed. No public route or no-auth `/internal/*` route was added.

## 8 Tests Added

Focused Rust tests cover:

- exact active server-side grant allow;
- missing or invalid caller deny;
- missing grant deny;
- revoked grant deny;
- expired grant deny;
- inactive grant deny;
- duplicate grant deny;
- malformed/wrong capability deny;
- unavailable source deny;
- timeout deny;
- misconfigured source deny;
- forbidden source deny;
- test-only static grants work only through isolated test construction.

Existing protected historical audit tests continue to cover disabled route precedence, missing JWT, invalid JWT, missing caller identity, missing capability, query validation, rate limiting, safe envelopes, and no `/internal/audit/dry-run` route.

## 9 Remaining Boundaries

This branch intentionally does not implement a live Supabase HTTP/PostgREST client or RPC call. The repository trait is the server-side boundary for the later reviewed source adapter. The default production resolver remains misconfigured/unavailable and denies closed until a future branch explicitly adds server-only source configuration and keeps the route exposure controls approved.

The route switch remains disabled by default, and the router remains unwired.

## 10 Migration Validation Status

Supabase preview branch validation was not available in this local environment.

Local migration validation was attempted with Docker Postgres because the repository has no dedicated Supabase migration CI step, `supabase` CLI is not installed, and `psql` is not installed. Docker Desktop was started, but `docker info` timed out and the Docker daemon did not become available. No database migration success is claimed from this environment.

Static review updates made during this fix:

- `omni_capability_grants_metadata_size_check` bounds `metadata::text` to 8192 bytes.
- Active grant indexing is non-unique so expired historical grants can coexist with a current effective grant.
- Duplicate current effective grants remain fail-closed in the Rust resolver.
