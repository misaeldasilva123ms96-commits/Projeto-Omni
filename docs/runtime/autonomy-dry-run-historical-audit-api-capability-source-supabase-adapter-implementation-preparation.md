# Historical Dry-Run Audit API Supabase Capability Adapter Implementation Preparation

## 1. Executive summary

This documentation-only review converts the merged Supabase capability-adapter design into an implementation-ready contract for a future server-side `SupabaseCapabilityGrantRepository` serving only `historical_audit:read`.

It corrects two inherited ambiguities. First, `capability_source_mode` identifies the repository origin and is limited to `supabase_grants`, `unavailable`, or `static_test`; lookup failures are not source modes. Second, the live PostgREST request selects only potentially effective grants and uses `limit=2`, so accumulated inactive, revoked, or expired history cannot deny access by inflating response cardinality.

The future adapter is conditionally approved only after explicit Misael approval. This branch implements no adapter, dependency, configuration, secret, call, state integration, router wiring, route enablement, endpoint exposure, or frontend behavior.

## 2. Scope

This review defines the exact future Rust module, adapter, asynchronous repository boundary, configuration model, secret boundary, URL and network controls, PostgREST request, response validation, safe errors, tests, rollout, rollback, blockers, and acceptance gates.

## 3. Non-goals

Adapter code, PostgREST/RPC/SQL calls, dependencies, migrations, environment files, secrets, `AppState` changes, router wiring, route enablement, endpoint exposure, public access, Cockpit UI or detail-drawer work, copy/export, retention, Python delegation, `MemoryFacade`, `HistoricalDryRunAuditQueryService`, and runtime/provider/prompt/retry/replan/autonomy/self-repair behavior are out of scope.

## 4. Reviewed materials

- `backend/rust/src/historical_audit_capability.rs`
- `backend/rust/src/protected_historical_audit.rs`
- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs`
- `backend/rust/src/error.rs`
- `backend/rust/src/run_control.rs`
- `backend/rust/Cargo.toml`
- `supabase/migrations/20260711120000_omni_capability_grants.sql`
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-implementation.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-supabase-adapter-design-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-protected-route-skeleton.md`
- `ROADMAP.md`
- `docs/status/current-state.md`
- `docs/roadmap/omni-post-omniroute-roadmap.md`
- Existing Rust authentication, `AppState`, configuration, timeout, safe-error, URL/log sanitization, redaction, and test patterns.

## 5. Current main baseline

Inspection used current `origin/main` at `364f810f576fcab68c3c09a48627a982f46cf731`. Required prerequisite PRs #529 (`3502b0518237da488cd14fc5a321cf304b304c25`), #530 (`b0f3e39abbc1135234b1edf9b3136e1287e2f83d`), and #531 (`9729a16318711ddf8169ae07ffe7724c95e627c7`) are merged. The current roadmap keeps capability-source implementation, production wiring, route enablement, and endpoint exposure as independently governed tracks.

## 6. Current capability-source implementation state

`CapabilityGrantRepository`, `CapabilityGrantRecord`, `CapabilityGrantLookup`, `HistoricalAuditCapabilityResolver`, and the fail-closed unavailable repository exist. `CapabilityGrantLookup` currently has `Records`, `Unavailable`, `Timeout`, `Misconfigured`, and `Forbidden`, but not `Malformed`. Static grants exist only under `#[cfg(test)]`. Production has no live repository.

The current trait and resolver are synchronous. A network adapter must not block a Tokio worker; the future adapter branch must make lookup and authorization asynchronous while preserving trait-object use and existing semantics.

## 7. Current protected-route state

`protected_historical_audit.rs` contains dormant candidate routes protected by existing Supabase JWT middleware and a route-specific `historical_audit:read` check. `main.rs` declares the module for compilation but does not call or merge `protected_historical_audit_router`. The production router remains unwired, the route remains disabled, and no endpoint is exposed.

## 8. Current database/RLS state

`public.omni_capability_grants` stores UUID `supabase_sub`, exact capability, active/revoked/expiration state, audit fields, and bounded metadata. The capability check permits only `historical_audit:read`. RLS is enabled and no `anon` or `authenticated` client policies grant access. Service-role access bypasses RLS, so server isolation remains mandatory.

## 9. Current adapter state

No Supabase adapter, outbound Rust HTTP client, service-role configuration, PostgREST call, RPC, direct database connection, or adapter test harness exists. `Cargo.toml` has no outbound HTTP, UUID, or timestamp parsing dependency suitable for this adapter.

## 10. Inherited design decisions

Retain authenticated Supabase `sub` as the only caller identity; exact server-owned `historical_audit:read`; server-only access; fixed PostgREST table `SELECT`; strict projection; fail-closed decisions; bounded timeout; no retry; no authorization cache; reusable connections; strict parsing; categorical errors; secret redaction; disabled-by-default production behavior; and separate governance for state integration, routing, enablement, exposure, and UI.

Supersede the inherited five-row/four-row historical query and any failure-derived source mode.

## 11. Corrected source-mode contract

`capability_source_mode` describes the repository origin, not a lookup result:

