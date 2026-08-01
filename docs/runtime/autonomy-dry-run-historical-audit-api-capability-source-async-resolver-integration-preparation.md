# Historical Dry-Run Audit API Async Capability Resolver Integration Preparation

## 1. Executive summary

This documentation-only review approves a future narrow migration from the current synchronous `CapabilityGrantRepository` and `HistoricalAuditCapabilityResolver` boundary to one object-safe asynchronous contract. The approved contract returns a boxed `Send` future, keeps `Arc<dyn CapabilityGrantRepository>`, adds no dependency, and preserves one resolver-owned authorization policy. No resolver, route, `AppState`, router, endpoint, configuration, or runtime behavior is implemented here.

## 2. Scope

This review records the merged baseline, selects the exact future trait and resolver shapes, defines the pure evaluator boundary, prepares the protected route consumer migration, and fixes the cancellation, time, timeout, compatibility, test, rollout, and rollback contracts. It is limited to implementation preparation for `historical_audit:read`.

## 3. Non-goals

This branch does not modify Rust code or tests, Cargo manifests, migrations, environment files, `AppState`, startup, router registration, route enablement, query-service delegation, frontend/Cockpit, Python, runtime/provider/prompt/tool behavior, retries, replanning, autonomy, self-repair, copy/export, retention, or cleanup. It does not contact a real Supabase project.

## 4. Reviewed materials

The review inspected:

- `backend/rust/src/historical_audit_capability.rs`, including every `CapabilityGrantRepository` implementation, resolver constructor, caller, and focused test;
- `backend/rust/src/historical_audit_capability/supabase_capability_grant_repository.rs`, including its private async adapter, transport seam, configuration parser, and 25 focused tests;
- `backend/rust/src/protected_historical_audit.rs`, including both handlers, route state, rate limiter, envelopes, and all protected-route tests;
- `backend/rust/src/main.rs`, including `AppState` and production router construction;
- `backend/rust/src/observability_auth.rs` and `backend/rust/src/error.rs`;
- `backend/rust/Cargo.toml` and `backend/rust/Cargo.lock`;
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-implementation.md`;
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-supabase-adapter-design-review.md`;
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-supabase-adapter-implementation-preparation.md`;
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-supabase-adapter-implementation.md`;
- `docs/runtime/autonomy-dry-run-historical-audit-api-protected-route-skeleton.md`;
- `supabase/migrations/20260711120000_omni_capability_grants.sql`;
- `ROADMAP.md`, `docs/status/current-state.md`, and `docs/roadmap/omni-post-omniroute-roadmap.md`;
- all workflows under `.github/workflows`, with focused inspection of Rust, lint, security, dependency-audit, public-demo, audit-pack, and manual-validation commands.

No repository-local `AGENTS.md` was present.

## 5. Base main SHA

The branch base is current `origin/main` at `cb7580da6de7c84a327a8f60c472d1952e4d37e0`, recorded after `git fetch --all --prune` on 2026-08-01.

## 6. Current merged baseline

`origin/main` contains PR #559 through merge commit `4a2e4ed5709d0c20eef15c63adf527f77224a307`. That PR merged the isolated Supabase/PostgREST adapter. The adapter is asynchronous and private, has no production constructor call, is absent from `AppState`, and is not wired to the router. No protected historical-audit endpoint is exposed. Static grants remain `#[cfg(test)]` only.

## 7. Current synchronous repository contract

`CapabilityGrantRepository: Send + Sync` is `pub(crate)` and synchronous. It exposes `source_mode()` and `lookup_grants(&self, caller_sub: &str, capability: &str, now_ms: u64) -> CapabilityGrantLookup`. Its production implementation is `UnavailableCapabilityGrantRepository`; `StaticTestCapabilityGrantRepository` and test doubles are test-only. The private Supabase adapter has an async inherent lookup but does not yet implement this trait.

## 8. Current synchronous resolver contract

`HistoricalAuditCapabilityResolver` holds `Arc<dyn CapabilityGrantRepository>` and a `&'static str` required capability. `authorize` obtains one local timestamp and calls synchronous `authorize_at`; `authorize_at` validates caller and exact capability, performs the lookup, maps typed outcomes, validates returned records, and returns `CapabilityDecision`. The grant-policy evaluator currently lives as a private resolver method.

## 9. Current route-consumer contract

