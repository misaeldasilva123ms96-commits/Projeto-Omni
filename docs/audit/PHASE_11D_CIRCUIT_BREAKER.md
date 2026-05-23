# PHASE 11D - CIRCUIT BREAKER / FALLBACK

Date: 2026-05-02

Base branch: architecture/rust-client-11c

Base commit: e4e879666cebd923c3624e6d32c415f4314eba5e

Working branch: architecture/circuit-breaker-11d

## Scope

Phase 11D adds bounded retry, circuit breaker state, and optional subprocess fallback around the Rust Python service path. Subprocess mode remains the default and public `/chat` response shape remains compatible.

## Files Changed

- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs`
- `backend/rust/src/run_control.rs`
- `docs/architecture/circuit-breaker-fallback.md`
- `docs/audit/PHASE_11D_CIRCUIT_BREAKER.md`

## Circuit Breaker Paths

- `call_python(...)`
- `call_python_service(...)`
- Python service execution policy around `post_python_service(...)`

## State Machine

- `CLOSED`
- `OPEN`
- `HALF_OPEN`

## Retry Policy

Service retries are bounded and apply only to Python service calls. Retry attempts are clamped to `0..=3`.

## Fallback Policy

Subprocess fallback is disabled by default and enabled only when:

```txt
OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS=true
```

## Runtime Truth Behavior

Degraded service responses include public-safe metadata:

- `fallback_triggered`
- `service_mode_attempted`
- `service_fallback_used`
- `circuit_breaker_state`
- `error_public_code`
- `internal_error_redacted`

Fallback responses are never labeled `FULL_COGNITIVE_RUNTIME`.

## Error / Taxonomy Behavior

- timeout -> `TIMEOUT`
- unavailable / non-2xx / malformed / unusable service response -> `PYTHON_ORCHESTRATOR_FAILED`

## Security Posture

No raw service errors, env, secrets, stack, stdout/stderr, request body, service body, or raw payloads are exposed.

## Tests / Validation Results

Commands executed:

- `cargo test service_retry_is_bounded_and_can_recover -- --nocapture`
  - Result: PASS
- `cargo test service_failure_optionally_falls_back_to_subprocess -- --nocapture`
  - Result: PASS
- `cargo test service_failure_without_fallback_does_not_invoke_subprocess -- --nocapture`
  - Result: PASS
- `cargo test circuit_opens_skips_service_and_half_open_transitions -- --nocapture`
  - Result: PASS
- `cargo test half_open_failure_reopens_circuit -- --nocapture`
  - Result: PASS
- `cd backend/rust && cargo test`
  - Result: PASS, 46 passed
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
- `python -m py_compile backend/python/brain_service.py backend/python/main.py`
  - Result: PASS
- `git diff --check`
  - Result: PASS with CRLF warnings for touched Rust files

Narrow Phase 11D validation passed. Broad validation passed.

## Known Limitations

- Circuit breaker state is process-local and in-memory.
- No service lifecycle management is added.
- No cross-instance breaker coordination exists.

## Rollback

Set `OMNI_PYTHON_MODE=subprocess` or revert the Phase 11D commit.

## Gate 11D Status

Status: PASSED.

Gate evidence:

- Circuit breaker exists for Python service mode.
- Retry policy is bounded and clamped.
- Optional subprocess fallback works behind env flag.
- Service failures are public-safe.
- Runtime truth marks degraded/fallback responses correctly.
- Subprocess mode remains default.
- Phase 5 rejected input still returns before runtime invocation.
- Tests were added/updated and executed.
- No merge into main.

## No Merge Into Main

This phase does not merge into main.
