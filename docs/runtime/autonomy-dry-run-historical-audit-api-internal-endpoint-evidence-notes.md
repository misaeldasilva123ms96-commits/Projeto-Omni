# Autonomy Dry-Run Historical Audit Internal API Endpoint Evidence Notes

**Date:** 2026-06-30
**Branch:** `feature/autonomy-dry-run-historical-audit-api-internal-endpoint-evidence-notes`
**Base:** `main` after PR #477
**Status:** Evidence notes only
**Runtime impact:** None

## 1. Executive Summary

PR #477 added internal contract-level handlers for historical dry-run audit
reads. These handlers define how future internal API routes may call the
historical audit service, but they are not registered as routes and are not
publicly exposed.

The handlers fail closed by default with `internal_enabled=False`. That guard
prevents accidental use while route exposure remains blocked. It is not
authentication, not authorization, and not a substitute for a future protected
route boundary.

## 2. Scope

This document explains the evidence from PR #477:

- What contract handlers were added.
- How list and detail reads behave.
- Why handlers remain unregistered.
- Why `internal_enabled=False` is fail-closed.
- How service-only delegation is preserved.
- What raw access paths remain forbidden.
- What tests and validation were run.
- What controls remain required before any route registration or exposure.

## 3. Non-Goals

This document does not:

- Add API endpoints.
- Register routes.
- Add or modify handlers.
- Modify runtime, persistence, MemoryFacade, internal query service, SQLite, or
  frontend/Cockpit code.
- Add detail drawer, copy/export, retention/cleanup, or route exposure.
- Rewrite prompts.
- Execute retry or replan.
- Call provider/model code.
- Change provider routing or runtime output.
- Enable autonomous execution or self-repair.

## 4. PR #477 Implementation Summary

PR #477 added contract scaffolding for future internal historical dry-run audit
reads:

- A small internal API contract module.
- List and detail contract handler functions.
- A response envelope type for handler return values.
- A service protocol matching `HistoricalDryRunAuditQueryService` behavior.
- Query and path parsing with safe validation.
- Fail-closed behavior when `internal_enabled=False`.
- Tests covering safe delegation, degradation, warnings, forbidden fields, and
  non-execution boundaries.

No route registration or public exposure was added.

## 5. Files Changed in PR #477

PR #477 changed:

- `backend/python/brain/memory/historical_audit_internal_api.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_internal_api.py`
- `docs/runtime/autonomy-dry-run-historical-audit-api-internal-endpoint-governance-review.md`

The governance document was updated to state that no reusable real
auth/authorization route pattern was identified for exposing historical audit
reads, so contract handlers must remain unregistered and fail closed until a
separate route-exposure branch adds the required controls.

## 6. Contract Handler Inventory

The contract module introduced:

- `query_historical_dry_run_audit_internal_endpoint(...)`
- `get_historical_dry_run_audit_internal_endpoint_detail(...)`
- `HistoricalDryRunAuditEndpointResponse`
- `HistoricalDryRunAuditEndpointService`

Candidate path constants are present for design alignment:

- `/internal/audit/dry-run`
- `/internal/audit/dry-run/`

These constants do not register routes.

## 7. List Handler Behavior

The list handler:

- Fails closed unless `internal_enabled=True`.
- Parses only allowed query parameters.
- Builds a `DryRunAuditQueryRequest`.
- Rejects unsupported parameters.
- Enforces size guards.
- Preserves existing governed filter, enum, sort, timestamp, ID, and bounded
  pagination behavior through `DryRunAuditQueryRequest`.
- Delegates to `service.query_historical_dry_run_audit(...)`.
- Returns a sanitized response envelope.
- Degrades with categorical error metadata only.

## 8. Detail Handler Behavior

The detail handler:

