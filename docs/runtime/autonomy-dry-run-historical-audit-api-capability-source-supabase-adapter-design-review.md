# Historical Dry-Run Audit Capability Source Supabase Adapter Design Review

## 1. Executive summary

This documentation-only review approves a future, narrow, server-only Supabase adapter for `CapabilityGrantRepository`. The preferred initial access method is a fixed PostgREST table `SELECT` performed by the Rust backend with server-held service-role material. It uses the already authenticated Supabase `sub`, the literal capability `historical_audit:read`, an allowlisted projection, a five-row sentinel request with a four-row accepted maximum, a 750 ms timeout, no automatic retry, and no authorization cache. Every configuration, network, parsing, permission, cardinality, or data-integrity failure denies closed.

This branch does not implement the adapter, alter schema, add configuration, wire the router, enable the route, or expose an endpoint.

## 2. Review scope

The scope is the future transport and security design between `HistoricalAuditCapabilityResolver` and `public.omni_capability_grants`. It covers ownership, query shape, data conversion, timeout, caching, secrets, safe failures, tests, rollout, and rollback.

## 3. Non-goals

Implementation, dependencies, migrations, credentials, route registration, route enablement, endpoint exposure, frontend use, export, retention, Python delegation, MemoryFacade, `HistoricalDryRunAuditQueryService`, provider behavior, prompt behavior, retry/replan behavior, autonomy, and self-repair are out of scope.

## 4. Reviewed materials

- `backend/rust/src/historical_audit_capability.rs`
- `backend/rust/src/protected_historical_audit.rs`
- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs`
- `backend/rust/Cargo.toml`
- `supabase/migrations/20260711120000_omni_capability_grants.sql`
- `supabase/migrations/20260409_omni_schema_foundation.sql`
- `supabase/migrations/20260418120000_runtime_tool_events.sql`
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-implementation.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-implementation-preparation.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-implementation-planning.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-design-review.md`
- Existing Rust authentication, `AppState`, timeout, safe-error, observability, redaction, and server-only configuration patterns.
- Current Supabase guidance for Data API security, RLS, service-role isolation, and database functions.

## 5. Current merged implementation state

PR #529 is merged at `3502b0518237da488cd14fc5a321cf304b304c25`. The grant table and repository trait exist. The resolver validates caller identity, exact capability, every returned row, effective grants, historical rows, duplicates, expiration, revocation, and safe source failures. Static grants are test-only. Production uses an unavailable/misconfigured repository and denies closed. The protected module compiles but is not merged into the production router; no endpoint is exposed.

## 6. Existing CapabilityGrantRepository contract

`CapabilityGrantRepository` supplies a safe static `source_mode` and `lookup_grants(caller_sub, capability, now_ms) -> CapabilityGrantLookup`. The lookup returns only typed records or categorical `Unavailable`, `Timeout`, `Misconfigured`, or `Forbidden` outcomes. Raw transport and database responses are outside the contract.

## 7. Existing HistoricalAuditCapabilityResolver contract

The resolver accepts only a safe caller `sub` and a constructor-owned required capability. It permits exactly one effective record where `active` is true, `revoked_at_ms` is absent, and `expires_at_ms` is absent or greater than `now_ms`. Historical inactive, revoked, or expired records do not invalidate one effective record. Zero effective records deny categorically; multiple effective records and malformed rows deny closed.

## 8. Existing database schema and RLS posture

`public.omni_capability_grants` stores UUID caller identity, a capability constrained to `historical_audit:read`, lifecycle timestamps, audit fields, and metadata constrained to a JSON object of at most 8192 bytes. RLS is enabled. No `anon` or `authenticated` policy grants browser access. Indexes support caller/capability lookup. No live adapter exists.

## 9. Threat model

Threats include caller spoofing, capability injection, wildcard matching, stolen or leaked service-role material, browser access, SSRF through a configurable URL, malicious proxying, stale authorization, duplicate effective grants, oversized or malformed responses, raw error leakage, timeout amplification, retry storms, DNS/TLS failure, compromised database functions, and accidental production route exposure. The design treats the grant source as untrusted input even when the transport is authenticated.