`HistoricalAuditRouteState::authorize` is synchronous. Both async handlers reject an empty extracted caller, call authorization synchronously, reject denial, mutate the per-caller rate limiter, validate query complexity or plan ID, then return the `501` placeholder boundary. The route state checks the disabled gate before invoking the resolver. No storage or query service is called.

## 10. Current Supabase adapter contract

`SupabaseCapabilityGrantRepository` is private and owns a validated origin, redacted service-role secret, bounded timeout, and async transport. Its lookup is async, performs exactly one request, uses canonical UUID and exact `historical_audit:read`, sends effective-only PostgREST filters and `limit=2`, strictly parses a bounded response, and returns only `CapabilityGrantLookup`. Its default end-to-end timeout is 750 ms; allowed configured bounds are 100–2,000 ms. Redirects and ambient proxies are disabled, DNS permits only validated public IPv4 destinations, privileged headers are sensitive, and there is no retry or cache.

## 11. Current AppState boundary

`AppState` contains no capability repository, capability resolver, adapter, capability configuration, or service-role material. The async-resolver implementation branch must preserve that boundary. A later, separately approved AppState preparation branch owns any production construction decision.

## 12. Current router state

`main.rs` declares the historical capability and protected-route modules so they compile, but production router construction does not call `protected_historical_audit_router`, merge its router, or register either candidate path. The protected route defaults to disabled; no public HTTP path reaches it.

## 13. Problem statement

The live-capable adapter is nonblocking while the repository, resolver, and route consumer are synchronous. Bridging them by blocking would endanger Tokio workers and cancellation. Duplicating policy or retaining parallel production stacks would create inconsistent authorization. The future implementation therefore needs one asynchronous repository contract and one asynchronous resolver while keeping the adapter dormant and the route disabled and unwired.

## 14. Architectural options considered

Considered options were: block the adapter behind the current trait; create or enter a Tokio runtime; use `block_on`; spawn and detach lookup work; keep separate sync and async production resolver hierarchies; add `async-trait`; or use an object-safe boxed future. Only the boxed-future, single-policy migration satisfies object safety, cancellation, dependency, and governance constraints.

## 15. Rejected blocking-adapter option

Rejected. A synchronous adapter around async HTTP could block executor workers, obscure cancellation, and make timeout ownership ambiguous. `reqwest::blocking` is prohibited.

## 16. Rejected nested-runtime option

Rejected. Constructing a runtime per lookup or inside an existing runtime can panic, waste resources, split lifecycle ownership, and defeat request cancellation.

## 17. Rejected block_on option

Rejected. Tokio handle/runtime `block_on`, futures executors, or equivalent synchronous waiting are forbidden at this boundary.

## 18. Rejected detached-task option

Rejected. `tokio::spawn`, background lookup, detached join handles, speculative work, or fire-and-forget authorization could outlive request cancellation and retain secrets or emit stale decisions.

## 19. Rejected dual production resolver stacks

Rejected. Permanent synchronous and asynchronous repository/resolver hierarchies would duplicate policy and invite divergent source-mode, reason, and failure mappings. A temporary compatibility wrapper is no-go unless created and removed within the same future implementation PR; no wrapper is presently justified.

## 20. Approved single-policy async architecture

Approve one async `CapabilityGrantRepository`, one async `HistoricalAuditCapabilityResolver`, and one shared pure evaluator. All implementations migrate together. The resolver alone owns authorization policy; repositories own typed lookup, and route code only orders guards and maps `CapabilityDecision` to the existing HTTP envelope.

## 21. Async repository trait shape

The exact future shape is:

```rust
use std::{future::Future, pin::Pin};

pub(crate) type CapabilityGrantLookupFuture<'a> =
    Pin<Box<dyn Future<Output = CapabilityGrantLookup> + Send + 'a>>;

pub(crate) trait CapabilityGrantRepository: Send + Sync {
    fn source_mode(&self) -> &'static str;

    fn lookup_grants<'a>(
        &'a self,
        caller_sub: &'a str,
        capability: &'static str,
        now_ms: u64,
    ) -> CapabilityGrantLookupFuture<'a>;
}
```

The `&'static str` capability matches the resolver-owned compile-time requirement, but `'static` controls only the reference lifetime, not the accepted string value; unrelated static literals would also satisfy the type. The security boundary is that `HistoricalAuditCapabilityResolver` is the only intended caller: it owns and supplies the server-defined capability, validates that its required capability equals exactly `historical_audit:read` before lookup, and accepts no capability from a request body, query, path, header, cookie, or caller claim. Future tests must prove that wrong resolver capability values fail before repository lookup. Implementations return `Box::pin(...)`; the trait remains usable as `Arc<dyn CapabilityGrantRepository>`.

