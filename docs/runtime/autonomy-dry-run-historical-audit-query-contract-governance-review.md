# Autonomy Dry-Run Historical Audit Query Contract Governance Review

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-historical-audit-query-contract-governance-review`
**Base:** `main` after PR #461
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

The historical dry-run audit query contract is safe to advance toward future
MemoryFacade query contract implementation only if strict allowlists, bounded
queries, deterministic ordering, sanitized response envelopes, and focused
tests are implemented before any API or Cockpit consumption.

Governance conclusions:

- Approved for documentation.
- Approved for future MemoryFacade query contract implementation, only with
  strict allowlists and tests.
- Approved for future internal sanitized query service design.
- Not approved for API exposure yet.
- Not approved for frontend/Cockpit consumption yet.
- Not approved for copy/export.
- Not approved for raw JSONL read.
- Not approved for raw SQLite row read.
- Not approved for raw SQL filters.
- Not approved for prompt rewriting.
- Not approved for provider/model retry execution.
- Not approved for provider/model replan execution.
- Not approved for persisted evidence as execution input.
- Not approved for autonomous execution.

Required warnings remain active: query results are readonly audit metadata.
Query results are not approval. Query results are not execution input.
`would_retry` and `would_replan` are not execution. Eligibility scores are not
permission. Suggested strategies are not instructions. Cockpit visibility is
not operational authorization. Copy/export remains disabled. Omni remains
advisory-only.

## 2. Scope

This review covers the design-only query/read contract for a future historical
dry-run audit view over persisted RETRY and REPLAN evidence.

It evaluates:

- Request and response safety.
- Evidence item shape.
- Filter, enum, sort, and pagination controls.
- Detail-read behavior.
- Error and degradation handling.
- Access-control expectations.
- Safe field allowlists and forbidden field denylists.
- Storage abstraction boundaries.
- MemoryFacade, JSONL, SQLite, API, and Cockpit boundaries.
- Required controls before future implementation.

## 3. Non-Goals

- Do not implement MemoryFacade queries.
- Do not implement an internal query service.
- Do not expose an API.
- Do not implement Cockpit consumption.
- Do not add detail drawer behavior.
- Do not enable copy/export.
- Do not read raw JSONL lines.
- Do not read raw SQLite rows directly from UI or API.
- Do not add raw SQL filters.
- Do not modify runtime code.
- Do not modify persistence code.
- Do not modify SQLite code.
- Do not modify frontend/Cockpit code.
- Do not rewrite prompts.
- Do not execute RETRY.
- Do not execute REPLAN.
- Do not call providers/models.
- Do not enable autonomous execution.

## 4. Reviewed Materials

Reviewed materials:

- `docs/runtime/autonomy-dry-run-historical-audit-view-design.md`
- `docs/runtime/autonomy-dry-run-historical-audit-query-contract-design.md`
- `docs/runtime/autonomy-dry-run-persistence-governance-review.md`
- Current event types:
  - `dry_run_retry_plan_evidence`
  - `dry_run_replan_plan_evidence`
- Current diagnostic keys:
  - `dry_run_retry_plan_persistence`
  - `dry_run_replan_plan_persistence`

## 5. Governance Decision Summary

The query contract design is acceptable as the next governance layer because it
keeps historical audit inspection readonly, bounded, allowlisted, and
metadata-only.

Approved:

- Documentation.
- Future MemoryFacade query contract implementation with strict allowlists and
  tests.
- Future internal sanitized query service design.

Not approved:

- API exposure.
- Frontend/Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Raw storage reads.
- Raw SQL filters.
- Prompt rewriting.
- Provider/model execution.
- Persisted evidence as execution input.
- Autonomous execution.

## 6. Query Contract Safety Review

The proposed contract is safe at design level because it requires:

- Static filter allowlist.
- Static sort allowlist.
- Enum validation.
- Strict boolean parsing.
- Safe ID validation.
- Bounded timestamps and date ranges.
- Bounded pagination.
- Sanitized response envelope.
- Safe item and detail allowlists.
- Degraded/error category only.

The contract must remain a read contract. It must not grow mutation,
retention, cleanup, execution, provider routing, prompt rewrite, retry, or
replan controls.

## 7. Request Model Review

The request model is acceptable only if it accepts known query fields and
rejects unknown or unsafe input.

Required controls:

- Allowlisted filter names.
- Allowlisted sort fields.
- Allowlisted sort directions.
- Bounded `limit`.
- Bounded `offset` or opaque bounded cursor.
- No arbitrary JSON blobs.
- No raw SQL.
- No raw JSONL fragments.
- No raw SQLite row fragments.
- No prompts, responses, provider payloads, command args, file paths, or
  secrets in request fields.

## 8. Response Model Review

The response model must be a sanitized envelope.

Required response properties:

- `items` contains allowlisted audit metadata only.
- `degraded` is boolean.
- `error_category` is categorical or null.
- Pagination metadata is bounded.
- Storage metadata is categorical.
- Validation errors do not echo unsafe input.
- No raw exception, traceback, SQL, paths, prompts, responses, payloads, tool
  outputs, or secrets.

## 9. Evidence Item Model Review

The evidence item model is acceptable if it includes only safe metadata:

- Event type.
- Plan ID.
- Plan type.
- Advisory flag.
- `would_retry` or `would_replan`.
- Blocked flag.
- Risk level.
- Source decision.
- Fingerprint ID.
- Scores and counts.
- Suggested strategy categories.
- Bounded evidence summary.
- Timestamps.
- Sanitized request, session, and trace IDs when present.
- Persistence diagnostic booleans and categorical values.

Evidence items must not include raw plan context, raw storage records, prompts,
responses, provider payloads, command args, file contents, or secrets.

## 10. Filter Model Review

Approved filters at design level:

- `plan_type`
- `event_type`
- `source_decision`
- `risk_level`
- `blocked`
- `recorded`
- `degraded`
- `storage_mode`
- `sqlite_enabled`
- `request_id`, if sanitized
- `trace_id`, if sanitized
- `session_id`, if sanitized
- `created_at_from`
- `created_at_to`
- `recorded_at_from`
- `recorded_at_to`

Filters must remain audit selectors only. They must not become execution
selectors.

## 11. Enum Validation Review

Required enum constraints:

- `plan_type`: `dry_run_retry`, `dry_run_replan`
- `event_type`: `dry_run_retry_plan_evidence`,
  `dry_run_replan_plan_evidence`
- `source_decision`: `CONTINUE`, `RETRY`, `REPLAN`, `SELF_REPAIR`,
  `SWITCH_PROVIDER`, `PAUSE`, `ESCALATE_TO_MISAEL`, `ABORT_SAFE`, `UNKNOWN`
- `risk_level`: `low`, `medium`, `high`, `unknown`
- `storage_mode`: `jsonl`, `sqlite`, `unavailable`, `unknown`

Unknown enum values must be rejected or normalized to a documented safe value,
not rendered directly.

## 12. Sort Model Review

Approved sort fields:

- `created_at`
- `recorded_at`
- `risk_level`
- `source_decision`
- `plan_type`
- `event_type`

Approved sort directions:

- `asc`
- `desc`

Sort implementation must map these fields through static code, not direct
string interpolation. Default sorting should be deterministic, preferably
`recorded_at desc` with a stable tie-breaker.

## 13. Pagination Model Review

Pagination is required before implementation.

Controls:

- Conservative default limit.
- Explicit maximum page size.
- No unbounded scans.
- Bounded `offset` or opaque bounded cursor.
- Deterministic ordering.
- Optional total count only when cheap and safe.
- Safe degradation when count or cursor generation fails.

## 14. Detail-Read Model Review

Detail reads are higher risk than list reads because operators may expect a
full record. The design is acceptable only if detail reads use the same
allowlist model as list reads.

Allowed detail additions:

- Bounded `block_reasons`.
- Allowlisted diagnostic details.
- Safe categorical storage metadata.

Forbidden:

- Raw JSON view.
- Raw JSONL line.
- Raw SQLite row.
- Raw exception.
- Raw Python repr.
- Prompt, rewritten prompt, response, provider payload, file content, command
  args, tool output, receipt, or secret content.

## 15. Error/Degradation Model Review

The proposed error model is acceptable if failures degrade to safe categories.

Allowed:

- `degraded: true`
- `error_category`
- `storage_mode`
- Empty items.
- Applied bounded pagination metadata.

Forbidden:

- Tracebacks.
- Stack traces.
- Raw exception messages.
- SQL statements.
- File paths.
- SQLite paths.
- JSONL paths.
- Raw context object reprs.
- Raw request payload echoes.

## 16. Access-Control Expectations Review

Access control is not approved for implementation in this branch, but must be
resolved before API exposure.

Expectations:

- Use an existing Cockpit/runtime diagnostics protection pattern.
- Require authenticated access if exposed over HTTP.
- Avoid public unauthenticated historical audit endpoints.
- Consider audit logging for query access before exposure.
- Avoid role expansion without governance review.

## 17. Safe Field Allowlist Review

Safe fields are limited to:

- Categorical event and plan fields.
- Booleans.
- Numeric scores and counts.
- Safe timestamps.
- Bounded sanitized IDs.
- Bounded sanitized evidence summaries.
- Bounded categorical block reasons.
- Persistence diagnostic booleans and categorical values.

The implementation must prefer response construction from explicit field
selection over object dumping.

## 18. Forbidden Field Denylist Review

Forbidden fields:

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
- Raw JSONL lines.
- Screenshots exposing secrets or raw payloads.

The denylist supplements the allowlist; it must not be the only protection.

## 19. Sanitization Review

Sanitization must occur before data reaches API responses or Cockpit.

Required behavior:

- Bound all strings.
- Bound all lists.
- Normalize enums.
- Validate IDs.
- Validate timestamps.
- Clamp or reject invalid numeric scores.
- Remove unsafe diagnostic text.
- Do not preserve raw error text.
- Do not stringify arbitrary objects.

## 20. ID Handling Review

`request_id`, `trace_id`, and `session_id` are allowed only when already
sanitized and bounded.

Required ID controls:

- Explicit maximum length.
- Safe character set.
- Rejection of path separators.
- Rejection of shell metacharacters.
- Rejection of URL query strings.
- Rejection of secrets or token-like content.
- Rejection of raw object reprs.

IDs are correlation metadata only. They must not authorize access or select
execution.

## 21. Timestamp Handling Review

Timestamp filters and returned timestamps must be safe and normalized.

Required controls:

- ISO 8601 parsing.
- UTC normalization or documented timezone behavior.
- Rejection of invalid timestamps.
- Rejection of inverted ranges.
- Maximum date range.
- Conservative default range.
- No unbounded historical scans.

## 22. Storage Abstraction Review

The storage abstraction must prevent callers from learning or depending on raw
storage internals.

Allowed storage metadata:

- `storage_mode`
- `sqlite_enabled`
- `recorded`
- `degraded`
- `error_category`

Forbidden storage metadata:

- File paths.
- SQLite paths.
- Raw table names in user-facing detail if not required.
- Raw rows.
- Raw JSONL lines.
- SQL statements.

## 23. MemoryFacade Boundary Review

MemoryFacade is the correct future boundary for query implementation because
it already owns sanitized evidence persistence contracts.

Required MemoryFacade controls:

- Query input model.
- Query result model.
- Safe detail result model.
- Static filter and sort mapping.
- Bounded pagination.
- Empty results on read failure.
- Corrupt-row degradation.
- No raw JSONL or SQLite row exposure.
- Tests for forbidden field suppression.

MemoryFacade must not become an execution queue or execution selector.

## 24. JSONL Boundary Review

JSONL remains the default audit recording path, but raw JSONL read is not
approved.

Future JSONL query support, if any, must:

- Parse and normalize into safe result models.
- Bound scans.
- Avoid returning paths.
- Avoid returning raw lines.
- Degrade safely when unavailable.
- Treat malformed lines as degraded or skipped records.

## 25. SQLite Boundary Review

SQLite remains opt-in structured evidence storage.

Future SQLite query support must:

- Use parameterized queries.
- Use static sort mappings.
- Enforce bounded limits.
- Enforce date range limits.
- Return sanitized model instances.
- Degrade corrupt rows safely.
- Avoid raw row exposure.
- Avoid SQLite path exposure.

SQLite availability must not change autonomy behavior.

## 26. Frontend/Cockpit Boundary Review

Frontend/Cockpit consumption is not approved yet.

Before approval, Cockpit must have:

- Safe normalizers.
- Readonly labels.
- Empty/loading/error/degraded states.
- No mutation controls.
- No retry/replan execution controls.
- No prompt rewrite controls.
- No provider routing controls.
- No copy/export controls.
- No `dangerouslySetInnerHTML`.
- Tests proving forbidden fields are not rendered.

## 27. Copy/Export Exclusion Review

Copy/export remains disabled.

Separate governance is required before:

- Copy safe summary.
- Export JSON.
- Export CSV.
- Download evidence.
- Copy diagnostic details.

Raw JSONL, raw SQLite rows, prompts, responses, payloads, command args, file
contents, receipts, exceptions, and secrets must never be export targets.

## 28. Audit Logging Review

Audit logging should be considered before API exposure.

Future audit logs should record only safe metadata:

- Query operation type.
- Actor or access context if already safe.
- Attempted timestamp.
- Result count or bounded count.
- Degraded flag.
- Error category.

Audit logs must not record raw query payloads, prompts, responses, SQL, paths,
rows, JSONL lines, or secrets.

## 29. Abuse/Misuse Cases

Abuse and misuse cases:

- Using filters to select records for execution.
- Treating query results as approval.
- Treating `would_retry` or `would_replan` as execution.
- Treating eligibility scores as permission.
- Treating suggested strategies as instructions.
- Querying unbounded historical data.
- Searching for secrets through free-text filters.
- Adding a debug raw-row view.
- Adding copy/export without governance.
- Feeding persisted evidence into future retry/replan automation.

## 30. Security Review Checklist

Before implementation, verify:

- Static filter allowlist.
- Static sort allowlist.
- Enum validation.
- Bounded limit.
- Maximum page size.
- Deterministic ordering.
- No unbounded scans.
- No raw SQL exposure.
- No direct raw JSONL exposure.
- No direct raw SQLite row exposure.
- Sanitized response envelope.
- Safe item allowlist.
- Safe detail allowlist.
- Degraded/error category only.
- No raw exception or traceback.
- No prompts, responses, provider payloads, or tool outputs.
- No secrets, tokens, headers, or cookies.
- Access control before API exposure.
- Audit logging before API exposure.
- Frontend warning labels before Cockpit consumption.
- Copy/export separate governance before enabling.

## 31. Required Controls Before MemoryFacade Implementation

- Query request model with strict validation.
- Query response model with allowlisted fields.
- Detail response model with allowlisted fields.
- Static filter mapping.
- Static sort mapping.
- Enum validation.
- Boolean validation.
- Safe ID validation.
- Date range validation.
- Bounded pagination.
- Tests for malformed and corrupt stored evidence.
- Tests for forbidden field suppression.
- Tests for JSONL and SQLite degradation.

## 32. Required Controls Before Internal Query Service Implementation

- MemoryFacade query contract approved and tested.
- Service boundary documented.
- Safe request normalization.
- Safe response envelope.
- Categorical error model.
- No raw SQL in service inputs.
- No raw storage records in service outputs.
- No execution coupling.
- No cleanup coupling.
- No provider routing coupling.

## 33. Required Controls Before API Exposure

- Existing auth/protection pattern selected.
- Access control tests.
- Safe API schema validation.
- Rate or size limits if needed.
- Audit logging plan.
- Safe validation errors.
- No public unauthenticated endpoint.
- No copy/export endpoint.
- No mutation endpoint.
- No execution endpoint.

## 34. Required Controls Before Frontend/Cockpit Consumption

- API contract approved.
- Frontend normalizer approved.
- Readonly UX labels approved.
- Warning labels included:
  - Query results are readonly audit metadata.
  - Query results are not approval.
  - Query results are not execution input.
  - Copy/export remains disabled.
  - Omni remains advisory-only.
- Empty, loading, error, and degraded states.
- No raw storage rendering.
- No action controls.
- Forbidden field rendering tests.

## 35. Required Controls Before Detail Drawer Consumption

- Detail allowlist approved.
- Bounded `block_reasons`.
- Safe diagnostic field list.
- Safe categorical storage metadata.
- No raw JSON view.
- No raw database row view.
- No raw JSONL line view.
- No copy/export button.
- Tests for forbidden field omission.

## 36. Required Controls Before Copy/Export

- Separate governance review.
- Separate export allowlist.
- Safe summary format.
- Role/access model.
- Export audit logging.
- Redaction tests.
- Explicit ban on raw rows, raw JSONL lines, prompts, responses, payloads,
  command args, file contents, receipts, exceptions, and secrets.

## 37. Required Controls Before Retention/Cleanup Integration

- Separate retention/cleanup design.
- Query filters cannot trigger cleanup.
- Cleanup cannot use query results as execution inputs.
- Lifecycle diagnostics are safe and categorical.
- Deletion scope is explicitly bounded.
- No Cockpit destructive controls without separate governance.

## 38. Required Controls Before Any Execution Design

- Separate governance review.
- Separate threat model.
- Explicit approval by Misael.
- Proof persisted evidence is not used as execution input.
- Proof query filters are not execution selectors.
- Prompt rewriting reviewed separately.
- Provider/model calls reviewed separately.
- Runtime output preservation reviewed separately.
- Human approval boundaries defined.

## 39. Explicit Non-Approval Statement

This review does not approve API exposure, frontend/Cockpit consumption,
detail drawer consumption, copy/export, raw JSONL read, raw SQLite row read,
raw SQL filters, prompt rewriting, provider/model retry execution,
provider/model replan execution, persisted evidence as execution input, or
autonomous execution.

Omni remains advisory-only.

## 40. Open Risks

- Operators may treat query visibility as authorization.
- Future API exposure may be implemented before access controls.
- A debug mode may accidentally expose raw rows or JSONL lines.
- Pagination defaults may be loosened over time.
- Sort mapping may become dynamic if implementation is rushed.
- Copy/export pressure may bypass governance.
- Retention/cleanup work may accidentally couple query selection with
  deletion.

## 41. Open Questions

- Should the first implementation require cursor pagination rather than
  bounded offset?
- What default and maximum date ranges should be enforced?
- Should total counts be omitted unless SQLite is enabled?
- Which existing access-control pattern should protect a future API?
- Should JSONL querying be implemented initially or return a safe unavailable
  storage mode?
- What audit logging fields are sufficient before API exposure?

## 42. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | This governance review is docs-only. |
| MemoryFacade query contract implementation | Conditional go | Only with strict allowlists and tests. |
| Internal sanitized query service implementation | Conditional go | Design is approved; implementation requires controls. |
| API exposure | No-go | Requires access control and audit logging. |
| Frontend/Cockpit consumption | No-go | Requires API and frontend controls. |
| Detail drawer consumption | No-go | Requires separate detail allowlist and tests. |
| Copy safe summary | No-go | Requires separate governance. |
| Export JSON/CSV | No-go | Requires separate governance. |
| Raw JSONL read | No-go | Forbidden. |
| Raw SQLite row read | No-go | Forbidden. |
| Raw SQL filters | No-go | Forbidden. |
| Prompt rewrite | No-go | Not approved. |
| Provider/model retry execution | No-go | Not approved. |
| Provider/model replan execution | No-go | Not approved. |
| Persisted evidence as execution input | No-go | Forbidden. |
| Autonomous execution | No-go | Omni remains advisory-only. |

## 43. Final Recommendation

Approve the historical audit query contract for documentation and for a future
MemoryFacade query contract implementation phase only after strict allowlists,
bounded query controls, deterministic ordering, sanitized response models, and
focused tests are explicitly in scope.

Do not proceed to API exposure, Cockpit consumption, detail drawer
consumption, copy/export, retention/cleanup integration, or execution design
from this review alone. Omni remains advisory-only.