## 10. Trust boundaries

The boundaries are: browser to Supabase JWT middleware; authenticated middleware extension to route authorization; resolver to repository trait; repository to fixed Supabase Data API; and secret manager to server startup configuration. Only the middleware-authenticated `sub` crosses into authorization. No request-controlled query construction crosses into Supabase.

## 11. Caller identity source

Caller identity comes only from the `sub` produced by successful Supabase JWT validation and inserted by `require_supabase_auth`. The future adapter receives that server-owned value after authentication. Body fields, query parameters, arbitrary headers, cookies, frontend state, and environment allowlists cannot provide or override caller identity.

## 12. Exact capability matching

The capability is the server constant `historical_audit:read`. Matching is case-sensitive and exact. Wildcards, prefixes, suffixes, lists, aliases, and client-supplied capability values are forbidden.

## 13. Adapter ownership boundary

The Rust backend owns transport, timeout, URL validation, secret attachment, response-size enforcement, parsing, conversion, and safe error mapping. The resolver owns grant semantics. Route handlers own neither database transport nor grant interpretation.

## 14. Proposed Rust module and type name

Use a future private module `backend/rust/src/supabase_capability_grant_repository.rs` with `pub(crate) struct SupabaseCapabilityGrantRepository`. It implements the existing trait and is not a router or handler.

## 15. Proposed constructor inputs

The constructor should receive an already validated base URL type, an opaque secret wrapper, a reusable HTTP client, a fixed timeout configuration, and optionally an injected clock/test transport. It must not receive a request, headers, cookies, table name, schema name, endpoint path, arbitrary capability, query fragments, or environment map.

## 16. Proposed AppState integration boundary

A future separately approved branch may add `Arc<dyn CapabilityGrantRepository>` or a fully constructed `HistoricalAuditCapabilityResolver` to `AppState`. Construction occurs once at startup. Handlers receive only the resolver. This review does not modify `AppState`.

## 17. Proposed server-only configuration boundary

Future configuration must be loaded at server startup from the approved secret-management boundary, validated once, wrapped to prevent `Debug`/`Display` disclosure, and never reconstructed from requests. Missing, empty, malformed, or public-demo placeholder configuration selects the unavailable/misconfigured repository and denies closed.

## 18. Approved Supabase access method

For the first implementation review, approve only fixed PostgREST table `SELECT` from the Rust server. Approval is conditional on explicit Misael authorization, secret provisioning, URL hardening, dependency review, and tests. No call is approved in this branch.

## 19. PostgREST versus RPC comparison

| Criterion | PostgREST table SELECT | Dedicated RPC |
| --- | --- | --- |
| Security surface | Fixed table read; service role has broad project privilege | Narrow callable contract; function security and grants become critical |
| Least privilege | Weak with service role; projection/filter narrow only the request | Better API surface, but service role remains broad unless a dedicated role is introduced |
| Complexity | Lowest; no new database object | Requires reviewed migration, function ownership, grants, search path, and versioning |
| Failure handling | Standard HTTP/status/JSON mapping | Same transport plus function-level failures |
| Deploy compatibility | Uses existing Data API | Requires function migration before adapter deployment |
| Testability | Straightforward mock HTTP tests | Requires HTTP tests plus database function integration tests |
| Freshness | Per-request live query | Per-request live query |
| Operational risk | Secret is powerful; query must stay fixed | Function drift and `SECURITY DEFINER` mistakes add risk |

## 20. Direct SQL comparison

Direct PostgreSQL would avoid PostgREST semantics and could use a dedicated read-only role, but introduces connection credentials, pooling, TLS/database networking, driver dependencies, connection exhaustion, and a larger operational footprint. It is not recommended initially. It may be reconsidered only with a dedicated least-privilege role and separate infrastructure review.

## 21. Recommended access method