## 22. Object-safety analysis

The trait has no associated generic type, no async trait method, no return-position `impl Trait`, no `Self` return, and no method requiring `Self: Sized`. A lifetime parameter tied to borrowed inputs is object-safe. The concrete returned alias erases each future type, so dynamic dispatch through `Arc<dyn CapabilityGrantRepository>` remains valid.

## 23. Send and Sync requirements

The repository remains `Send + Sync`, the boxed future is `Send`, and the resolver remains cloneable through an immutable `Arc`. Tests must compile-assert that the trait object is `Send + Sync` and that a returned lookup future is `Send`. No shared mutable decision state is introduced.

## 24. Boxed-future decision

Approve `Pin<Box<dyn Future<Output = CapabilityGrantLookup> + Send + 'a>>`. Allocation occurs once per authorization lookup and is acceptable for this dormant, bounded administrative path. The shape is explicit, stable, object-safe, and already mirrors the adapter transport seam.

## 25. No async-trait dependency decision

Do not add `async-trait` or any other dependency. `Cargo.toml` and `Cargo.lock` remain unchanged unless a separate reviewed blocker proves the standard-library boxed-future shape impossible.

## 26. Resolver async API

Approve:

```rust
pub(crate) async fn authorize(&self, caller_sub: &str) -> CapabilityDecision;

pub(crate) async fn authorize_at(
    &self,
    caller_sub: &str,
    now_ms: u64,
) -> CapabilityDecision;
```

`authorize` generates exactly one `now_ms` and delegates. `authorize_at` captures source mode, validates preconditions, awaits exactly one lookup, and invokes the pure evaluator.

## 27. Pure evaluator boundary

Extract a private synchronous function conceptually shaped as `evaluate_capability_lookup(caller_sub, required_capability, lookup, now_ms, source_mode) -> CapabilityDecision`. It owns typed outcome mapping and record defense-in-depth: zero/one/multiple effective grants, safe caller and equality, exact capability, active status, revocation, expiration, and stable safe reasons. It performs no I/O, clock read, locking, or source-specific logic.

## 28. Source-mode handling

Source mode is captured from repository origin before precondition checks or lookup and is never inferred from a result. Approved values remain `supabase_grants`, `unavailable`, and test-only `static_test`. An initialized Supabase repository reports `supabase_grants` for `Records`, `Unavailable`, `Timeout`, `Forbidden`, `Malformed`, and `Misconfigured`.

## 29. Lookup-outcome handling

Preserve exactly `Records`, `Unavailable`, `Timeout`, `Misconfigured`, `Forbidden`, and `Malformed`. The resolver receives no `reqwest::Error`, serde/URL/DNS errors, response bodies, PostgREST messages, SQLSTATE, or authentication details. All non-record outcomes fail closed through the pure evaluator.

## 30. Decision-reason compatibility

Preserve every current reason string during async migration: `historical_audit_readonly_authorized`, `missing_historical_audit_readonly_capability`, `revoked_historical_audit_readonly_capability`, `expired_historical_audit_readonly_capability`, `malformed_capability_grant`, `duplicate_capability_grant`, `invalid_caller_identity`, `capability_source_unavailable`, `capability_source_timeout`, `capability_source_misconfigured`, `capability_source_forbidden`, and `capability_source_malformed`. Do not rename them in the async implementation PR. Any canonical-reason migration requires a separate compatibility PR.

## 31. Caller validation

The handler accepts caller identity only from the existing Supabase authentication middleware extension. Missing identity is rejected before route state authorization. Invalid identity is rejected by resolver preconditions before repository lookup. Request body, query, cookie, arbitrary header, and client claims other than the authenticated middleware result cannot supply authority.

## 32. Exact capability validation

The required capability remains the server-owned static constant `historical_audit:read`. A resolver constructed with any other value returns `capability_source_misconfigured` before lookup. Repositories and returned records must match the exact value; caller-controlled capability input is forbidden.

## 33. Time-source contract

`authorize` reads the server clock exactly once. `authorize_at` accepts only a server/test-supplied timestamp and does not read the clock. No request body, query parameter, header, cookie, or JWT claim can provide `now_ms`.

## 34. Same-now_ms requirement

