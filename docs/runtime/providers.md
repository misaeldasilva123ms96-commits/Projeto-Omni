# Runtime Providers

This document describes the provider registry and runtime fallback behavior as of 2026-05-21.

## Provider Table

| Provider | Type | Config gate | Model env | Default model | Status |
| --- | --- | --- | --- | --- | --- |
| Groq | remote | `GROQ_API_KEY` | `GROQ_MODEL` | `llama-3.3-70b-versatile` | implemented |
| OpenRouter | remote | `OPENROUTER_API_KEY` | `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | implemented |
| OpenAI | remote | `OPENAI_API_KEY` | `OPENAI_MODEL` | `gpt-4o-mini` | implemented |
| Anthropic | remote | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | implemented |
| Gemini | remote | `GEMINI_API_KEY` | `GEMINI_MODEL` | `gemini-2.5-flash` | implemented |
| Ollama | local | `OLLAMA_URL` | `OLLAMA_MODEL` | `llama3` | implemented, local config gated |
| LM Studio | local | `LMSTUDIO_URL` | `LMSTUDIO_MODEL` | `local-model` | implemented, local config gated |
| DeepSeek | remote metadata | `DEEPSEEK_API_KEY` | `DEEPSEEK_MODEL` | `deepseek-chat` | registered, unsupported |
| local-heuristic | embedded | none | none | `native-heuristic` | fallback |

Optional local API keys:

- `OLLAMA_API_KEY`
- `LMSTUDIO_API_KEY`

These are private execution values when configured. They must not appear in public diagnostics.

## Fallback Order

Normal non-BYOK fallback order:

```txt
groq -> openrouter -> openai -> anthropic -> gemini -> ollama -> lmstudio -> local-heuristic
```

Unsupported or unrecognized provider preferences do not stop normal routing. In normal mode, the router falls back to the first executable provider in the chain.

## Local Providers

Local provider adapters are executable code, but the providers are not available by default. Availability requires their URL configuration. This avoids accidental localhost calls, latency, and confusing degraded behavior on machines without a local model server.

- Ollama requires `OLLAMA_URL`.
- LM Studio requires `LMSTUDIO_URL`.
- The optional local API key envs are used internally only when present.

## Public Diagnostics

Public diagnostics expose:

- provider id
- `configured`: required credential or URL configuration exists
- `executable`: an adapter is implemented, independently of configuration
- `available`: legacy compatibility signal requiring both configured and executable
- `reachable`: the last active test reached the provider (`null` when untested)
- `healthy`: the last active test succeeded (`null` when untested)
- health validity, timestamp, latency, cache status, and circuit state
- adapter implementation boolean
- execution status string
- env variable names
- fallback metadata

Public diagnostics must not expose:

- API key values
- optional local key values
- model values
- local URL values
- raw env dumps
- headers
- raw requests or responses
- provider status bodies
- stack traces

## Active Health Tests

Provider listing never pings remote services. An authenticated operator starts an active test explicitly from the BYOK settings surface. The bounded result is cached per user and provider under `.logs/provider-health/`; user ids are hashed and the cache never stores credentials, URLs, headers, response bodies, or exception details.

Health records expire after five minutes by default. Three consecutive failed tests open a one-minute circuit by default, so repeated manual requests reuse the safe cached failure until the next probe window. Saving, updating, or deleting a credential invalidates its previous health record.

Configuration knobs:

- `OMNI_PROVIDER_HEALTH_TTL_MS`
- `OMNI_PROVIDER_HEALTH_FAILURE_THRESHOLD`
- `OMNI_PROVIDER_HEALTH_CIRCUIT_OPEN_MS`
- `OMNI_PROVIDER_HEALTH_CACHE_DIR`

These controls affect explicit health tests and cached diagnostics only. Routing does not add a remote ping to each request.

## DeepSeek

DeepSeek remains registered for metadata and env propagation parity, but it is not executable. BYOK execution rejects DeepSeek, and normal routing treats it as unsupported.