| Repository | Source mode |
| --- | --- |
| Initialized live Supabase repository | `supabase_grants` |
| Disabled, absent, or unconstructed production repository | `unavailable` |
| Test-only static repository | `static_test` |

An initialized Supabase adapter remains `supabase_grants` when it times out, is forbidden, receives malformed data, or becomes unavailable. `timeout`, `forbidden`, `malformed`, and `misconfigured` are prohibited as source modes.

## 12. Corrected lookup-outcome contract

Lookup results are independent of source identity. Example: `source_mode=supabase_grants`, `CapabilityGrantLookup::Timeout`, and `decision_reason=capability_source_timeout`. The same separation applies to `Unavailable`, `Forbidden`, `Malformed`, and `Misconfigured`.

Only a repository that could not be safely constructed uses `source_mode=unavailable`; its lookup outcome is normally `Misconfigured` or `Unavailable`.

## 13. `CapabilityGrantLookup::Malformed` decision

Approve adding `CapabilityGrantLookup::Malformed` in the future implementation branch. It covers invalid content type, invalid JSON, invalid envelope, missing required fields, prohibited unexpected fields, invalid UUID/timestamp, wrong caller/capability, oversized body, unexpected cardinality, invalid boolean/null semantics, truncated response, and unsupported response encoding.

It maps to deny, `decision_reason=capability_source_malformed`, while an initialized adapter keeps `capability_source_mode=supabase_grants`. Raw parser, body, transport, and database details never cross the adapter boundary.

## 14. Required `CapabilityGrantLookup` variants

- `Records(Vec<CapabilityGrantRecord>)`
- `Unavailable`
- `Timeout`
- `Forbidden`
- `Malformed`
- `Misconfigured`

The enum remains a safe categorical boundary and carries no raw string or source error.

## 15. Required `CapabilityDecision` mappings

| Lookup/validation result | Allowed | Decision reason |
| --- | --- | --- |
| Exactly one fully revalidated effective grant | Yes | `capability_granted` |
| `Records([])` | No | `missing_capability_grant` |
| Two effective records | No | `duplicate_capability_grant` |
| `Unavailable` | No | `capability_source_unavailable` |
| `Timeout` | No | `capability_source_timeout` |
| `Forbidden` | No | `capability_source_forbidden` |
| `Malformed` | No | `capability_source_malformed` |
| `Misconfigured` | No | `capability_source_misconfigured` |

The current legacy allow and missing reasons must be migrated in the future branch with regression tests. Invalid authenticated caller input remains a safe deny and must not trigger transport.

## 16. Required safe decision reasons

The adapter/resolver integration allowlists `capability_granted`, `missing_capability_grant`, `duplicate_capability_grant`, `capability_source_unavailable`, `capability_source_timeout`, `capability_source_forbidden`, `capability_source_malformed`, and `capability_source_misconfigured`. Any additional reason requires explicit review; raw details are never substituted for a category.

## 17. Proposed Rust module

Use private module `backend/rust/src/supabase_capability_grant_repository.rs`. It owns validated configuration types, request construction, transport, bounded body reading, strict DTO parsing, conversion, and safe lookup mapping. It owns no router or handler.

## 18. Proposed adapter type

Use `pub(crate) struct SupabaseCapabilityGrantRepository` containing a validated project origin, opaque service-role secret, reusable HTTP client, validated timeout, and fixed constants. Its custom `Debug` must redact the secret and omit origin/query details.

## 19. Proposed trait implementation

The repository lookup must become asynchronous. Prefer an object-safe boxed-future signature, avoiding a blocking client and preserving `Arc<dyn CapabilityGrantRepository>`:

```rust
fn lookup_grants<'a>(
    &'a self,
    caller_sub: &'a str,
    capability: &'a str,
    now_ms: u64,
) -> Pin<Box<dyn Future<Output = CapabilityGrantLookup> + Send + 'a>>;
```

`HistoricalAuditCapabilityResolver::authorize`/`authorize_at` must await it. Static and unavailable repositories return immediately ready futures. This future change belongs only to the explicitly approved implementation branch.

## 20. Proposed constructor inputs

Constructor inputs are `ValidatedSupabaseProjectOrigin`, `SecretServiceRoleKey`, reusable `reqwest::Client`, and `CapabilityLookupTimeout`. Test construction may inject a clock or transport seam. Requests, headers, cookies, caller JWTs, environment maps, arbitrary URLs, paths, tables, columns, operators, selects, limits, or capabilities are forbidden constructor inputs.

## 21. Proposed `AppState` boundary

Future integration should store an `Arc<HistoricalAuditCapabilityResolver>` or `Arc<dyn CapabilityGrantRepository>` constructed once at startup. Handlers receive only the resolver. This preparation does not select or implement that integration, and the adapter-only branch must not add it without separate explicit approval.

## 22. Proposed configuration provider

Choose dedicated capability-adapter server configuration, loaded once by a narrow future factory. Do not reuse `SupabaseAuthConfig`: it contains JWT validation material and permits a browser-facing `VITE_SUPABASE_URL` fallback, while the adapter requires a privileged server-only origin and service-role secret with stricter validation.

## 23. Required configuration names

