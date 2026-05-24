# Omni Access Layer: Free Chat Bridge Contract

Phase 7J adds a pure frontend contract module for deciding whether a future
Free-mode chat request is eligible for the Puter path.

This phase does not connect Puter to the main chat flow, does not call Puter,
does not create a network path, and does not make Puter the default provider.

## Module

- Location: `frontend/src/lib/puter/freeModeChatBridgeContract.ts`
- Version: `free_mode_chat_bridge_contract_v1`
- Future bridge flag: `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false`

The module returns a deterministic public-safe decision. It is contract-only:
the provider is never attempted, provider success is always false, and
`sanitized_output` remains `null`.

## Required Gates

The contract allows the future bridge only when all gates pass:

- plan mode is Free
- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE` is enabled
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE` is enabled
- AccessSnapshotBoundary-style state is exact, ok, and not denied
- quota is allowed and not exceeded
- routing is allowed
- selected provider family is `experimental_free_provider`
- browser runtime marker is present
- Puter runtime marker is present
- no files, tools, function-calling, long memory, or sensitive tools are requested
- no public provider, adapter, policy, quota, credential, billing, or debug override fields are present

Any failed gate returns a denied decision before provider execution could occur.

## Fail-Closed Reasons

The contract uses stable public reasons such as:

- `not_free_mode`
- `feature_disabled`
- `chat_bridge_disabled`
- `invalid_access_snapshot`
- `quota_exceeded`
- `routing_denied`
- `provider_family_not_allowed`
- `unsupported_capability`
- `unsafe_request_options`
- `non_browser_runtime`
- `puter_runtime_unavailable`
- `invalid_token_estimate`
- `bridge_denied`

Missing Puter runtime is a safe denied/fallback decision. Production chat must
not implicitly load the Puter runtime; the dev-only `/dev/puter` loader remains
the manual runtime validation path.

## Runtime Truth

The decision exposes only public-safe runtime truth:

- access-layer plan mode
- selected public provider family
- provider attempted: false
- provider succeeded: false
- provider failed reason
- fallback state
- quota state
- routing state
- selected adapter id from the safe access snapshot
- boundary and snapshot versions
- sanitized output: null

No raw provider response, raw request, stack trace, private configuration,
environment value, credential material, billing configuration, or debug payload
is exposed.

## Non-Goals

This phase does not implement:

- production chat bridge execution
- real Puter calls
- hidden provider execution
- default Puter routing
- BYOK storage
- billing
- tools
- files
- function-calling
- long memory
- chat UI changes

## Future Path

- Phase 7K: mocked chat bridge integration behind flags
- Phase 7L: dev-only real bridge behind flags
- Phase 7M: controlled pilot, still not default
