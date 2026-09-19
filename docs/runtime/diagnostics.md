# Runtime Diagnostics

Omni exposes public-safe diagnostics so operators and contributors can distinguish transport success, provider execution, fallback, and degraded runtime behavior without exposing secrets.

## Chat Response Diagnostics

The public chat payload may include:

- `runtime_mode`
- `runtime_reason`
- `fallback_triggered`
- `failure_class`
- `provider_actual`
- `provider_failed`
- `provider_diagnostics`
- `provider_diagnostics_snapshot`
- `cognitive_runtime_inspection`

`provider_diagnostics` remains the legacy array for frontend, provenance, and inspector compatibility.

`provider_diagnostics_snapshot` is the newer object with:

- `providers`
- `fallback_chain`
- `active_provider`
- `fallback_triggered`
- `fallback_reason`

The snapshot provider table includes Groq, OpenRouter, OpenAI, Anthropic, Gemini, Ollama, LM Studio, and DeepSeek.

Provider capability and health are separate signals:

- `configured`: required credential or URL configuration exists
- `executable`: runtime adapter code exists
- `available`: legacy combined configuration + adapter signal
- `reachable` / `healthy`: result of the last explicit active test, or `null` when untested
- `health_valid`, `last_checked_at`, `valid_until`, `latency_ms`, `cache_status`, and `circuit_state`: freshness and bounded retry evidence

Listing diagnostics reads cached metadata only. It never contacts providers. Active checks occur only through the authenticated settings test action, and stale health is never presented as current.

## Public Health Endpoint

`GET /health` is a shallow, public-safe snapshot. It does not start a subprocess.
Python and Node expose `observable`, `last_status`, `error_code`, and
`last_checked_ms`. Python states are `not_checked`, `ready`, `mock`, `timeout`,
`unavailable`, or `degraded`; Node states remain `observable` or `unavailable`.
Python errors are classified as `TIMEOUT` or `PYTHON_ORCHESTRATOR_FAILED`, or
`null` when no failure is known. No arbitrary internal exception text is returned.

`configured_bin`, `entry`, `entry_exists`, and `last_error` have been removed from
the public contract. There are no filesystem paths, raw stderr/stdout, environment
values, credentials, or process arguments. Internal dependency errors remain
internal; clients must use the semantic status and public error code.

## Runner Smoke Endpoint

```txt
GET /api/v1/runtime/runner-smoke
```

Purpose: verify that production can execute the Node runner path used by chat,
with a minimal diagnostic environment and no real provider credentials. This is
not a provider availability or authentication test.

Resource policy, per Rust process:

- Always limited to **6 requests per 60 seconds per effective client IP**,
  including cache hits. This is separate from chat's budget and cannot be disabled
  by `OMNI_RATE_LIMIT_ENABLED`. It reuses the same bounded limiter implementation
  and `OMNI_TRUST_PROXY_*` identity policy; spoofed forwarding headers do not
  create new clients. The smoke client table is capped at 10,000 entries (or the
  configured chat table cap if smaller), with rejection when full.
- At most **one execution in flight**, shared by all clients. Concurrent cache
  misses receive HTTP 503 with `busy`; they do not queue subprocesses. Missing
  TCP identity fails closed. Exhausted client budgets receive HTTP 429.
- One sanitized result (success or failure) is cached for **10 seconds after
  completion**. A request after expiry can run a fresh check. Caching errors also
  prevents amplification during an outage.
- The end-to-end Rust diagnostic deadline stays at **8 seconds**. A disconnected
  caller does not release the single-flight slot early: the bounded worker
  completes and caches its result. No automatic retries are performed.
- Python starts with a minimal OS execution environment, not the server's provider,
  BYOK, service-token, or Supabase environment. The diagnostic entrypoint does not
  load the repository `.env`. The existing Node diagnostic scrub remains in place.

Use an edge/global limit as well when deploying multiple Rust replicas. These
process-local limits do not constitute fleet-wide admission control or an OS
process-tree sandbox.

The endpoint runs a fixed safe prompt:

```txt
responda apenas OK
```

It returns only:

```json
{
  "api_version": "1",
  "status": "ok",
  "selected_runtime": "node",
  "cwd_label": "app",
  "runner_exists": true,
  "adapter_exists": true,
  "fusion_brain_exists": true,
  "contract_exists": true,
  "runner_exit_code": 0,
  "stdout_json_valid": true,
  "result_degraded": false,
  "public_failure_class": null,
  "public_summary": "runner_smoke_ok"
}
```

Allowed values are bounded labels, booleans, a numeric exit code, and closed public
failure strings. Summary text is derived from the allowed status/failure class,
never copied from subprocess text. HTTP 503 responses also use this safe envelope.

## Redaction Contract

Public diagnostics must never expose:

- API key values
- bearer tokens
- `Authorization` header values
- `x-api-key` header values
- key-bearing Gemini URLs
- local URL values
- raw env values
- raw stdout or stderr
- raw request or response bodies
- provider error bodies
- stack traces or tracebacks
- `session_provider_credentials`

## Interpreting Results

`/health` and `/api/v1/status` are shallow liveness/status endpoints. They can prove that Rust/Python/Node binaries are configured or observable, but they do not prove that the chat runner can execute.

Use `/api/v1/runtime/runner-smoke` when a deployment returns `degraded:node_runner` while `/health` still reports Node as observable.
