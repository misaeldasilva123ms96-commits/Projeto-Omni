# Historical Dry-Run Audit API Supabase Capability Adapter Implementation

## 1. Executive summary

This branch implements a dormant, private, asynchronous Supabase/PostgREST capability-grant adapter for the exact server-owned capability `historical_audit:read`. It adds strict configuration, URL, DNS destination, request, response, timeout, cardinality, and secret boundaries plus focused tests. The adapter is compiled but has no production constructor call, state integration, router wiring, route enablement, or endpoint exposure.

## 2. Base main SHA

The branch was created from current `origin/main` at `32f5896b52351ce915636a1680a80e56aab9598b`, the merge commit for PR #546.

## 3. Files inspected

- The merged implementation-preparation contract and preceding capability-source design/implementation documents.
- `backend/rust/src/historical_audit_capability.rs` and all `HistoricalAuditCapabilityResolver` callers.
- `backend/rust/src/protected_historical_audit.rs`, `backend/rust/src/main.rs`, `backend/rust/src/observability_auth.rs`, and `backend/rust/src/error.rs`.
- Rust manifest/lockfile, the existing grant migration, secret-redaction and URL sanitization patterns.
- Rust, security, dependency-audit, runtime, public-demo, and general CI workflows.

## 4. Files changed

- `backend/rust/src/historical_audit_capability.rs`
- `backend/rust/src/historical_audit_capability/supabase_capability_grant_repository.rs`
- `backend/rust/Cargo.toml`
- `backend/rust/Cargo.lock`
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-supabase-adapter-implementation.md`

## 5. Dependencies added and justification

- `reqwest 0.13.4`, default features disabled, with asynchronous query support and Rustls without an implicit provider: reusable nonblocking HTTP, typed query encoding, redirect/proxy control, bounded response streaming, and custom DNS resolution.
- `rustls 0.23.42` with ring, standard-library, and TLS 1.2 support: explicit crypto-provider selection without the heavier AWS-LC native graph.
- `uuid 1.24.0`: canonical authenticated caller parsing and returned-row equality.
- `time 0.3.53` with parsing/formatting: strict RFC 3339 UTC request timestamps and lossless millisecond conversion.

No blocking client, SQL driver, RPC dependency, cache, retry library, or environment loader was added.

## 6. Implemented adapter architecture

`SupabaseCapabilityGrantRepository` is a private submodule under `historical_audit_capability`. It owns a validated origin, opaque server secret, validated timeout, and an injected asynchronous transport. The production transport owns one reusable `reqwest::Client`; tests use a deterministic fake transport. The adapter returns only `CapabilityGrantLookup` values and typed `CapabilityGrantRecord` rows.

## 7. Async isolation boundary

The adapter exposes a private `async fn lookup_grants` and the transport uses an object-safe boxed future. It uses no blocking API, nested runtime, `block_on`, detached task, subprocess, or route future. An outer Tokio timeout drops the in-flight future on expiry. The existing synchronous resolver and route consumer remain unchanged.

## 8. Source-mode behavior

The production `supabase_grants` source constant is now available outside tests. An initialized adapter always reports `supabase_grants`, including unavailable, timeout, forbidden, malformed, and misconfigured lookup outcomes. Disabled configuration reports `unavailable`; `static_test` remains test-only.

## 9. Malformed behavior

`CapabilityGrantLookup::Malformed` was added and maps fail-closed to `capability_source_malformed` without changing source mode. It covers invalid successful-response headers, encoding, body, envelope, DTO fields, UUIDs, timestamps, caller/capability, cardinality, body size, truncation category, and unexpected successful status.

## 10. Configuration model

A pure private parser receives an injected key/value lookup; tests do not mutate global environment. Defaults are source unavailable and adapter disabled. Live configuration requires both explicit live source and enabled state plus a valid dedicated origin, nonempty header-safe non-placeholder server secret, and timeout in the approved range. No browser-facing URL, anon credential, or caller token fallback is consulted.

## 11. Secret boundary

The secret wrapper has redacted `Debug`, no `Display`, no serialization, and no public accessor. It prevalidates only presence, placeholder rejection, whitespace, and safe request-value construction. Both `apikey` and `Authorization` `HeaderValue` instances are marked sensitive before storage or request construction; `Accept` and `Accept-Encoding` remain nonsensitive and contain only fixed public values. Secret values are copied only into the outbound request immediately before sending and never enter lookup outcomes, errors, metadata, logs, URLs, docs, or snapshots.

## 12. URL validation

The origin parser requires lowercase absolute HTTPS, no userinfo, query, fragment, or base path, port 443 only, no IP literal or localhost, and exactly one lowercase 20-character project reference under the approved Supabase host suffix. Lookalike suffixes, custom domains, uppercase hosts, alternate ports, and path overrides are rejected.

## 13. DNS/SSRF implementation status

DNS/IP enforcement is implemented, not inferred from hostname validation. A custom `reqwest` resolver accepts only the previously validated exact host, resolves it for port 443, permits only validated public IPv4 destinations, rejects every IPv6 destination in this initial adapter (including IPv4-mapped forms), and returns only filtered IPv4 addresses to the client that opens the connection. This deliberately avoids a partial claim of exhaustive IPv6 or IANA special-purpose classification. TLS hostname validation remains tied to the validated host. Redirects and ambient proxies are disabled. Tests cover public IPv4 plus loopback, private, link-local, shared, documentation, benchmark, mapped, reserved, former-6bone, unique-local, and other IPv6 cases.

## 14. Exact PostgREST request

Each lookup can issue exactly one `GET` to the compile-time resource `/rest/v1/omni_capability_grants`. The projection is exactly `supabase_sub,capability,active,revoked_at,expires_at`. Typed query pairs enforce canonical caller UUID, exact capability, active state, null revocation, null-or-future expiration using one server timestamp, and limit two. No range, count, pagination, offset, order, history query, confirmation query, retry, RPC, or SQL exists.

## 15. Response parser

Successful bodies are capped at 16,384 bytes before and during streaming. `Content-Type` must occur exactly once; `Content-Encoding`, `Content-Length`, and `Content-Range` may occur at most once. Duplicated, conflicting, or invalid-byte header values are malformed. Only JSON with optional UTF-8 charset and identity/no content encoding is accepted. Missing `Content-Range` is accepted; otherwise zero rows require `*/0`, one row requires `0-0/*` or `0-0/1`, and two rows require `0-1/*` or `0-1/2`. Numeric totals that differ from the received row count are rejected so partial effective-grant responses cannot authorize. A complete top-level array may contain zero, one, or two rows. A custom DTO visitor rejects duplicate, missing, unknown, wrongly typed, or invalid-null fields. UUID and timestamp parsing is strict; timestamp conversion rejects local, pre-epoch, lossy sub-millisecond, expired, and invalid values.

## 16. Error mappings

Valid `200` arrays become `Records`. Invalid successful responses, `204`, and redirects become `Malformed`. Contract-related client errors become `Misconfigured`; source authentication/permission failures become `Forbidden`; request deadline becomes `Timeout`; rate limiting and server/network failures become `Unavailable`. Raw status bodies, database errors, parser text, transport exceptions, URLs, queries, rows, and response headers are discarded.

## 17. Timeout behavior

Default end-to-end timeout is 750 ms; accepted configured values are 100 through 2,000 ms. The same bound is applied to client connect/request behavior and the outer async future. The same `now_ms` generates the query timestamp and validates returned expiration. Timeout tests prove one attempt and no detached completion.

## 18. No-retry evidence

There is one transport invocation in `lookup_grants`, no loop around transport, no retry dependency, no fallback destination, and no second authorization request. Tests assert one attempt for success, transport failures, and timeout.

## 19. No-cache evidence

The adapter stores only origin, secret, timeout, and transport/client. It stores no lookup result or authorization decision. A focused test queues different consecutive responses and proves repeated calls perform two independent attempts and observe both results.

## 20. Tests and counts

The Rust suite passes 137 tests. The adapter module contributes 25 focused tests covering configuration, IPv4-only DNS/IP policy, exact request, source stability, zero/one/two rows, fail-closed `Content-Range`, duplicate/conflicting/invalid response headers, strict malformed matrix, status matrix, UUID/time conversion, sensitive secret headers, no cache, no retry, timeout cancellation, and dormant client construction. Existing resolver, protected-route, auth, control, and runtime regression tests also pass.

## 21. Redaction evidence

Synthetic low-entropy values are used. Tests prove the secret is absent from wrapper/adapter debug output and categorical results, both privileged headers carry the sensitive marker, the test transport retains only header names and sensitivity booleans, the origin and caller are absent from adapter debug output, only the expected privileged request fields are present, no cookie/range/browser/caller-token surface is added, and response bodies cannot propagate through the lookup enum.

## 22. Dependency/security audit

Rust formatting, compilation, all 137 tests, and Clippy with warnings denied pass. The resolved dependency graph excludes AWS-LC and uses the explicitly selected ring provider. `cargo audit` passes with only the repository's existing allowed yanked-crate warning for `spin 0.9.8`; it reports no new blocking advisory. `npm run test:security`, `npm run validate:public-demo`, and `npm run validate:audit-pack` all pass. Unresolved high/critical findings remain a no-go.

## 23. Confirmed prohibited files untouched

`main.rs`, `protected_historical_audit.rs`, migrations, environment examples, workflows, frontend, Python, MemoryFacade, query service, providers, prompts, runtime, tool execution, copy/export, and retention/cleanup are unchanged.

## 24. Confirmed router remains unwired

`main.rs` still only declares the historical capability and protected-route modules. It contains no historical route builder call or router merge. Existing negative route-registration tests pass.

## 25. Confirmed no route or endpoint exposed

No router, handler, state field, route switch, public payload, frontend client, or endpoint was added or changed. Directly instantiated tests are the only callers of the adapter.

## 26. Known limitations

- The existing `CapabilityGrantRepository`/resolver boundary is synchronous. Integrating an async network adapter would require a separately approved resolver/consumer change; it is intentionally deferred.
- IPv6 destinations are intentionally rejected rather than relying on incomplete manual special-purpose classification; deployments require a public IPv4 resolution path.
- Existing protected-route tests rely on legacy allow/missing reason strings. This branch adds the required malformed reason but does not silently migrate externally relied-on allow/missing reasons.
- No real Supabase project or credential is used. Preview/staging integration remains a later controlled validation.
- Service-role privilege remains broader than the fixed query; secret isolation and future least-privilege review remain operational requirements.

## 27. Remaining blockers before AppState integration

Explicit approval for async resolver integration; a reviewed state/config construction boundary; deployment secret provisioning/rotation; preview or staging validation; safe health/observability design; decision on legacy reason migration compatibility; operational monitoring; and separate approval that does not imply router wiring.

## 28. Rollback

Revert the isolated implementation commit. Because no state, startup, router, route, or endpoint consumes the adapter, rollback requires no migration or data cleanup. If future secret provisioning occurs separately, disable it and rotate on suspected exposure.

## 29. Go/no-go table

| Area | Decision |
| --- | --- |
| Isolated async adapter and tests | Go |
| `Malformed` safe category | Go |
| Fixed effective-only PostgREST request | Go when directly instantiated |
| Production construction/startup wiring | No-go |
| Existing synchronous resolver integration | No-go in this branch |
| AppState integration | No-go |
| Router wiring/route enablement | No-go |
| Endpoint or public exposure | No-go |
| Frontend/runtime/provider/tool behavior | No-go |
| Real credential/network tests | No-go in normal tests |
| Merge or auto-merge | No-go; manual Misael decision only |

## 30. Final recommendation

Approve the isolated adapter implementation for draft review after all required local and CI validations pass. Keep it dormant and disconnected. The recommended next phase is a separately approved asynchronous resolver-integration design/implementation branch; it must still exclude router wiring, route enablement, endpoint exposure, and frontend consumption.