One `now_ms` value is passed unchanged to repository lookup, PostgREST effective-grant filter construction, adapter returned-record expiration validation, pure resolver evaluation, and deterministic tests. Neither resolver nor adapter reads the clock again after lookup begins.

## 35. Timeout ownership

The Supabase adapter retains ownership of its bounded 750 ms default end-to-end timeout and approved configuration bounds. Add no resolver timeout, retry loop, hedging, fallback, or second request. No additional route-level authorization timeout is approved in this phase; revisit an outer request budget only during route-enablement review.

## 36. Cancellation semantics

Dropping the resolver future drops the repository future. Dropping the request future therefore cancels pending authorization, including the adapter timeout/transport future, without a detached task. No result is cached, no allow decision or retry occurs after cancellation, and secrets remain inside adapter-owned state rather than task metadata.

## 37. No-retry guarantee

The resolver calls `lookup_grants` at most once per decision. It adds no loop, backoff, retry library, failover destination, fallback lookup, or second confirmation query. The adapter's existing single-request behavior is unchanged.

## 38. No-cache guarantee

Do not add positive, negative, record, or decision caches. Each accepted authorization attempt receives an independent repository future and fresh bounded lookup. Cancellation leaves no cached state.

## 39. Unavailable repository migration

`UnavailableCapabilityGrantRepository` implements the async trait by cloning its typed `Misconfigured` result into `Box::pin(std::future::ready(...))` or an equivalent ready async block. It preserves `source_mode=unavailable`, performs no I/O, sleep, thread spawn, or task spawn, and remains the fail-closed production default.

## 40. Static test repository migration

`StaticTestCapabilityGrantRepository` remains fully under `#[cfg(test)]`, implements the async trait with a ready boxed future, performs no sleep or network access, supports authorized and unauthorized callers, and remains deterministic. No production configuration or constructor may instantiate it.

## 41. Supabase repository trait implementation

The private adapter implements the async repository trait and delegates exactly once to its existing async lookup behavior. It preserves exact capability, canonical UUID validation, effective-only filters, `limit=2`, strict response parsing, public-IPv4-only destination policy, sensitive headers, one-request cardinality, safe categorical errors, no retry, and no cache. No PR #559 security decision is reopened or weakened.

## 42. Adapter visibility

The repository trait and resolver remain `pub(crate)`. `SupabaseCapabilityGrantRepository` stays private to the capability submodule. The async implementation requires no production constructor exposure; a future AppState branch may expose only a narrowly scoped `pub(super)` constructor or repository factory after separate review. Transport and DTO seams remain private.

## 43. Configuration visibility

Existing configuration names, parsing, and validation remain private and dormant. The async-resolver implementation does not load configuration, read startup environment, export configuration types, or add `AppState` fields. No frontend, handler, or public payload can observe adapter configuration.

## 44. Secret ownership

The adapter alone owns the opaque service-role secret and creates sensitive privileged headers. The resolver, route, futures metadata, audit envelope, observability, logs, and errors never receive or copy secret text, JWTs, raw rows, raw responses, or query-bearing URLs.

## 45. Route-state migration

`HistoricalAuditRouteState::authorize` becomes async. It checks `route_enabled` first and returns `404 route_disabled` without calling the resolver; otherwise it awaits the resolver and maps the resulting decision. The state remains internal and no production configuration changes.

## 46. List-handler migration

`list_dry_run_audit` changes only its authorization call to `route_state.authorize(&caller_id).await`. It retains missing-identity rejection, denial envelope, rate limiting, query validation, and placeholder response ordering. No storage or service delegation is added.

## 47. Detail-handler migration

`get_dry_run_audit_detail` changes only its authorization call to `route_state.authorize(&caller_id).await`. It retains missing-identity rejection, denial envelope, rate limiting, plan-ID validation, and placeholder response ordering. No query service is called.

## 48. Authorization ordering

Preserve the current security ordering because it already matches the required future contract:

1. Supabase authentication middleware.
2. Extract authenticated `sub`.
3. Reject missing identity.
4. Check route-enabled gate.
5. Validate caller identity and exact server-owned capability.
6. Await exactly one capability lookup and pure evaluation.
7. Reject denied capability.
8. Apply the per-caller rate limit.
9. Validate list-query complexity or detail plan ID.
10. Return the placeholder service-delegation response.

This keeps unauthenticated/missing identity at `401`, disabled route at `404` for authenticated callers, and all storage/service work behind authorization.

