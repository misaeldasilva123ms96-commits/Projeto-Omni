# Session BYOK

BYOK means bring your own key. Omni currently supports session-only BYOK at the Rust -> Python -> Node bridge boundary.

## Current Scope

Implemented:

- typed Rust request boundary
- provider allowlist and payload bounds
- private Python bridge extraction
- request-scoped Node env overlay
- fail-closed BYOK execution policy
- cross-language tests for forwarding, isolation, and redaction

Not implemented:

- persistent credential storage
- encrypted user credential vault
- tenant/account credential management
- frontend key-entry UI
- billing, quotas, or hosted BYOK governance
- local URL BYOK overrides

## Request Shape

```json
{
  "message": "Olá",
  "provider_preference": "openai",
  "session_provider_credentials": {
    "openai": {
      "api_key": "<session-only-api-key>",
      "model": "optional-model"
    }
  }
}
```

Allowed BYOK providers:

- `groq`
- `openrouter`
- `openai`
- `anthropic`
- `gemini`
- `ollama`
- `lmstudio`

DeepSeek is rejected.

## Fail-Closed Policy

When `session_provider_credentials` is non-empty:

1. BYOK session mode is active.
2. `provider_preference` is required.
3. `provider_preference` must match a credential entry.
4. Only the selected provider receives the request-scoped credential overlay.
5. The selected session credential overrides the system env credential for that provider only for the current request.
6. If the selected BYOK provider fails, Omni does not fall back to system owner keys or another provider.

Provider preference without `session_provider_credentials` keeps normal system-provider behavior.

## Privacy Rules

Session API keys must not enter:

- public response payloads
- `provider_diagnostics`
- `provider_diagnostics_snapshot`
- runtime truth
- cognitive runtime inspection
- provenance
- debug payloads
- logs
- learning artifacts
- transcript/history stores
- error bodies

Model names are diagnostic metadata, not secrets, but they should appear only in approved model-related fields and not in raw request/credential surfaces.

## Local Provider Limits

For Ollama and LM Studio, P5C only allows request-scoped model/key overlay. It does not accept arbitrary local URLs from the request. Local providers still require `OLLAMA_URL` or `LMSTUDIO_URL` from system configuration.
