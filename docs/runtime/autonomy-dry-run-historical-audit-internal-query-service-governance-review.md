# Autonomy Dry-Run Historical Audit Internal Query Service Governance Review

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-historical-audit-internal-query-service-governance-review`
**Base:** `main` after PR #464
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

The internal sanitized historical dry-run audit query service design is safe to
move toward a future implementation phase only if the implementation remains
readonly, typed, allowlisted, MemoryFacade-only, and fully tested for
sanitization and degradation. The service design correctly separates future
API/Cockpit consumers from MemoryFacade while preserving the prohibition on
raw JSONL reads, raw SQLite row reads, raw SQL filters, runtime calls,
provider/model calls, prompt rewriting, and execution behavior.

Governance conclusions:

- Approved for documentation.
- Approved for future internal service implementation only after this review
  and with strict tests.
- Not approved for API exposure.
- Not approved for frontend/Cockpit consumption.
- Not approved for detail drawer consumption.
- Not approved for copy/export.
- Not approved for raw JSONL read.
- Not approved for raw SQLite row read.
- Not approved for raw SQL filters.
- Not approved for runtime calls.
- Not approved for provider/model calls.
- Not approved for prompt rewriting.
- Not approved for provider/model retry execution.
- Not approved for provider/model replan execution.
- Not approved for persisted evidence as execution input.
- Not approved for autonomous execution.

Required warnings remain active: the internal service is readonly. Service
results are audit metadata only. Service results are not approval. Service
results are not execution input. `would_retry` and `would_replan` are not
execution. Eligibility scores are not permission. Suggested strategies are not
instructions. API exposure remains not approved. Cockpit consumption remains
not approved. Copy/export remains disabled. Omni remains advisory-only.

## 2. Scope

This review evaluates the design for an internal sanitized query service that
would sit between future API/Cockpit layers and the MemoryFacade historical
dry-run audit query contracts.

It reviews:

- Service boundary safety.
- Typed request validation.
- Sanitized response envelope.
- List and detail read flows.
- Filter, enum, sort, pagination, ID, and timestamp validation.
- Access-control assumptions.
- Safe audit logging.
- Degradation and error handling.
- Safe field allowlist and forbidden field denylist.
- Storage and MemoryFacade-only boundaries.
- Required controls before implementation and any downstream exposure.

## 3. Non-Goals

- Do not implement the internal service in this branch.
- Do not expose APIs.
- Do not add Cockpit/frontend UI.
- Do not modify runtime code.
- Do not modify persistence code.
- Do not modify MemoryFacade code.
- Do not modify SQLite code.
- Do not add copy/export.
- Do not add retention/cleanup integration.
- Do not call runtime.
- Do not call providers/models.
- Do not rewrite prompts.
- Do not execute RETRY or REPLAN.
- Do not use persisted evidence as execution input.
- Do not approve autonomous execution.

## 4. Reviewed Materials

Reviewed materials:

- `docs/runtime/autonomy-dry-run-historical-audit-query-contract-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-query-contract-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-internal-query-service-design.md`
- MemoryFacade query contract models from PR #463:
  - `DryRunAuditQueryRequest`
  - `DryRunAuditQueryResponse`
  - `DryRunAuditPageInfo`
  - `DryRunAuditEvidenceItem`
  - `DryRunAuditEvidenceDetail`
- MemoryFacade methods from PR #463:
  - `query_historical_dry_run_audit_evidence(...)`
  - `get_historical_dry_run_audit_evidence_detail(...)`

## 5. Governance Decision Summary

The internal service design is acceptable as a future implementation target
only when the implementation is constrained to an internal readonly boundary.

Approved:

- Documentation.
- Future internal service implementation with strict tests.

Not approved:

- API exposure.
- Frontend/Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Raw JSONL reads.
- Raw SQLite row reads.
- Raw SQL filters.
- Runtime calls.
- Provider/model calls.
- Prompt rewriting.
- Retry/replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 6. Internal Service Boundary Review

The proposed service boundary is safe because it is positioned above
MemoryFacade and below any future API/Cockpit layer. Its job is policy,
validation, safe logging, and response normalization, not storage access or
execution.

Required boundary properties:

- Readonly.
- Typed request objects only.
- Validation before MemoryFacade calls.
- MemoryFacade safe query/detail methods only.
- Sanitized response envelopes only.
- Safe audit metadata only.
- No runtime or provider/model dependency.

## 7. Request Validation Review

The request model must reject unsafe input before MemoryFacade is called.

Required controls:

- Typed request model only.
- Static filter allowlist.
- Static sort allowlist.
- Enum validation.
- Strict boolean validation.
- Bounded limit.
- Max page size.
- Timestamp range validation.
- Sanitized ID validation.
- No arbitrary JSON blobs.
- No raw SQL, raw JSONL, raw SQLite row fragments, prompts, responses,
  provider payloads, tool outputs, command args, paths, or secrets.

Invalid filters must degrade safely with `error_category` only.

## 8. Response Envelope Review

The response envelope should preserve the MemoryFacade-safe shape:

- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category`, only when degraded
- `generated_at`

