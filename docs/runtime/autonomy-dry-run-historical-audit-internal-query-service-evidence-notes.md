# Autonomy Dry-Run Historical Audit Internal Query Service Evidence Notes

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-historical-audit-internal-query-service-evidence-notes`
**Base:** `main` after PR #466
**Status:** Evidence notes only
**Runtime impact:** None

## 1. Executive Summary

PR #466 implemented the internal readonly historical dry-run audit query
service contracts that sit between future API/Cockpit layers and the
MemoryFacade historical dry-run audit query contracts. The implemented service
is a validation, delegation, degradation, and safe metadata logging boundary.

The service is not an API, not a UI surface, not a runtime execution path, and
not an authorization mechanism. It returns readonly audit metadata only. It
does not execute RETRY or REPLAN, does not rewrite prompts, does not call
providers/models, does not change provider routing, does not mutate runtime
output, and does not use persisted evidence as execution input.

## 2. Scope

These notes document the implemented service contracts from PR #466:

- `HistoricalDryRunAuditQueryService`
- `query_historical_dry_run_audit(...)`
- `get_historical_dry_run_audit_detail(...)`
- Safe request validation behavior.
- MemoryFacade-only delegation.
- Sanitized response and degradation behavior.
- Optional safe audit metadata logging.
- Test evidence and validation caveats.
- Future governance gates.

## 3. Non-Goals

- Do not define a public API.
- Do not define Cockpit or frontend behavior.
- Do not add a detail drawer contract.
- Do not approve copy/export.
- Do not approve raw JSONL reads.
- Do not approve raw SQLite row reads.
- Do not approve raw SQL filters.
- Do not modify runtime behavior.
- Do not modify persistence behavior.
- Do not modify MemoryFacade contracts.
- Do not modify SQLite behavior.
- Do not rewrite prompts.
- Do not execute RETRY.
- Do not execute REPLAN.
- Do not call providers/models.
- Do not use persisted evidence as execution input.
- Do not approve autonomous execution.

## 4. Implementation Summary

PR #466 added a narrow internal service module. The service accepts a typed
`DryRunAuditQueryRequest`, rejects invalid requests before calling
MemoryFacade, delegates valid list/detail reads only to MemoryFacade safe
methods, and returns MemoryFacade-safe response models.

When the service sees invalid input, MemoryFacade exceptions, or invalid
MemoryFacade response shapes, it degrades safely with categorical
`error_category` values and safe warnings. It does not return raw exception
messages or tracebacks.

## 5. Files Introduced

PR #466 introduced:

- `backend/python/brain/memory/historical_audit_query_service.py`
- `backend/python/tests/memory/test_historical_dry_run_audit_query_service.py`

No runtime, persistence, SQLite, API, frontend, Cockpit, provider, prompt, or
execution files were introduced or modified by the service implementation.

## 6. Service Class Summary

`HistoricalDryRunAuditQueryService` is an internal readonly service boundary.
It is initialized with a MemoryFacade-compatible object and an optional audit
logger callback.

The service depends on a protocol with only these methods:

- `query_historical_dry_run_audit_evidence(...)`
- `get_historical_dry_run_audit_evidence_detail(...)`

This keeps the service scoped to MemoryFacade safe contracts instead of raw
storage access.

## 7. Public Internal Service Functions

The module also exposes convenience functions:

- `query_historical_dry_run_audit(memory_facade, request, audit_logger=None)`
- `get_historical_dry_run_audit_detail(memory_facade, plan_id, audit_logger=None)`

These functions instantiate the service and delegate to the matching service
methods. They are internal helpers, not API endpoints.

## 8. Request Model Handling

The list path expects a typed `DryRunAuditQueryRequest`. Non-request input
degrades safely as `invalid_request` and does not call MemoryFacade.

The detail path accepts a `plan_id`, sanitizes it through the audit ID
allowlist, and returns `None` without delegation when the ID is invalid.

## 9. Validation Behavior

Validation is enforced before MemoryFacade delegation:

- Filter allowlists are enforced by `DryRunAuditQueryRequest`.
- Sort field and direction allowlists are enforced.
- Enum filters are validated.
- Boolean filters are normalized strictly.
- Limit and offset are bounded.
- Timestamp ranges are validated.
- Request, session, trace, and plan IDs are sanitized.
- Invalid requests degrade safely before storage reads.

Unsupported filters remain warnings only when the request model safely ignores
them. Invalid filters produce degraded responses with categorical
`error_category` values.

## 10. MemoryFacade-Only Delegation Behavior

The service calls only MemoryFacade safe query/detail methods:

- `MemoryFacade.query_historical_dry_run_audit_evidence(...)`
- `MemoryFacade.get_historical_dry_run_audit_evidence_detail(...)`

It does not instantiate SQLite adapters, JSONL readers, raw storage clients, or
runtime objects. It does not construct SQL or accept raw SQL filters.

## 11. List Query Behavior

List query flow:

1. Receive typed `DryRunAuditQueryRequest`.
2. Reject non-request input safely.
3. Reject invalid request objects before delegation.
4. Call MemoryFacade safe list query only for valid requests.
5. Validate the returned response object type.
6. Return the safe response envelope or a degraded safe envelope.
7. Optionally emit safe audit metadata.

The returned list remains audit metadata only. It is not execution input.

## 12. Detail Read Behavior

Detail read flow:

1. Receive a `plan_id`.
2. Sanitize the ID.
3. Return `None` for invalid IDs without calling MemoryFacade.
4. Call MemoryFacade safe detail read for valid IDs.
5. Return a safe `DryRunAuditEvidenceDetail` or `None`.
6. Degrade to `None` on MemoryFacade errors without raw exception exposure.
7. Optionally emit safe audit metadata.

The detail path is a safe metadata read, not a raw record dump.

## 13. Sanitized Response Behavior

The list response preserves the MemoryFacade safe envelope:

- `items`
- `page_info`
- `applied_filters`
- `warnings`
- `degraded`
- `error_category`, only when degraded
- `generated_at`

The detail response preserves the MemoryFacade safe detail model and does not
add raw storage records, raw SQL, raw JSONL lines, prompts, responses,
provider payloads, tool outputs, or secrets.

## 14. Degradation Behavior

Safe degradation cases include:

- Non-`DryRunAuditQueryRequest` input: `invalid_request`.
- Invalid request model: the request model error category, or
  `invalid_request`.
- MemoryFacade list failure: `query_failed`.
- Invalid MemoryFacade list response shape:
  `invalid_memoryfacade_response`.
- Invalid detail ID: safe `None`.
- MemoryFacade detail failure: safe `None` with logged `query_failed` only.
- Invalid detail response shape: safe `None` with
  `invalid_memoryfacade_response`.

Raw exception messages, tracebacks, stack traces, paths, SQL, rows, JSONL
lines, prompts, responses, payloads, and secrets are not returned.

## 15. Safe Audit Metadata Logging

The service supports an optional audit logger callback. Logged metadata is
limited to safe fields:

- `operation_name`
- `filter_keys`
- `sort_field`
- `sort_direction`
- `limit`
- `offset`
- `generated_at`
- `degraded`
- `error_category`, categorical only
- sanitized `request_id`, `session_id`, and `trace_id` when present
- sanitized `plan_id` for detail reads

The service does not log raw request bodies, raw response bodies, raw
exceptions, tracebacks, raw SQL, rows, JSONL lines, prompts, responses,
provider payloads, tool outputs, headers, cookies, tokens, or secrets. Audit
logger failures are ignored safely.

## 16. Forbidden Behavior Confirmation

The implemented service does not:

- Add API endpoints.
- Add frontend or Cockpit UI.
- Add detail drawer behavior.
- Add copy/export.
- Read raw JSONL directly.
- Read raw SQLite rows directly.
- Build or expose raw SQL.
- Call runtime.
- Call providers/models.
- Rewrite prompts.
- Execute RETRY.
- Execute REPLAN.
- Change provider routing.
- Change runtime output.
- Use persisted evidence as execution input.
- Approve autonomous execution.

## 17. Storage Boundary Confirmation

Storage access remains behind MemoryFacade. The service is not a storage
adapter and is not a query engine over raw storage.

JSONL and SQLite behavior are inherited only through MemoryFacade safe query
contracts. The service does not inspect JSONL files, SQLite files, SQLite
paths, SQLite rows, SQL strings, or raw persistence records.

## 18. Runtime Boundary Confirmation

The service does not import or call runtime wiring, runtime controllers,
provider routing, Autonomy Controller execution paths, or runtime response
generation code.

Runtime output preservation remains intact because the service is not wired
into runtime response construction.

## 19. Provider/Model Boundary Confirmation

The service does not call provider clients, model clients, routing logic,
retry execution, replan execution, prompt rewriting, or tool execution.

Any `would_retry` or `would_replan` value returned by the service is historical
audit metadata. It is not evidence that a provider/model call occurred.

## 20. Execution-Input Boundary Confirmation

Query results must never become execution input. Persisted evidence is
readonly audit metadata. It must not be used to select, authorize, or trigger
RETRY, REPLAN, provider calls, prompt rewrites, tools, commands, CI repair,
file writes, commits, pushes, or PR automation.

## 21. API/Frontend Boundary Confirmation

API exposure remains not approved. Frontend/Cockpit consumption remains not
approved. The service creates a safer future backend boundary, but no API
routes, UI components, data fetching hooks, or Cockpit screens were added.

Future API and Cockpit work requires separate governance and tests.

## 22. Copy/Export Boundary Confirmation

Copy/export remains disabled and not approved. The service does not add
clipboard output, CSV output, JSON export, raw row export, or raw JSONL export.

Any future copy/export feature requires separate governance, allowlisted field
schemas, redaction review, and abuse-case testing.

## 23. Test Coverage Summary

PR #466 added focused tests for:

- List query delegation to MemoryFacade safe query only.
- Detail read delegation to MemoryFacade safe detail only.
- Module helper delegation.
- Invalid non-request input degradation.
- Invalid request degradation before MemoryFacade calls.
- Filter, sort, enum, limit, timestamp, and ID validation behavior.
- Safe response field shape.
- Forbidden field absence in list/detail responses.
- MemoryFacade query failure degradation.
- MemoryFacade detail failure degradation.
- Invalid detail ID handling.
- Invalid MemoryFacade response handling.
- Safe audit logger metadata.
- Audit logger failure safety.
- No runtime/provider execution behavior and no execution input semantics.

## 24. Validation Results

Validation reported for PR #466:

- `python -m pytest backend/python/tests/memory/test_historical_dry_run_audit_query_contracts.py`: passed.
- `python -m pytest backend/python/tests/memory/test_historical_dry_run_audit_query_service.py backend/python/tests/memory/test_historical_dry_run_audit_query_contracts.py`: passed.
- `python -m pytest backend/python/tests/runtime/autonomy/`: passed.
- `npm run test:security`: passed.
- `git diff --check`: passed.

One broad local memory-suite run was inconclusive because a restored local
untracked test outside the PR scope failed. The focused service and existing
query contract tests passed.

## 25. Known Caveats

- The service is internal only and has no access-control layer by itself.
- API exposure is not implemented and not approved.
- Cockpit consumption is not implemented and not approved.
- Detail drawer behavior is not implemented and not approved.
- Copy/export is not implemented and not approved.
- Retention/cleanup integration is not implemented and not approved.
- The service relies on MemoryFacade safe query contracts for storage access.
- Audit logger behavior is optional and must remain metadata-only.
- Future consumers must not treat service results as authorization.

## 26. Security Interpretation

The service should be interpreted as a defense-in-depth boundary. It narrows
future consumers to typed requests, sanitized response models, MemoryFacade-only
access, and safe degradation.

It does not prove that API or UI exposure is safe by itself. Before exposure,
access control, rate limiting if applicable, schema validation, response
allowlists, redaction tests, logging tests, and abuse-case tests must be
reviewed separately.

## 27. Operator Interpretation Warnings

- Internal service results are readonly audit metadata.
- Internal service results are not approval.
- Internal service results are not execution input.
- `would_retry` and `would_replan` are not execution.
- Eligibility scores are not permission.
- Suggested strategies are not instructions.
- `blocked=false` is not approval.
- API exposure remains not approved.
- Cockpit consumption remains not approved.
- Copy/export remains disabled.
- JSONL/SQLite storage is not operational authorization.
- Omni remains advisory-only.

## 28. Future Implementation Gates

Before any downstream implementation, governance must confirm:

- The consumer calls only this service or an equally safe successor.
- Inputs remain typed and validated.
- Outputs remain allowlisted.
- Errors remain categorical.
- Audit logs remain metadata-only.
- No raw storage access is introduced.
- No execution-input usage is introduced.

## 29. Required Controls Before API Exposure

- Explicit API governance approval.
- Authentication and authorization review.
- Request schema validation at the API boundary.
- Static filter and sort allowlists.
- Bounded pagination enforcement.
- Safe error response model.
- No raw exception, traceback, SQL, row, JSONL, prompt, response, payload, or
  secret exposure.
- Tests for unauthorized access.
- Tests for malformed input.
- Tests proving API routes do not call runtime or providers/models.

## 30. Required Controls Before Cockpit Consumption

- Separate Cockpit consumption approval.
- Readonly warning labels.
- No destructive controls.
- No execution controls.
- No use of query results as operational authorization.
- Empty/loading/error states that do not leak raw details.
- No `dangerouslySetInnerHTML`.
- Frontend tests for missing/degraded diagnostics.
- Frontend tests for forbidden field absence.

## 31. Required Controls Before Detail Drawer Consumption

- Separate detail drawer approval.
- Safe detail field allowlist.
- Bounded `block_reasons` and evidence summaries.
- No raw record display.
- No raw JSONL line display.
- No raw SQLite row display.
- No raw diagnostic object dumps.
- Clear labels: readonly, not approval, not execution input.

## 32. Required Controls Before Copy/Export

- Separate copy/export governance approval.
- Safe summary format.
- Explicit field allowlist.
- Redaction review.
- Export size limits.
- Audit trail for export action if approved.
- No raw JSONL export.
- No raw SQLite row export.
- No screenshots or exports that include secrets, payloads, prompts, responses,
  tool outputs, headers, cookies, or command args.

## 33. Required Controls Before Retention/Cleanup Integration

- Separate retention/cleanup governance approval.
- Clear lifecycle rules for historical audit evidence.
- Dry-run cleanup design before deletion behavior.
- Explicit manual cleanup controls if deletion is supported.
- No background deletion loop unless separately approved.
- Tests proving non-expired evidence is not deleted.
- Safe cleanup diagnostics only.

## 34. Required Controls Before Any Execution Design

- Separate execution design governance.
- Proof that persisted evidence is not execution input.
- Explicit user approval requirements.
- Provider/model call boundary review.
- Prompt rewrite boundary review.
- Tool/command/file/Git/CI boundary review.
- Runtime output preservation review.
- Security and privacy review.
- Tests proving no accidental execution path.

## 35. Go/No-Go Table

| Area | Decision | Notes |
| --- | --- | --- |
| Documentation | Go | Evidence notes are approved. |
| Internal service contracts | Go | Implemented in PR #466 as readonly metadata contracts. |
| Internal service implementation hardening | Go with controls | Future hardening may proceed with strict tests and no scope widening. |
| API exposure | No-Go | Requires separate governance and access-control review. |
| Frontend/Cockpit consumption | No-Go | Requires separate governance and readonly UI review. |
| Detail drawer consumption | No-Go | Requires separate detail allowlist and tests. |
| Copy safe summary | No-Go | Requires separate copy/export governance. |
| Export JSON/CSV | No-Go | Requires separate export governance and redaction controls. |
| Raw JSONL read | No-Go | Forbidden. |
| Raw SQLite row read | No-Go | Forbidden. |
| Raw SQL filters | No-Go | Forbidden. |
| Runtime call | No-Go | Forbidden. |
| Provider/model call | No-Go | Forbidden. |
| Prompt rewrite | No-Go | Forbidden. |
| Provider/model retry execution | No-Go | Forbidden. |
| Provider/model replan execution | No-Go | Forbidden. |
| Persisted evidence as execution input | No-Go | Forbidden. |
| Autonomous execution | No-Go | Forbidden. |

## 36. Final Recommendation

The internal query service contracts from PR #466 are safe to document as
readonly, sanitized, MemoryFacade-only evidence access contracts.

Approved:

- Documentation.
- Internal readonly service evidence interpretation.
- Future hardening of the internal service under the same safety boundaries.

Not approved:

- API exposure.
- Cockpit consumption.
- Detail drawer consumption.
- Copy/export.
- Raw storage access.
- Runtime calls.
- Provider/model calls.
- Prompt rewriting.
- RETRY or REPLAN execution.
- Persisted evidence as execution input.
- Autonomous execution.

Omni remains advisory-only.
