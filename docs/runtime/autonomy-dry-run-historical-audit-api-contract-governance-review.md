# Autonomy Dry-Run Historical Audit API Contract Governance Review

**Date:** 2026-06-30
**Branch:** `feature/autonomy-dry-run-historical-audit-api-contract-governance-review`
**Base:** `main` after PR #470, PR #471, and PR #472
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

The historical dry-run audit API contract design is approved as documentation
and as a safe contract target for a future internal/private endpoint
implementation only. Implementation remains conditional and must stay behind
an internal/private boundary with strict tests, route-level validation, safe
logging, bounded pagination, required advisory warnings, categorical errors,
and delegation only to `HistoricalDryRunAuditQueryService`.

Public exposure remains blocked. Cockpit consumption, detail drawer
consumption, copy/export, raw storage reads, raw SQL filters, direct
API-to-MemoryFacade access, provider/model execution, prompt rewriting,
persisted evidence as execution input, and autonomous execution remain
blocked.

## 2. Scope

This review evaluates the API contract design for future readonly historical
dry-run RETRY/REPLAN audit endpoints. It reviews:

- Candidate endpoint contracts.
- List/detail request and response contracts.
- Query and path parameter contracts.
- Filter, sort, pagination, validation, and sanitized ID models.
- Safe response, detail, degradation, and error category behavior.
- Safe field allowlist and forbidden field denylist.
- Delegation and internal-service dependencies.
- Authentication, authorization, rate limit, size limit, audit logging, and
  observability requirements.
- Required controls before implementation, exposure, Cockpit consumption,
  copy/export, retention/cleanup integration, or execution design.

## 3. Non-Goals

- Do not implement API endpoints.
- Do not add routes.
- Do not add handlers.
- Do not add API schemas in code.
- Do not modify runtime code.
- Do not modify persistence code.
- Do not modify MemoryFacade code.
- Do not modify internal query service code.
- Do not modify SQLite code.
- Do not modify frontend/Cockpit code.
- Do not add copy/export.
- Do not add retention/cleanup behavior.
- Do not rewrite prompts.
- Do not execute RETRY or REPLAN.
- Do not call providers/models.
- Do not change provider routing or runtime output.
- Do not enable autonomous execution or self-repair.

## 4. Reviewed Materials

Reviewed materials:

- `docs/runtime/autonomy-dry-run-historical-audit-query-contract-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-query-contract-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-boundary-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-boundary-governance-review.md`
- `docs/runtime/autonomy-dry-run-historical-audit-api-contract-design.md`
- MemoryFacade safe query controls from PR #471.
- Internal query service controls from PR #472.
- Current safe internal layers:
  - governed historical audit query models
  - MemoryFacade query controls
  - `HistoricalDryRunAuditQueryService`
  - static filter allowlist
  - static sort allowlist
  - strict enum validation
  - bounded pagination
  - safe response/detail shapes
  - fixed safe degraded/error categories
  - required advisory warnings

## 5. Governance Decision Summary

Approved:

- Documentation.
- API contract design.

Conditionally approved:

- Future internal/private endpoint implementation only after a separate
  implementation branch adds strict route-level validation, tests, safe
  logging, bounded pagination, required warnings, categorical errors, and
  service-only delegation.

Not approved:

- Public exposure.
- Frontend/Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Raw JSONL reads.
- Raw SQLite row reads.
- Raw SQL filters.
- Direct API-to-MemoryFacade access bypassing the internal query service.
- Prompt rewriting.
- Provider/model retry execution.
- Provider/model replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 6. API Contract Safety Review

The API contract is safe as a design artifact because it is readonly,
metadata-only, allowlisted, bounded, and explicitly non-executing. It requires
the API to call only `HistoricalDryRunAuditQueryService` and forbids direct
storage access, raw SQL, runtime calls, provider/model calls, and execution
input usage.

The contract is not sufficient for exposure by itself. Authentication,
authorization, rate limits, size limits, safe audit logging, and negative
security tests remain required before any route can be exposed beyond an
internal/private boundary.

## 7. Candidate Endpoint Review

Candidate endpoints:

- `GET /internal/audit/dry-run`
- `GET /internal/audit/dry-run/{plan_id}`

The endpoints are acceptable as placeholders because they signal internal,
readonly audit intent. They are not implemented by this review. Future
implementation must confirm route naming against existing backend conventions.

## 8. List Endpoint Review

The list endpoint contract is acceptable with these constraints:

- Readonly only.
- Query parameters only.
- Static filter and sort allowlists.
- Bounded pagination.
- Safe response envelope.
- Required advisory warnings preserved.
- Internal query service delegation only.

The list endpoint must not support bulk dump, export, raw storage selectors,
runtime selectors, provider selectors, or execution selectors.

