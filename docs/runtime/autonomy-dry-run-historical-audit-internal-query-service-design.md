# Autonomy Dry-Run Historical Audit Internal Query Service Design

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-historical-audit-internal-query-service-design`
**Base:** `main` after PR #463
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs a future internal sanitized query service boundary for
historical dry-run RETRY and REPLAN audit evidence. The service would sit
between future API/Cockpit layers and the MemoryFacade historical dry-run audit
query contracts added in PR #463.

The service is readonly. It accepts only typed and sanitized request objects,
validates filters, sort, IDs, timestamps, and pagination before calling
MemoryFacade, calls only MemoryFacade safe query/detail methods, and returns
sanitized response envelopes. It must never read raw JSONL directly, read raw
SQLite rows directly, emit raw SQL, expose forbidden fields, call runtime, call
providers/models, mutate runtime output, trigger RETRY/REPLAN, or use
persisted evidence as execution input.

This branch is documentation/design only. It does not implement service code,
APIs, UI, runtime changes, persistence changes, MemoryFacade changes, SQLite
changes, provider routing, prompt rewriting, retry execution, replan execution,
or autonomous execution.

## 2. Scope

This design covers:

- Internal readonly service boundary.
- Request validation before MemoryFacade access.
- Response envelope expectations.
- List and detail read flows.
- Safe audit logging.
- Degradation and error categories.
- Safe field allowlist and forbidden field denylist.
- MemoryFacade-only storage access.
- JSONL, SQLite, raw SQL, copy/export, and execution boundaries.
- Required controls before implementation and before any downstream exposure.

## 3. Non-Goals

- Do not add internal service code.
- Do not add API endpoints.
- Do not add Cockpit or frontend components.
- Do not modify runtime behavior.
- Do not modify MemoryFacade contracts in this branch.
- Do not modify SQLite queries or schema.
- Do not modify JSONL persistence.
- Do not add copy/export.
- Do not add retention or cleanup integration.
- Do not rewrite prompts.
- Do not execute RETRY.
- Do not execute REPLAN.
- Do not call providers/models.
- Do not use persisted evidence as execution input.
- Do not approve autonomous execution.

## 4. Relationship To MemoryFacade Query Contracts

PR #463 added the MemoryFacade-level query/read contracts:

- `DryRunAuditQueryRequest`
- `DryRunAuditQueryResponse`
- `DryRunAuditPageInfo`
- `DryRunAuditEvidenceItem`
- `DryRunAuditEvidenceDetail`
- `query_historical_dry_run_audit_evidence(...)`
- `get_historical_dry_run_audit_evidence_detail(...)`

The internal service must be a policy and validation layer above those
contracts. It should not bypass them, widen them, or return fields that
MemoryFacade does not already normalize safely.

## 5. Relationship To Future API Exposure

API exposure is not approved yet. A future API, if approved, should call this
internal service rather than calling MemoryFacade directly. The service should
therefore define the final safe backend response envelope that an API may
serialize.

Before API exposure, access control, request schema validation, safe error
handling, and safe audit logging must be implemented and reviewed.

## 6. Relationship To Future Cockpit Consumption

Cockpit consumption is not approved yet. A future Cockpit view should consume
only API responses derived from this internal service. Cockpit must not call
MemoryFacade directly and must not read raw JSONL, SQLite, or local storage
records.

The service should preserve the labels and semantics needed by Cockpit:
readonly audit metadata, not approval, not execution input, no retry executed,
no replan executed, and advisory-only.

## 7. Service Boundary Overview

The internal service boundary should be:

1. Caller submits a typed/sanitized query request object.
2. Service validates filter, sort, pagination, IDs, and timestamps.
3. Service rejects or safely degrades invalid input.
4. Service calls only MemoryFacade safe query/detail methods.
5. Service receives MemoryFacade sanitized response models.
6. Service applies no raw storage reads.
7. Service logs safe audit metadata only.
8. Service returns a sanitized response envelope.

The service must be dependency-injected with a MemoryFacade instance or
factory. It must not construct raw SQLite or JSONL readers.

## 8. Request Validation Model

The service should accept only typed request objects that have already passed a
schema boundary or can be normalized into `DryRunAuditQueryRequest`.

Required validation:

- Static filter allowlist.
- Static sort allowlist.
- Enum validation.
- Strict boolean parsing.
- Bounded limit.
- Explicit max page size.
- Safe offset or opaque bounded cursor.
- Deterministic ordering requirement.
- Timestamp range validation.
- Sanitized ID validation.
- Unsupported filters rejected or safely ignored with warnings.
- Invalid filters degraded safely with `error_category` only.

The service must not accept arbitrary dictionaries from API code without
normalization.

## 9. Response Envelope Model

The service response should preserve the MemoryFacade-safe envelope:

- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category`, only when degraded
- `generated_at`

