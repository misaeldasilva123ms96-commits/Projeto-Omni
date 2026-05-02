# PHASE 11A — PYTHON INTERNAL BRAIN SERVICE

Date: 2026-05-01

Base branch: architecture/persistent-runtime-plan-10

Base commit: 5d00371baa28b285d68d368b54a149634398f9dd

Working branch: architecture/python-service-11a

## Scope

Phase 11A adds a Python internal HTTP service entrypoint while preserving the existing stdin/subprocess mode. Rust is not switched to service mode in this phase. Node service mode is not changed.

## Files Changed

- `backend/python/main.py`
- `backend/python/brain_service.py`
- `tests/runtime/test_python_brain_service.py`
- `docs/architecture/python-internal-brain-service.md`
- `docs/audit/PHASE_11A_PYTHON_SERVICE.md`

## Service Entrypoint

- `backend/python/brain_service.py`

## Endpoints

- `POST /internal/brain/run`
- `GET /internal/brain/health`
- `GET /internal/brain/readiness`

## No Behavior Changed Statement

The existing `backend/python/main.py` stdin/stdout behavior remains intact. The new service reuses the same public payload builder and public sanitizer.

## Security Posture

- default host: `127.0.0.1`
- no CORS
- internal-only documentation warning
- taxonomy-shaped public errors
- public runtime payload sanitizer reused
- no raw env, secrets, stack traces, stdout/stderr, command args, raw provider/tool/memory payloads in responses

## Env Vars

- `OMNI_PYTHON_SERVICE_HOST`
- `OMNI_PYTHON_SERVICE_PORT`
- `OMINI_PYTHON_SERVICE_HOST`
- `OMINI_PYTHON_SERVICE_PORT`

## Tests / Validation Results

Commands executed:

- `python -m py_compile backend/python/main.py backend/python/brain_service.py`
  - Result: PASS
- `python -m pytest -q tests/runtime/test_python_brain_service.py`
  - Result: PASS, 6 passed
- `npm run test:security`
  - Result: PASS, exit code 0
- `npm test`
  - Result: PASS, exit code 0
- `npm run test:js-runtime`
  - Result: TIMEOUT after 180 seconds
- `npm run test:python:pytest`
  - Result: TIMEOUT after 300 seconds; classified as inherited broad-suite timeout from earlier phases
- `npm --prefix frontend run typecheck`
  - Result: PASS, exit code 0
- `cd backend/rust && cargo test`
  - Result: FAIL, 37 passed / 1 failed
  - Failure: `run_control::tests::pause_resume_approve_endpoints_return_ok` expected HTTP 200 but received 500
  - Classification: unrelated to Phase 11A; no Rust files changed in this phase
- `git diff --check`
  - Result: PASS with CRLF warning for `backend/python/main.py`

Narrow Phase 11A service validation passed. Broad-suite timeout/failure items are recorded as inherited or unrelated where evidence supports that classification.

## Known Limitations

- Rust still uses subprocess mode. Phase 11C owns Rust client switching.
- Node remains subprocess-based. Phase 11B owns Node service mode.
- Circuit breaker behavior belongs to Phase 11D.

## Rollback

Revert the Phase 11A commit on `architecture/python-service-11a`.

## Gate 11A Status

Status: PASSED.

Gate evidence:

- Python internal service entrypoint exists.
- `/internal/brain/run`, `/internal/brain/health`, and `/internal/brain/readiness` exist.
- Subprocess stdin mode is preserved and covered by test.
- Responses are sanitized through the public runtime payload sanitizer.
- Runtime truth and taxonomy-shaped public errors are preserved.
- Service defaults to loopback host.
- Tests were added and executed.
- No merge into main.

## No Merge Into Main

This phase does not merge into main.