## 9. Detail Endpoint Review

The detail endpoint contract is acceptable with these constraints:

- `plan_id` must be sanitized.
- Invalid `plan_id` must not trigger service or storage access.
- Not-found must be safe and metadata-only.
- Detail payload must remain an allowlisted metadata shape.
- Raw storage records, raw diagnostic object dumps, raw SQL, raw JSONL lines,
  and raw SQLite rows are forbidden.

## 10. Request Parameter Review

The request parameter set is acceptable because it contains only audit
metadata filters, sorting, pagination, and safe IDs. It does not include raw
SQL, storage selectors, prompt selectors, provider selectors, command
selectors, file selectors, or execution controls.

Future routes must reject or safely warn on unsupported parameters according
to the implementation policy selected for the route.

## 11. Path Parameter Review

Only `plan_id` is allowed as a path parameter. It must be bounded,
sanitized, non-empty, non-redacted, and free of path traversal, query
injection, shell metacharacters, quotes, pipes, and separators.

Invalid path parameters must not be echoed raw and must not reach MemoryFacade
or raw storage.

## 12. Filter Model Review

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

Filters remain audit query controls only. They must never become execution
selectors, cleanup selectors, or export selectors.

## 13. Sort Model Review

Allowed sort fields:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`

Allowed directions:

- `asc`
- `desc`

Raw SQL, arbitrary column names, nested field paths, and storage-specific
sorting are blocked.

## 14. Pagination Model Review

The pagination model is acceptable if future implementation enforces:

- Conservative default limit.
- Explicit maximum page size.
- Bounded offset.
- Deterministic ordering.
- Safe `page_info`.
- No raw row IDs.
- No storage cursors.
- No unbounded query path.

Cursor support remains reserved for future design and must be opaque if added.

## 15. Validation Model Review

Validation must occur before service delegation:

- Typed request schema.
- Static filter allowlist.
- Static sort allowlist.
- Enum validation.
- Boolean validation.
- Timestamp range validation.
- Sanitized ID validation.
- Bounded pagination.
- Route-level size limits.

Invalid inputs must produce categorical errors or safe warnings only.

## 16. Response Envelope Review

Required response envelope:

- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category`
- `generated_at`

`error_category` should only carry categorical values and should be present
when degraded. The response must preserve required advisory warnings:

- Query results are readonly audit metadata.
- Query results are not approval.
- Query results are not execution input.
- `would_retry/would_replan` are not execution.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- Copy/export remains disabled.
- Omni remains advisory-only.

## 17. Detail Response Review

Detail responses may include list item fields plus bounded, allowlisted
diagnostic metadata. Detail responses must not include raw record dumps,
storage rows, JSONL lines, SQL, raw diagnostics, raw exceptions, tracebacks,
prompts, responses, provider payloads, tool outputs, or secrets.

## 18. Error Response Review

Error responses must be categorical and safe. Acceptable categories include
invalid request, invalid filter, invalid sort, unauthenticated, unauthorized,
rate limited, payload too large, storage unavailable, query failed, not found,
invalid service response, and unknown.

Error responses must not include raw exception text, stack traces, tracebacks,
storage paths, SQL, rows, JSONL lines, prompts, responses, payloads, headers,
cookies, command args, tokens, or secrets.

## 19. Safe Field Allowlist Review

Safe fields include:

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
- sanitized `request_id`, `session_id`, and `trace_id`
- safe persistence diagnostics
- envelope fields and page info

The allowlist is closed. New fields require separate governance review.

## 20. Forbidden Field Denylist Review

Forbidden fields include:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys, tokens, secrets.
- Headers, cookies.
- Stack traces, tracebacks.
- Stdout, stderr.
- Command args.
- File contents.
- `.env` content.
- Full tool outputs.
- Raw receipts.
- Raw exception objects.
- Raw Python reprs.
- Raw DB rows.
- Raw SQL.
- Raw JSONL lines.
- Screenshots exposing secrets or raw payloads.

## 21. Delegation Boundary Review

The only approved future dependency path is:

API route -> `HistoricalDryRunAuditQueryService` -> MemoryFacade safe query
contracts.

The API must not bypass the service. The API must not perform direct storage
querying, raw row filtering, SQL construction, runtime calls, provider/model
calls, or execution decisions.

## 22. Internal Service Dependency Review

`HistoricalDryRunAuditQueryService` is the required API dependency because it
centralizes safe validation, MemoryFacade-only delegation, safe degradation,
safe error category handling, and safe audit metadata logging.

Future API code must treat the service as the policy boundary, not merely as
an optional helper.

## 23. MemoryFacade Boundary Review

MemoryFacade remains below the internal service. Future API routes must not
call MemoryFacade directly. Direct access would bypass route/service controls,
increase duplication, and risk inconsistent validation or warning behavior.

