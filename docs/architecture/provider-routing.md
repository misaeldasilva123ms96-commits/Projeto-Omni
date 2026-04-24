# Provider Routing

## Goal

Describe how Omni discovers provider configuration, selects a provider, records provider provenance, and exposes provider diagnostics without leaking secrets.

## Environment variables

The provider layer currently depends on these logical inputs:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `DEEPSEEK_API_KEY`
- `OLLAMA_URL`
- optional model overrides such as `OPENAI_MODEL`, `ANTHROPIC_MODEL`, `GROQ_MODEL`, `GEMINI_MODEL`, `DEEPSEEK_MODEL`, `OLLAMA_MODEL`
- `OMNI_AVAILABLE_PROVIDERS`
- `OMNI_POLICY_HINT_JSON`

Python validates provider credentials through:

- [provider_registry.py](../../backend/python/config/provider_registry.py)
- [secrets_manager.py](../../backend/python/config/secrets_manager.py)

Node receives only the validated environment subset through:

- [js_runtime_adapter.py](../../backend/python/brain/runtime/js_runtime_adapter.py)

## Discovery

Python-side discovery:

1. `config.secrets_manager.get_secret(...)` validates that a provider secret exists and is not a placeholder.
2. `config.provider_registry.get_available_providers()` returns logical provider ids that passed validation.
3. `JSRuntimeAdapter.build_env()` forwards those validated credentials and also exports `OMNI_AVAILABLE_PROVIDERS`.

Node-side discovery:

1. [providerRouter.js](../../platform/providers/providerRouter.js) checks the forwarded environment.
2. It builds a provider list with model defaults and priority order.
3. It always appends `local-heuristic` as an embedded fallback provider.

## Selection

Node-side selection currently happens in:

- [queryEngineAuthority.js](../../core/brain/queryEngineAuthority.js)

Flow:

1. Python may produce a policy hint (`OMNI_POLICY_HINT_JSON`) with baseline and recommended provider.
2. Node reads that hint via [executionProvenance.js](../../core/brain/executionProvenance.js).
3. `chooseProvider(...)` selects a provider based on:
   - policy-preferred provider when present and available
   - prompt complexity
   - configured provider order
   - fallback to `local-heuristic`

## Execution

Important distinction:

- provider selection is not the same as provider-backed execution
- bridge execution and local heuristic responses may carry provider selection context without a remote LLM call

Current practical cases:

- `matcher_shortcut`
  - provider is `local-heuristic`
  - attempted and succeeded locally
- `local_direct_response`
  - provider context may exist, but there may be no remote provider attempt
- `bridge_execution_request`
  - provider was selected for the execution graph, but the remote provider may not have executed yet
- `true_action_execution`
  - the execution path is real, but provider-backed success still depends on downstream executor behavior

## Fallback behavior

Provider fallback currently means one of these:

- policy recommended provider was unavailable and another provider was selected
- no remote provider was available and the system relied on `local-heuristic`
- provider-backed execution failed and the failure is recorded in provenance/inspection

This is exposed through:

- `provider_diagnostics`
- `provider_failed`
- `failure_class`
- `failure_reason`
- `provider_fallback_occurred`
- `no_provider_available`

## Diagnostics emission

Provider diagnostics are emitted in these layers:

- Node selection/provenance:
  - [providerRouter.js](../../platform/providers/providerRouter.js)
  - [executionProvenance.js](../../core/brain/executionProvenance.js)
  - [queryEngineAuthority.js](../../core/brain/queryEngineAuthority.js)
- Python provenance normalization:
  - [provenance_models.py](../../backend/python/brain/runtime/provenance/provenance_models.py)
  - [provenance_parser.py](../../backend/python/brain/runtime/provenance/provenance_parser.py)
- Python public response shaping:
  - [main.py](../../backend/python/main.py)
- Frontend debug surface:
  - [RuntimeDebugSection.tsx](../../frontend/src/components/status/RuntimeDebugSection.tsx)

## Public diagnostic shape

Each provider diagnostic row is additive and safe for public debugging:

```json
{
  "provider": "openai",
  "configured": true,
  "available": true,
  "selected": true,
  "attempted": false,
  "succeeded": false,
  "failed": false,
  "failure_class": null,
  "failure_reason": null,
  "latency_ms": null
}
```

Interpretation:

- `configured` / `available` currently mean configuration-level availability, not network reachability
- `attempted` means a provider-backed attempt is evidenced for the turn
- `failed` plus `failure_class` distinguishes provider-layer failure from bridge failure

## Contributor notes

- Treat missing provider keys as configuration state, not as a bridge failure.
- Treat `NODE_BRIDGE_*` and `PYTHON_BRIDGE_*` as transport problems, not provider problems.
- When debugging provider behavior, compare:
  - `providers`
  - `provider_diagnostics`
  - `provider_actual`
  - `provider_failed`
  - `failure_class`
  - `execution_provenance`
