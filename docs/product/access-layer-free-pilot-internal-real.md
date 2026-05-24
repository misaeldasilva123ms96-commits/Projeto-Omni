# Omni Access Layer Phase 7R: Internal-only Real Free Pilot

Phase 7R adds an internal-only real pilot module for the experimental Free Mode Puter path. It remains disabled by default and does not expose Puter to normal users.

## Scope

- Module only: `frontend/src/lib/puter/freeModePilotInternalReal.ts`
- No normal chat integration
- No default provider change
- No automatic calls on import, app load, render, mount, or route load
- No direct `puter.ai.chat` call from the internal pilot module
- No direct `fetch`, `XMLHttpRequest`, `sendBeacon`, or `WebSocket` provider path
- No BYOK storage, billing, Pro behavior, tools, files, function-calling, or long memory

The only real provider path allowed by this phase is:

`internal pilot -> Phase 7L dev-real bridge -> gated Puter manual harness`

## Required Flags

All flags remain default-disabled:

```env
VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL=false
```

The internal pilot must deny unless the pilot contract allows and the internal-only flag or marker is explicitly enabled.

## Required Gates

The module composes the Phase 7P pilot flag contract first. It denies before any real bridge invocation unless:

- plan mode is Free
- rollback is inactive
- pilot flag is enabled
- internal pilot flag is enabled
- allowlist is matched when allowlist is required
- quota is allowed and not exceeded
- routing is allowed
- selected provider family is `experimental_free_provider`
- consent/auth state is safe and not pending
- Puter runtime is available
- requested capabilities exclude tools, files, function-calling, long memory, and sensitive tools
- request options contain no provider overrides, quota overrides, credentials, keys, tokens, environment fields, provider config, private endpoints, billing, debug, or raw provider payloads

## Consent/Auth State

Consent or auth pending states remain fail-closed. The module must not bypass, auto-click, auto-accept, hide, or simulate Puter consent/auth prompts. Pending or failed provider states are reported with safe constants only.

## Runtime Truth

Runtime truth is public-safe and includes:

- `pilot_enabled`
- `pilot_eligible`
- `pilot_denied_reason`
- `internal_pilot`
- `bridge_allowed`
- `bridge_denied_reason`
- `access_layer_plan_mode`
- `provider_family`
- `provider_attempted`
- `provider_succeeded`
- `provider_failed_reason`
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

`provider_attempted` may become true only when the Phase 7L dev-real bridge is actually invoked. `provider_succeeded` may become true only on sanitized success.

## Public Output

The internal pilot must never expose raw provider requests, raw provider responses, stack traces, credentials, API keys, access tokens, env vars, provider config, private endpoints, billing data, or debug internals.

Visible output is sanitized text only. Failures expose safe reason constants only.

## Future Phase

Phase 7S should define an allowlisted Free pilot that is still not default. It should preserve explicit flags, rollback, allowlist controls, Access Layer gates, consent/auth safety, and public-safe runtime truth before any broader user exposure is considered.