- Fails closed unless `internal_enabled=True`.
- Validates the supplied `plan_id`.
- Rejects oversized or unsafe path values.
- Delegates to `service.get_historical_dry_run_audit_detail(...)`.
- Returns a sanitized detail envelope.
- Returns `not_found` safely when no detail exists.
- Degrades with categorical error metadata only.

## 9. Fail-Closed internal_enabled=False Behavior

`internal_enabled=False` is the default. With that default:

- The list handler returns `404` with `internal_route_disabled`.
- The detail handler returns `404` with `internal_route_disabled`.
- The service is not called.
- No storage, runtime, provider, retry, or replan path is reached.

This is fail-closed behavior. It is not auth and must not be treated as auth.

## 10. Why Handlers Remain Unregistered

Handlers remain unregistered because route exposure is not approved yet. The
repository has internal Python service routes, but PR #476 did not identify a
reusable auth/authorization pattern sufficient for historical audit reads.

Route registration remains blocked until a separate branch adds and tests real:

- Authentication.
- Authorization.
- Rate limits.
- Size limits.
- Audit logging.
- Observability.
- Abuse review.
- Security review.

## 11. HistoricalDryRunAuditQueryService-Only Delegation Evidence

The contract module accepts a `HistoricalDryRunAuditEndpointService` protocol
with only two methods:

- `query_historical_dry_run_audit(...)`
- `get_historical_dry_run_audit_detail(...)`

The handlers call only those methods. This preserves the approved boundary:

future route -> contract handler -> `HistoricalDryRunAuditQueryService` ->
MemoryFacade safe query contracts

## 12. MemoryFacade Bypass Prevention

The endpoint contract handlers do not accept a MemoryFacade instance and do not
import MemoryFacade. That prevents direct API-to-MemoryFacade access at this
layer.

Tests use a service spy and verify delegation to the service methods only.
Tests also include unsafe attribute guards for storage/runtime/provider-like
names.

## 13. Raw Storage Exposure Prevention

The contract module does not read JSONL directly, does not read SQLite
directly, and does not construct SQL.

Raw storage exposure remains forbidden:

- No raw JSONL.
- No raw SQLite rows.
- No raw SQL.
- No storage paths.
- No adapter internals.
- No raw database rows.

## 14. Query/Path Parsing Evidence

Query parsing allows only known filter and control parameters:

- Filters such as `plan_type`, `event_type`, `source_decision`, `risk_level`,
  `blocked`, `recorded`, `degraded`, `storage_mode`, `sqlite_enabled`,
  `request_id`, `trace_id`, `session_id`, created-at range, and recorded-at
  range.
- Controls `sort_by`, `sort_direction`, `limit`, and `offset`.

Path parsing for detail reads sanitizes `plan_id` through the existing safe ID
rules before calling the service.

## 15. Size Guard Evidence

The contract module defines route-level contract guards:

- Maximum query parameter count.
- Maximum query parameter length.
- Maximum `plan_id` length.

Oversized inputs degrade safely to `payload_too_large` and do not call the
service.

## 16. Bounded Pagination Evidence

The list handler uses `DryRunAuditQueryRequest`, which already enforces the
historical audit query pagination bounds. Oversized `limit` values are clamped
by the governed request model.

The handler does not introduce unbounded query behavior.

## 17. Safe Response Envelope Evidence

List responses use `HistoricalDryRunAuditEndpointResponse` with:

- `status_code`
- `body`
- JSON content-type header metadata

The body comes from `DryRunAuditQueryResponse.as_dict()` or a degraded response
built from existing safe query models.

## 18. Detail Response Safety Evidence

Detail responses include:

- `detail`
- `warnings`
- `degraded`
- `generated_at`
- `error_category` only when degraded

When a safe detail exists, it comes from `DryRunAuditEvidenceDetail.as_dict()`.
When it does not exist or fails validation, no raw row or raw exception is
returned.

## 19. Categorical Error/Degradation Evidence

Allowed endpoint error categories are fixed and categorical:

- `internal_route_disabled`
- `invalid_request`
- `invalid_filter`
- `invalid_sort`
- `payload_too_large`
- `not_found`
- `query_failed`
- `invalid_service_response`

Raw exceptions and tracebacks are never returned.

## 20. Required Advisory Warnings Evidence

Responses preserve the required advisory warnings:

- Query results are readonly audit metadata.
- Query results are not approval.
- Query results are not execution input.
- `would_retry` and `would_replan` are not execution.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- Copy/export remains disabled.
- Omni remains advisory-only.

## 21. Forbidden Field Exclusion Evidence

PR #477 tests assert that responses do not contain forbidden terms such as:

- `raw_prompt`
- `rewritten_prompt`
- `raw_response`
- `provider_payload`
- `api_key`
- `token=`
- `traceback`
- `stack trace`
- `stdout`
- `stderr`
- `command args`
- `file contents`
- `raw jsonl`
- `raw sql`
- `database row`

The tests intentionally include these strings as negative fixtures; they are
not exposed by successful or degraded handler responses.

## 22. No Public Route Exposure Evidence

PR #477 did not register any route. It added callable contract handlers only.

No public API route was exposed.

## 23. No Router Registration Evidence

The implementation did not modify router registration code. There is no
handler binding to HTTP server route tables, frontend clients, or Cockpit
consumption paths.

## 24. No Cockpit/Frontend/Detail Drawer Evidence

PR #477 did not modify frontend code and did not add Cockpit consumption.

No detail drawer behavior was added.

## 25. No Copy/Export Evidence

The contract handlers are read-only metadata envelopes. They do not implement:

- Copy safe summary.
- CSV export.
- JSON export.
- Raw JSONL export.
- Raw SQLite export.
- Bulk dump behavior.

## 26. No Retention/Cleanup Evidence

The contract handlers do not delete, expire, compact, migrate, or clean up
historical evidence.

Retention/cleanup remains a separate governance area.

## 27. No Runtime/Provider/Prompt Behavior Evidence

PR #477 did not modify runtime code, provider routing, prompt handling, or
runtime output.

The contract handlers do not call runtime or provider/model code.

## 28. No Retry/Replan Execution Evidence

The contract handlers are readonly and do not execute retry or replan. Tests
assert that response payloads do not include retry/replan execution controls.

`would_retry` and `would_replan` remain audit metadata only.

## 29. No Autonomous Execution Evidence

No autonomous execution path was added. Persisted evidence and query results
remain audit metadata only and are not execution input.

Omni remains advisory-only.

## 30. Test Evidence Summary

PR #477 added focused tests covering:

- List handler fail-closed behavior.
- Detail handler fail-closed behavior.
- Service-only delegation when enabled.
- Query parameter validation.
- Unsupported query parameter rejection.
- Size guard behavior.
- Invalid `plan_id` rejection.
- Service failure degradation.
- Invalid service response degradation.
- Required advisory warnings.
- Forbidden field exclusion.
- No runtime/provider/execution controls.

## 31. Validation Evidence Summary

Validation reported for PR #477:

- New internal API endpoint contract tests passed with `unittest`.
- Existing historical dry-run audit query service tests passed with
  `PYTHONPATH=backend/python`.
- Historical dry-run audit memory tests passed through focused unittest
  discovery.
- Runtime autonomy tests passed through unittest discovery.
- `py_compile` passed for the new module and test.
- `git diff --check` passed.
- `git diff --cached --check` passed before commit.

## 32. Pytest Unavailability Note

The requested `python -m pytest ...` command could not run locally during PR
#477 because the active Python environment did not have the `pytest` module.

Equivalent focused validation was run with `unittest` because the affected
tests use `unittest`.

## 33. Known Risks

Known risks:

- `internal_enabled=False` could be misunderstood as authentication. It is not
  auth.
- A future branch could accidentally register handlers before real protection
  exists.