- `OMNI_HISTORICAL_AUDIT_CAPABILITY_SOURCE`
- `OMNI_HISTORICAL_AUDIT_SUPABASE_URL`
- `OMNI_HISTORICAL_AUDIT_SUPABASE_SERVICE_ROLE_KEY`
- `OMNI_HISTORICAL_AUDIT_CAPABILITY_TIMEOUT_MS`
- `OMNI_HISTORICAL_AUDIT_CAPABILITY_ADAPTER_ENABLED`

No name is added by this branch. Future accepted source values are `unavailable` (default) and `supabase_grants`; `static_test` is construction-only under `#[cfg(test)]`. Live construction requires source `supabase_grants`, adapter enabled, and all validated live inputs.

## 24. Server-only secret-loading boundary

Load the service-role key only in the Rust server process through the approved deployment secret provider. Never read it from a request, frontend build variable, checked-in file, command argument, or client-visible configuration. Wrap it in a non-`Debug`/non-`Display` secret type and attach it only at send time.

## 25. Service-role isolation

Use the key only for the fixed capability lookup. Never expose it to browsers, Python, provider runtimes, prompts, tools, child processes, telemetry, health payloads, crash strings, or test snapshots. The future client sends fixed `apikey` and `Authorization: Bearer` headers containing the service-role material; it never forwards the caller JWT.

## 26. Service-role rotation

Rotation is an operator procedure: provision a replacement secret, update the secret provider, restart/redeploy to rebuild clients, verify categorical health without values, then revoke the old key. Suspected disclosure requires immediate rotation and adapter disablement. No dual-key automatic fallback or secret logging is approved.

## 27. Missing-secret behavior

If the adapter is disabled, missing live secrets are tolerated because the unavailable repository is selected. If live source and enable flag are requested, an absent or empty secret prevents adapter construction and yields `source_mode=unavailable`, lookup `Misconfigured`, and `capability_source_misconfigured`. It never falls back to anon keys or caller JWTs.

## 28. Invalid-configuration behavior

Unknown source, contradictory gates, invalid URL, invalid timeout, placeholder values, or malformed secret prevent live construction. Production remains disabled and fail-closed. Startup/health may report only a safe category such as `capability_adapter_misconfigured`, never the variable value, URL, host, key length, or parser error.

## 29. Supabase project URL validation

Parse once as an absolute URL. Require exactly an origin: no userinfo, path other than `/`, query, fragment, IP literal, localhost, or Unicode/punycode ambiguity. Normalize only a trailing slash and retain the validated typed origin. Do not accept `VITE_SUPABASE_URL` fallback.

## 30. HTTPS-only requirement

Require `https`, TLS certificate and hostname verification, TLS 1.2 or newer, and port 443 only. Plain HTTP is permitted only for a loopback test harness compiled under tests; it is never accepted by production configuration.

## 31. Host allowlist requirement

Initial production approval permits only the exact configured project-ref host matching lowercase `<project-ref>.supabase.co`; custom domains, regional aliases, IPs, wildcard runtime overrides, and arbitrary hosts require separate review. Validate the project-ref grammar and compare the final request host exactly to the validated origin.

## 32. Path construction rules

Append the compile-time literal `/rest/v1/omni_capability_grants` to the validated origin. Reject base paths. Use typed query serialization from fixed keys/values; never concatenate raw query fragments. The final path cannot be overridden by configuration or request data.

## 33. SSRF prevention

Enforce the origin, scheme, host, port, path, redirect, and proxy rules above. Reject loopback, private, link-local, multicast, unspecified, and reserved resolved addresses for production requests. Re-check every resolved A/AAAA result before connection and preserve TLS SNI/hostname validation. No alternate host, user-controlled DNS name, or URL override is accepted.

## 34. Redirect policy

Configure zero redirects. Every 3xx response is `Malformed` because the fixed resource must not redirect. Never follow a redirect even when it appears to remain on the same host.

## 35. Proxy policy

Build the privileged client with ambient proxies disabled. If deployment later requires a proxy, it needs separate approval, a fixed trusted endpoint, TLS and secret-handling review, and tests proving it cannot change destinations or log credentials. Proxy failure never triggers direct fallback.

## 36. DNS/network failure policy

DNS failure, rejected resolution, TLS failure, connect failure, reset before a valid response, or network partition maps to `Unavailable`. A completed `200` whose body is truncated maps to `Malformed`. No alternate DNS target, region, host, retry, or raw transport detail is exposed.

## 37. Recommended HTTP client dependency

Recommend `reqwest` with `default-features = false` and Rustls TLS only, reviewed and pinned in the future branch. Configure one reusable client with redirect disabled, proxies disabled, bounded connect/request timeouts, no automatic content decoding, and connection reuse. Do not use `reqwest::blocking` in Tokio.

## 38. Dependency alternatives

`hyper`/`hyper-util` offers lower-level control but substantially more request, TLS, redirect, proxy, and body-limit code. Direct PostgreSQL adds credentials, pooling, TLS, and operational surface. A bespoke `TcpStream` HTTP client is prohibited. The future branch will also need reviewed UUID and RFC 3339 parsing support, preferably `uuid` and `time`; dependency changes are not approved here.