Recommend fixed PostgREST table `SELECT` for the initial adapter because it uses the existing table without a new privileged function, has the smallest deploy delta, supports deterministic HTTP tests, and preserves per-request revocation freshness. Its service-role blast radius is the principal residual risk; secret isolation and a future dedicated RPC/role remain hardening options.

## 22. Required query semantics

The adapter performs one read per authorization decision. It requests only matching caller/capability rows, uses a deterministic order, fetches one sentinel row beyond the accepted maximum, validates status and content type, enforces body bounds, parses into a private DTO, validates every row, and returns only `CapabilityGrantLookup`.

## 23. Required exact filters

The server generates `supabase_sub=eq.<validated-uuid>` and `capability=eq.historical_audit%3Aread`. No request input supplies operators or filter syntax. Table, schema, resource path, select list, ordering, limit, and capability are compile-time constants or private typed constants.

## 24. Required maximum returned records

The accepted maximum is four records. The adapter requests five records as a sentinel. Five returned rows, a response indicating additional rows, or any body exceeding the configured byte bound maps to `Malformed` in the future safe lookup extension or otherwise `Unavailable` until that category exists. It never truncates and authorizes from a partial set.

## 25. Required ordering behavior

Use fixed `updated_at.desc,id.asc` ordering for deterministic diagnostics and tests. Ordering never affects authorization semantics: all accepted rows are validated and evaluated. No client may select ordering.

## 26. Required selected columns

Select exactly `supabase_sub,capability,active,revoked_at,expires_at`. These are the only fields required to construct `CapabilityGrantRecord`.

## 27. Forbidden selected columns

Do not select `id`, `created_at`, `updated_at`, `created_by`, `updated_by`, `grant_reason`, `grant_source`, `review_ticket`, or `metadata`. Do not use `select=*`.

## 28. Required timeout

Set a 750 ms end-to-end authorization lookup timeout, including connection acquisition, DNS, TLS, headers, and body read. The value is server-owned, bounded, and reviewed before production. Timeout denies closed.

## 29. Retry policy

No automatic retry. Authorization is latency-sensitive, a repeated read can amplify an outage, and a retry may cross a revocation boundary. The provider/runtime retry system must never participate.

## 30. Circuit-breaker position

No authorization-specific circuit breaker is required initially. If added later, it sits inside the repository transport boundary, may only short-circuit to `Unavailable`, never to allow, and requires separate review. It must not reuse the Python/provider circuit breaker.

## 31. Connection reuse

Construct one HTTP client at startup and reuse its connection pool. Do not construct a client per request. Pooling must not persist authorization decisions or response bodies.

## 32. Request cancellation

Dropping the route future or reaching the timeout must cancel the in-flight HTTP work as far as the client permits. No detached task may complete and mutate authorization state after cancellation.

## 33. Revocation freshness

Every authorization performs a live lookup. A row with `revoked_at` set is historical and ineffective. No prior allow survives revocation through caching.

## 34. Expiration freshness

The resolver compares converted timestamps against its current server clock on every decision. `expires_at <= now` is ineffective. The adapter does not trust client time.

## 35. Cache policy

No positive authorization cache is approved for the initial implementation. HTTP intermediary caching must be disabled; requests should use no-store semantics where supported.

## 36. Negative caching policy

No negative cache is approved. Missing grants, source failures, and denied decisions are evaluated on every request so newly granted access is not delayed and failures do not create hidden state.

## 37. Cache invalidation

There is no application authorization cache to invalidate. Any future cache requires a separate design for revocation, expiration, grant creation, outage recovery, tenancy, and bounded TTL.

## 38. Duplicate effective-grant handling

Two or more effective grants deny with `duplicate_capability_grant`. The adapter must return all accepted rows to the resolver and must never select the first row as authoritative.

## 39. Historical grant handling

Inactive, revoked, and expired rows are converted and passed to the resolver. Exactly one effective grant still allows when historical rows coexist. If history exceeds the four-row accepted maximum, the lookup denies as unexpected cardinality; operators must remediate grant history before access can resume.

