# Omni Access Layer Phase 7S: Allowlisted Free Pilot

Phase 7S adds a conservative allowlisted Free pilot contract layer. It prepares controlled rollout checks for selected Free users or sessions while keeping Puter disabled by default and not the default provider.

## Scope

- Module only: `frontend/src/lib/puter/freeModePilotAllowlisted.ts`
- Contract/readiness gate only in this branch
- No normal chat integration
- No default provider change
- No automatic calls on import, app load, render, mount, route load, or default path
- No direct `puter.ai.chat` call
- No direct `fetch`, `XMLHttpRequest`, `sendBeacon`, or `WebSocket` provider path
- No BYOK storage, billing, Pro behavior, tools, files, function-calling, or long memory

This phase composes the Phase 7P pilot flag contract first. Because the Phase 7R internal-real module is not present on this branch's `origin/main` base, Phase 7S remains contract-only and does not call a real provider path.

## Required Flags

All relevant flags remain default-disabled:

```env
VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED=false
```

The allowlisted pilot must deny unless the pilot contract allows and the allowlisted pilot flag/marker is explicitly enabled.

## Required Gates

The allowlisted pilot denies unless:

- plan mode is Free
- rollback is inactive
- Free Puter flag is enabled
- chat bridge flag is enabled
- dev-real bridge flag is enabled for future real-path compatibility
- pilot flag is enabled
- allowlisted pilot flag is enabled
- allowlist is explicitly matched
- quota is allowed and not exceeded
- routing is allowed
- selected provider family is `experimental_free_provider`
- consent/auth state is safe and not pending
- Puter runtime availability marker is true for future real-path readiness
- requested capabilities exclude tools, files, function-calling, long memory, and sensitive tools
- request options contain no provider overrides, quota overrides, credentials, keys, tokens, environment fields, provider config, private endpoints, billing, debug, or raw provider payloads

## Deny Behavior

Fail-closed reasons are safe constants only. The module denies for:

- allowlisted pilot flag false
- allowlist missing or mismatched
- rollback active
- pilot flag false
- non-Free plan
- quota denied or exceeded
- routing denied
- wrong provider family
- consent/auth pending
- missing Puter runtime marker
- tools, files, function-calling, long memory, or sensitive tools
- forbidden override fields
- sensitive request fields
- unsafe key variants inherited from Phase 7P

## Runtime Truth

Runtime truth is public-safe and includes:

- `allowlisted_pilot`
- `allowlist_required`
- `allowlist_matched`
- `pilot_enabled`
- `pilot_eligible`
- `pilot_denied_reason`
- `rollback_active`
- `access_layer_plan_mode`
- `provider_family`
- `provider_attempted=false`
- `provider_succeeded=false`
- `provider_failed_reason`
- `fallback_triggered`
- `quota_allowed`
- `quota_exceeded`
- `routing_allowed`
- `consent_state`
- `selected_adapter_id`
- `boundary_version`
- `snapshot_version`
- `sanitized_output_present=false`
- `raw_provider_payload_exposed=false`

No raw provider request, raw provider response, stack trace, credential, API key, access token, env var, provider config, private endpoint, billing data, debug payload, or raw user/session identifier may be exposed.

## Future Phase

Phase 7T should cover pilot UI/ops controls or rollout readiness, still not default. Any later real-provider pilot must preserve explicit flags, rollback controls, allowlist checks, Access Layer gates, consent/auth safety, and public-safe runtime truth before any broader exposure is considered.
