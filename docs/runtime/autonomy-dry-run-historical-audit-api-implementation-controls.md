# Dry-Run Historical Audit API Implementation Controls

## 1 Executive summary
Implementation controls were added for a future historical dry-run audit API boundary. The controls are dormant, fail closed by default, and do not register or expose any route.

## 2 Scope
This change adds route-specific authorization, caller identity extraction, route switch configuration, request complexity guards, safe audit fields, safe observability fields, and focused tests for a future internal historical dry-run audit route.

## 3 Non-goals
This change does not register routes, expose endpoints, add Cockpit UI, add detail drawers, add copy/export, add retention cleanup, change runtime behavior, change provider routing, change prompts, or trigger execution.

## 4 Files inspected
- `backend/python/brain/memory/historical_audit_internal_api.py`
- `backend/python/brain/memory/historical_audit_query_models.py`
- `backend/python/brain/memory/historical_audit_query_service.py`
- `backend/python/brain/runtime/rate_limiter.py`
- `backend/python/brain/runtime/observability/public_runtime_payload.py`
- `backend/rust/src/observability_auth.rs`
- `backend/rust/src/main.rs`

## 5 Controls added
The new `historical_audit_route_controls.py` module adds dormant pre-route controls for caller identity, readonly capability authorization, route disablement, bounded rate and size configuration, query complexity checks, safe audit event construction, and safe observability field construction.

## 6 Authorization model
Authorization requires an accepted caller identity and the exact `historical_audit:read` capability. Missing callers, invalid callers, unauthorized callers, and callers without the historical-audit readonly capability fail closed.

## 7 Caller identity model
Caller identity extraction accepts only a safe authenticated Supabase `sub` string. Empty, non-string, path-like, query-like, token-like, or otherwise unsafe identities are rejected before authorization.

## 8 Route switch behavior
The route switch defaults to disabled. Disabled route state returns a fail-closed control decision and blocks the authorization helper before any future handler could reach query logic.

## 9 Rate limit control
The route-control configuration includes bounded deterministic rate limit fields. The default is 30 requests per 60 seconds, and values are clamped to safe upper bounds.

## 10 Size limit control
The route-control configuration includes bounded deterministic request size fields for query parameter count, parameter length, plan id length, page size, and offset.

## 11 Query complexity control
List query complexity validation rejects unsupported parameters, excessive filters, excessive pagination, unsupported sort fields, unsupported sort directions, and oversized values. Detail query complexity validation rejects missing, oversized, or unsafe plan ids.

## 12 Safe audit schema
The safe audit event schema contains only route id, operation name, caller id/source, decision status, query key summary, page size, safe logging flag, warnings, and generation time. It excludes raw request bodies, raw JSONL, raw SQLite rows, raw SQL, prompts, provider payloads, tool outputs, secrets, headers, cookies, stacks, stdout, stderr, command args, file contents, and raw exceptions.

## 13 Safe observability schema
The safe observability schema contains only route id, operation name, decision status, route enabled state, bounded rate limit values, safe observability flag, and bounded latency. It excludes raw runtime payloads, provider data, prompts, tool data, secrets, headers, cookies, stacks, stdout, stderr, command args, file contents, and raw exceptions.

## 14 Rollback/disablement behavior
Rollback is the default: route controls are disabled unless explicitly enabled in a future reviewed branch. The disabled switch fails closed and keeps route registration blocked.

## 15 Test evidence
Focused unit tests cover missing auth, invalid caller identity, unauthorized caller, missing readonly capability, authorized helper pass-through, default disabled state, disabled fail-closed behavior, bounded rate config, bounded size config, query complexity rejection, safe audit schema redaction, safe observability schema redaction, no raw storage/SQL/provider/prompt/tool exposure, no direct API-to-MemoryFacade exposure, no route registration, and no runtime/provider/execution trigger.

## 16 Validation evidence
Validation completed with `git diff --check`, Python compilation of changed files, focused historical audit route-control tests, existing internal API tests, existing query-service tests, historical audit memory discovery tests, and runtime autonomy unittest discovery. All commands passed.

## 17 Explicit no-route-registration confirmation
No Rust or Python router was modified. The future historical dry-run audit route remains unregistered.

## 18 Explicit no-endpoint-exposure confirmation
No endpoint was exposed. Route exposure remains blocked, and public exposure remains blocked.

## 19 Explicit no-Cockpit/export confirmation
No Cockpit surface, detail drawer, copy flow, export flow, or frontend API consumer was added. Cockpit/detail drawer remains blocked. Copy/export remains blocked.

## 20 Explicit no-runtime/provider/prompt/execution confirmation
Runtime/provider/prompt/execution remains unchanged. The controls do not call provider/model logic, execute retry/replan, self-repair, or autonomous execution.

## 21 Remaining blockers before route registration
Route registration still requires a separate reviewed branch, explicit internal routing design approval, final auth integration review, rate limiter integration review, audit/observability review, and endpoint-level validation evidence. Retention/cleanup remains blocked.

## 22 Go/no-go table
| Area | Status | Reason |
| --- | --- | --- |
| Implementation controls | Go | Controls added and tested. |
| Route registration | No-go | No reviewed route-registration branch yet. |
| Route exposure | No-go | Exposure remains explicitly blocked. |
| Public exposure | No-go | Public exposure remains explicitly blocked. |
| Cockpit/detail drawer | No-go | UI remains out of scope. |
| Copy/export | No-go | Export behavior remains out of scope. |
| Retention/cleanup | No-go | Cleanup policy remains out of scope. |
| Runtime/provider/prompt/execution | No-go | Behavior must remain unchanged. |

## 23 Final recommendation
Keep route registration blocked. Future route registration should happen only in a separate branch after review of these implementation controls, with no public exposure and no Cockpit/export expansion unless separately authorized.