## 40. Malformed row handling

Any missing, null where forbidden, wrong type, invalid UUID, wrong caller, wrong capability, invalid timestamp, or contradictory conversion denies the entire lookup. Valid rows cannot mask a malformed row.

## 41. Unexpected row-count handling

Zero through four rows are passed to the resolver. Five sentinel rows, evidence of more rows, or inconsistent range/count metadata denies closed. Do not truncate, paginate, or issue follow-up authorization queries.

## 42. Supabase unavailable handling

DNS, connection, TLS, proxy, gateway, 5xx, cancellation, or Data API unavailability maps to `CapabilityGrantLookup::Unavailable` and then `capability_source_unavailable`.

## 43. Timeout handling

An elapsed deadline maps to `CapabilityGrantLookup::Timeout` and then `capability_source_timeout`. Record only a safe timeout category and bounded latency bucket.

## 44. Authentication failure handling

Missing or invalid caller JWT is handled before the adapter by existing middleware. The adapter never forwards the caller JWT and never uses it as database authority.

## 45. Authorization failure handling

Zero effective grants, revoked-only, expired-only, inactive-only, duplicate effective grants, or wrong/malformed records map through existing resolver reason codes. No raw source detail reaches the route.

## 46. Database permission failure handling

PostgREST 401/403 or equivalent permission denial maps to `CapabilityGrantLookup::Forbidden` and then `capability_source_forbidden`. Do not expose status text, body, SQLSTATE, role, policy, or table details.

## 47. Response parsing failure handling

Invalid JSON, non-array shape, unknown required types, invalid timestamps, excessive nesting/size, or unexpected content type denies as malformed source data. No raw body is logged.

## 48. Configuration failure handling

Missing secret, invalid URL, non-HTTPS origin, path/query/fragment in the configured origin, unsupported host, or invalid timeout maps to the unavailable/misconfigured repository at startup. Startup may report only a categorical configuration error.

## 49. Safe CapabilityGrantLookup mapping

Use `Records` only after complete validation and conversion. Map network/5xx to `Unavailable`, deadline to `Timeout`, missing/invalid config to `Misconfigured`, and 401/403 to `Forbidden`. A future `Malformed` variant is recommended for parse/cardinality failures; until added, map them to the safest existing non-allow category without raw detail.

## 50. Safe CapabilityDecision mapping

The resolver remains the only component that maps lookup outcomes and records to allow/deny. The adapter cannot construct an allow decision. Existing safe reasons remain authoritative.

## 51. Safe audit metadata

Allowlist: route identifier, operation, allowed boolean, safe decision reason, safe source mode, route-enabled boolean, HTTP response status generated by Omni, timestamp, and bounded latency bucket. A caller identifier should be omitted or irreversibly pseudonymized with a server-managed scheme reviewed separately.

## 52. Safe observability metadata

Allow aggregate counters for lookup attempts, allows, denial categories, timeout, unavailable, forbidden, malformed, duplicate, and cardinality violation, plus coarse latency histograms. Do not attach URLs, query strings, row values, or secrets as labels.

## 53. Forbidden logs and fields

Never log or return project URL, resource URL, query string, raw HTTP status/body, request/response headers, database messages, SQLSTATE, JWT, service-role key, cookies, authorization headers, caller token, raw row, metadata, SQL, connection string, stack trace, raw exception, stdout, stderr, command arguments, or file contents.

## 54. Service-role key lifecycle

Provision outside the repository through the approved production secret manager, restrict access to the Rust service identity and designated operators, audit access, rotate on schedule and incident, revoke replaced material promptly, and verify no old instance retains it.

## 55. Service-role isolation

The key exists only in server process memory and its secret provider. It must not enter browser bundles, frontend environment variables, test fixtures, snapshots, docs examples, telemetry, shell arguments, crash dumps, or child processes. The adapter's secret wrapper must redact `Debug` and `Display`.

## 56. Secret loading requirements