The service may add safe service diagnostics only if they are boolean,
numeric, categorical, or safe timestamps. It must not add raw request bodies,
raw response bodies, raw exception text, tracebacks, paths, SQL, rows, or JSONL
lines.

## 10. List Query Flow

List query flow:

1. Receive typed/sanitized query request.
2. Validate all query fields.
3. Build or reuse `DryRunAuditQueryRequest`.
4. Call `MemoryFacade.query_historical_dry_run_audit_evidence(...)`.
5. Validate that the returned object is a safe response envelope.
6. Emit safe audit log metadata.
7. Return the response unchanged or with only safe service-level metadata.

The service must not perform post-query raw filtering against raw storage data.

## 11. Detail Read Flow

Detail read flow:

1. Receive sanitized `plan_id`.
2. Validate ID format and length.
3. Call `MemoryFacade.get_historical_dry_run_audit_evidence_detail(...)`.
4. If missing, return a safe empty/not-found response.
5. If degraded, return safe degradation metadata.
6. Emit safe audit log metadata.
7. Return only the safe detail item model.

Detail reads must not expose raw JSON, raw database rows, raw JSONL lines, raw
exception objects, or raw Python reprs.

## 12. Filter Validation

Allowed filter keys:

- `plan_type`
- `event_type`
- `source_decision`
- `risk_level`
- `blocked`
- `recorded`
- `degraded`
- `storage_mode`
- `sqlite_enabled`
- `request_id`
- `trace_id`
- `session_id`
- `created_at_from`
- `created_at_to`
- `recorded_at_from`
- `recorded_at_to`

Unsupported filters should be rejected or safely ignored with warnings,
matching the MemoryFacade contract. Silent broadening should be avoided.

## 13. Enum Validation

Required enums:

- `plan_type`: `dry_run_retry`, `dry_run_replan`
- `event_type`: `dry_run_retry_plan_evidence`,
  `dry_run_replan_plan_evidence`
- `source_decision`: `CONTINUE`, `RETRY`, `REPLAN`, `SELF_REPAIR`,
  `SWITCH_PROVIDER`, `PAUSE`, `ESCALATE_TO_MISAEL`, `ABORT_SAFE`, `UNKNOWN`
- `risk_level`: `low`, `medium`, `high`, `unknown`
- `storage_mode`: `jsonl`, `sqlite`, `unavailable`, `unknown`

Unknown enum values must not be rendered, echoed, or forwarded to
MemoryFacade as-is.

## 14. Sort Validation

