# Autonomy Dry-Run Historical Audit API Boundary Design

**Date:** 2026-06-30
**Branch:** `feature/autonomy-dry-run-historical-audit-api-boundary-design`
**Base:** `main` after PR #472
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs a future readonly API boundary for historical dry-run
RETRY and REPLAN audit metadata. It updates the boundary design after the safe
internal layers from PR #471 and PR #472: governed query models,
MemoryFacade query controls, and `HistoricalDryRunAuditQueryService`.

This design is approved for documentation only. It does not approve API
endpoint implementation, route exposure, frontend/Cockpit consumption, detail
drawer consumption, copy/export, raw storage reads, prompt rewrite,
provider/model execution, persisted evidence as execution input, or autonomous
execution.

The future API must consume only `HistoricalDryRunAuditQueryService`, return
only sanitized response envelopes, preserve required advisory warnings, enforce
authentication and authorization before exposure, apply rate limits, audit
query usage safely, and remain readonly.

## 2. Scope

This design covers:

- Future API boundary principles for historical dry-run audit reads.
- Candidate endpoint shapes for design discussion only.
- Mapping from HTTP request inputs to governed query models.
- Mapping from service responses to safe API responses.
- Access control, authentication, authorization, and rate-limit requirements.
- Pagination, filter, sort, enum, timestamp, and ID validation expectations.
- Sanitization, forbidden fields, raw storage prohibitions, and safe errors.
- Controls required before implementation, exposure, Cockpit consumption,
  detail drawer consumption, copy/export, retention/cleanup, or execution.

## 3. Non-Goals

- Do not implement API endpoints.
- Do not add HTTP routes.
- Do not add API handlers.
- Do not add API schemas in code.
- Do not add frontend/Cockpit components.
- Do not add detail drawer UI.
- Do not add copy/export.
- Do not add retention/cleanup behavior.
- Do not modify runtime, provider routing, prompt handling, or execution.
- Do not call providers/models.
- Do not execute RETRY or REPLAN.
- Do not use persisted evidence as execution input.
- Do not approve autonomous execution or self-repair.

## 4. Current Safe Internal Layers

Current safe internal layers are:

- Governed query models in `historical_audit_query_models.py`.
- MemoryFacade query controls from PR #471.
- Internal `HistoricalDryRunAuditQueryService` controls from PR #472.
- Static filter allowlist.
- Static sort allowlist.
- Strict enum validation.
- Bounded pagination.
- Safe response and detail shapes.
- Required advisory warnings.
- Fixed safe degraded/error categories.

The API boundary must treat these layers as the only approved data path.

## 5. API Exposure Risk Summary

API exposure increases risk because it can widen access, automate repeated
queries, and make historical evidence appear operationally authoritative.

Primary risks:

- Exposing audit metadata without authentication or authorization.
- Treating query output as approval or execution input.
- Returning raw storage records, raw JSONL, raw SQLite rows, raw SQL, raw
  exceptions, tracebacks, prompts, provider payloads, tool outputs, or secrets.
- Allowing unbounded scans through broad filters or pagination.
- Bypassing `HistoricalDryRunAuditQueryService` and calling MemoryFacade or
  storage directly.
- Adding Cockpit, copy/export, retention, cleanup, or execution behavior before
  separate governance approval.

## 6. Proposed API Boundary Overview

The future API boundary should follow this flow:

1. Authenticate the caller.
2. Authorize readonly historical dry-run audit access.
3. Enforce method, route, query-size, and rate limits.
4. Map query parameters into `DryRunAuditQueryRequest`.
5. Reject or safely degrade invalid input before service delegation.
6. Call only `HistoricalDryRunAuditQueryService`.
7. Return only the governed sanitized response envelope.
8. Log safe audit metadata only.

The API must never call raw JSONL, SQLite, storage adapters, runtime code,
provider/model code, prompt rewrite code, retry execution, or replan execution.

## 7. Endpoint Candidates, Design Only

Candidate list endpoint:

`GET /internal/audit/dry-run`

Candidate detail endpoint:

`GET /internal/audit/dry-run/{plan_id}`

These names are placeholders only. They are not implementation approval.
Future route naming must be reviewed again with auth, authorization, rate
limits, and tests in scope.

## 8. Request Model Mapping

The API request model may map safe query parameters into
`DryRunAuditQueryRequest`:

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
- `limit`
- `offset`
- `sort_field`
- `sort_direction`

The API must not pass raw request dictionaries to storage. It must not accept
raw SQL, raw JSONL selectors, raw SQLite selectors, prompt text, response text,
provider payload fragments, tool output fragments, command args, file paths,
headers, cookies, tokens, or secrets as filters.

