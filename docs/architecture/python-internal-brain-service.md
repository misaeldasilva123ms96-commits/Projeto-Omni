# Python Internal Brain Service

Status: Phase 11A implementation. The existing stdin/subprocess Python entrypoint remains supported and Rust does not use service mode yet.

## Purpose

The Python internal brain service exposes the existing brain runtime through local-only HTTP endpoints so future phases can migrate away from subprocess-per-request execution without changing the public Rust `/chat` API.

## Internal-Only Warning

This service is not a public API. It must bind to loopback or a private container network only. Do not expose it directly through Render, Cloudflare, public ingress, browser clients, or frontend code.

Default bind:

```txt
127.0.0.1:7010
```

## Entrypoint

```bash
python backend/python/brain_service.py
```

The module uses Python standard library `http.server`; no new runtime dependency is required.

## Environment Variables

Canonical:

```txt
OMNI_PYTHON_SERVICE_HOST=127.0.0.1
OMNI_PYTHON_SERVICE_PORT=7010
```

Legacy aliases:

```txt
OMINI_PYTHON_SERVICE_HOST
OMINI_PYTHON_SERVICE_PORT
```

`OMNI_*` values take precedence over `OMINI_*` aliases.

## Endpoints

### GET /internal/brain/health

Response:

```json
{
  "ok": true,
  "service": "python-brain",
  "mode": "service"
}
```

### GET /internal/brain/readiness

Response:

```json
{
  "ok": true,
  "service": "python-brain",
  "checks": {
    "orchestrator_importable": true,
    "public_payload_sanitizer": true,
    "stdin_subprocess_entrypoint_preserved": true
  }
}
```

Readiness exposes booleans only. It must not expose env, paths, secrets, stack traces, raw provider state, or runtime payloads.

### POST /internal/brain/run

Input:

```json
{
  "message": "string",
  "session_id": "optional string",
  "request_id": "optional string",
  "metadata": {}
}
```

Output:

The output is the same public-safe envelope produced by the current `backend/python/main.py` stdout path where possible. It preserves:

- `response`
- `runtime_mode`
- `runtime_reason`
- `cognitive_runtime_inspection`
- runtime truth public fields
- `error_public_code`
- `error_public_message`
- `severity`
- `retryable`
- `internal_error_redacted`

## Error Behavior

Malformed requests return Phase 8 taxonomy-shaped public errors:

- invalid content type: `INVALID_CONTENT_TYPE`
- invalid JSON: `INVALID_JSON`
- invalid body/message: `INPUT_VALIDATION_FAILED`
- oversized service body: `PAYLOAD_TOO_LARGE`
- orchestrator exception: `PYTHON_ORCHESTRATOR_FAILED`

No response should contain raw exceptions, env, stack traces, stdout, stderr, command arguments, provider raw responses, tool raw results, memory content, tokens, or filesystem paths.

## Subprocess Compatibility

`backend/python/main.py` still supports stdin/stdout mode. Phase 11A only extracts a reusable `build_public_chat_payload(...)` function and keeps `main()` JSON-only stdout behavior intact.

Rust still invokes Python through subprocess. Rust service-mode client work belongs to Phase 11C.

## Rollback

Rollback is safe:

```bash
git revert <phase-11a-commit>
```

No public API, data migration, or Rust switch is involved in this phase.

## Known Limitations

- This service uses the standard-library HTTP server and is intended for internal migration testing.
- Rust does not call this service yet.
- Node remains subprocess-based until Phase 11B.
- Circuit breaker/fallback service client behavior belongs to Phase 11C/11D.