## 24. Raw Storage Exposure Review

Raw storage exposure remains blocked:

- No raw JSONL reads.
- No raw SQLite row reads.
- No raw SQLite paths.
- No raw DB row selectors.
- No raw SQL filters.
- No storage cursor exposure.

Storage behavior must remain hidden behind MemoryFacade and the internal
service.

## 25. Authentication Placeholder Review

The authentication placeholder is acceptable for contract design only.
Endpoint implementation must identify and use an existing safe authentication
convention or stop for a separate authentication design.

Unauthenticated access must be rejected before service delegation.

## 26. Authorization Placeholder Review

The authorization placeholder is acceptable for contract design only.
Endpoint implementation must define explicit readonly audit metadata
permission. This permission must not grant runtime control, retry/replan
execution, provider/model calls, cleanup, copy/export, or prompt rewriting.

## 27. Rate Limit Requirements Review

Rate limits are required before exposure. Future implementation must define
per-caller or per-session limits and safe behavior for repeated invalid or
expensive queries.

Internal/private implementation may proceed conditionally only if route-level
rate-limit expectations are documented and tested before exposure.

## 28. Size Limit Requirements Review

Size limits are required before exposure:

- Maximum query string size.
- Maximum number of parameters.
- Maximum ID length.
- Maximum limit/page size.
- Maximum offset.
- Optional maximum time range.

Oversized requests must fail safely before service delegation when possible.

## 29. Audit Logging Requirements Review

Audit logging before exposure must include safe metadata only:

- Operation name.
- Caller category or safe caller ID, if approved.
- Safe filter keys.
- Sort field and direction.
- Limit and offset.
- Response status category.
- Degraded boolean.
- Categorical error category.
- Generated timestamp.

Logs must not include raw request bodies, response bodies, exceptions,
tracebacks, prompts, responses, provider payloads, tool outputs, headers,
cookies, tokens, secrets, SQL, rows, or JSONL lines.

## 30. Observability Requirements Review

Future observability should report only safe operational metadata:

- request accepted/rejected counts
- degraded counts by category
- rate-limit counts
- authorization failure counts
- latency buckets
- page-size buckets

Observability must not include raw query strings, raw response bodies, raw
exceptions, prompts, responses, payloads, rows, SQL, JSONL lines, headers,
cookies, or secrets.

## 31. Abuse/Misuse Cases

Misuse cases:

- Treating query results as approval.
- Treating query results as execution input.
- Treating `would_retry=true` as retry execution.
- Treating `would_replan=true` as replan execution.
- Treating `blocked=false` as permission.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Using filters as execution selectors.
- Using filters as cleanup selectors.
- SQL injection through sort/filter parameters.
- Path traversal through `plan_id`.
- Scraping data through unbounded pagination.
- Exposing routes without auth.
- Logging sensitive request or response material.

## 32. Security Review Checklist

Before implementation, reviewers must verify:

- API calls only `HistoricalDryRunAuditQueryService`.
- API does not call raw storage.
- API does not construct SQL from request input.
- API does not expose raw storage rows.
- API preserves required warnings.
- API enforces parameter validation.
- API enforces bounded pagination.
- API enforces filter/sort allowlists.
- API returns sanitized response envelopes only.
- API returns categorical errors only.
- Tests cover forbidden field exclusion.
- Tests prove no provider/runtime/execution behavior.
- Tests prove no direct raw JSONL/SQLite/SQL exposure.
- Route-level size limits exist before exposure.
- Auth/authorization exists before non-local exposure.
- Audit logging exists before exposure.
- Rate limits exist before exposure.

## 33. Required Controls Before Endpoint Implementation

Required before implementation:

- API must call `HistoricalDryRunAuditQueryService` only.
- API must not call raw storage.
- API must not construct SQL from request input.
- API must not expose raw storage rows.
- API must preserve required warnings.
- API must enforce parameter validation.
- API must enforce bounded pagination.
- API must enforce filter/sort allowlists.
- API must return sanitized response envelopes only.
- API must return categorical errors only.
- Focused tests for forbidden field exclusion.
- Tests proving no provider/runtime/execution behavior.
- Tests proving no direct raw JSONL/SQLite/SQL exposure.

## 34. Required Controls Before Route Exposure

Required before any route exposure:

- Route-level size limits.
- Authentication.
- Explicit authorization.
- Readonly permission model.
- Audit logging.
- Rate limits.
- Abuse-case review.
- Security review.
- Operational ownership.
- No public exposure without separate approval.

## 35. Required Controls Before Cockpit Consumption

Required before Cockpit consumption:

- API route implementation and exposure governance completed.
- Separate Cockpit governance approval.
- Readonly UI labels.
- "Not approval" and "not execution input" warnings.
- Missing/degraded states.
- Forbidden field absence tests.
- No execution controls.
- No destructive controls.
- No copy/export controls.

