# PHASE 11C - RUST INTERNAL CLIENT

Date: 2026-05-01

Base branch: architecture/node-service-11b

Base commit: 485b799481fc76203e24371e09f687208d865d8d

Working branch: architecture/rust-client-11c

## Scope

Phase 11C adds a Rust internal HTTP client path for the Python Brain Service behind an explicit mode flag. Subprocess mode remains the default. The public `/chat` contract is unchanged.

## Files Changed

- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs`
- `backend/rust/src/run_control.rs`
- `docs/architecture/rust-internal-python-client.md`
- `docs/audit/PHASE_11C_RUST_CLIENT.md`

## Rust Client Paths

- Existing subprocess path: `call_python(...)` -> `backend/python/main.py`
- New service path: `call_python(...)` -> `call_python_service(...)` -> `POST /internal/brain/run`

## Mode Selection

- `OMNI_PYTHON_MODE=subprocess|service`
- `OMINI_PYTHON_MODE=subprocess|service`
- default: `subprocess`
- invalid mode: safely falls back to `subprocess`

## Service Endpoint

```txt
POST http://{OMNI_PYTHON_SERVICE_HOST}:{OMNI_PYTHON_SERVICE_PORT}/internal/brain/run
```

Defaults:

- host: `127.0.0.1`
- port: `7010`
- timeout: `30000` ms

## Subprocess Compatibility

Subprocess mode remains the default and existing subprocess tests are preserved.

## Response Contract

Rust parses the same public-safe Python envelope used by subprocess mode and preserves:

- `response`
- `conversation_id`
- `cognitive_runtime_inspection`
- `providers`
- public error taxonomy fields
- runtime truth fields inside public inspection

## Error / Taxonomy Behavior

- service timeout -> `TIMEOUT`
- service unavailable/non-success -> `PYTHON_ORCHESTRATOR_FAILED`
- service failures return `SAFE_FALLBACK`, not `FULL_COGNITIVE_RUNTIME`
- raw service errors are not exposed

## Security Posture

- Python service remains internal-only.
- Service mode is opt-in.
- No raw service error, env, secret, stack, stdout/stderr, request body, or raw payload is returned.
- Phase 5 validation and rate limiting still run before runtime invocation.

## Tests / Validation Results

Commands executed:

- `cargo test python_runtime_mode_env_aliases_and_precedence_work -- --nocapture`
  - Result: PASS
- `cargo test service_mode_sends_expected_json_and_preserves_public_envelope -- --nocapture`
  - Result: PASS
- `cargo test service_mode_unavailable_and_timeout_are_public_safe -- --nocapture`
  - Result: PASS
- `cargo test chat_route_rejects_empty_message_before_runtime -- --nocapture`
  - Result: PASS
- `cargo test call_python_returns_successful_response -- --nocapture`
  - Result: PASS
- `python -m py_compile backend/python/brain_service.py backend/python/main.py`
  - Result: PASS
- `git diff --check`
  - Result: PASS with CRLF warnings for touched Rust files
- `npm run test:security`
  - Result: PASS, exit code 0
- `npm test`
  - Result: PASS, exit code 0
- `npm run test:js-runtime`
  - Result: PASS, exit code 0
- `npm run test:python:pytest`
  - Result: PASS, exit code 0
- `npm --prefix frontend run typecheck`
  - Result: PASS, exit code 0
- `cd backend/rust && cargo test`
  - First broad run: transient failure in `run_control::tests::list_and_get_endpoints_return_structured_json`
  - Follow-up isolated run: PASS
  - Final broad rerun: PASS, 41 passed

Narrow Phase 11C validation passed. Final broad validation passed after rerunning a transient `run_control` test.

## Known Limitations

- Phase 11C does not implement retry budget or circuit breaker.
- Phase 11C does not automatically start the Python service.
- Service mode requires the Python service to be reachable.

## Rollback

Unset `OMNI_PYTHON_MODE` / `OMINI_PYTHON_MODE` or set `OMNI_PYTHON_MODE=subprocess`.

Code rollback: revert the Phase 11C commit on `architecture/rust-client-11c`.

## Gate 11C Status

Status: PASSED.

Gate evidence:

- Rust supports `subprocess|service` mode for the Python runtime.
- Subprocess remains default.
- Service mode calls `POST /internal/brain/run`.
- Public `/chat` response shape remains compatible.
- Runtime truth and public error taxonomy fields are preserved.
- Service failures return public-safe fallback responses.
- Phase 5 rejected input still returns before runtime invocation.
- Tests were added/updated and executed.
- No merge into main.

## No Merge Into Main

This phase does not merge into main.