## 49. Rate-limit ordering

Authorization completes before rate-limit mutation. Denied, timed-out, malformed, unavailable, or cancelled lookups do not consume a rate-limit slot. Rate limiting remains per caller and begins only after allow.

## 50. Lock-across-await analysis

No mutex is acquired before authorization. The rate-limit `MutexGuard` is created only after `.await`, remains local to synchronous `check_rate_limit`, and is dropped on return. No guard, mutable borrow, or shared authorization result crosses an await; a pending repository cannot deadlock the limiter.

## 51. Query-validation ordering

Query complexity and plan-ID validation remain after successful authorization and rate limiting, matching the current skeleton and required order. No storage query or service delegation occurs before authorization succeeds.

## 52. HTTP status preservation

Preserve: missing or invalid identity `401`; capability denial or any capability-source failure `403`; disabled route `404`; rate-limit denial `429`; placeholder service boundary `501`. Timeout, unavailability, forbidden, malformed, and misconfigured results must never become accidental `500` responses.

## 53. Envelope compatibility

Preserve the existing `SafeRouteEnvelope` shape, `status`, `degraded`, categorical `error_category`, warnings, route metadata, audit metadata, observability metadata, empty placeholder data, and bounded generated timestamp. Async migration adds no serialized field and exposes no future/transport detail.

## 54. Audit metadata compatibility

Preserve route ID, operation name, safe caller ID/source, allowed bit, exact legacy decision reason, source mode, safe query keys, and page size. Do not emit raw grants, lookup errors, secrets, URLs, headers, or a post-cancellation allow event.

## 55. Observability metadata compatibility

Preserve route ID, operation name, allowed bit, reason, source mode, status code, route-enabled value, and rate-limit configuration. Capability source failures remain categorical. Do not record transport bodies, DNS details, SQLSTATE, service-role details, or query URLs.

## 56. Disabled-by-default behavior

`HistoricalAuditRouteConfig::default()` remains `route_enabled=false` with the unavailable/misconfigured resolver. Even if a live adapter were accidentally present in an internal test configuration, the disabled gate must return before lookup.

## 57. Router remains unwired

The future async-resolver implementation must not modify `main.rs`, call `protected_historical_audit_router`, add `Router::merge`, or register candidate paths. Existing negative source-inspection tests remain.

## 58. No endpoint exposure

The candidate list and detail paths remain unavailable through public HTTP. No endpoint documentation, client, CORS change, route switch, or externally usable contract is approved.

## 59. No AppState integration

Neither this preparation branch nor the following async-resolver implementation branch adds an `AppState` field or startup constructor. AppState integration requires `feature/autonomy-dry-run-historical-audit-api-capability-source-appstate-integration-preparation` after explicit approval.

## 60. No query-service delegation

The route remains placeholder-only after authorization and disconnected from `HistoricalDryRunAuditQueryService`. `storage_accessed=false`, `runtime_invoked=false`, and `copy_export_enabled=false` remain true statements in the placeholder payload.

## 61. Future implementation files

After explicit Misael approval, one narrow implementation branch may modify only:

- `backend/rust/src/historical_audit_capability.rs`;
- `backend/rust/src/historical_audit_capability/supabase_capability_grant_repository.rs`;
- `backend/rust/src/protected_historical_audit.rs`;
- focused Rust tests contained in those modules;
- `docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-async-resolver-integration.md`.

## 62. Prohibited files

Prohibited are `backend/rust/src/main.rs`, every `AppState` definition/construction site, `backend/rust/Cargo.toml`, `backend/rust/Cargo.lock` absent a separate blocker review, migrations, environment files, workflows, frontend, Python, runtime/provider/prompt/tool execution, query-service delegation, router wiring, route enablement, endpoint exposure, copy/export, retention, and cleanup.

## 63. Unit-test matrix

| Area | Required focused tests |
| --- | --- |
| Unavailable repository | ready future returns `Misconfigured`; source mode remains `unavailable`; no lookup I/O/spawn |
| Static repository | authorized caller returns one record; unauthorized caller returns zero; remains `#[cfg(test)]`; repeated calls deterministic |
| Trait shape | Supabase adapter implements trait; `Arc<dyn ...>` is `Send + Sync`; returned future is `Send`; trait object dispatch succeeds |
| Preconditions | empty and malformed caller each avoid lookup; wrong required capability and an alternate invalid capability each avoid lookup; call count remains zero |
| Success/time | exactly one valid grant allows; repository receives exact caller/capability; same `now_ms` reaches lookup and evaluator; source remains `supabase_grants` |
| Denials | zero records; two effective records; wrong caller; wrong capability; inactive; revoked; expired; mixed historical rows; all preserve existing reasons |
| Outcomes | at least two assertions per categorical family where practical; all six variants map safely and retain source mode |
| Pure evaluator | deterministic repeated input; no clock or I/O; one active plus historical rows behavior preserved; malformed records fail closed |