## 9. Response Model Mapping

The list response must preserve the governed safe envelope:

- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category` when degraded
- `generated_at`

The API must not add raw diagnostic fields, raw storage fields, raw exception
objects, tracebacks, paths, SQL, JSONL lines, SQLite rows, prompts, provider
payloads, tool outputs, headers, cookies, tokens, or secrets.

## 10. Detail-Read Mapping

The detail candidate must map a sanitized `plan_id` to
`HistoricalDryRunAuditQueryService.get_historical_dry_run_audit_detail(...)`.

Detail responses may include only the governed safe detail shape. Detail reads
must not return raw JSON views, raw JSONL lines, raw SQLite rows, raw SQL, raw
diagnostic dumps, prompts, provider payloads, tool outputs, command args, file
contents, or secrets.

## 11. Access Control Requirements

API exposure requires access control before route implementation:

- Historical dry-run audit access must be explicit.
- Access must be readonly.
- Unauthorized callers must be rejected before service delegation.
- Cockpit visibility must not imply API authorization.
- Access decisions must not be based on persisted evidence content.
- Access must not grant execution, cleanup, copy/export, prompt rewrite, or
  provider routing authority.

## 12. Authentication Requirements

Authentication must be selected before implementation. If the repo has an
existing protected internal API pattern, the future implementation should reuse
it. If no safe pattern exists, API work must stop for a separate auth design.

Authentication must happen before query service calls and before any storage
work can be triggered indirectly.

## 13. Authorization Requirements

Authorization must verify readonly historical audit metadata permission.

It must not grant:

- Runtime execution authority.
- RETRY or REPLAN execution authority.
- Prompt rewrite authority.
- Provider/model call authority.
- Provider switching authority.
- Copy/export authority.
- Retention or cleanup authority.

## 14. Rate Limit Requirements

Future implementation must define rate limits before exposure:

- Per-caller or per-session request limits.
- Safe behavior for repeated invalid requests.
- Conservative query-size limits.
- Protection against metadata scraping.
- No bypass for detail reads.

Rate-limit responses must be categorical and must not include raw request
payloads, raw exceptions, headers, cookies, tokens, secrets, SQL, paths, rows,
or JSONL lines.

## 15. Pagination Enforcement

Pagination must preserve the governed query model:

- Default limit remains bounded.
- Maximum limit remains enforced.
- Offset remains bounded or is replaced by an opaque safe cursor in a separate
  design.
- No unbounded list queries.
- No full historical scans through the API.
- `page_info` must expose only safe pagination metadata.

## 16. Filter Allowlist Enforcement

The API must enforce the governed filter allowlist by constructing
`DryRunAuditQueryRequest` and preserving its validation behavior.

Supported filters are the model-approved dry-run audit filters only. Unknown
filters must be rejected or safely ignored with warnings according to the
governed contract. The API must not invent new filter names.

## 17. Sort Allowlist Enforcement

The API sort fields must match the governed sort allowlist:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`
- `plan_type`
- `event_type`

Sort directions must be only `asc` or `desc`. Raw column names, SQL fragments,
field paths, nested selectors, JSONPath, regex, and arbitrary storage fields
are forbidden.

## 18. Enum Validation Enforcement

The API must preserve strict enum validation for:

- `plan_type`
- `event_type`
- `source_decision`
- `risk_level`
- `storage_mode`

Unknown enum values must not be rendered, logged, forwarded to storage, or
treated as broad queries.

## 19. Sanitization Requirements

Future API code must sanitize before service delegation and rely on the
governed request model for final validation.

Sanitization requirements:

- Bound all strings.
- Reject unsafe IDs.
- Reject invalid timestamps and inverted ranges.
- Avoid echoing rejected raw values.
- Do not stringify arbitrary objects.
- Do not log raw request payloads.
- Preserve required warnings.

## 20. Safe Response Envelope Requirements

The API may return only the safe envelope emitted by the internal service. It
must preserve:

- Safe item allowlist.
- Safe detail allowlist.
- `page_info`.
- `applied_filters`.
- Required warnings.
- `degraded`.
- Safe categorical `error_category` when degraded.
- `generated_at`.

The API must not add debug expansion flags or raw-storage passthrough options.

## 21. Required Advisory Warnings

Every successful or degraded response must preserve:

- Query results are readonly audit metadata.
- Query results are not approval.
- Query results are not execution input.
- would_retry/would_replan are not execution.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- Copy/export remains disabled.
- Omni remains advisory-only.