Load once at startup from the approved secret source, not from request data. Validate presence without echoing value or length. This branch does not define or add an environment variable; the implementation branch must separately approve the configuration name and provider.

## 57. Secret rotation requirements

Support controlled process restart or a separately reviewed atomic credential refresh. During rotation, either credential may be staged only within the secret manager. Failure to load the active credential denies closed; never fall back to a repository file or client key.

## 58. RLS and service-role interaction

RLS remains enabled and browser roles remain without policies. Supabase service-role requests bypass RLS, so RLS is not the primary control for the adapter. Server isolation, fixed query construction, secret protection, and minimal selected columns are mandatory compensating controls.

## 59. Least-privilege alternative analysis

A dedicated database role limited to `SELECT` on an allowlisted view/function would reduce service-role blast radius, but Supabase Data API role/JWT issuance and operations require separate design. A dedicated RPC can narrow returned data but does not narrow a leaked service-role key by itself. This remains the preferred future hardening investigation.

## 60. Dedicated RPC security analysis

If later approved, use a non-client-supplied capability and one parameter `p_supabase_sub uuid`. Return only `supabase_sub uuid, capability text, active boolean, revoked_at timestamptz, expires_at timestamptz`, with fixed ordering and a five-row sentinel limit. Prefer `SECURITY INVOKER` when the invoking role has only the necessary read privilege. Revoke execution from `PUBLIC`, `anon`, and `authenticated`; grant only to the reviewed server role. Service-role-only invocation is acceptable but retains service-role blast radius.

## 61. SECURITY DEFINER risk analysis

`SECURITY DEFINER` can bypass RLS and inherits owner privileges. It is not approved merely to fix permissions. If a future least-privilege design proves it necessary, require a separate threat review, fixed parameters, explicit caller checks where applicable, hardened `search_path`, non-superuser ownership, complete qualification, and explicit execute grants.

## 62. Search-path hardening requirements

Any future function must set `search_path` to an empty or tightly controlled value and fully qualify referenced objects (`public.omni_capability_grants`, `pg_catalog` functions as needed). Never rely on caller-controlled schemas.

## 63. Function ownership requirements

Own a future function with a dedicated non-login, non-superuser migration role having only required object privileges. Do not use an application user or broad interactive operator as owner. Ownership transfer and rollback must be explicit SQL.

## 64. Grant/revoke SQL requirements

Future RPC migration must revoke execute from `PUBLIC`, `anon`, and `authenticated`, then grant execute only to the reviewed server role. It must not grant table access to browser roles. All grants and revokes require preview/local migration validation and rollback SQL.

## 65. Browser/anon/authenticated denial

Browser, `anon`, and ordinary `authenticated` clients must have no direct table or RPC authority. A valid user JWT authenticates the caller to Omni but is never forwarded as authority for the grant lookup.

## 66. SSRF and URL validation

Accept only one configured HTTPS origin matching the expected Supabase project host allowlist. Reject userinfo, non-default or unapproved ports, IP literals, localhost, private/link-local targets, path, query, fragment, redirects, and runtime request overrides. Build `/rest/v1/omni_capability_grants` from constants.

## 67. TLS requirements

Require HTTPS with normal certificate and hostname verification. Do not permit insecure TLS, custom trust bypass, downgrade, or plaintext fallback. TLS failure denies closed.

## 68. Proxy behavior

Do not inherit unreviewed ambient proxy configuration for this privileged call. If production requires a proxy, approve a fixed trusted proxy separately and ensure it cannot log authorization material or redirect destinations.

## 69. DNS/network failure behavior

DNS failure, rebinding suspicion, connect reset, partial body, and network partition deny as unavailable. No retry or alternate host is attempted. Metrics remain categorical.

## 70. Input validation

Parse caller `sub` as a canonical UUID before transport, enforce the exact capability constant, and reject missing or malformed values. Do not accept raw filters, paths, headers, URL, table, schema, columns, range, order, or timeout from the request.

## 71. Output validation

