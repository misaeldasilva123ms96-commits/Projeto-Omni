# PHASE 8 RUNTIME ERROR TAXONOMY — Projeto Omni

Date: 2026-05-01
Base branch: governance/tool-enforcement-03
Base commit: 339641799a5d2603bd6c6b498a3c4e19364e15be
Working branch: runtime/error-taxonomy-08

## Scope

Phase 8 centralizes public-safe runtime error codes and messages across Python and JS. This phase does not change runtime execution architecture or security semantics from Phases 1A, 2, or 3.

## Files Changed

- `backend/python/brain/runtime/error_taxonomy.py`
- `runtime/tooling/errorTaxonomy.js`
- `backend/python/brain/runtime/shell_policy.py`
- `backend/python/brain/runtime/tool_governance_policy.py`
- `backend/python/brain/runtime/engineering_tools.py`
- `backend/python/main.py`
- `backend/python/brain/runtime/observability/public_runtime_payload.py`
- `runtime/tooling/toolGovernance.js`
- `features/multiagent/specialists/specialistErrorPolicy.js`
- `frontend/src/types.ts`
- `frontend/src/types/ui/chat.ts`
- `frontend/src/lib/api/adapters.ts`
- `frontend/src/components/status/RuntimeDebugSection.tsx`
- tests covering Python, JS, and frontend debug display

## Taxonomy Modules

- Python: `backend/python/brain/runtime/error_taxonomy.py`
- JS: `runtime/tooling/errorTaxonomy.js`

Both expose:

- error code enum/object
- public messages
- severity mapping
- retryable mapping
- `build_public_error` / `buildPublicError`
- `normalize_public_error` / `normalizePublicError`

## Error Codes Defined

- `SHELL_TOOL_BLOCKED`
- `TOOL_BLOCKED_PUBLIC_DEMO`
- `TOOL_BLOCKED_BY_GOVERNANCE`
- `TOOL_APPROVAL_REQUIRED`
- `SPECIALIST_FAILED`
- `MATCHER_SHORTCUT_USED`
- `RULE_BASED_INTENT_USED`
- `PROVIDER_UNAVAILABLE`
- `NODE_EMPTY_RESPONSE`
- `NODE_RUNNER_FAILED`
- `PYTHON_ORCHESTRATOR_FAILED`
- `MEMORY_STORE_UNAVAILABLE`
- `SUPABASE_NOT_CONFIGURED`
- `TIMEOUT`
- `INTERNAL_ERROR_REDACTED`

## Severity Mapping

- `info`: matcher shortcut, rule-based intent, Supabase not configured
- `degraded`: specialist failed, provider unavailable, node empty response, node runner failed, memory store unavailable
- `blocked`: shell/tool/governance/approval blocks
- `error`: Python orchestrator failure, timeout
- `critical`: internal error redacted

## Retryable Mapping

Retryable:

- `SPECIALIST_FAILED`
- `PROVIDER_UNAVAILABLE`
- `NODE_EMPTY_RESPONSE`
- `NODE_RUNNER_FAILED`
- `PYTHON_ORCHESTRATOR_FAILED`
- `MEMORY_STORE_UNAVAILABLE`
- `TIMEOUT`

Non-retryable:

- policy/governance/approval/public-demo blocks
- matcher/rule-based informational codes
- Supabase not configured
- internal redacted error

## Integration Points Updated

- Phase 1A shell blocked result now uses Python taxonomy.
- Phase 3 governance decisions/results now include standard `severity` and `retryable`.
- Specialist fallback now uses JS taxonomy for `SPECIALIST_FAILED`.
- Python main public errors now include standard public error fields.
- Engineering tool timeout returns `TIMEOUT` standard shape.
- Public runtime sanitizer preserves `severity` and `retryable`.

## Frontend Display Impact

Frontend runtime debug metadata types and adapters now carry:

- `error_public_code`
- `error_public_message`
- `severity`
- `retryable`
- `internal_error_redacted`

`RuntimeDebugSection` displays these fields after sanitization. No raw error payload rendering was added.

## Tests Run / Results

Narrow tests:

- `python -m pytest -q tests/runtime/test_error_taxonomy.py tests/runtime/test_shell_policy_hardening.py tests/runtime/test_tool_governance_enforcement.py tests/runtime/observability/test_public_runtime_payload.py` — passed
- `node tests/runtime/errorTaxonomy.test.mjs` — passed
- `node tests/runtime/toolGovernanceEnforcement.test.mjs` — passed
- `node tests/runtime/specialistErrorPolicy.test.mjs` — passed
- `npm --prefix frontend run test -- RuntimeDebugSection.test.tsx` — passed

An earlier frontend command form `npm --prefix frontend test -- RuntimeDebugSection.test.tsx` timed out after 120 seconds. The project script uses `npm run test`, and the script form completed.

Broad validation:

- `python -m py_compile ...changed_python_files...` — passed
- `git diff --check` — passed
- `npm test` — passed
- `npm run test:python:pytest` — passed on final run
- `npm run test:js-runtime` — timed out after 300 seconds and again after 180 seconds
- `npm --prefix frontend run typecheck` — timed out after 180 seconds and again after 360 seconds

Targeted JS tests from the changed/critical paths passed:

- `node scripts/js-runtime-launcher.mjs tests/runtime/errorTaxonomy.test.mjs`
- `node scripts/js-runtime-launcher.mjs tests/runtime/toolGovernanceEnforcement.test.mjs`
- `node scripts/js-runtime-launcher.mjs tests/runtime/specialistErrorPolicy.test.mjs`
- `node scripts/js-runtime-launcher.mjs tests/runtime/executionProvenance.test.mjs`
- `node scripts/js-runtime-launcher.mjs tests/runtime/queryengineRuntimeMode.test.mjs`

## Known Limitations

- Phase 8 normalizes public error shape but does not redesign every internal exception path.
- Some legacy fields such as `failure_class` and `message` remain for backward compatibility.
- Frontend displays taxonomy fields when present; it does not fabricate them if an older backend omits them.

## Rollback

Rollback command:

```bash
git revert <phase-8-commit>
```

## Gate 8 Status

PASSED if broad validation completes or any failure is documented as inherited/unrelated with evidence.

## No Merge Into Main

Confirmed. This phase is committed only to `runtime/error-taxonomy-08`.