## 22. Error/Degradation Response Requirements

Errors must be categorical and safe:

- Invalid request.
- Unauthorized.
- Forbidden.
- Rate limited.
- Not found.
- Storage unavailable through the service.
- Query failed through the service.
- Invalid internal service response.

Forbidden error output:

- Raw exception message.
- Traceback or stack trace.
- SQL statement.
- File path.
- JSONL path or line.
- SQLite path or row.
- Prompt, response, provider payload, tool output, command args, headers,
  cookies, tokens, credentials, or secrets.

## 23. Audit Logging Requirements

API audit logging must record safe metadata only:

- Operation name.
- Safe caller identity or caller category if available.
- Safe request/session/trace ID when already sanitized.
- Filter keys, not raw unsafe values.
- Sort field and direction.
- Bounded limit and offset.
- Response status category.
- Degraded flag.
- Categorical error category.
- Timestamp.

Audit logs must not include raw request bodies, raw response bodies, raw rows,
raw JSONL lines, raw SQL, prompts, provider payloads, tool outputs, headers,
cookies, tokens, secrets, or tracebacks.

## 24. Observability Requirements

Operational observability must be metadata-only:

- Count safe request outcomes.
- Count degraded categories.
- Count rejected invalid requests.
- Count rate-limited requests.
- Track latency without raw payloads.

Observability must not store prompts, provider responses, payloads, tool
outputs, raw SQL, rows, JSONL lines, headers, cookies, tokens, secrets, or raw
exceptions.

## 25. Abuse/Misuse Cases

The API boundary must prevent:

- Treating API visibility as approval.
- Treating `would_retry` as retry execution.
- Treating `would_replan` as replan execution.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Using filters as execution selectors.
- Scraping audit metadata through unbounded queries.
- Attempting SQL injection through filter/sort fields.
- Attempting path traversal through IDs.
- Retrieving raw JSONL, SQLite rows, SQL, prompts, or provider payloads.
- Adding copy/export or execution controls through the API.

## 26. Security Review Checklist

Before implementation, verify:

- Endpoint remains readonly.
- Authentication is selected and tested.
- Authorization is explicit and tested.
- Rate and size limits are defined.
- API delegates only to `HistoricalDryRunAuditQueryService`.
- API never calls MemoryFacade directly.
- API never reads raw JSONL, SQLite, or storage directly.
- Filters, sorts, enums, IDs, and timestamps use governed validation.
- Responses preserve required warnings.
- Errors are categorical and safe.
- Audit logs are metadata-only.
- No API route exposes copy/export, cleanup, runtime, provider, prompt, retry,
  replan, or execution behavior.

## 27. Forbidden Fields Denylist

Forbidden request, response, error, log, and observability content:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys.
- Tokens.
- Secrets.
- Headers.
- Cookies.
- Stack traces.
- Tracebacks.
- stdout.
- stderr.
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

## 28. Raw Storage Exposure Prohibition

The API must never expose raw storage. It must not:

- Read JSONL directly.
- Return JSONL lines.
- Read SQLite rows directly.
- Return SQLite rows.
- Return database paths.
- Return raw SQL.
- Return storage adapter objects.
- Accept storage selectors.

Storage remains behind MemoryFacade and the internal query service.

## 29. Copy/Export Exclusion

Copy/export remains excluded. The API boundary must not define or implement:

- Copy safe summary.
- Export JSON.
- Export CSV.
- Download JSONL.
- Download SQLite data.
- Bulk evidence dumps.
- Clipboard helpers.

Any copy/export work requires separate governance.

## 30. Frontend/Cockpit Consumption Exclusion

Frontend/Cockpit consumption is not approved by this design. Future Cockpit
work requires a separate branch after API implementation and exposure controls
are reviewed.

Cockpit visibility is not operational authorization, and API output is not
execution input.

## 31. Detail Drawer Exclusion

Detail drawer UI consumption is not approved. Detail endpoint candidates in
this document are design-only and must not be treated as UI implementation
approval.

## 32. Retention/Cleanup Exclusion

Retention and cleanup behavior is excluded. Query filters must not become
cleanup selectors. No destructive API control is approved.

## 33. Execution Exclusion

The API boundary must not trigger or feed:

- RETRY execution.
- REPLAN execution.
- Prompt rewriting.
- Provider/model calls.
- Provider switching.
- Tool execution.
- File writes.
- CI repair.
- Git commit, push, PR, or merge automation.
- Autonomous execution.

Persisted evidence remains audit metadata only.

