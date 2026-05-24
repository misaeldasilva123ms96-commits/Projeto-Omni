# Omni Access Layer: Free Pilot Mock

Phase 7Q adds a mocked controlled Free chat pilot integration module. It is an
orchestration contract for tests and future design only. It does not connect
Puter to normal chat, call Puter, create network paths, make Puter the default
provider, or enable production pilot behavior.

## Module

- Location: `frontend/src/lib/puter/freeModePilotMock.ts`
- Version: `free_mode_pilot_mock_v1`
- Depends on:
  - Phase 7P Pilot Flag Contract
  - Phase 7J Free Chat Bridge Contract
  - Phase 7K Free Chat Bridge Mock

The module calls the pilot flag contract first. If the pilot contract denies,
the mock pilot denies without invoking the bridge mock. If the pilot contract
allows, the module then composes the bridge contract and mocked bridge shape.

## Flags

All related flags remain disabled by default:

- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false`

No new runtime flag is added in this phase. The module consumes explicit test
markers and must remain unreachable from normal chat unless a future phase adds
a reviewed, disabled-by-default integration.

## Behavior

The mocked pilot returns deterministic mock output only when:

- the pilot flag contract allows
- the bridge contract allows
- the mocked bridge allows
- quota and routing are allowed
- rollback is inactive
- allowlist requirements are satisfied
- consent/auth state is safe
- selected provider family is `experimental_free_provider`
- no tools, files, function-calling, long memory, or sensitive tools are present
- no provider, adapter, policy, quota, credential, billing, debug, or raw
  provider fields are present

The success output is mock-only and not a provider response.

## Deny And Rollback

The mock pilot fails closed when:

- pilot flag is false
- rollback is active
- allowlist is required but not matched
- plan mode is not Free
- quota is denied or exceeded
- routing is denied
- selected provider family is wrong
- consent/auth is pending
- bridge contract denies
- tools, files, function-calling, long memory, or sensitive tools are requested
- forbidden or sensitive public fields are present

Rollback remains a pilot-level denial and prevents bridge mock execution.

## Runtime Truth

Runtime truth exposes only public-safe fields:

- `pilot_enabled`
- `pilot_eligible`
- `pilot_denied_reason`
- `bridge_allowed`
- `bridge_denied_reason`
- `access_layer_plan_mode`
- `provider_family`
- `provider_attempted=false`
- `provider_succeeded=false`
- `provider_failed_reason`
- `mock_provider_attempted`
- `mock_provider_succeeded`
- `fallback_triggered`
- `quota_allowed`
- `quota_exceeded`
- `routing_allowed`
- `consent_state`
- `selected_adapter_id`
- `boundary_version`
- `snapshot_version`
- `sanitized_output_present`
- `raw_provider_payload_exposed=false`

Real provider fields remain false. Mock status is separate so future reviews can
distinguish deterministic mock behavior from real provider behavior.

## Non-Goals

This phase does not add:

- real Puter calls
- `puter.ai.chat` usage
- normal chat integration
- network calls
- dev-real bridge invocation
- manual harness invocation
- default Puter provider behavior
- BYOK storage
- billing
- Pro behavior
- tools
- files
- function-calling
- long memory

## Future Path

Next phase:

- Phase 7R: Internal-only real pilot behind flags

That future phase should remain disabled by default, compose the same pilot and
bridge contracts, and require a separate review before any real provider path is
considered.