The service may add safe service-level metadata only if it is boolean,
numeric, categorical, or a safe timestamp. It must not add raw request bodies,
raw response bodies, raw exception text, tracebacks, paths, SQL, rows, JSONL
lines, prompts, responses, payloads, or secrets.

## 9. List Query Flow Review

The list query flow is acceptable:

1. Receive typed/sanitized request.
2. Validate all fields.
3. Build or reuse `DryRunAuditQueryRequest`.
4. Call `MemoryFacade.query_historical_dry_run_audit_evidence(...)`.
5. Validate safe response shape.
6. Log safe audit metadata.
7. Return sanitized envelope.

The flow must not add raw storage filtering or direct storage reads.

## 10. Detail Read Flow Review

The detail read flow is acceptable only if the service treats detail reads as
safe metadata reads, not raw record reads.

Required controls:

- Sanitized `plan_id`.
- MemoryFacade detail method only.
- Safe not-found/degraded response.
- Safe audit log metadata.
- Safe detail allowlist.
- No raw JSON, raw row, raw JSONL line, raw exception object, or raw Python
  repr.

## 11. Filter Validation Review

Allowed filters:

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

Unsupported filters must be rejected or safely ignored with warnings. The
service must not silently broaden unsafe queries.

## 12. Enum Validation Review

Required enum validation:

- `plan_type`: `dry_run_retry`, `dry_run_replan`
- `event_type`: `dry_run_retry_plan_evidence`,
  `dry_run_replan_plan_evidence`
- `source_decision`: `CONTINUE`, `RETRY`, `REPLAN`, `SELF_REPAIR`,
  `SWITCH_PROVIDER`, `PAUSE`, `ESCALATE_TO_MISAEL`, `ABORT_SAFE`, `UNKNOWN`
- `risk_level`: `low`, `medium`, `high`, `unknown`
- `storage_mode`: `jsonl`, `sqlite`, `unavailable`, `unknown`

Unknown enum values must not be echoed, logged raw, displayed, or forwarded.

## 13. Sort Validation Review

