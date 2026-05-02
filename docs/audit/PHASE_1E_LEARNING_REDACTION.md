# PHASE 1E LEARNING REDACTION — Projeto Omni

Date: 2026-05-01

Branch: hardening/learning-redaction-01e

Base branch: hardening/frontend-debug-01d

Base commit: 5a07a45fec2c97b774c659866d1171a60b5d4a56

Statement: Phase 1E hardens learning/log persistence redaction only. Memory/learning architecture, shell policy, backend public sanitizer, frontend debug sanitizer, and training-label rules were not rewritten.

## Files Changed

- `.gitignore`
- `backend/python/brain/runtime/learning/redaction.py`
- `backend/python/brain/runtime/learning/learning_logger.py`
- `backend/python/brain/runtime/learning/learning_store.py`
- `backend/python/brain/runtime/telemetry/supabase_tool_events.py`
- `tests/runtime/learning/test_learning_redaction.py`
- `docs/audit/PHASE_1E_LEARNING_REDACTION.md`

## Learning / Log Paths Inspected

- `backend/python/brain/runtime/learning/learning_logger.py`
- `backend/python/brain/runtime/learning/learning_store.py`
- `backend/python/brain/runtime/learning/learning_models.py`
- `backend/python/brain/runtime/telemetry/supabase_tool_events.py`
- `backend/python/brain/runtime/observability/*`
- `backend/python/brain/runtime/memory/*`
- `.gitignore`

## Redaction Helper Summary

Added centralized learning/log redaction helpers:

- `redact_sensitive_text(...)`
- `redact_sensitive_payload(...)`
- `redact_learning_record(...)`

Properties:

- Recursive dict/list/tuple/string handling.
- No mutation of original payloads.
- Preserves useful non-sensitive metadata.
- Redacts sensitive text patterns with stable placeholders.
- Replaces dangerous internal payload fields with `[REDACTED_INTERNAL_PAYLOAD]`.
- Safe behavior on null and scalar inputs.

Applied at persistence boundaries:

- Controlled learning records.
- Controlled improvement signals.
- General learning evidence/signals/pattern snapshots.
- Supabase tool telemetry metadata.

## Patterns Covered

Text redaction covers:

- `sk-proj-*`
- `sk-ant-*`
- `sk-groq-*`
- generic `sk-*`
- Bearer tokens
- JWT-like tokens
- emails
- Brazilian phones
- CPF
- `password=*`
- `token=*`
- `secret=*`
- `api_key=*`
- Supabase-like URLs / JWT-like keys
- Unix absolute paths under `/home`, `/root`, `/tmp`, `/var`, `/usr`, `/etc`
- Windows absolute paths under `C:\Users`, `C:\Windows`, `C:\Program Files`

Dangerous payload keys redacted:

- `stack`
- `trace`
- `traceback`
- `raw_error`
- `stdout`
- `stderr`
- `command`
- `args`
- `argv`
- `env`
- `api_key`
- `token`
- `jwt`
- `secret`
- `password`
- `authorization`
- `bearer`
- `provider_raw`
- `raw_provider`
- `raw_response`
- `raw_payload`
- `execution_request`
- `tool_raw_result`
- `memory_raw`
- `memory_content`

## Gitignore Updates

Added:

- `runtime_logs/`
- `learning_logs/`
- `storage/local/`
- `*.trace.json`
- `*.debug.json`

Existing `.env`, `.env.*`, `.logs/`, and `logs/` rules were preserved.

## Tests Run / Results

- `python -m pytest -q tests/runtime/learning/test_learning_redaction.py` — PASS, 5 tests
- `python -m py_compile backend/python/brain/runtime/learning/redaction.py backend/python/brain/runtime/learning/learning_logger.py backend/python/brain/runtime/learning/learning_store.py backend/python/brain/runtime/telemetry/supabase_tool_events.py` — PASS
- `python -m pytest -q tests/runtime/learning/test_learning_loop.py` — PASS
- `npm run test:js-runtime` — PASS
- `npm run test:python:pytest` — PASS
- `npm test` — PASS
- `git diff --check` — PASS

## Known Limitations

- This phase protects learning/log persistence paths touched by the current runtime. Historical existing logs are not rewritten.
- Phase 9 still owns training-label safety for fallback/matcher learning decisions.
- Some tracked memory fixtures were modified by validation and restored before commit because they are not part of Phase 1E deliverables.

## Rollback

Rollback command:

```bash
git revert <phase-1e-commit>
```

## Gate 1E Status

PASSED:

- Learning/log redaction is stronger.
- PII/secrets/paths are redacted.
- Raw internal payload fields are redacted before persistence.
- Runtime/learning log locations are gitignored.
- Tests cover PII, secrets, paths, nested payloads, and no-mutation behavior.
- No merge into main.

No merge into main: confirmed.