Require a JSON array, bounded bytes, at most the accepted row count, exactly the expected fields/types, canonical UUID equality, exact capability equality, valid booleans, and valid RFC 3339 timestamps within representable range. Unknown fields should be rejected by the private DTO to detect contract drift.

## 72. Record conversion to CapabilityGrantRecord

Convert only after full DTO validation. Copy canonical caller UUID and exact capability, preserve `active`, and convert optional lifecycle timestamps to milliseconds. Do not carry transport metadata into the record.

## 73. Timestamp conversion

Parse `timestamptz` as an offset-aware instant, normalize to UTC, reject pre-epoch or overflow values that cannot map safely to `u64` milliseconds, and avoid lossy local-time parsing. Database time does not replace the resolver's server clock.

## 74. UUID/Supabase sub conversion

The middleware currently stores `sub` as a string. The adapter must parse it as UUID, serialize canonical lowercase hyphenated form for the server-generated filter, and verify every returned UUID equals it. Non-UUID values deny before transport.

## 75. Metadata exclusion

The adapter neither selects nor parses the `metadata` JSON column. Its schema bound is defense in depth, not permission to transport metadata through authorization.

## 76. No raw response exposure

Raw JSON, PostgREST bodies, headers, status text, SQL, rows, and client errors never leave the adapter. Route responses receive only existing safe decisions and metadata-only envelopes.

## 77. Unit-test design

Use synthetic UUIDs and fake clocks/transports. Cover constructor validation, exact request construction, conversion, every safe lookup category, limits, cancellation, and secret redaction. No real credentials or network calls in unit tests.

## 78. Repository-mock tests

Preserve resolver tests for active, missing, inactive, expired, revoked, historical combinations, duplicate effective grants, wrong caller/capability, malformed identity, unavailable, timeout, misconfigured, and forbidden. Verify the adapter cannot directly allow.

## 79. HTTP adapter tests

Use a local mock server bound to loopback only in tests. Assert method `GET`, fixed path, exact encoded filters, exact projection, fixed order, sentinel limit, server-only key attachment, no caller JWT forwarding, no redirects, bounded body, and categorical output.

## 80. Timeout tests

Simulate delayed headers and delayed body. Verify completion within a small tolerance, request cancellation, `Timeout`, no retry, no raw error, and no allow.

## 81. Malformed response tests

Cover invalid JSON, object instead of array, missing field, null required field, wrong types, unknown fields, invalid UUID, wrong caller, wrong capability, malformed/overflow timestamp, oversized body, and unsupported content type. Every case denies closed.

## 82. Duplicate row tests

Two effective rows must reach the resolver and deny `duplicate_capability_grant`. Ensure the adapter does not deduplicate or choose the first row.

## 83. Historical row tests

Test one active plus expired, revoked, and inactive historical rows; each combination allows while accepted cardinality remains within four. Test only historical rows deny. Test five sentinel rows deny without partial evaluation.

## 84. Secret-redaction tests

Construct synthetic marker secrets and force URL, auth, timeout, status, parse, and panic-safe formatting paths. Assert markers never appear in `Debug`, `Display`, tracing fields, returned errors, snapshots, or response envelopes.

## 85. Integration-test design

Run against an ephemeral Supabase preview/local stack with synthetic users and grants. Verify service-only read, browser-role denial, exact caller/capability behavior, revocation/expiration freshness, duplicates, row limit, and cleanup. Keep production router unwired during adapter integration tests.

## 86. Supabase preview validation

The implementation branch must obtain a successful preview branch migration/runtime result or an approved local Supabase validation. Record only project-neutral evidence: migration identifier, command category, pass/fail, timestamp, and safe test counts. Never paste credentials or raw responses.

## 87. Migration compatibility validation

Reapply the existing migration in the preview/local validation path, confirm table/constraints/indexes/RLS, confirm no browser policies, and run the future adapter query with synthetic rows. This design branch changes no migration.

## 88. Abuse-case matrix

