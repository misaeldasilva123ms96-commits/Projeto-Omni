# Dry-Run Historical Audit API Capability Source Design Review

## 1 Executive summary

This design review approves documentation and capability-source design review only for the future `historical_audit:read` authorization check required by the protected historical dry-run audit API route skeleton.

The approved design direction is server-side-only capability evaluation after Supabase JWT authentication and before any service delegation. Client-provided, request-provided, header-provided, and environment-only production capabilities are rejected. The route switch must remain disabled by default, the production router must remain unwired, and endpoint exposure remains not approved.

## 2 Scope

Scope is limited to defining how Omni should eventually decide whether an authenticated Supabase JWT caller may read historical dry-run audit metadata through the protected skeleton. This review covers capability name, caller identity assumptions, source options, recommended model, failure behavior, safe audit/observability requirements, tests, abuse cases, rollback, risks, and go/no-go decisions.

## 3 Non-goals

This branch does not implement the capability source, modify route code, modify `main.rs`, wire the router, enable the route, add database reads, add Supabase queries, add schema or migrations, add cross-language delegation, expose endpoints, add Cockpit/detail drawer UI, add copy/export, add retention/cleanup, or change runtime/provider/prompt/execution behavior.

## 4 Reviewed materials

- `backend/rust/src/protected_historical_audit.rs`
- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs`
- Existing Rust protected route patterns in `main.rs`
- Existing Rust config/server state patterns in `AppState`
- Existing Rust caller identity use in settings handlers
- `docs/runtime/autonomy-dry-run-historical-audit-api-protected-route-skeleton.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-protected-route-skeleton-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-route-registration-design-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-implementation-controls.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-implementation-controls-governance-review.md`

## 5 Current implementation state

The protected route skeleton defines `HISTORICAL_AUDIT_READONLY_CAPABILITY = "historical_audit:read"`. It uses `require_supabase_auth`, extracts caller identity from the authenticated Supabase `sub`, checks route-local test authorization through server-side skeleton config, defaults disabled, and returns a `501 service_delegation_unavailable` placeholder when enabled and authorized in tests.

Production `main.rs` declares the module for compilation but does not merge `protected_historical_audit_router(...)` into the app router. No production capability source exists.

## 6 Current governance state

PR #513 approved the skeleton only as isolated, protected, unwired, and fail-closed. Capability source design is the next governance blocker. Cross-language delegation, production router wiring, route enablement, endpoint exposure, public exposure, Cockpit/detail drawer, copy/export, retention/cleanup, raw storage, direct MemoryFacade access, and execution behavior remain blocked.

## 7 Capability being reviewed

The capability under review is exactly:

`historical_audit:read`

This capability authorizes readonly access to safe historical dry-run audit metadata only. It does not authorize route enablement, service delegation, public exposure, Cockpit consumption, copy/export, retention/cleanup, storage access, prompt access, provider access, retry/replan, autonomous execution, or self-repair.

## 8 Why capability source is required

Supabase JWT authentication proves the caller has a valid session, but it does not by itself prove the caller is allowed to inspect historical dry-run audit metadata. The route needs a server-side capability source so authenticated but unauthorized callers fail closed before rate/query work can reach any future service boundary.

## 9 Threat model

The design must defend against authenticated users probing historical audit metadata, clients forging capability claims, headers attempting to grant roles, query parameters attempting privilege escalation, stale JWT claims, route discovery, broad audit scraping, sensitive operational inference, logging leaks, and fallback paths that accidentally treat audit evidence as execution input.

## 10 Caller identity assumptions

Caller identity is the authenticated Supabase `sub` inserted into Axum request extensions by `require_supabase_auth`. A missing, empty, unsafe, or unavailable `sub` must fail closed before capability evaluation can succeed.

## 11 Supabase JWT boundary

The existing Supabase JWT middleware validates bearer tokens, rejects missing/malformed/expired/invalid tokens, validates issuer, and inserts `sub` when present. The capability source must be evaluated only after this boundary succeeds.

## 12 Supabase sub as caller identity

`sub` is the stable authorization lookup key for this route. The route must not accept caller id, user id, subject, role, or capability from query params, path params, request bodies, cookies, or arbitrary headers.

## 13 Required capability name

The required capability name is approved as `historical_audit:read`. Future implementation must use exact string matching and must not accept aliases such as `admin`, `operator`, `audit`, `read`, or wildcard-like values.

## 14 Capability granularity

The capability is route-specific and read-only. It grants only permission to request safe historical dry-run audit metadata through the protected route, after all other guards pass. It is not a broad operator capability.

## 15 Readonly-only requirement

The capability must not permit mutation, deletion, retention cleanup, export generation, copy/download, prompt rewrite, retry execution, replan execution, provider/model calls, or autonomous action. Future responses must continue to state that results are audit metadata, not approval and not execution input.

## 16 Server-side-only source requirement

Capability evaluation must occur on the server using a server-controlled source. The client may authenticate with a Supabase JWT, but the client must not be trusted to supply the authorization decision.

## 17 Client claim rejection

Client-provided capability claims are rejected. A future implementation must not trust client-side local storage, UI state, request bodies, JSON payload fields, browser Supabase metadata, or frontend-computed roles as the authorization source.

## 18 Request parameter rejection

Request parameters must not grant or influence authorization. Query params such as `capability=historical_audit:read`, `role=admin`, `authorized=true`, or `caller_id=...` must be ignored or rejected and must not affect the server-side decision.

## 19 Header-provided capability rejection

Headers must not grant the capability. `X-Role`, `X-Capability`, `X-User-Role`, forwarded identity headers, or similar values are not trusted authorization sources for this route.

## 20 Environment-only capability risk

An environment-only production allowlist is risky because it is operationally coarse, hard to audit per caller, easy to drift across deployments, and usually requires deploy/config changes for revocation. It may be acceptable for isolated tests but is not approved as the production source.

## 21 Static allowlist risk

A static local allowlist is useful for skeleton tests but unsafe as production authorization because it couples access policy to code or process config. Static test capability remains acceptable only for isolated tests and must not become production policy.

## 22 Supabase table-backed capability option

A Supabase table-backed source would store caller-to-capability grants server-side and be read by the Rust backend using server-side credentials or a tightly scoped RPC. This option provides revocation, auditability, explicit grants, and separation from client-controlled request data. It requires a future schema/query/security review before implementation.

## 23 Supabase role/claim-backed capability option

A Supabase role or custom-claim source can reduce lookup latency, but JWT claims may be stale until token refresh and can blur authentication with authorization. This option is not approved as the sole production source for historical audit access unless a future design proves freshness, revocation, and tamper-resistance.

## 24 Internal config-backed capability option

An internal config-backed source can be useful for local development, tests, or emergency deny behavior. It is not recommended as the primary production allow source because revocation, observability, and per-caller governance are weaker than a durable server-side authorization registry.

## 25 Hybrid option

A hybrid design can combine a durable server-side production source with test-only static config and an operational deny/disable path. Hybrid is acceptable only if the production allow decision comes from the server-side authority, the route switch still gates access, and every unavailable or inconsistent source fails closed.

## 26 Recommended capability source design

Recommended design: a future Rust capability resolver evaluates `historical_audit:read` server-side for the authenticated Supabase `sub`, with Supabase table-backed grants as the preferred production authority. The resolver must run after JWT validation and the disabled-route switch, before rate/query work reaches service delegation.

The only approved non-production fallback is test-only static configuration under test/build controls. Production must not accept client claims, request params, headers, or environment-only allowlists as the final allow decision.

## 27 Fail-closed behavior

Capability evaluation must fail closed when the caller is missing, the source is unavailable, the source returns malformed data, the capability is absent, multiple inconsistent records exist, or the route switch is disabled. Denials must return safe degraded metadata only.

## 28 Missing capability behavior

An authenticated caller without `historical_audit:read` must receive a forbidden denial before service delegation. The denial must not reveal other capabilities, grant lists, table structure, SQL, storage rows, or operational secrets.

## 29 Invalid capability behavior

Invalid capability names, aliases, wildcard values, disabled grants, expired grants, or malformed source records must deny access. Invalid source data must be treated as an authorization failure, not as a partial allow.

## 30 Unknown caller behavior

Unknown callers must be denied. Unknown means the authenticated `sub` has no active server-side grant for `historical_audit:read` in the production source.

## 31 Disabled route switch interaction

The disabled route switch remains the first rollback boundary. While disabled, capability lookup should not be required for access and must not cause route exposure. A future implementation may avoid production source calls while disabled, but the observable result must remain `route_disabled`.

## 32 Rate/size/query guard interaction

Capability denial must happen before any future service delegation. Rate limits, size checks, and query guards remain required, but they do not substitute for authorization. The future implementation should ensure denied callers cannot use query behavior to infer audit data.

## 33 Safe audit logging requirements

Audit logs may record safe route id, operation name, caller id or safe caller category, capability required, allowed/denied decision, denial reason, status code, route-enabled state, query-key summary, and timestamp. Logs must not include bearer tokens, headers, cookies, raw JWTs, grant table rows, SQL, secrets, raw storage, prompts, provider payloads, tool outputs, stacks, stdout/stderr, raw exceptions, or raw reprs.

## 34 Safe observability requirements

Observability may track counts for allowed decisions, missing capability denials, invalid capability denials, unknown caller denials, source-unavailable denials, route-disabled denials, rate-limit denials, validation denials, and bounded latency. Metrics must be aggregate and safe, not raw authorization source dumps.

## 35 Forbidden fields

Responses, logs, and metrics must not expose raw JSONL, raw SQLite rows, raw SQL, prompts, responses, provider payloads, tool outputs, secrets, headers, cookies, stack traces, stdout/stderr, command args, file contents, `.env` content, raw exceptions, raw reprs, bearer tokens, JWTs, or capability-source raw records.

## 36 No raw storage exposure

Capability evaluation must not expose raw storage and must not read historical audit storage directly. It only decides whether the caller may proceed to the future safe route flow.

## 37 No direct MemoryFacade access

Capability source work must not call MemoryFacade. Direct API-to-MemoryFacade access remains not approved.

## 38 No HistoricalDryRunAuditQueryService changes

Capability source work must not modify `HistoricalDryRunAuditQueryService`. Service delegation remains a separate blocker and requires separate design review.

## 39 No route enablement

This design review does not approve route enablement. The route switch remains disabled by default.

## 40 No production router wiring

This design review does not approve production router wiring. `protected_historical_audit_router(...)` must remain unmerged until a future approved branch.

## 41 No public exposure

Public exposure is not approved. The capability source must not be used to justify public historical audit endpoints.

## 42 No Cockpit/detail drawer consumption

Cockpit/detail drawer consumption is not approved. UI work remains blocked until endpoint exposure and frontend redaction governance are separately approved.

## 43 No copy/export

Copy/export is not approved. Capability `historical_audit:read` must not imply export rights.

## 44 No retention/cleanup

Retention/cleanup is not approved. Capability `historical_audit:read` must not imply deletion, pruning, or lifecycle permissions.

## 45 Required implementation constraints for future branch

A future implementation branch must be narrow, Rust-owned, server-side only, exact-match on `historical_audit:read`, keyed by authenticated Supabase `sub`, fail-closed, redaction-safe, and isolated from runtime/provider/prompt/execution behavior. It must not alter route exposure, route enablement, production wiring, storage behavior, MemoryFacade, or HistoricalDryRunAuditQueryService.

## 46 Required tests for future branch

Future tests must cover source availability, missing source, malformed source, missing caller, unknown caller, missing capability, invalid capability, exact capability match, disabled route precedence, no request/header/client capability trust, safe audit/observability output, and no service delegation on denial.

## 47 Required negative tests

Negative tests must prove denial for missing JWT, invalid JWT, missing `sub`, unsafe `sub`, unknown caller, missing capability, disabled capability, expired capability if supported, wrong capability, wildcard capability, client-provided capability, header-provided capability, query-param-provided capability, source outage, malformed records, and route disabled.

## 48 Required positive tests

Positive tests must prove that an authenticated caller with an active server-side `historical_audit:read` grant can pass the capability check only when the route is explicitly enabled in test configuration, while still reaching only the placeholder or approved future service boundary.

## 49 Abuse cases

Abuse cases include a valid user attempting broad audit scraping, repeated pagination, filter probing, route discovery, privilege escalation through headers or params, replaying stale JWT claims, operational insight mining through denial details, and pressure to use audit records as execution instructions.

## 50 Rollback requirements

Rollback must be possible by keeping the route switch disabled or disabling the future capability source path without changing runtime/provider/prompt/storage behavior. Source failure must deny rather than expose, and rollback must not require deleting historical evidence.

## 51 Operational monitoring requirements

Future monitoring should track safe counts for capability allows, capability denials, source errors, route-disabled denials, unknown callers, invalid source records, rate-limit denials, and validation denials. Alerts should focus on repeated denials, source outages, and unexpected allow spikes without exposing raw caller secrets or source records.

## 52 Open risks

- Supabase table schema and RPC/security model are not designed.
- Capability revocation freshness is unresolved.
- Claim-backed authorization may become stale if used incorrectly.
- Environment/static allowlists could drift if promoted beyond tests.
- Future route wiring could accidentally evaluate rate/query work before authorization unless tests enforce order.

## 53 Open questions

- What exact Supabase table or RPC shape should hold `historical_audit:read` grants?
- Should grants support expiration, reason, reviewer, and audit metadata?
- Should capability checks be cached, and if so what maximum TTL is acceptable?
- What safe audit sink should record authorization denials?
- Who is the operational owner for grant creation and revocation?

## 54 Go/no-go table

| Area | Decision | Rationale |
| --- | --- | --- |
| Documentation | Go | Approved for this design review. |
| Capability-source design review | Go | Approved as documentation/design only. |
| Capability name historical_audit:read | Go | Approved as exact readonly capability name. |
| Server-side capability evaluation | Go | Required for future authorization. |
| Client-provided capability | No-go | Client-controlled data is not trusted. |
| Header-provided capability | No-go | Headers cannot grant access. |
| Request-param-provided capability | No-go | Query/path/body input cannot grant access. |
| Static local test capability | Go | Approved for isolated tests only. |
| Environment-only production capability | No-go | Too coarse for production authorization. |
| Supabase table-backed capability source | Conditional go | Recommended production direction; requires future implementation review. |
| Supabase claim-backed capability source | Conditional go | May be a supplemental design only if revocation and freshness are solved. |
| Hybrid capability source | Conditional go | Acceptable if production allow comes from a server-side authority. |
| Capability-source implementation | Conditional go | Future narrow branch only after explicit Misael approval. |
| Production router wiring | No-go | Not approved. |
| Route enablement | No-go | Not approved. |
| Endpoint exposure | No-go | Not approved beyond isolated skeleton tests. |
| Public exposure | No-go | Not approved. |
| Cross-language delegation design | No-go | Separate future design review only. |
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

## 55 Final recommendation

Approve this branch for documentation and capability-source design review only. Approve the capability name `historical_audit:read`, server-side-only evaluation, fail-closed behavior, and rejection of client/request/header-provided capability data.

The recommended future model is a server-side Rust capability resolver keyed by authenticated Supabase `sub`, with a Supabase table-backed grant source as the preferred production authority and static allowlists limited to isolated tests. A future narrow implementation branch may proceed only after explicit Misael approval. Production router wiring, route enablement, endpoint exposure, public exposure, cross-language delegation implementation, Cockpit/detail drawer, copy/export, retention/cleanup, raw storage access, direct MemoryFacade access, prompt/provider/runtime/execution changes, autonomous execution, and self-repair remain not approved.