## 39. Connection pooling/reuse

Create one client at startup and reuse its bounded pool. Never create a client per lookup. Do not pool database connections because the selected method is PostgREST. Idle connection lifetime and per-host idle count must be bounded and tested; a reused connection does not authorize caching.

## 40. Required timeout

Default end-to-end timeout is 750 ms, covering pool acquisition, DNS, connect, TLS, headers, and full body read. `OMNI_HISTORICAL_AUDIT_CAPABILITY_TIMEOUT_MS` may be accepted only in the reviewed range 100-2,000 ms. Zero, parse failure, or out-of-range values are misconfiguration. The resolver-supplied time remains fixed for the entire lookup.

## 41. Request cancellation

Dropping or timing out the lookup future must cancel response/body work. The adapter returns `Timeout` only once and must not leave background retries, detached tasks, or body readers. Cancellation caused by request shutdown never turns into an allow.

## 42. No-retry decision

No automatic retry on timeout, 429, 5xx, connection failure, DNS failure, forbidden, malformed, or misconfigured outcomes. Authorization fails closed on the first attempt, preventing retry amplification and inconsistent decisions.

## 43. No-cache decision

No positive or negative authorization cache. Connection reuse is allowed; grant-result reuse is not. Every future authorization decision performs one fresh lookup so grant, revocation, and expiration changes become effective on the next request.

## 44. Revocation freshness

The request includes `revoked_at=is.null`, and the resolver revalidates `revoked_at`. Revoked historical rows remain in the database but are excluded from live lookup. No cache or retry extends a revoked authorization.

## 45. Expiration freshness

Generate one UTC RFC 3339 timestamp from the server `now_ms` passed to lookup. Request `expires_at is null OR expires_at > now`. The resolver revalidates expiration against the same `now_ms`, preventing boundary drift between query and decision.

## 46. Exact PostgREST resource path

The sole resource is `GET /rest/v1/omni_capability_grants`. No RPC, view, alternate schema, table, method, write, or direct SQL is approved for the initial implementation.

## 47. Exact selected columns

The exact projection, in fixed order, is:

```text
select=supabase_sub,capability,active,revoked_at,expires_at
```

These are exactly the fields required to construct `CapabilityGrantRecord`. Do not select `id`, `metadata`, `created_at`, `updated_at`, `created_by`, `updated_by`, `grant_reason`, `grant_source`, `review_ticket`, or any unrelated audit field.

## 48. Exact server-generated filters

The fixed logical filters are:

```text
supabase_sub=eq.<canonical-authenticated-uuid>
capability=eq.historical_audit:read
active=eq.true
revoked_at=is.null
or=(expires_at.is.null,expires_at.gt.<server-utc-rfc3339>)
limit=2
```

Use typed query encoding. Only the already authenticated Supabase `sub` and server timestamp vary. Table, schema, columns, operators, order, limit, select, RPC name, URL, and capability are server-owned constants.

## 49. Effective-grant-only query

Approve querying only potentially effective records: exact caller, exact capability, active, not revoked, and unexpired at server time. Expired, revoked, and inactive history remains stored but is irrelevant to the live authorization lookup. The resolver still revalidates every returned semantic field.

## 50. Strict limit of two

Set `limit=2`. Zero rows become `Records([])`. One row is passed to the resolver. Two rows are both passed to the resolver and deny as `duplicate_capability_grant`. A response array containing more than two rows violates the request contract and maps to `Malformed`; no row is selected or dropped.

## 51. No pagination

Do not send `Range`, `offset`, cursor, count preference, or pagination requests. Do not interpret `Content-Range` as permission to fetch another page. Authorization is decided from the one bounded request only.

## 52. No follow-up authorization query

Exactly one PostgREST request is allowed per decision. No count query, history query, duplicate confirmation, retry, fallback query, RPC, or SQL follow-up is allowed.

## 53. Response body maximum size

Set a hard decompressed/received body cap of 16,384 bytes for the two-row projection. Reject an excessive `Content-Length` before reading and enforce the cap while streaming when length is absent or dishonest. Never truncate and parse a prefix. Oversize maps to `Malformed`.

## 54. Content-Type validation

Accept only `application/json` with an optional UTF-8 charset on a successful `200`. Missing, multiple/conflicting, vendor-object, HTML, text, or other content types map to `Malformed`. Status mapping occurs before body parsing, without exposing the body.

## 55. JSON parsing rules

Require one complete top-level JSON array containing zero, one, or two objects. Reject trailing data, duplicate object keys where the parser can detect them, excessive nesting, non-array envelopes, null array entries, and partial/truncated JSON. Parsing occurs only after size and content-type validation.

## 56. Strict row validation

Use a private DTO with `deny_unknown_fields`. Require exactly `supabase_sub`, `capability`, `active`, `revoked_at`, and `expires_at`; only lifecycle timestamps may be null. Reject missing/extra fields, wrong types, numeric/string booleans, invalid nulls, wrong caller, and wrong capability before constructing any record.

## 57. Timestamp parsing

