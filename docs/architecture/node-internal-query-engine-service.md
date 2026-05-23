# Node Internal QueryEngine Service

Status: Phase 11B implementation. The existing Node CLI/subprocess runner remains supported and Python/Rust do not use service mode yet.

## Purpose

The Node internal QueryEngine service exposes the current QueryEngine runner through local-only HTTP endpoints. This prepares the runtime for future persistent-service migration without changing the public Rust API or Python orchestration behavior.

## Internal-Only Warning

This service is not a public API. It must bind to loopback or a private container network only. Do not expose it directly through Render, Cloudflare, public ingress, browser clients, or frontend code.

Default bind:

```txt
127.0.0.1:7020
```

## Entrypoint

```bash
npm run start:node-service
```

Equivalent direct command:

```bash
node js-runner/queryEngineService.js
```

The service uses the Node built-in `http` module. No Express/Fastify dependency is required.

## Environment Variables

Canonical:

```txt
OMNI_NODE_SERVICE_HOST=127.0.0.1
OMNI_NODE_SERVICE_PORT=7020
```

Legacy aliases:

```txt
OMINI_NODE_SERVICE_HOST
OMINI_NODE_SERVICE_PORT
```

`OMNI_*` values take precedence over `OMINI_*` aliases.

## Endpoints

### GET /internal/query-engine/health

Response:

```json
{
  "ok": true,
  "service": "node-query-engine",
  "mode": "service"
}
```

### GET /internal/query-engine/readiness

Response:

```json
{
  "ok": true,
  "service": "node-query-engine",
  "checks": {
    "query_engine_runner_importable": true,
    "public_sanitizer": true,
    "cli_subprocess_entrypoint_preserved": true
  }
}
```

Readiness exposes booleans only. It must not expose environment values, paths, secrets, stack traces, raw provider state, raw tool state, or runtime payloads.

### POST /internal/query-engine/run

Input:

```json
{
  "message": "string",
  "session_id": "optional string",
  "request_id": "optional string",
  "metadata": {},
  "runtime_context": {}
}
```

Output:

The output follows the same public-safe JSON shape produced by the current `js-runner/queryEngineRunner.js` path where possible. It preserves:

- `response`
- `runtime_truth`
- governance/tool public status fields
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
- QueryEngine exception: `NODE_RUNNER_FAILED`

No response should contain raw exceptions, env, stack traces, stdout, stderr, command arguments, provider raw responses, tool raw results, memory content, tokens, or filesystem paths.

## CLI/Subprocess Compatibility

`js-runner/queryEngineRunner.js` remains the CLI/subprocess runner. Phase 11B only adds a new service entrypoint and does not switch Python or Rust to service mode.

Python service-mode integration belongs to later phases. Rust internal client switching belongs to Phase 11C.

## Rollback

Rollback is safe:

```bash
git revert <phase-11b-commit>
```

No public API, data migration, Python switch, or Rust switch is involved in this phase.

## Known Limitations

- Python does not call this service yet.
- Rust does not call this service yet.
- Circuit breaker/fallback service client behavior belongs to Phase 11C/11D.
- The service is intended for internal migration testing, not public exposure.