## 34. Required Controls Before Implementation

Before any implementation:

- Separate implementation approval.
- Auth pattern selected.
- Authorization model selected.
- Route names reviewed.
- Request schema reviewed.
- Response schema reviewed.
- Safe error categories reviewed.
- Rate and size limits reviewed.
- Audit logging design reviewed.
- Security test plan reviewed.

## 35. Required Controls Before Route Exposure

Before route exposure:

- Authentication implemented and tested.
- Authorization implemented and tested.
- Rate limits implemented and tested.
- Query size limits implemented and tested.
- Safe audit logging implemented and tested.
- Service-only delegation verified.
- Raw storage bypass tests added.
- Forbidden field tests added.
- Security review completed.

## 36. Required Controls Before Cockpit Consumption

Before Cockpit consumption:

- API route exposure approved.
- Frontend data contract reviewed.
- Readonly/advisory labels approved.
- Empty/loading/error/degraded states reviewed.
- No execution controls.
- No copy/export controls.
- Forbidden field rendering tests added.

## 37. Required Controls Before Detail Drawer Consumption

Before detail drawer consumption:

- Detail API contract approved.
- Detail allowlist approved.
- Safe not-found and degraded states approved.
- No raw JSON view.
- No raw row view.
- No raw SQL, JSONL, prompt, payload, tool output, or secret rendering.
- UI tests for forbidden field absence.

## 38. Required Controls Before Copy/Export

Before copy/export:

- Separate governance review.
- Separate export allowlist.
- Export size limits.
- Export authorization.
- Export audit logging.
- Redaction tests.
- Explicit ban on raw JSONL, SQLite rows, SQL, prompts, provider payloads,
  tool outputs, command args, file contents, and secrets.

## 39. Required Controls Before Retention/Cleanup

Before retention/cleanup:

- Separate governance review.
- Separate cleanup design.
- Proof query filters cannot trigger cleanup.
- Proof cleanup cannot use query results as execution input.
- Safe lifecycle diagnostics only.
- No destructive Cockpit or API control without explicit approval.

## 40. Required Controls Before Any Execution Design

Before any execution design:

- Separate governance review.
- Separate threat model.
- Explicit approval from Misael.
- Proof persisted evidence is not execution input.
- Proof API output is not execution input.
- Prompt rewrite controls reviewed separately.
- Provider/model call controls reviewed separately.
- Runtime output preservation reviewed separately.
- Human approval boundaries defined.

## 41. Open Risks

- Future API code could bypass the internal service.
- Auth and authorization patterns may be unclear.
- Query output may be overinterpreted as approval.
- Filters may be misused as operational selectors.
- Broad query access may create metadata scraping risk.
- Copy/export pressure may widen the boundary.
- Future UI work may accidentally render forbidden fields.

## 42. Open Questions

- Which existing auth pattern should protect the future API?
- Which role or permission should authorize readonly audit metadata access?
- Should endpoints be internal-only, admin-only, or both?
- Should the initial pagination model remain offset-based or move to cursor?
- What rate limits are appropriate for local and deployed environments?
- What safe not-found shape should detail reads return?
- What audit event name should be used for API query access?

## 43. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | Approved for docs/design only. |
| API boundary design | Go | This document only. |
| API endpoint implementation | No-Go | Requires separate approval and controls. |
| API route exposure | No-Go | Requires auth, authorization, limits, logging, and review. |
| API auth/authorization | No-Go | Required before exposure, not implemented here. |
| Rate limiting | No-Go | Required before exposure, not implemented here. |
| Audit logging | No-Go | Required before exposure, not implemented here. |
| Frontend/Cockpit consumption | No-Go | Requires separate governance. |
| Detail drawer consumption | No-Go | Requires separate governance. |
| Copy safe summary | No-Go | Requires separate governance. |
| Export JSON/CSV | No-Go | Requires separate governance. |
| Raw JSONL read | No-Go | Forbidden. |
| Raw SQLite row read | No-Go | Forbidden. |
| Raw SQL filters | No-Go | Forbidden. |
| Prompt rewrite | No-Go | Not approved. |
| Provider/model retry execution | No-Go | Not approved. |
| Provider/model replan execution | No-Go | Not approved. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Omni remains advisory-only. |

## 44. Final Recommendation

Approve this document for API boundary design review only. Do not implement or
expose API routes from this branch.

The next safe step is an API boundary governance review or an implementation
plan that explicitly includes authentication, authorization, rate limits, safe
audit logging, service-only delegation tests, and forbidden-field tests.

Omni remains advisory-only.
