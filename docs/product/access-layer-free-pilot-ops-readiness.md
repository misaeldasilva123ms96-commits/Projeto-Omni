# Omni Access Layer Phase 7T: Pilot Ops Readiness

Phase 7T defines pilot UI/ops controls and rollout readiness for the allowlisted Free Pilot. This phase does not add normal chat integration, does not make Puter the default provider, and does not enable Puter by default.

## Scope

- Documentation and rollout-readiness contract only
- No normal user exposure
- No automatic Puter calls
- No direct `puter.ai.chat` call
- No direct `fetch`, `XMLHttpRequest`, `sendBeacon`, or `WebSocket` provider path
- No tools, files, function-calling, long memory, BYOK storage, billing, or Pro behavior

The only real provider path remains:

`allowlisted pilot -> Phase 7R internal real pilot -> Phase 7L dev-real bridge -> existing gated manual harness`

## Rollout Controls

All flags must default to false:

```env
VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED=false
```

Rollout requires:

- explicit allowlist match
- rollback inactive
- `plan_mode=free`
- quota allowed and not exceeded
- routing allowed
- `selected_provider_family=experimental_free_provider`
- safe consent/auth state
- Puter runtime available only when a real path is evaluated
- no tools, files, function-calling, long memory, or sensitive tools
- no public provider, adapter, quota, policy, credential, billing, debug, private endpoint, or provider config overrides

## Operational Checklist

Before any allowlisted pilot:

- confirm CI is green
- confirm security/public-boundary tests are green
- confirm focused Puter pilot tests are green
- confirm runtime truth uses exact public-safe key sets
- confirm no raw provider payload can be exposed
- confirm no stack trace, secret, API key, token, env var, provider config, private endpoint, billing, or debug data can be exposed
- confirm fallback behavior is safe and understandable
- confirm rollback disables the pilot
- confirm allowlist miss denies before provider execution
- confirm consent/auth pending returns a safe state
- confirm normal chat behavior is unchanged when flags are false
- confirm Puter is not the default provider

## Runtime Truth

Pilot observability must be public-safe. The minimum runtime truth fields are:

- `pilot_enabled`
- `allowlisted_pilot`
- `allowlist_matched`
- `rollback_active`
- `provider_attempted`
- `provider_succeeded`
- `provider_failed_reason`
- `fallback_triggered`
- `consent_state`
- `sanitized_output_present`
- `raw_provider_payload_exposed=false`

Runtime truth must not include raw prompts beyond existing safe chat handling, raw provider requests, raw provider responses, stack traces, credentials, API keys, access tokens, env vars, provider config, private endpoints, billing data, debug payloads, or raw user/session identifiers.

## Rollout Stages

- Stage 0: local/dev validation
- Stage 1: internal-only allowlisted test
- Stage 2: one-user allowlisted pilot
- Stage 3: small allowlisted pilot
- Stage 4: production candidate review

No stage makes Puter the default provider. Any default-provider change requires a separate future phase, explicit review, and updated contracts.

## Rollback

Rollback must be simple and fail-closed:

- disable `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT`
- disable `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED`
- remove the allowlist marker
- fall back to the normal chat path
- do not delete user state
- do not require remote configuration unless a future phase adds it safely

Disabling either pilot flag must stop new Puter pilot attempts. Rollback must not expose raw provider payloads, stack traces, secrets, env vars, or debug internals.

## Readiness Gate

The allowlisted pilot is not ready for broader exposure unless all of the following remain true:

- all relevant flags are false by default
- allowlist checks cannot be bypassed by public input
- rollback controls cannot be bypassed by public input
- Access Layer gates remain authoritative
- consent/auth pending is not treated as success
- provider failure is sanitized
- normal chat is unchanged when flags are false
- Puter remains non-default

## Future Phase

Phase 7U should cover any next rollout step only after explicit review. If the next phase adds UI or operational controls, they must remain disabled by default, allowlisted, rollback-safe, and public-boundary safe.