## 64. Route-test matrix

| Path | Required focused tests |
| --- | --- |
| Short circuits | disabled list and detail perform zero calls; missing identity list and detail perform zero calls; invalid identity list and detail perform zero calls |
| Await behavior | list waits for pending lookup; detail waits for pending lookup; neither reaches rate limit or placeholder early |
| Denials | denied grant returns expected `403` envelope in both handlers; timeout and malformed each return safe `403`; source/reason preserved |
| Allow path | allowed list reaches rate limit then query validation; allowed detail reaches rate limit then plan-ID validation; both retain `501` placeholder |
| State mutation | denied lookup does not mutate limiter; cancellation does not mutate limiter; allowed lookup does; poisoned limiter behavior remains bounded and recoverable |
| Isolation | `production_wired=false`; `storage_accessed=false`; `runtime_invoked=false`; `copy_export_enabled=false`; disabled default remains `404` |

## 65. Cancellation-test matrix

Use controllable pending test futures with drop/completion/attempt counters. Cover at least: dropping `authorize_at` immediately after lookup begins drops the repository future; dropping immediately before signalled completion produces no detached completion; request-future cancellation propagates through route state; no second attempt starts; no cache survives cancellation; no allow/audit result is produced after drop. Repeat for a permanently pending future and for adapter timeout cancellation.

## 66. Concurrency-test matrix

Cover at least two simultaneous authorized callers with independent futures and results; one caller timeout while another succeeds; one caller cancellation while another completes; multiple callers sharing cloned immutable resolvers; pending lookup while another caller reaches its own repository future; no shared mutable decision/cache; no rate-limit guard across await; no deadlock; cancellation does not poison route state.

## 67. Regression-test matrix

Assert by source inspection and behavior that: `main.rs` is unchanged and has no route builder call; `AppState` has no capability field; no candidate path is registered; no frontend/Python/query-service/runtime change exists; no dependency was added; no blocking API, runtime creation, `block_on`, spawn, retry, cache, secret logging, endpoint, copy/export, self-repair, or autonomous execution was introduced. Retain all existing resolver, adapter, auth, route, and envelope tests.

## 68. Abuse-case matrix

| Abuse/failure case | Required fail-closed preparation |
| --- | --- |
| Slow repository | bounded adapter timeout; safe `403`; one attempt; cancellation-safe |
| Permanently pending repository | route remains cancellable; no lock held; test can drop future |
| Repeated timeout requests | independent requests; no retry/cache; bounded resource lifetime |
| Malformed caller flood | reject before lookup; zero network calls |
| Duplicate grants | pure evaluator denies `duplicate_capability_grant` |
| Source forbidden | categorical `Forbidden` to safe `403`; source remains `supabase_grants` |
| Malformed PostgREST response | categorical `Malformed`; no raw body/error exposure |
| Cancel just after lookup starts | repository future dropped; no detached completion |
| Cancel just before result completion | no post-drop allow/audit decision or cache |
| Disabled route with live adapter | disabled gate wins; zero lookup calls |
| Invalid capability constant | precondition deny; zero lookup calls |
| Poisoned rate-limit mutex | recovery remains after authorization; no await while guarded |
| Concurrent callers sharing resolver | independent futures and outcomes; no shared decision state |
| Caller-controlled capability attempt | impossible through public API; server static value only |
| Caller-controlled `now_ms` attempt | impossible; server/test-only value only |

## 69. Validation plan

Validate the committed PR diff with failing checks, not only by inspecting working-tree output:

```sh
git merge-base --is-ancestor \
  4a2e4ed5709d0c20eef15c63adf527f77224a307 \
  origin/main

git diff --check origin/main...HEAD

EXPECTED_FILE="docs/runtime/autonomy-dry-run-historical-audit-api-capability-source-async-resolver-integration-preparation.md"

test "$(git diff --name-only origin/main...HEAD)" = "$EXPECTED_FILE"
```