Parse non-null Postgres `timestamptz` values as strict offset-aware RFC 3339 instants, normalize to UTC, and convert exactly to non-negative `u64` milliseconds. Reject missing offset, local time, leap/overflow/pre-epoch values, excess unsupported precision, and lossy conversion. The resolver receives the parsed optional millisecond values.

## 58. UUID parsing

Parse the authenticated `sub` as UUID before transport and serialize canonical lowercase hyphenated form. Parse every returned `supabase_sub` and require UUID equality with the authenticated caller. Invalid or noncanonical-equivalent input is denied before lookup; an invalid/wrong returned UUID is `Malformed`.

## 59. Caller identity validation

Caller identity comes only from `AuthenticatedSubject.user_id` inserted by `require_supabase_auth`. No body, query, path, cookie, arbitrary header, frontend state, capability header, or environment allowlist may supply or override it. Resolver validation remains in place after adapter validation.

## 60. Exact capability validation

The adapter accepts only the resolver-owned literal `historical_audit:read`; any other argument returns `Misconfigured` without transport. Every returned row must match the literal exactly and case-sensitively. Wildcards, aliases, prefixes, lists, and client values are forbidden.

## 61. Duplicate effective-grant handling

Two returned rows are not deduplicated or reduced. Pass both typed rows to the resolver, which must deny with `duplicate_capability_grant`. The adapter never chooses newest/oldest and never issues a follow-up query.

## 62. Unexpected cardinality handling

An array longer than two, a non-array envelope, contradictory response range metadata, or evidence that the server ignored the fixed limit is `Malformed`. Empty, one-row, and two-row arrays follow the normal mappings. No raw cardinality or response metadata is exposed.

## 63. Malformed response handling

All malformed cases return only `CapabilityGrantLookup::Malformed`. The resolver denies with `capability_source_malformed` and retains `source_mode=supabase_grants`. Do not log the body, parser error, offending field/value, URL, or row.

## 64. HTTP status mapping

| Result | Lookup outcome |
| --- | --- |
| `200` with valid bounded array | `Records` |
| `200` with invalid body/headers | `Malformed` |
| `204` or any `3xx` | `Malformed` |
| `400`, `404`, `405`, `406`, `415`, other contract `4xx` | `Misconfigured` |
| `401` or `403` | `Forbidden` |
| `408` or local end-to-end deadline | `Timeout` |
| `429` | `Unavailable` |
| `5xx`, including gateway timeout | `Unavailable` |

No status body is read for diagnostics beyond bounded discard required by the client, and no source status is returned to callers.

## 65. Authentication failure mapping

Incoming missing/invalid/expired Supabase JWT remains an existing middleware `401`; the adapter is not called. PostgREST `401` indicates rejected server credential and maps to `Forbidden`, then `capability_source_forbidden`, without revealing whether the key was absent, invalid, or rotated.

## 66. Authorization failure mapping

Valid caller authentication plus zero grants, duplicate grants, or a source category produces an Omni authorization deny. The route should return its existing safe `403` category only after future wiring is separately approved. No source body/status or row is included.

## 67. Database permission failure mapping

PostgREST `403` or equivalent service-role permission denial maps to `Forbidden`. RLS/policy/table/role/SQLSTATE details are never exposed. Repeated permission failure is an operational alert, not a reason to retry or use anon/authenticated access.

## 68. Timeout mapping

Only the local 750 ms deadline or explicit HTTP `408` maps to `Timeout`. It denies with `capability_source_timeout`, retains `supabase_grants`, cancels work, and performs no retry. Gateway `504` is source `Unavailable`, preserving a distinction between Omni's deadline and upstream failure.

## 69. Source unavailable mapping

Validated adapter network/DNS/TLS/connect failures, `429`, and `5xx` map to `Unavailable`, then `capability_source_unavailable`, with `source_mode=supabase_grants`. A disabled/unconstructed repository may also return `Unavailable`, but its source mode is `unavailable`.

## 70. Safe audit metadata

Allowlist route identifier, operation, allowed boolean, safe decision reason, safe source mode, adapter-enabled boolean, route-enabled boolean, Omni response category, bounded latency bucket, and timestamp. Omit caller identity or use only a separately reviewed irreversible pseudonym. Never include row counts above the safe category boundary.

## 71. Safe observability metadata

Allowlist counters by safe source mode, safe lookup outcome, safe decision reason, latency bucket, and adapter enabled/disabled state. Metrics must have bounded cardinality and no project, host, caller, URL, query, status body, database, or secret labels.

## 72. Forbidden logging fields

Never log service-role key, `apikey`, authorization header, caller JWT, cookie, raw caller `sub`, project URL/host, full request URL, query string, response headers/body, raw row, database error, SQLSTATE, connection string, parser input, stack trace, raw exception, secret length/hash, or credentials.

## 73. No raw PostgREST response exposure

The raw response stays inside the adapter and is converted only to typed records or a categorical lookup. It is never returned in HTTP responses, audit envelopes, observability, snapshots, errors, tests, or documentation evidence.

## 74. No raw database error exposure

