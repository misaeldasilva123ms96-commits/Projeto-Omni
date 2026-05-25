# Access Layer Free Chat Internal Allowlisted Wiring

Status: Internal/allowlisted wiring only, still not default

## Purpose

Phase 8J adds an internal allowlisted Free Chat wiring decision layer. It can decide whether a request should stay on normal chat or enter the existing gated Free/Puter pilot path.

This phase does not make Puter the default provider, does not enable Puter by default, does not expose the path to normal users, and does not change normal chat behavior when flags are false.

## Scope

Module:

- `frontend/src/lib/puter/freeModeChatInternalAllowlistedWiring.ts`

Tests:

- `frontend/src/lib/puter/freeModeChatInternalAllowlistedWiring.test.ts`

The module is not imported by normal chat code and is not mounted in UI. It is a decision/wrapper layer for future internal pilot planning.

## Feature Flag

The internal wiring flag is default-disabled:

```env
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_INTERNAL_WIRING=false
```

All related Puter/Free flags remain default-disabled in `frontend/.env.example`:

```env
VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_MOCKED_WIRING=false
VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=false
```

## Composition

The only permitted real path is:

```text
internal allowlisted chat wiring
-> Phase 7S allowlisted pilot wrapper
-> Phase 7R internal real pilot
-> Phase 7L dev-real bridge
-> existing gated manual harness
```

The Phase 8J module imports only the allowlisted pilot wrapper. It does not directly import the dev-real bridge, internal real pilot, or manual harness.

## Behavior

When the internal wiring flag is false:

- `should_use_normal_chat=true`
- no provider is attempted
- no mock provider is attempted
- no behavior change is expected

When gates deny:

- the module fails closed with a safe reason
- provider is not attempted for Access Layer, allowlist, rollback, quota, routing, provider-family, consent/auth, unsafe-field, or restricted-capability denials
- `should_use_normal_chat` may be true for safe fallback states
- consent/auth pending remains a safe pending state and is not success

When all internal allowlisted gates pass:

- only the existing gated allowlisted pilot path may be invoked
- `provider_attempted=true` only when that path actually invokes the gated bridge
- `provider_succeeded=true` only on sanitized success
- `raw_provider_payload_exposed=false`

## Public Result Shape

The public result shape is exact-key:

```text
ok
mode
should_use_normal_chat
status
reason
user_message
sanitized_output
retry_allowed
manual_action_required
fallback_triggered
runtime_truth
```

No raw prompt, raw provider payload, raw user/session identifier, stack trace, API key, token, env var, provider config, private endpoint, billing data, or debug data may appear.

## Runtime Truth

Runtime truth is exact-key and public-safe:

```text
access_layer_plan_mode
pilot_enabled
pilot_eligible
pilot_denied_reason
allowlisted_pilot
allowlist_required
allowlist_matched
rollback_active
quota_allowed
quota_exceeded
routing_allowed
provider_family
provider_attempted
provider_succeeded
provider_failed_reason
consent_state
sanitized_output_present
raw_provider_payload_exposed
should_use_normal_chat
internal_allowlisted_wiring_enabled
```

Required invariants:

- `raw_provider_payload_exposed=false`
- `provider_attempted=true` only after actual gated internal path invocation
- `provider_succeeded=true` only after sanitized success
- denied gate states use safe constants
- consent/auth pending is not success
- normal chat remains available as fallback

## Deny And Fail-Closed Behavior

The wiring layer denies safely for:

- internal wiring flag false
- rollback active
- allowlist missing
- allowlist mismatch
- quota denied or exceeded
- routing false
- wrong provider family
- consent/auth pending
- missing runtime
- provider failure
- tools requested
- files requested
- function-calling requested
- long memory requested
- sensitive tools requested
- unsafe request fields, including camelCase, PascalCase, kebab-case, spaced, and mixed variants

## Explicit Non-Integration

Phase 8J does not:

- modify normal chat components
- modify `sendOmniMessage`
- make Puter the default provider
- enable Puter by default
- expose this to normal users
- remove normal chat fallback
- bypass Access Layer gates
- bypass allowlist checks
- bypass rollback
- bypass quota/routing gates
- bypass consent/auth
- auto-accept consent
- hide auth/consent prompts
- call `puter.ai.chat` from chat components
- add direct `fetch`, `XMLHttpRequest`, `navigator.sendBeacon`, or `WebSocket` provider paths
- add BYOK, billing, tools, files, function-calling, or long memory behavior

## Test Coverage

Focused tests cover:

- flags false returns `should_use_normal_chat=true`
- flags false has no provider attempt
- flags false documents normal chat behavior expected unchanged
- rollback active denies
- allowlist miss denies
- quota exceeded denies
- routing false denies
- wrong provider family denies
- consent pending maps to safe pending and no success
- unsafe key variants deny
- restricted capabilities deny
- internal allowlisted path only when all gates pass
- provider attempt only after gated internal path invocation
- provider success only after sanitized success
- provider failure is safe
- exact public result key set
- exact runtime truth key set
- serialized output leak checks
- source guards for no direct `puter.ai.chat`
- source guards for no direct network path
- source guard that `sendOmniMessage` is not modified

## Future Phase

Phase 8K should record a one-user live chat pilot execution. It must preserve disabled-by-default flags, non-default provider behavior, allowlist, rollback, Access Layer gates, consent/auth safety, result UX mapping, normal chat fallback, and no raw provider payload exposure.