A nonzero ancestry-check exit blocks publication because the prepared async migration depends on the isolated adapter merged through PR #559. Separately, `git status --short` validates that the working tree and index contain no uncommitted changes. Scan the changed document, `origin/main...HEAD`, and the complete branch history with Gitleaks or the repository secret scan before publication. No Rust test is required because no Rust/Cargo file changes.

For the future implementation branch run:

```text
cargo fmt --manifest-path backend/rust/Cargo.toml -- --check
cargo check --manifest-path backend/rust/Cargo.toml
cargo test --manifest-path backend/rust/Cargo.toml
cargo clippy --manifest-path backend/rust/Cargo.toml --all-targets -- -D warnings
(
  cd backend/rust
  cargo audit
)
npm run test:security
npm run validate:public-demo
npm run validate:audit-pack
```

Also run focused resolver/route tests with pending-future instrumentation and the repository secret scan.

## 70. Dependency plan

No dependency is needed: `Future`, `Pin`, `Box`, and `Arc` are in the standard library, while Tokio already exists for async tests and adapter timeout. `async-trait`, blocking reqwest, executors, retry, and cache packages are no-go. Cargo files stay unchanged.

## 71. Security-review checklist

- [ ] One resolver remains the only policy owner.
- [ ] Exact caller, capability, source mode, outcome, and reason contracts are preserved.
- [ ] One server timestamp and one repository request are used per decision.
- [ ] Future and trait-object `Send`/`Sync` assertions pass.
- [ ] Cancellation drops work; no spawn, blocking, retry, cache, or lock across await exists.
- [ ] Adapter timeout, DNS/IP, strict parsing, header sensitivity, and redaction remain intact.
- [ ] Missing/invalid/disabled preconditions perform zero lookups.
- [ ] HTTP statuses and safe envelopes remain compatible.
- [ ] `AppState`, startup, router, route switch, endpoint, storage, frontend, and runtime remain untouched.
- [ ] Diff and secret scans contain only the approved files and no sensitive values.

## 72. Rollout plan

1. Merge this docs-only preparation manually after review.
2. Obtain explicit Misael approval for a new narrow async-resolver implementation branch from then-current `origin/main`.
3. Migrate the trait, all implementations, resolver, route-state test consumer, both handlers, and focused tests atomically.
4. Run focused and full validation plus security review.
5. Open a draft PR; keep the route disabled, unavailable, and unwired.
6. Merge only manually after approval. AppState work remains a later branch.

## 73. Rollback plan

Revert the future async-resolver implementation commit/PR as one atomic unit, restoring the synchronous trait and consumers. Because neither this preparation nor that implementation wires state, startup, router, route, storage, or endpoint, rollback requires no migration, data cleanup, secret rotation, or runtime traffic change. If any prohibited integration appears, stop and revert before review continues.

## 74. Known limitations

This review does not validate a real Supabase project, production cancellation under live traffic, external request budgets, secret provisioning, startup construction, operational health, router behavior after wiring, query-service behavior, or endpoint consumers. The adapter accepts only public IPv4 destinations by prior decision. Reason canonicalization is deliberately deferred.

## 75. Remaining blockers before AppState integration

Required blockers include: completed and reviewed async trait/resolver implementation; explicit AppState preparation approval; narrowly scoped repository factory/constructor visibility; server-only configuration loading design; secret provisioning and rotation; preview/staging validation; safe health/observability without secret or URL leakage; deployment failure/rollback procedure; operational ownership; and confirmation that state integration still does not imply router wiring.

## 76. Remaining blockers before router wiring

Require separate router-wiring preparation; completed AppState integration; authentication and middleware ordering review; explicit candidate path/collision analysis; full route tests using the live-shaped repository boundary; request budget/concurrency review; safe observability and rate-limit review; deployment rollback; and explicit Misael approval. Wiring must not imply enablement.

## 77. Remaining blockers before route enablement

Require explicit enablement review, preview/staging validation with non-production credentials/data, operational monitoring and alerting, abuse/load/cancellation evidence, outer request-budget decision, rate-limit sizing, incident/rollback runbook, access governance, and confirmation that the query service is still not delegated unless separately approved.

## 78. Remaining blockers before endpoint exposure

Require separate endpoint-exposure approval after wiring and enablement reviews; stable authenticated HTTP/envelope compatibility; privacy and data-minimization review; query-service authorization and storage boundary review; schema/RLS validation; public documentation decision; client/Cockpit threat model; CORS and deployment review; and explicit manual approval. Copy/export remains separate.

