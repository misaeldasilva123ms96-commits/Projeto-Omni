# Omni Access Layer: Free Chat Bridge Mock

Phase 7K adds a mocked Free chat bridge module for validating orchestration
shape behind disabled-by-default flags. It is not a production chat
integration.

## Scope

- Module: `frontend/src/lib/puter/freeModeChatBridgeMock.ts`
- Contract dependency: `frontend/src/lib/puter/freeModeChatBridgeContract.ts`
- Mock flag: `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK=false`

All related flags remain disabled by default:

- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK=false`

## Behavior

The mock module calls the Phase 7J contract decision and returns deterministic
mock output only when the contract allows and the mock flag is enabled.

It does not:

- call Puter
- call `puter.ai.chat`
- call network APIs
- import the manual harness as an execution path
- connect to the main chat flow
- make Puter the default provider
- enable tools, files, function-calling, long memory, BYOK, billing, or Pro behavior

Denied contract decisions remain denied in the mock result.

## Runtime Truth Convention

The mock result exposes a public-safe result shape and reuses the contract
runtime truth. Real provider fields remain false:

- `provider_attempted=false`
- `provider_succeeded=false`
- `runtime_truth.sanitized_output=null`

The top-level `mock_succeeded` field may be true only for deterministic mock
success. The top-level `sanitized_output` is mock-only and contains no provider
payload.

## Safety

The mock path rejects unsafe request options and capabilities through the Phase
7J contract. It also rejects mock prompt input rather than echoing caller text.

Public output must not contain raw provider payloads, raw requests, stack
traces, credentials, API keys, access tokens, environment values, provider
config, private endpoints, billing data, or debug data.

## Future Path

Next phase:

- Phase 7L: Dev-only Real Free Chat Bridge behind flags

That future phase should remain gated, reviewed, and separate from default
production chat behavior until explicitly promoted.