| Abuse case | Required result |
| --- | --- |
| Spoof caller in body/query/header/cookie | Ignored or rejected; authenticated `sub` remains authoritative |
| Supply wildcard, alternate case, list, or prefix capability | Deny; server literal only |
| Call table from browser roles | Database denial |
| Force arbitrary URL/path/filter/order/select | Impossible through typed private construction |
| Return wrong caller/capability row | Malformed denial |
| Accumulate more than four matching rows | Sentinel cardinality denial |
| Create two effective grants | Duplicate denial |
| Reuse access after revocation/expiration | Fresh lookup denies |
| Stall or fail Supabase | Timeout/unavailable denial, no retry |
| Leak secret through error/debug | Redaction test failure; release blocked |
| Redirect to attacker host | Redirect rejected |
| Inject SQL/PostgREST operators | No interpolation; canonical UUID encoding only |

## 89. Failure-mode matrix

| Failure | Lookup category | Decision behavior | Safe source mode |
| --- | --- | --- | --- |
| Missing/invalid config | `Misconfigured` | Deny | `misconfigured` |
| DNS/connect/TLS/5xx | `Unavailable` | Deny | `unavailable` |
| Deadline elapsed | `Timeout` | Deny | `timeout` |
| 401/403 from source | `Forbidden` | Deny | `forbidden` |
| Parse/schema/cardinality failure | Future `Malformed` or safest existing deny | Deny | `malformed` |
| Valid zero rows | `Records([])` | Missing-grant deny | `supabase_grants` |
| One effective row | `Records` | Allow | `supabase_grants` |
| Multiple effective rows | `Records` | Duplicate deny | `supabase_grants` |

## 90. Rollback design

Keep production disabled by default. Rollback replaces the adapter with `UnavailableCapabilityGrantRepository`, removes server secret access, and redeploys without wiring the router. If credentials may be exposed, rotate them. Do not delete audit evidence or alter runtime/provider behavior.

## 91. Feature-switch requirements

A future adapter source switch must be server-owned, default to unavailable, enumerate only approved modes, and deny on unknown/missing values. It is not a capability allowlist and cannot enable the route.

## 92. Production-disabled default

The unavailable/misconfigured repository remains the production default until configuration, preview validation, security tests, and explicit Misael approval are complete. A configured adapter still does not register or enable routes.

## 93. Router wiring remains separate

Adding the repository to state does not approve `.merge(protected_historical_audit_router(...))` or equivalent production router registration. Wiring requires a separate branch and review.

## 94. Route enablement remains separate

The route switch remains disabled by default. Capability-source success cannot override route-disabled behavior.

## 95. Endpoint exposure remains separate

No protected, internal, public, or no-auth endpoint is exposed by this design or the future adapter-only branch.

## 96. Cockpit consumption remains separate

No Cockpit/detail drawer, frontend query, copy, export, download, or UI affordance is approved.

## 97. Implementation branch exact scope

The recommended next branch is `feature/autonomy-dry-run-historical-audit-api-capability-source-supabase-adapter-implementation`. Its exact scope should be the private adapter, safe configuration wrapper/factory, trait-safe malformed category if approved, focused tests, and evidence documentation. It must preserve unavailable default and avoid route wiring.

## 98. Allowed future files

- `backend/rust/src/supabase_capability_grant_repository.rs`
- `backend/rust/src/historical_audit_capability.rs` only for a reviewed safe lookup category or trait integration
- `backend/rust/src/main.rs` only for private module declaration/state construction, never router wiring
- `backend/rust/Cargo.toml` and lockfile only for a pinned reviewed HTTP/UUID/time dependency if existing facilities are insufficient
- Focused Rust test modules/fixtures containing synthetic data only
- A narrowly named server configuration module if separately approved
- Implementation evidence documentation under `docs/runtime/`

## 99. Prohibited future files

Do not modify the existing capability migration, create unrelated migrations, touch `.env`/`.env.example`, frontend/Cockpit, Python, MemoryFacade, `HistoricalDryRunAuditQueryService`, provider/prompt/runtime/retry/replan/autonomy/self-repair modules, route registration, route enablement, endpoint handlers, copy/export, or retention/cleanup files.