- Route-level rate and size limits are still future controls.
- Audit logging and observability are not implemented at the route layer yet.
- Frontend/Cockpit consumption remains unreviewed.
- Copy/export remains unreviewed.

## 34. Required Controls Before Route Registration

Before route registration:

- Internal-only route registration approval.
- Real authentication design.
- Real authorization design.
- Route-level rate limit design.
- Route-level size limit design.
- Safe audit logging design.
- Safe observability design.
- Forbidden-field regression tests.
- Tests proving no raw JSONL/SQLite/SQL exposure.
- Tests proving no runtime/provider/execution behavior.

## 35. Required Controls Before Route Exposure

Before route exposure:

- Real authentication.
- Real authorization.
- Route-level rate limits.
- Route-level size limits.
- Audit logging without raw payloads.
- Observability without raw payloads.
- Abuse review.
- Security review.
- Internal-only network or deployment boundary review.
- No public exposure by default.

## 36. Required Controls Before Public Exposure

Public exposure is not approved. Any proposal for public exposure requires a
separate design, governance review, threat model, authentication and
authorization model, abuse review, privacy review, and explicit approval.

## 37. Required Controls Before Cockpit Consumption

Before Cockpit consumption:

- Separate Cockpit design.
- Separate governance review.
- Readonly warning labels.
- Safe empty/loading/error states.
- Detail field allowlist.
- Tests proving forbidden fields are not rendered.
- No copy/export without separate approval.

## 38. Required Controls Before Copy/Export

Before copy/export:

- Separate governance approval.
- Safe summary format.
- Export-specific forbidden-field tests.
- Secret and payload scans.
- Audit logging for export attempts without raw content.
- Explicit decision on whether JSON/CSV export is allowed.

## 39. Required Controls Before Retention/Cleanup

Before retention/cleanup:

- Separate retention/cleanup design.
- Separate governance review.
- Explicit/manual cleanup semantics if destructive.
- Tests proving reads do not trigger cleanup.
- Tests proving non-expired data is preserved.
- Safe metadata-only cleanup results.

## 40. Required Controls Before Execution Design

Before execution design:

- Separate governance review.
- Human approval gates.
- Explicit separation between audit reads and execution inputs.
- Tests proving persisted evidence is not used as execution input.
- Separate approval for prompt rewrite, retry execution, replan execution,
  provider/model calls, provider switching, CI repair, and Git automation.

## 41. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | This evidence note is docs-only. |
| PR #477 contract handlers | Go | Contract-level only. |
| Handlers remaining unregistered | Go | Required until route exposure controls exist. |
| `internal_enabled=False` fail-closed guard | Go | Safe default, not auth. |
| Route registration | No-Go | Blocked pending separate approval and controls. |
| Route exposure | No-Go | Blocked pending real auth, authorization, rate, size, audit, and observability controls. |
| Public exposure | No-Go | Blocked. |
| Cockpit/detail drawer consumption | No-Go | Separate governance required. |
| Copy/export | No-Go | Separate governance required. |
| Retention/cleanup | No-Go | Separate governance required. |
| Raw JSONL/SQLite/SQL access | No-Go | Forbidden. |
| Direct API-to-MemoryFacade | No-Go | Forbidden. |
| Prompt rewrite | No-Go | Forbidden. |
| Provider/model retry or replan execution | No-Go | Forbidden. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Forbidden. |

## 42. Final Recommendation

Approve these evidence notes as documentation. PR #477 is safe to interpret as
contract-level internal handler scaffolding only. The handlers remain
unregistered, fail closed by default, delegate only to
`HistoricalDryRunAuditQueryService`, and do not expose raw storage or execution
paths.

Do not register or expose routes until a separate branch adds real
authentication, authorization, route-level rate limits, route-level size
limits, audit logging without raw payloads, observability without raw payloads,
abuse review, security review, forbidden-field regression tests, and tests
proving no raw storage, runtime, provider, or execution behavior.

Omni remains advisory-only.
