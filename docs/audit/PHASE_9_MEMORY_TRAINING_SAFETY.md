# PHASE 9 — MEMORY & TRAINING SAFETY

Date: 2026-05-01

Base branch: security/regression-suite-07

Base commit: bc27752e8ee79e2cd7d65f56de15f6a64342ad4a

Working branch: memory/training-safety-09

## Scope

Phase 9 prevents low-truth or unsafe runtime events from being marked as positive memory/training candidates. This phase does not start LoRA/RAG/training export, does not rewrite memory architecture, and does not merge into main.

## Memory / Learning Paths Inspected

- `backend/python/brain/runtime/learning/learning_logger.py`
- `backend/python/brain/runtime/learning/learning_models.py`
- `backend/python/brain/runtime/learning/learning_store.py`
- `backend/python/brain/runtime/learning/redaction.py`
- `backend/python/brain/runtime/error_taxonomy.py`
- `tests/runtime/learning/test_learning_loop.py`
- `tests/runtime/learning/test_learning_redaction.py`

## Files Changed

- `backend/python/brain/runtime/learning/learning_safety.py`
- `backend/python/brain/runtime/learning/learning_logger.py`
- `backend/python/brain/runtime/learning/learning_models.py`
- `tests/runtime/learning/test_learning_training_safety.py`
- `tests/runtime/learning/test_learning_loop.py`
- `docs/audit/PHASE_9_MEMORY_TRAINING_SAFETY.md`

## Classification Policy

The new `learning_safety.py` helper provides:

- `classify_learning_record(...)`
- `should_save_positive_learning(...)`
- `build_learning_safety_metadata(...)`

The classifier uses runtime truth, provider status, tool status, governance status, public error taxonomy severity, fallback status, and redaction markers to decide whether a record is positive, negative, diagnostic, or evaluation-only.

## Positive Exclusion Rules

Records are not positive training candidates when any of these are observed:

- `fallback_triggered=true`
- `runtime_mode=MATCHER_SHORTCUT`
- `runtime_mode=SAFE_FALLBACK`
- `runtime_mode=NODE_FALLBACK`
- `runtime_mode=PROVIDER_UNAVAILABLE`
- `runtime_mode=TOOL_BLOCKED`
- provider failure or `provider_succeeded=false`
- `tool_status=failed`, `blocked`, or `denied`
- governance status `blocked`
- public error code with severity `degraded`, `blocked`, `error`, or `critical`
- internal error redacted with unknown quality
- internal payload redaction marker present

## Negative / Diagnostic Classifications

Supported classifications include:

- `positive_training_candidate`
- `diagnostic_memory`
- `failure_memory`
- `routing_eval_case`
- `tool_failure_case`
- `governance_block_case`

## Safety Metadata Schema

Every controlled learning record now includes a `learning_safety` object:

```json
{
  "learning_classification": "diagnostic_memory",
  "positive_training_candidate": false,
  "negative_training_candidate": false,
  "runtime_mode": "...",
  "fallback_triggered": false,
  "provider_succeeded": true,
  "tool_status": "",
  "governance_status": "",
  "error_public_code": "",
  "redaction_applied": false,
  "learning_safety_reason": "..."
}
```

## Redaction Interaction

Phase 1E redaction remains active before persistence. Phase 9 builds safety metadata before persistence and the final record is still passed through `redact_learning_record(...)` before writing JSONL. The store also continues to apply `redact_sensitive_payload(...)` at the append boundary.

## Tests Run / Results

- `python -m pytest -q tests/runtime/learning/test_learning_training_safety.py tests/runtime/learning/test_learning_loop.py tests/runtime/learning/test_learning_redaction.py` — PASS. 12 passed.
- `python -m py_compile backend/python/brain/runtime/learning/learning_safety.py backend/python/brain/runtime/learning/learning_logger.py backend/python/brain/runtime/learning/learning_models.py` — PASS.
- `npm run test:security` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `node tests/security/security-regression-suite.mjs` — PASS. Consolidated security suite passed across Phases 1A-1E, 2, 3, 4, 5, 6, and 8.
- `npm test` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `npm run test:js-runtime` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `npm --prefix frontend run typecheck` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `npm run test:python:pytest` — TIMEOUT after 300 seconds. Classified as inherited broad-suite timeout because focused Phase 9 and consolidated security tests passed.
- `cd backend/rust && cargo test` — PASS. 38 passed; warning remains for unused `InvalidRequest` variant.
- `git diff --check` — PASS with CRLF warnings in touched files.

## Known Limitations

- The classifier does not export training datasets; Phase 13 owns export readiness.
- Historical logs are not rewritten.
- Existing memory systems outside controlled learning records were inspected but not rewritten in this phase.

## Rollback

Revert the Phase 9 commit on `memory/training-safety-09`.

## Gate 9 Status

Status: PASSED.

Reason: learning records now carry safety metadata, positive training candidacy excludes fallback/matcher/provider/tool/governance/error cases, redaction remains active before persistence, focused tests cover the required policy, and no merge into main occurred.

## No Merge Into Main

This phase does not merge into main.