## 100. Acceptance criteria

- Authenticated Supabase `sub` is the only caller authority.
- Exact `historical_audit:read` is fixed server-side.
- Request construction, projection, order, and row bounds are fixed.
- Every row and timestamp is validated.
- All source/config/parse/cardinality failures deny closed.
- Timeout is 750 ms; retries and caches are absent.
- Secrets and raw source material cannot appear in logs/responses.
- Browser roles remain denied.
- Resolver and HTTP tests pass with synthetic data.
- Preview/local Supabase validation succeeds.
- Production repository remains unavailable by default.
- Router remains unwired and no endpoint is exposed.

## 101. Remaining blockers

Explicit Misael approval for implementation; final secret provider/configuration name; HTTP client/dependency review; decision to add a `Malformed` lookup variant; validated Supabase project URL allowlist; preview/local Supabase environment; service-role provisioning/rotation process; and security approval of broad service-role risk. Router wiring, route enablement, endpoint exposure, and frontend use remain later independent blockers.

## 102. Go/no-go table

| Area | Decision | Rationale |
| --- | --- | --- |
| Documentation/design review | Go | Scope of this branch |
| Live Supabase adapter | No-go | Future explicit approval required |
| PostgREST table access | Conditional go | Preferred initial future method under controls above |
| Dedicated RPC | No-go now | Future hardening option requiring migration/security review |
| Direct PostgreSQL access | No-go | Excess operational and credential surface initially |
| Service-role use | Conditional go | Server-only future use with acknowledged broad privilege |
| Authenticated Supabase sub | Go | Sole caller identity |
| Exact historical_audit:read capability | Go | Sole capability |
| Client-provided capability | No-go | Untrusted authority |
| Header-provided capability | No-go | Untrusted authority |
| Query-param capability | No-go | Untrusted authority |
| Body-provided capability | No-go | Untrusted authority |
| Cookie-provided capability | No-go | Untrusted authority |
| Environment-only production allowlist | No-go | Not a grant source |
| Positive capability caching | No-go | Revocation/expiration freshness |
| Negative capability caching | No-go | Fresh grant/outage recovery |
| Retry on authorization timeout | No-go | Fail closed without amplification |
| Raw Supabase response logging | No-go | Sensitive/raw data |
| Raw database errors | No-go | Sensitive internals |
| Safe categorical errors | Go | Required contract |
| Production router wiring | No-go | Separate phase |
| Route enablement | No-go | Separate phase |
| Endpoint exposure | No-go | Separate phase |
| Public exposure | No-go | Forbidden |
| Cross-language delegation | No-go | Out of scope |
| Cockpit/detail drawer | No-go | Out of scope |
| Copy/export | No-go | Out of scope |
| Retention/cleanup | No-go | Out of scope |
| MemoryFacade access | No-go | Forbidden boundary |
| Raw JSONL/SQLite/SQL | No-go | Forbidden exposure/storage coupling |
| Runtime/provider/prompt changes | No-go | Out of scope |
| Autonomous execution | No-go | Out of scope |
| Self-repair | No-go | Out of scope |

## 103. Final recommendation

Approve this documentation-only Supabase adapter design review. Preserve authenticated Supabase `sub` as the only caller identity, exact `historical_audit:read` matching, fail-closed behavior, safe categorical errors, metadata-only observability, no authorization cache, a bounded 750 ms timeout, and no automatic authorization retry.

Conditionally approve a future narrow server-only PostgREST adapter after explicit Misael approval and resolution of the blockers above. Do not approve implementation, dependencies, service-role configuration, PostgREST/RPC/SQL calls, router wiring, route enablement, endpoint/public exposure, cross-language delegation, Cockpit use, copy/export, retention/cleanup, MemoryFacade access, raw storage/SQL exposure, or runtime/provider/prompt/retry/replan/autonomy/self-repair changes in this branch.