## 79. Go/no-go table

| Item | Decision | Boundary |
| --- | --- | --- |
| Documentation-only preparation | Go | This branch only |
| Async repository trait | Conditional go | Future narrow implementation after approval |
| Boxed `Send` future | Go | Approved exact shape |
| `async-trait` dependency | No-go | No new dependency |
| Synchronous blocking adapter | No-go | Never approved |
| `reqwest::blocking` | No-go | Never approved |
| Tokio `block_on` | No-go | Never approved |
| Nested Tokio runtime | No-go | Never approved |
| Detached authorization task | No-go | Never approved |
| Pure shared evaluator | Go | One private synchronous policy function |
| Permanent sync/async production dual stack | No-go | Atomic migration required |
| Async Supabase repository implementation | Conditional go | Delegate once; preserve PR #559 |
| Async unavailable repository | Conditional go | Ready boxed future |
| Async static test repository | Conditional go | `#[cfg(test)]`, ready future |
| Async resolver `authorize` | Conditional go | One timestamp and one lookup |
| Async route-state `authorize` | Conditional go | Disabled gate before await |
| List handler await | Conditional go | Route stays unwired |
| Detail handler await | Conditional go | Route stays unwired |
| One `now_ms` per decision | Go | Mandatory invariant |
| Repository-owned timeout | Go | Preserve adapter bound |
| Additional resolver timeout | No-go | Revisit at route enablement |
| Retry | No-go | Resolver and adapter |
| Positive cache | No-go | Authorization freshness |
| Negative cache | No-go | Authorization freshness |
| Cancellation propagation | Go | Drop request/resolver/repository future |
| Capability reason renaming | No-go | Separate compatibility PR only |
| AppState integration | No-go | Later preparation branch |
| Configuration loading | No-go | No startup work |
| Secret provisioning | No-go | No deployment work |
| Router wiring | No-go | Later branch |
| Route enablement | No-go | Later branch |
| Endpoint exposure | No-go | Later branch |
| Historical query-service delegation | No-go | Separate review |
| Cockpit consumption | No-go | No frontend |
| Copy/export | No-go | Separate review |
| Frontend changes | No-go | Prohibited |
| Python changes | No-go | Prohibited |
| Runtime/provider/prompt/tool changes | No-go | Prohibited |
| Self-repair | No-go | Prohibited |
| Autonomous execution | No-go | Prohibited |
| Manual merge by Misael | Go | Exclusive final merge authority |

## 80. Acceptance criteria

- The branch contains only this preparation document and accurately records base/PR #559.
- One object-safe boxed `Send` future trait shape is approved without dependencies.
- All repository implementations migrate together; no blocking, runtime nesting, spawn, dual stack, retry, or cache is approved.
- Resolver methods become async while one pure evaluator retains all policy and reason strings.
- One timestamp, stable source mode, typed outcomes, timeout ownership, and future-drop cancellation are explicit.
- Route-state and both handlers await authorization before rate limiting and validation, with no lock across await.
- Status/envelope/audit/observability compatibility and disabled/unwired/no-endpoint state are preserved.
- Future/prohibited file scopes, comprehensive tests, abuse cases, rollout, rollback, and blockers are explicit.
- `Cargo.toml`, `Cargo.lock`, `main.rs`, `AppState`, router, and production behavior are unchanged.
- Publication is a draft PR; auto-merge and merge are not performed.

## 81. Final recommendation

Approved for docs-only async-resolver integration preparation. Approved for one asynchronous `CapabilityGrantRepository` contract, an object-safe boxed `Send` future, asynchronous `HistoricalAuditCapabilityResolver` methods, and one shared pure policy evaluator. Approved for async migration of unavailable and static-test repositories and for the isolated Supabase adapter to implement the async repository contract. Approved for future asynchronous migration of the protected route consumer while it remains disabled and unwired. Approved for cancellation propagation by future dropping, preservation of current reason strings and source-mode semantics, and preservation of adapter timeout/no-retry/no-cache behavior.

Conditionally approved for a future narrow implementation branch only after explicit Misael approval. Not approved for implementation in this branch, AppState integration, startup configuration loading, router wiring, route enablement, endpoint exposure, query-service delegation, frontend/Cockpit, copy/export, or runtime/provider/prompt/tool/autonomy/self-repair changes. Merge remains manual and exclusive to Misael.