PostgREST error JSON, database message/detail/hint/code, SQLSTATE, policy, role, table, schema, and SQL never leave the adapter. Only `Forbidden`, `Misconfigured`, or `Unavailable` is retained according to status.

## 75. No URL/query-string exposure

Do not emit the origin, resource path plus filters, encoded URL, query string, or request builder error. Logs identify only a fixed operation such as `historical_audit_capability_lookup` and safe category.

## 76. Unit-test preparation

Use synthetic UUIDs, marker secrets, fake clocks, and an injected local transport. Cover constructor validation, async cancellation, exact request construction, strict conversion, all variants/mappings, source-mode stability, body bounds, and no code path that directly allows inside the adapter.

## 77. Mock repository regression tests

Preserve and update resolver tests for one grant, none, duplicates, inactive/revoked/expired values, historical combinations, wrong caller/capability, invalid identity, unavailable, timeout, forbidden, misconfigured, malformed, and static test mode. Assert canonical future reason names and source mode independent of outcome.

## 78. HTTP adapter test harness

Use a loopback-only mock server under tests. Capture method, path, parsed query pairs, and header presence without snapshotting secrets. Support delayed headers/body, chunked/truncated/oversized bodies, arbitrary status/content type/encoding, and connection close. Production URL validation remains strict.

## 79. Success test matrix

| Case | Expected result |
| --- | --- |
| Exact valid effective grant | `Records([record])` then `capability_granted` |
| No effective grant | `Records([])` then `missing_capability_grant` |
| Two effective grants | Two records then `duplicate_capability_grant` |
| Nullable expiration | Valid record |
| Future expiration | Valid record and resolver revalidation |

Assert one request, exact projection/filters, limit two, no pagination, no follow-up, no retry, no cache, and no caller JWT forwarding.

## 80. Failure test matrix

Cover 401, 403, 404, 408, 429, every 5xx class used by the harness, connection refusal/reset, DNS failure seam, TLS failure seam, forbidden redirect, invalid/non-HTTPS URL, missing secret, invalid timeout, contradictory feature gates, and cancellation. Assert exact categorical outcome, deny, stable source mode, and no raw detail.

## 81. Malformed-response test matrix

Cover invalid/missing/conflicting content type; invalid/trailing/truncated JSON; object or null envelope; zero/one/two valid rows; three rows; missing and unexpected fields; duplicate keys where supported; invalid UUID/timestamp; wrong caller/capability; invalid boolean/null semantics; oversized body with and without `Content-Length`; unsupported encoding; and misleading range metadata.

## 82. Timeout test matrix

Test slow DNS seam, connect, TLS, headers, first byte, and body completion against the end-to-end deadline. Assert cancellation near the configured bound, exactly one attempt, `Timeout`, `capability_source_timeout`, no detached work, and no response details.

## 83. Secret-redaction test matrix

Use unique marker secrets through successful, forbidden, misconfigured, network, timeout, redirect, parse, debug, display, tracing, panic-safe, health, and snapshot paths. Assert the marker, bearer form, header value, length, and derived URL never appear. Test caller JWT non-forwarding separately.

## 84. URL/SSRF test matrix

Reject HTTP, userinfo, path/query/fragment, non-443 port, IP literals, localhost, private/link-local/multicast/reserved resolutions, uppercase/invalid project refs, lookalike suffixes, custom domains, redirect responses, ambient proxies, and runtime URL overrides. Accept only the canonical approved Supabase project origin and fixed resource.

## 85. Duplicate-grant tests

Return exactly two effective rows in both orders and assert both reach the resolver and deny. Return three rows despite `limit=2` and assert `Malformed`, not duplicate. Assert no deduplication, ordering choice, count query, or second request.

## 86. Historical-grant tests

Seed expired, revoked, and inactive history plus zero/one/two effective rows. Assert the request filters exclude history regardless of accumulated count, one effective row can authorize, zero denies missing, two deny duplicate, and the resolver still rejects any historical or malformed row injected by a mock bypassing the query.

## 87. Supabase integration-test preparation

Use an ephemeral local/preview Supabase project with synthetic users and grants. Provision secrets only through CI/deployment secret storage. Verify fixed query behavior, browser-role denial, service-only read, exact caller/capability, revocation/expiration freshness, duplicate denial, and cleanup. Keep the production router unwired.

## 88. Supabase preview validation

Before implementation approval closes, record project-neutral evidence: environment class, commit, migration identifier, safe test names/counts, result, and timestamp. Do not record project URL/ref, keys, JWTs, headers, SQL output containing data, raw rows, or error bodies.

## 89. Local-test strategy

Unit and mock HTTP tests are the default and require no real network or credentials. Optional local Supabase integration uses synthetic data and an isolated test-only origin path. Tests must prove no route wiring, endpoint exposure, provider/runtime/tool execution, Python delegation, or environment mutation.

## 90. Feature-switch design

Two server-owned gates are required: source must equal `supabase_grants` and `OMNI_HISTORICAL_AUDIT_CAPABILITY_ADAPTER_ENABLED` must be explicitly true. Source `unavailable` or disabled flag selects the unavailable repository. Unknown or contradictory configuration is misconfigured and fails closed. These gates do not register or enable a route.