Allowed sort fields:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`

Allowed directions:

- `asc`
- `desc`

Sort validation must use a static allowlist. Raw SQL `ORDER BY` fragments,
column fragments, table names, and dynamic sort strings are forbidden.

## 14. Pagination Validation Review

Pagination requirements:

- Bounded limit.
- Explicit max page size.
- Safe offset or opaque bounded cursor.
- Deterministic ordering.
- No unbounded scans.
- No all-records mode.
- No unbounded total counts.

Page metadata must not contain raw SQL, raw row IDs, file paths, database
paths, storage internals, or secrets.

## 15. Access-Control Assumptions Review

The service is internal and does not itself approve API exposure.

Access-control assumptions:

- Internal backend callers only until separate API approval.
- Existing protected Cockpit/runtime diagnostics access pattern required
  before HTTP exposure.
- No public unauthenticated route may call the service.
- Access metadata must be safe and minimal.
- Audit logging must exist before API exposure.

## 16. Audit Logging Review

Safe audit logging should include:

- Operation name.
- Sanitized `request_id`, `session_id`, or `trace_id` if present.
- Safe filter keys only.
- Safe sort key only.
- Bounded limit.
- Page/cursor metadata only if safe.
- `generated_at`.
- `degraded` boolean.
- `error_category` only.

Forbidden audit log content:

- Raw request body.
- Raw response body.
- Raw exception.
- Traceback.
- Stack trace.
- Prompt.
- Response.
- Provider payload.
- Tool output.
- Raw SQL.
- Raw JSONL.
- Raw SQLite row.
- Secrets, tokens, headers, or cookies.

## 17. Degradation/Error Model Review

The degradation model is safe if it returns only categories.

Acceptable categories:

- `invalid_request`
- `invalid_filter`
- `invalid_sort`
- `storage_unavailable`
- `query_failed`
- `detail_not_found`
- `access_denied`, only after access control exists

The service must never return raw exception text, SQL, paths, tracebacks,
object reprs, prompts, responses, payloads, tool outputs, or secrets.

## 18. Safe Field Allowlist Review

Allowed service result fields:

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
- Safe page metadata
- Safe warnings
- Degradation flag and error category

## 19. Forbidden Field Denylist Review

Forbidden fields and content:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys, tokens, and secrets.
- Headers and cookies.
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

The denylist is secondary to explicit response allowlisting.

## 20. Storage Boundary Review

The service must not become a storage adapter.

Forbidden:

- Opening JSONL files.
- Opening SQLite connections.
- Inspecting tables.
- Parsing raw JSONL.
- Building SQL.
- Returning storage paths.
- Returning raw storage metadata.

Storage behavior must remain encapsulated by MemoryFacade.

## 21. MemoryFacade-Only Access Review

The MemoryFacade-only rule is approved and required.

Allowed calls:

- `query_historical_dry_run_audit_evidence(...)`
- `get_historical_dry_run_audit_evidence_detail(...)`

Forbidden calls:

- SQLite adapter methods.
- JSONL mirror methods.
- Raw audit file readers.
- Runtime functions.
- Provider/model functions.
- Tool or command execution.

## 22. JSONL Boundary Review

Raw JSONL reads are not approved.

If JSONL historical query support is unavailable, the service must preserve
MemoryFacade safe degradation. It must not fallback to reading raw JSONL
files, lines, paths, or raw event payloads.

## 23. SQLite Boundary Review

Raw SQLite row reads are not approved.

The service must not know or expose table names, SQL statements, raw row
shapes, SQLite paths, connection state internals, or query plans. SQLite
behavior must be mediated through MemoryFacade safe models.

## 24. No Raw SQL Review

Raw SQL is forbidden at the service boundary.

The service must not accept, construct, log, emit, or serialize raw SQL.
Filters and sorts must remain typed contract fields. Any future SQL mapping
must stay below MemoryFacade and use static allowlists.

## 25. No Copy/Export Review

Copy/export remains disabled.

Not approved:

- Copy safe summary.
- Export JSON.
- Export CSV.
- Download evidence.
- Copy diagnostic details.

Separate governance is required before copy/export design or implementation.

## 26. No Execution-Input Review

Service outputs must never be execution inputs.

Forbidden uses:

- Selecting RETRY execution candidates.
- Selecting REPLAN execution candidates.
- Feeding evidence into prompt rewriting.
- Feeding evidence into provider/model calls.
- Feeding evidence into tool or command execution.
- Feeding evidence into provider routing.
- Feeding evidence into autonomous control loops.

## 27. Abuse/Misuse Cases

Misuse cases:

- Treating service results as approval.
- Treating `would_retry` as retry execution.
- Treating `would_replan` as replan execution.
- Treating `blocked=false` as approval.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Using filters as execution selectors.
- Logging raw request/response bodies.
- Bypassing MemoryFacade.
- Adding raw debug views.
- Adding API/Cockpit access before approval.
- Adding copy/export without governance.

## 28. Security Review Checklist

Before implementation, verify:

- Service is readonly.
- Typed request model only.
- Static filter allowlist.
- Static sort allowlist.
- Enum validation.
- Bounded limit and max page size.
- Deterministic ordering.
- Timestamp range validation.
- Sanitized ID validation.
- No unbounded scans.
- No raw request body logging.
- No raw response body logging.
- No raw exception logging.
- No traceback logging.
- No prompts, responses, provider payloads, or tool outputs.
- No secrets, tokens, headers, or cookies.
- MemoryFacade-only access.
- No raw JSONL exposure.
- No raw SQLite row exposure.
- No raw SQL exposure.
- Sanitized response envelope.
- Safe item/detail allowlist.
- Degraded/error category only.

## 29. Required Controls Before Internal Service Implementation

- Typed request model only.
- Static filter allowlist.
- Static sort allowlist.
- Enum validation.
- Bounded limit.
- Max page size.
- Deterministic ordering.
- Timestamp range validation.
- Sanitized ID validation.
- No unbounded scans.
- Sanitized response envelope.
- Safe item/detail allowlist.
- Degraded/error category only.
- Tests for invalid input and degradation.
- Tests proving MemoryFacade-only access.
- Tests proving no execution coupling.

## 30. Required Controls Before API Exposure

- Internal service implementation reviewed and tested.
- Access control selected.
- Authentication/authorization tests.
- Safe API request schema.
- Safe API response schema.
- Safe API error model.
- API audit logging.
- No public unauthenticated endpoint.
- No mutation route.
- No copy/export route.
- No execution route.

## 31. Required Controls Before Cockpit Consumption

- API contract approved.
- Frontend normalizer approved.
- Readonly warning labels:
  - Service results are audit metadata only.
  - Service results are not approval.
  - Service results are not execution input.
  - Copy/export remains disabled.
  - Omni remains advisory-only.
- Empty/loading/error/degraded states.
- No raw storage rendering.
- No `dangerouslySetInnerHTML`.
- No action controls.
- Forbidden field rendering tests.

## 32. Required Controls Before Detail Drawer Consumption

- Detail allowlist approved.
- Bounded `block_reasons`.
- Safe diagnostic fields.
- Safe storage metadata only.
- No raw JSON view.
- No raw database row view.
- No raw JSONL line view.
- No copy/export button.
- Tests for forbidden field omission.

## 33. Required Controls Before Copy/Export

- Separate governance review.
- Separate copy/export design.
- Safe export allowlist.
- Safe summary format.
- Access model.
- Export audit logging.
- Redaction tests.
- Explicit ban on raw rows, raw JSONL, prompts, responses, provider payloads,
  command args, file contents, receipts, exceptions, and secrets.

## 34. Required Controls Before Retention/Cleanup Integration

- Separate retention/cleanup governance.
- Separate retention/cleanup design.
- Proof query filters cannot trigger cleanup.
- Proof cleanup cannot consume query results as execution input.
- Safe lifecycle diagnostics.
- Bounded deletion scope.
- No Cockpit destructive controls without separate governance.

## 35. Required Controls Before Any Execution Design

- Separate governance review.
- Separate threat model.
- Explicit approval by Misael.
- Proof persisted evidence is not execution input.
- Proof service filters are not execution selectors.
- Prompt rewriting reviewed separately.
- Provider/model calls reviewed separately.
- Runtime output preservation reviewed separately.
- Human approval boundaries defined.

## 36. Explicit Non-Approval Statement

This review does not approve API exposure, frontend/Cockpit consumption,
detail drawer consumption, copy/export, raw JSONL read, raw SQLite row read,
raw SQL filters, runtime calls, provider/model calls, prompt rewriting,
provider/model retry execution, provider/model replan execution, persisted
evidence as execution input, or autonomous execution.

Omni remains advisory-only.

## 37. Open Risks

- Service validation could drift from MemoryFacade validation.
- Future implementation could log raw request/response bodies.
- API exposure could happen before access control and audit logging.
- Debug tooling could bypass MemoryFacade-only access.
- Detail views could pressure raw storage display.
- Copy/export could reuse service responses without governance.
- Retention/cleanup could misuse query filters.

## 38. Open Questions

- Should unsupported filters be rejected or ignored with warnings at the
  service boundary?
- Should the service expose an operation ID in safe audit logs?
- Should detail not-found be represented as `None` internally or as a typed
  not-found envelope?
- Which audit log sink is approved before API exposure?
- Should service tests mock MemoryFacade only, or include integration tests
  with the real MemoryFacade query contracts?

## 39. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | This review is docs-only. |
| Internal service implementation | Conditional go | Only after this review with strict tests. |
| API exposure | No-go | Requires separate approval and controls. |
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

## 40. Final Recommendation

Approve this governance review for documentation and allow a future internal
service implementation branch only if that branch remains strictly internal,
readonly, MemoryFacade-only, typed, allowlisted, fully tested, and disconnected
from API exposure, Cockpit consumption, copy/export, retention/cleanup, and
execution design.

Do not proceed from this review directly to API exposure, Cockpit consumption,
copy/export, retention/cleanup integration, or any execution design. Omni
remains advisory-only.
