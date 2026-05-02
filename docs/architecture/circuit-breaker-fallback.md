# Circuit Breaker and Fallback

Status: Phase 11D implementation. Applies only to Rust Python service mode.

## Mode Behavior

Subprocess remains the default Python runtime mode.

```txt
OMNI_PYTHON_MODE=subprocess
```

Service mode is opt-in:

```txt
OMNI_PYTHON_MODE=service
```

When service mode is enabled, Rust calls:

```txt
POST /internal/brain/run
```

on the internal Python Brain Service.

## Environment Variables

Canonical:

```txt
OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS=false
OMNI_PYTHON_SERVICE_RETRY_ATTEMPTS=0
OMNI_PYTHON_SERVICE_CIRCUIT_BREAKER_ENABLED=true
OMNI_PYTHON_SERVICE_CIRCUIT_FAILURE_THRESHOLD=3
OMNI_PYTHON_SERVICE_CIRCUIT_RESET_MS=30000
```

Legacy aliases:

```txt
OMINI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS
OMINI_PYTHON_SERVICE_RETRY_ATTEMPTS
OMINI_PYTHON_SERVICE_CIRCUIT_BREAKER_ENABLED
OMINI_PYTHON_SERVICE_CIRCUIT_FAILURE_THRESHOLD
OMINI_PYTHON_SERVICE_CIRCUIT_RESET_MS
```

`OMNI_*` values take precedence over `OMINI_*`. Retry attempts are clamped to `0..=3`.

## State Machine

States:

- `CLOSED`: service calls are allowed.
- `OPEN`: service calls are skipped until reset time elapses.
- `HALF_OPEN`: one probe call is allowed after reset time.

Transitions:

- `CLOSED` failure increments the failure count.
- Failure count reaching threshold opens the circuit.
- `OPEN` transitions to `HALF_OPEN` after reset window.
- `HALF_OPEN` success closes the circuit.
- `HALF_OPEN` failure reopens the circuit.

## Retry Policy

Retries apply only to Python service calls. Subprocess fallback is never retried by the service retry policy.

## Fallback Policy

Fallback to subprocess is disabled by default.

If enabled:

```txt
OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS=true
```

Rust calls the existing subprocess path once after service failure. The response is marked degraded and fallback-aware.

## Runtime Truth Behavior

Degraded service responses include public-safe metadata:

- `fallback_triggered=true`
- `service_mode_attempted=true`
- `service_fallback_used=true|false`
- `circuit_breaker_state=CLOSED|OPEN|HALF_OPEN`
- `error_public_code`
- `internal_error_redacted=true`

Fallback responses are never reported as `FULL_COGNITIVE_RUNTIME`.

## Error Taxonomy

Service timeout:

```txt
TIMEOUT
```

Service unavailable, non-2xx, invalid HTTP response, malformed JSON, or unusable service payload:

```txt
PYTHON_ORCHESTRATOR_FAILED
```

## Security

Rust does not expose raw service URLs, request bodies, service bodies, stack traces, env values, secrets, stdout/stderr, or raw payloads.

The Python and Node internal services must remain private to loopback or an internal network.

## Rollback

Set:

```txt
OMNI_PYTHON_MODE=subprocess
```

or unset `OMNI_PYTHON_MODE` / `OMINI_PYTHON_MODE`.

Code rollback:

```bash
git revert <phase-11d-commit>
```

## Known Limitations

- Circuit breaker state is in-memory and per Rust process.
- No cross-instance circuit sharing exists.
- Service startup/lifecycle management is not implemented in this phase.