## 91. Disabled-by-default behavior

Defaults are source `unavailable` and adapter enabled `false`. Missing configuration never enables access. Even a fully constructed adapter does not wire the router, enable the route, or expose an endpoint.

## 92. Rollout plan

1. Obtain explicit Misael approval for the narrow implementation branch.
2. Add `Malformed`, async trait/resolver evolution, private adapter/config types, reviewed dependencies, and unit/mock tests only.
3. Validate local/preview Supabase with synthetic data and complete security review.
4. Keep the adapter disabled and production repository unavailable.
5. Seek separate approval for `AppState` integration; later seek independent router wiring, route enablement, and endpoint exposure approvals.

## 93. Rollback plan

Disable the adapter or select source `unavailable`, redeploy, and verify categorical disabled state. If secret exposure is suspected, rotate immediately. Revert only the adapter/config integration commit set; do not delete historical grants or alter migration data. Router remains unwired, so rollback exposes no endpoint.

## 94. Operational monitoring

Monitor bounded counters for lookup outcomes, decision reasons, latency buckets, cancellations, disabled/misconfigured state, and duplicate/malformed events. Alert on sustained forbidden, malformed, unavailable, timeout, or duplicate categories. Do not log URLs, queries, callers, rows, statuses with bodies, or secrets.

## 95. Abuse-case matrix

| Abuse case | Required result |
| --- | --- |
| Spoof caller through request input | Ignored/rejected; authenticated `sub` only |
| Supply capability through header/query/body | Ignored/rejected; server literal only |
| Inject PostgREST operator/select/path/limit | Impossible through typed fixed construction |
| Accumulate historical rows | Excluded by effective-only filters |
| Create two effective grants | Resolver denies duplicate |
| Force more than two response rows | `Malformed` deny |
| Redirect or SSRF to alternate host | Rejected, no follow |
| Stall or rate-limit source | Single fail-closed attempt |
| Return wrong/malformed row | `Malformed` deny |
| Steal service-role key | Rotation/disable incident; browser never receives key |
| Reuse stale positive/negative decision | Impossible; no result cache |
| Extract raw error through logs | Redaction test failure blocks release |

## 96. Security review checklist

- [ ] Explicit implementation approval exists.
- [ ] Async nonblocking trait boundary is reviewed.
- [ ] Dependencies and lockfile delta are reviewed.
- [ ] Dedicated configuration and disabled defaults are verified.
- [ ] URL, resolution, TLS, redirect, and proxy controls pass.
- [ ] Secret provider, isolation, rotation, and redaction pass.
- [ ] Exact request/projection/filter/limit contract passes.
- [ ] Size, content type, encoding, strict JSON, UUID, and time validation pass.
- [ ] All safe mappings and source-mode stability pass.
- [ ] No retry, cache, pagination, or follow-up query exists.
- [ ] Browser anon/authenticated roles remain denied.
- [ ] Router remains unwired and no endpoint is exposed.

## 97. Files allowed in future implementation branch

- `backend/rust/src/supabase_capability_grant_repository.rs`
- `backend/rust/src/historical_audit_capability.rs` for `Malformed`, async trait/resolver, canonical reasons, and focused tests
- A narrowly named private Rust configuration module if approved
- `backend/rust/Cargo.toml` and `backend/rust/Cargo.lock` only for reviewed adapter dependencies
- Focused Rust test modules/fixtures using synthetic data
- One implementation evidence document under `docs/runtime/`

`backend/rust/src/main.rs` is excluded from the initial adapter-only branch to preserve the separate `AppState` boundary.

## 98. Files prohibited in future implementation branch

Prohibit `main.rs`, `protected_historical_audit.rs`, migrations/schema, `.env`/`.env.example`, frontend/Cockpit, Python, `MemoryFacade`, `HistoricalDryRunAuditQueryService`, router/route handlers, public APIs, copy/export, retention/cleanup, provider/prompt/runtime/retry/replan/autonomy/self-repair, and unrelated manifests or workflows.

## 99. Exact future implementation scope

After explicit approval, implement only: `Malformed`; canonical decision mappings; asynchronous object-safe repository/resolver boundary; private validated configuration types/factory; `SupabaseCapabilityGrantRepository`; exact single-request PostgREST transport; strict parsing/conversion; safe errors/metadata; and focused unit/mock/integration evidence. Keep defaults unavailable and do not integrate `AppState`.

Recommended branch: `feature/autonomy-dry-run-historical-audit-api-capability-source-supabase-adapter-implementation`.

## 100. Remaining blockers before implementation

Explicit Misael approval; dependency/security review; final object-safe async signature; validated project-host/resolution strategy; approved server secret provider; service-role provisioning/rotation runbook; preview/local Supabase environment; confirmation of canonical reason migration compatibility; and acceptance of service-role blast radius.

## 101. Remaining blockers before `AppState` integration

Completed adapter implementation and tests; configuration factory review; startup/degraded behavior decision; safe health/observability contract; client lifecycle/pool review; preview evidence; secret availability in deployment; and separate explicit Misael approval. Integration must not imply routing.

## 102. Remaining blockers before router wiring

