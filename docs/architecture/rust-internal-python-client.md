# Rust Internal Python Client

Status: Phase 11C implementation. Rust can select the Python subprocess runner or the Python internal brain service, but subprocess mode remains the default.

## Purpose

The Rust API remains the public boundary for `/chat`. Phase 11C adds an internal HTTP client path so Rust can call the Python Brain Service introduced in Phase 11A when explicitly enabled.

## Mode Selection

Default:

```txt
OMNI_PYTHON_MODE=subprocess
```

Supported values:

- `subprocess`
- `service`

Canonical env var:

```txt
OMNI_PYTHON_MODE=subprocess|service
```

Legacy alias:

```txt
OMINI_PYTHON_MODE=subprocess|service
```

`OMNI_*` values take precedence over `OMINI_*`. Invalid values safely fall back to `subprocess`.

## Service Configuration

Canonical:

```txt
OMNI_PYTHON_SERVICE_HOST=127.0.0.1
OMNI_PYTHON_SERVICE_PORT=7010
OMNI_PYTHON_SERVICE_TIMEOUT_MS=30000
```

Legacy aliases:

```txt
OMINI_PYTHON_SERVICE_HOST
OMINI_PYTHON_SERVICE_PORT
OMINI_PYTHON_SERVICE_TIMEOUT_MS
```

## Service Endpoint

Rust service mode posts to:

```txt
POST http://{host}:{port}/internal/brain/run
```

Payload:

```json
{
  "message": "...",
  "session_id": "optional",
  "request_id": "optional",
  "metadata": {}
}
```

## Subprocess Compatibility

Subprocess mode remains unchanged and default. Rust continues to call `backend/python/main.py` with JSON over stdin unless `OMNI_PYTHON_MODE=service` is set.

No public `/chat` response fields were removed or renamed.

## Response Contract

Rust parses the same public-safe envelope used by the subprocess path:

- `response`
- `conversation_id`
- `cognitive_runtime_inspection`
- `providers`
- `stop_reason`
- `error`
- top-level public error taxonomy fields, when returned by the Python service

Runtime truth and public cognitive inspection fields are preserved from the Python service response.

## Error Behavior

Service failures return controlled public-safe fallback responses:

- service timeout: `TIMEOUT`
- service unavailable/non-success: `PYTHON_ORCHESTRATOR_FAILED`

Service failure is never labeled `FULL_COGNITIVE_RUNTIME`.

Phase 11C does not implement retry budget or circuit breaker behavior. That remains Phase 11D.

## Security Notes

- Python service must remain internal-only.
- Default host is loopback.
- Rust does not expose raw service errors, stack traces, env, secrets, stdout/stderr, request bodies, or raw payloads.
- Input validation and rate limiting from Phase 5 run before either subprocess or service invocation.

## Rollback

Set:

```txt
OMNI_PYTHON_MODE=subprocess
```

or unset `OMNI_PYTHON_MODE` and `OMINI_PYTHON_MODE`.

Code rollback:

```bash
git revert <phase-11c-commit>
```

## Known Limitations

- Service mode requires the Python Brain Service to already be running.
- No automatic fallback from service to subprocess is added in Phase 11C.
- No circuit breaker or retry budget is implemented until Phase 11D.
