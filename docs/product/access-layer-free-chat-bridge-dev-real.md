# Omni Access Layer: Free Chat Bridge Dev Real

Phase 7L adds an isolated dev-only real Free chat bridge module for controlled
local validation. It is not a production chat integration and it is not the
default provider.

## Scope

- Module: `frontend/src/lib/puter/freeModeChatBridgeDevReal.ts`
- Contract dependency: `frontend/src/lib/puter/freeModeChatBridgeContract.ts`
- Real provider path: existing `invokePuterFreeModeManualHarness(...)`
- Dev-real flag: `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false`

All related flags remain disabled by default:

- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false`

## Required Gates

The dev-real bridge calls the Phase 7J contract decision first. It may invoke
the existing manual Puter harness only when all gates pass:

- Free plan only
- Free Puter feature flag enabled
- chat bridge feature flag enabled
- dev-real bridge feature flag enabled
- browser runtime available
- Puter runtime already loaded and available
- safe AccessSnapshotBoundary-style state
- `routing_allowed=true`
- `quota_allowed=true`
- `quota_exceeded=false`
- selected provider family is `experimental_free_provider`
- no tools, files, function-calling, long memory, or sensitive tools
- no provider overrides, quota overrides, credentials, provider config, private
  endpoints, billing fields, or debug fields

## Behavior

No call happens on import, route load, app load, render, or mount. A real call is
possible only when code explicitly invokes the exported dev-real bridge
function and all gates pass.

This phase does not:

- connect Puter to normal chat
- make Puter the default provider
- enable Puter by default
- add BYOK storage
- add billing
- add Pro behavior
- enable tools, files, function-calling, or long memory
- expose raw provider payloads, raw requests, stack traces, credentials, API
  keys, access tokens, environment values, provider config, private endpoints,
  billing data, or debug data

## Runtime Truth

The result exposes public-safe runtime truth fields. `provider_attempted` is true
only when the bridge actually invokes the manual harness call path. It remains
false for contract denials, missing runtime, unsupported options, or other early
fail-closed states. `provider_succeeded` is true only for sanitized success.

Provider errors are returned as stable public reasons, such as
`puter_call_failed`, without raw exception text or stack traces.

## Future Path

Next phase:

- Phase 7M: Dev-only Chat UI Toggle behind flags, still not default

That phase should remain disabled by default and separate from production chat
promotion.