## 36. Required Controls Before Detail Drawer Consumption

Required before detail drawer consumption:

- Detail endpoint implemented and reviewed.
- Safe detail field allowlist approved.
- Bounded detail diagnostics.
- No raw row/JSONL/SQL/diagnostic dumps.
- Safe not-found/degraded states.
- Tests for forbidden field absence.

## 37. Required Controls Before Copy/Export

Copy/export remains disabled. Required before reconsideration:

- Separate governance approval.
- Export-specific allowlist.
- Export size limits.
- Redaction review.
- Authorization review.
- Audit trail.
- No raw JSONL export.
- No raw SQLite row export.
- No secret/payload/prompt/response/tool-output screenshots or files.

## 38. Required Controls Before Retention/Cleanup Integration

Required before retention/cleanup integration:

- Separate retention/cleanup governance approval.
- Query routes remain readonly.
- Cleanup controls remain separate.
- Query filters do not become cleanup selectors.
- Lifecycle diagnostics remain safe metadata.
- Tests proving no destructive behavior through audit query routes.

## 39. Required Controls Before Any Execution Design

Required before any execution design:

- Separate execution governance approval.
- Persisted evidence remains non-execution input.
- Query results remain non-execution input.
- Explicit user approval model.
- Runtime output preservation review.
- Provider/model call boundary review.
- Prompt rewrite boundary review.
- Tool/command/file/Git/CI boundary review.
- Tests proving query paths cannot trigger execution.

## 40. Explicit Non-Approval Statement

This review does not approve:

- Public API exposure.
- Frontend/Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Raw JSONL read.
- Raw SQLite row read.
- Raw SQL filters.
- Direct API-to-MemoryFacade bypassing the internal query service.
- Prompt rewriting.
- Provider/model retry execution.
- Provider/model replan execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 41. Open Risks

- Future implementation could bypass the internal service.
- Auth/authorization conventions may not be ready.
- Operators may misinterpret advisory metadata as approval.
- Offset pagination may not scale to large audit history.
- Route observability could accidentally log query strings.
- Copy/export requests may pressure the allowlist.
- Public exposure may be proposed before rate limits and auth are complete.

## 42. Open Questions

- Which authentication mechanism should protect the routes?
- Which authorization role should grant readonly audit metadata access?
- Should implementation begin as local-only, internal-only, or admin-only?
- Should API implementation keep offset or move to opaque cursor first?
- Which exact HTTP status should represent degraded storage availability?
- Should safe caller metadata be logged as ID, role, or category?
- What rate limit is appropriate for local and deployed modes?

## 43. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | Approved. |
| API contract design | Go | Approved as design. |
| Internal/private endpoint implementation | Conditional Go | Requires separate implementation branch and strict tests. |
| Public API exposure | No-Go | Requires separate approval. |
| Route exposure without auth | No-Go | Forbidden. |
| Route exposure with auth placeholder only | No-Go | Placeholder is insufficient. |
| Route exposure with real auth/authorization | Conditional Go | Requires rate limits, size limits, logging, and security review. |
| Rate limiting | Conditional Go | Required before exposure. |
| Size limiting | Conditional Go | Required before exposure. |
| Audit logging | Conditional Go | Safe metadata only, required before exposure. |
| Frontend/Cockpit consumption | No-Go | Requires separate governance. |
| Detail drawer consumption | No-Go | Requires separate governance. |
| Copy safe summary | No-Go | Copy/export remains disabled. |
| Export JSON/CSV | No-Go | Requires separate governance. |
| Raw JSONL read | No-Go | Forbidden. |
| Raw SQLite row read | No-Go | Forbidden. |
| Raw SQL filters | No-Go | Forbidden. |
| Direct API-to-MemoryFacade | No-Go | API must use internal service. |
| Prompt rewrite | No-Go | Forbidden. |
| Provider/model retry execution | No-Go | Forbidden. |
| Provider/model replan execution | No-Go | Forbidden. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Forbidden. |

## 44. Final Recommendation

Approve the API contract design as documentation. Conditionally approve a
future internal/private endpoint implementation only if it remains readonly,
calls `HistoricalDryRunAuditQueryService` only, preserves required warnings,
enforces validation and bounded pagination, returns sanitized envelopes and
categorical errors only, avoids raw storage/SQL exposure, and includes focused
negative tests proving no provider/runtime/execution behavior.

Do not approve public exposure, Cockpit consumption, detail drawer
consumption, copy/export, direct API-to-MemoryFacade access, raw storage
access, prompt rewriting, provider/model execution, persisted evidence as
execution input, or autonomous execution.

Omni remains advisory-only.