Allowed sort fields:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`

Allowed sort directions:

- `asc`
- `desc`

The service must use static mappings and must never accept raw SQL sort
fragments. Categorical sorting for risk and source decision must remain
deterministic and documented.

## 15. Pagination Validation

Pagination controls:

- Conservative default limit.
- Explicit maximum page size.
- Bounded offset or opaque bounded cursor.
- Deterministic ordering.
- No unbounded scans.
- No all-records mode.
- No unbounded total counts.

Pagination metadata returned to callers must not contain raw SQL, raw storage
keys, raw row IDs, file paths, or secrets.

## 16. Access-Control Assumptions

The internal service does not itself approve API exposure. Before any HTTP
route uses it, the route must apply an existing protected Cockpit/runtime
diagnostics access pattern.

Assumptions:

- Internal callers are trusted backend code paths only.
- API-facing callers require separate authentication and authorization.
- No public unauthenticated endpoint may call this service.
- Access metadata logged by the service must be safe and minimal.

## 17. Audit Logging Model

Audit logging should record only safe metadata:

- Operation name.
- Sanitized `request_id`, `session_id`, or `trace_id` if present.
- Safe filter keys only.
- Safe sort key only.
- Bounded limit.
- Page/cursor metadata only if safe.
- `generated_at`.
- `degraded` boolean.
- `error_category` only.

Audit logging must not record:

- Raw request body.
- Raw response body.
- Raw exception.
- Traceback.
- Stack trace.
- Raw SQL.
- Raw JSONL.
- Raw SQLite row.
- Prompt.
- Response.
- Provider payload.
- Tool output.
- Secrets, tokens, headers, or cookies.

## 18. Degradation/Error Model

The service must degrade safely and categorically.

Allowed categories include:

- `invalid_request`
- `invalid_filter`
- `invalid_sort`
- `storage_unavailable`
- `query_failed`
- `detail_not_found`
- `access_denied`, only after access control exists

Errors must not include raw exception messages, SQL statements, file paths,
SQLite paths, JSONL paths, object reprs, prompts, responses, payloads, or
secrets.

## 19. Safe Field Allowlist

Safe response fields:

- `event_type`
- `plan_id`
- `plan_type`
- `advisory`
- `would_retry`
- `would_replan`
- `blocked`
- `block_reasons`
- `risk_level`
- `source_decision`
- `fingerprint_id`
- `progress_score`
- `stagnation_score`
- `retry_eligibility_score`
- `replan_eligibility_score`
- `repeated_strategy_count`
- `suggested_retry_strategy`
- `suggested_strategy`
- `evidence_summary`
- `created_at`
- `recorded_at`
- Sanitized request/session/trace IDs
- Persistence diagnostic booleans and categorical values
- Page metadata, warnings, degradation flag, and safe error category

## 20. Forbidden Field Denylist

Forbidden fields and content:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys, tokens, or secrets.
- Headers or cookies.
- Stack traces.
- stdout/stderr.
- Command args.
- File contents.
- `.env` content.
- Full tool outputs.
- Raw receipts.
- Raw exception objects.
- Raw Python reprs.
- Raw database rows.
- Raw SQL.
- Raw JSONL lines.
- Screenshots exposing secrets or raw payloads.

The denylist is a backstop. The service must primarily rely on allowlisted
response construction.

## 21. Storage Boundary Rules

The service is not a storage adapter.

Rules:

- Do not open files.
- Do not open SQLite connections.
- Do not inspect tables.
- Do not parse raw JSONL.
- Do not build SQL.
- Do not return storage paths.
- Do not return raw storage metadata beyond safe categorical fields.

## 22. MemoryFacade-Only Access Rule

The service must call only these safe MemoryFacade methods:

- `query_historical_dry_run_audit_evidence(...)`
- `get_historical_dry_run_audit_evidence_detail(...)`

It must not call lower-level SQLite adapter methods, JSONL mirror methods, raw
audit file readers, or runtime functions.

## 23. JSONL Boundary

JSONL remains an audit recording path, but this service must never read raw
JSONL directly.

If MemoryFacade reports JSONL historical querying as unavailable, the service
should pass through safe degradation metadata. It must not fallback to reading
the JSONL file itself.

## 24. SQLite Boundary

SQLite remains opt-in structured evidence storage, but this service must never
read raw SQLite rows directly.

SQLite behavior must be mediated by MemoryFacade. The service must not know
table names, SQL strings, row shapes, database paths, or connection details.

## 25. No Raw SQL Rule

The service must never accept, construct, log, or emit raw SQL.

Sort and filter choices must be represented as enum-like contract fields and
mapped by MemoryFacade internals. Raw SQL filters, WHERE fragments, ORDER BY
fragments, table names, column fragments, and query plans are forbidden.

## 26. No Copy/Export Rule

Copy/export is not part of the service.

The service must not provide:

- Copy summaries.
- JSON export.
- CSV export.
- Raw detail export.
- Download links.

Copy/export requires separate governance before any design or implementation.

## 27. No Execution-Input Rule

The service output must never be used as execution input.

Forbidden use:

- Selecting records for RETRY execution.
- Selecting records for REPLAN execution.
- Feeding persisted evidence into prompt rewriting.
- Feeding persisted evidence into provider/model calls.
- Feeding persisted evidence into tool or command execution.
- Feeding persisted evidence into provider routing.

Query results are readonly audit metadata only.

## 28. Abuse/Misuse Cases

Misuse cases:

- Treating query results as approval.
- Treating `would_retry` as retry execution.
- Treating `would_replan` as replan execution.
- Treating `blocked=false` as approval.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Using filters as execution selectors.
- Adding raw debug views.
- Logging raw request/response bodies.
- Bypassing MemoryFacade to read storage directly.
- Adding copy/export without governance.

## 29. Security Review Checklist

Before implementation, verify:

- Service is readonly.
- Service accepts only typed/sanitized request objects.
- Service validates before MemoryFacade calls.
- Static filter allowlist exists.
- Static sort allowlist exists.
- Enum validation exists.
- Limit and page size are bounded.
- Ordering is deterministic.
- Timestamp ranges are validated.
- IDs are sanitized.
- Unsupported filters are rejected or safely warned.
- Errors are categorical only.
- Audit logs contain safe metadata only.
- MemoryFacade is the only data access boundary.
- No raw JSONL read.
- No raw SQLite row read.
- No raw SQL.
- No API, UI, runtime, provider/model, retry, or replan behavior.

## 30. Testing Strategy

Future implementation tests should cover:

- Valid list request.
- Valid detail request.
- Invalid enum degradation.
- Invalid sort degradation.
- Unsupported filter warnings.
- Limit and max page enforcement.
- Offset/cursor bounds.
- Deterministic ordering.
- Timestamp range validation.
- Sanitized ID validation.
- MemoryFacade success.
- MemoryFacade degradation passthrough.
- MemoryFacade exception conversion to safe category.
- Safe audit log payload.
- Forbidden field omission.
- No raw JSONL/SQLite/SQL access.
- No runtime/provider/model calls.
- No execution controls.

## 31. Required Controls Before Implementation

- Approved service request type.
- Approved service response envelope.
- MemoryFacade dependency boundary.
- Static validation tables.
- Safe audit log schema.
- Error category enum.
- Tests for invalid requests.
- Tests for degradation.
- Tests for forbidden field suppression.
- Tests proving no raw storage access.
- Tests proving no execution coupling.

## 32. Required Controls Before API Exposure

- Service implementation reviewed and tested.
- API authentication/authorization selected.
- Request schema validation.
- Response schema validation.
- Rate or size limits if needed.
- Safe API error model.
- Safe API audit logging.
- No public unauthenticated route.
- No copy/export route.
- No mutation route.
- No execution route.

## 33. Required Controls Before Cockpit Consumption

- API contract approved.
- Frontend normalizer approved.
- Readonly warning labels approved.
- Empty/loading/error/degraded states.
- No raw storage rendering.
- No `dangerouslySetInnerHTML`.
- No action controls.
- No copy/export controls.
- Tests for forbidden field suppression.

## 34. Required Controls Before Copy/Export

- Separate governance review.
- Separate export allowlist.
- Safe summary format.
- Access model.
- Export audit logging.
- Redaction tests.
- Explicit ban on raw rows, raw JSONL, prompts, responses, provider payloads,
  command args, file contents, receipts, exceptions, and secrets.

## 35. Required Controls Before Retention/Cleanup Integration

- Separate retention/cleanup design.
- Proof query filters cannot trigger cleanup.
- Proof cleanup cannot consume query results as execution input.
- Safe lifecycle diagnostics.
- Bounded deletion scope.
- No Cockpit destructive controls without separate governance.

## 36. Required Controls Before Any Execution Design

- Separate governance review.
- Separate threat model.
- Explicit approval by Misael.
- Proof persisted evidence is not execution input.
- Proof service filters are not execution selectors.
- Prompt rewriting reviewed separately.
- Provider/model calls reviewed separately.
- Runtime output preservation reviewed separately.
- Human approval boundaries defined.

## 37. Explicit Non-Approval Statement

This design does not approve internal service implementation, API exposure,
Cockpit consumption, detail drawer consumption, copy/export, raw JSONL reads,
raw SQLite row reads, raw SQL filters, runtime calls, provider/model calls,
prompt rewriting, retry execution, replan execution, persisted evidence as
execution input, or autonomous execution.

Omni remains advisory-only.

## 38. Open Risks

- Future service implementation could duplicate MemoryFacade validation and
  drift.
- API teams may treat the service as approval for exposure before access
  controls exist.
- Audit logging could accidentally capture raw request bodies.
- Debug tooling could bypass the MemoryFacade-only rule.
- Copy/export pressure could reuse service responses without governance.
- Retention/cleanup work could misuse query filters as deletion selectors.

## 39. Open Questions

- Should the service request type wrap `DryRunAuditQueryRequest` directly or
  define a separate service-specific input model?
- Should unsupported filters be rejected or ignored with warnings at the
  service boundary?
- What safe audit log sink should be used before API exposure?
- Should the service attach a service operation ID?
- Should detail reads return a typed not-found envelope or `None` internally?

## 40. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | This branch is design-only. |
| Internal service implementation | No-go | Requires controls in section 31. |
| API exposure | No-go | Requires access control and audit logging. |
| Frontend/Cockpit consumption | No-go | Requires API and frontend controls. |
| Detail drawer consumption | No-go | Requires detail allowlist and tests. |
| Copy safe summary | No-go | Requires separate governance. |
| Export JSON/CSV | No-go | Requires separate governance. |
| Raw JSONL read | No-go | Forbidden. |
| Raw SQLite row read | No-go | Forbidden. |
| Raw SQL filters | No-go | Forbidden. |
| Runtime call | No-go | Forbidden. |
| Provider/model call | No-go | Forbidden. |
| Prompt rewrite | No-go | Not approved. |
| Provider/model retry execution | No-go | Not approved. |
| Provider/model replan execution | No-go | Not approved. |
| Persisted evidence as execution input | No-go | Forbidden. |
| Autonomous execution | No-go | Omni remains advisory-only. |

## 41. Final Recommendation

Approve this document for review as the design boundary for a future internal
sanitized query service. The next implementation phase should be limited to an
internal readonly service that validates typed request objects, calls only
MemoryFacade safe query/detail methods, returns sanitized envelopes, and logs
only safe metadata.

Do not proceed from this document directly to API exposure, Cockpit
consumption, copy/export, retention/cleanup integration, or any execution
design. Omni remains advisory-only.