Approved `AppState` integration; resolver availability in handlers; auth/capability middleware ordering; disabled-route precedence; rate/query guards; security and abuse review; negative route-registration tests; and separate explicit Misael approval.

## 103. Remaining blockers before route enablement

Approved router wiring; deployment configuration and secrets; operational monitoring/alerts; rollback rehearsal; preview/staging authorization tests; operator runbook; default-disabled switch review; and separate explicit Misael approval.

## 104. Remaining blockers before endpoint exposure

Approved enablement; stable safe HTTP contract; authenticated/unauthenticated denial tests; payload/redaction review; abuse/rate limits; privacy and operational sign-off; no raw storage/delegation proof; and separate explicit Misael approval. Public exposure remains prohibited.

## 105. Remaining blockers before Cockpit consumption

Approved protected endpoint exposure; frontend-specific design/security review; safe typed client; redaction and no-raw-payload tests; loading/empty/error/degraded states; warning UX; authorization handling; and explicit approval. Copy/export remains separately prohibited.

## 106. Acceptance criteria

- All 108 preparation sections are present and reflect current main.
- Source mode is limited to `supabase_grants`, `unavailable`, and `static_test` and never changes per lookup.
- Future `Malformed` and canonical safe reasons are approved and exactly mapped.
- Caller is authenticated Supabase UUID `sub`; capability is exact server literal.
- One effective-only PostgREST request selects five required fields and uses `limit=2`.
- Resolver revalidates identity, capability, active, revoked, expiration, and duplicates.
- Timeout is bounded; retry, result cache, pagination, and follow-up lookup are absent.
- URL/SSRF, secret, response-bound, strict-parse, safe-error, and test contracts are exact.
- Dedicated adapter configuration is chosen and defaults disabled/fail-closed.
- Adapter implementation, dependencies, configuration, state, router, route, endpoint, UI, and runtime behavior remain unchanged in this branch.
- Only this document changes and docs-only validation passes.

## 107. Go/no-go table

| Area | Decision | Rationale |
| --- | --- | --- |
| Documentation | Go | Sole deliverable of this branch |
| Implementation preparation | Go | Exact future contract approved |
| `SupabaseCapabilityGrantRepository` implementation | No-go now / conditional future go | Requires explicit Misael approval and blockers closed |
| `CapabilityGrantLookup::Malformed` | Conditional future go | Required in adapter implementation, not this branch |
| PostgREST `SELECT` | Conditional future go | Fixed effective-only request under this contract |
| Dedicated RPC | No-go | Separate migration/security review required |
| Direct PostgreSQL | No-go | Larger credential/pooling/operations surface |
| Service-role use | Conditional future go | Server-only with acknowledged broad privilege |
| Existing Supabase server configuration reuse | No-go | Auth config and browser URL fallback are the wrong boundary |
| Dedicated capability-adapter configuration | Conditional future go | Selected model, server-only and isolated |
| Authenticated Supabase `sub` | Go | Sole caller identity |
| Exact `historical_audit:read` | Go | Sole server capability |
| Effective-grant-only query | Conditional future go | Corrected cardinality contract |
| Limit two | Conditional future go | Detects duplicate effective grants |
| Historical full-table query | No-go | History must not cause cardinality denial |
| Client-provided caller identity | No-go | Untrusted authority |
| Client-provided capability | No-go | Untrusted authority |
| Header-provided capability | No-go | Untrusted authority |
| Query-param capability | No-go | Untrusted authority |
| Body-provided capability | No-go | Untrusted authority |
| Positive authorization cache | No-go | Revocation/expiration freshness |
| Negative authorization cache | No-go | Grant/outage freshness |
| Automatic retry | No-go | Fail closed without amplification |
| Safe categorical errors | Go | Required boundary |
| Raw PostgREST logging | No-go | Sensitive source data |
| `AppState` integration | No-go | Separate phase |
| Production router wiring | No-go | Separate phase |
| Route enablement | No-go | Separate phase |
| Endpoint exposure | No-go | Separate phase |
| Public exposure | No-go | Prohibited |
| Cross-language delegation | No-go | Out of scope |
| Cockpit/detail drawer | No-go | Later separate review |
| Copy/export | No-go | Separate governance required |
| Runtime/provider/prompt changes | No-go | Out of scope |
| Autonomous execution | No-go | Out of scope |
| Self-repair | No-go | Out of scope |

## 108. Final recommendation

Approved for docs-only implementation preparation. Approved to separate source mode from lookup outcome. Approved to add `CapabilityGrantLookup::Malformed` in a future implementation. Approved for exact `historical_audit:read`, authenticated Supabase `sub` as the only caller identity, an effective-grant-only PostgREST query, strict limit two, a bounded timeout, no automatic retry, no positive or negative authorization cache, and fail-closed behavior.

Conditionally approve a future narrow adapter implementation branch only after explicit Misael approval and closure of the implementation blockers. Do not approve adapter code, dependencies/configuration, secret configuration, `AppState` integration, router wiring, route enablement, endpoint exposure, Cockpit consumption, copy/export, or runtime/provider/prompt/retry/replan/autonomy/self-repair changes in this branch.
