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

## Runner Smoke Endpoint

```txt
GET /api/v1/runtime/runner-smoke
```

Purpose: verify that production can execute the same Node runner path used by chat.

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

Allowed values are bounded labels, booleans, a numeric exit code, and closed public failure strings.

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
