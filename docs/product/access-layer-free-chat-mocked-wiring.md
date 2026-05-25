# Access Layer Free Chat Mocked Wiring

Status: Mocked wiring only

## Purpose

Phase 8I adds a mocked Free Chat wiring layer behind disabled-by-default flags. It proves that a future chat-adjacent Free/Puter route can be gated before any real provider path exists.

This phase does not call real Puter, does not call `puter.ai.chat`, does not add direct network or provider calls, does not change normal chat behavior when flags are false, and does not make Puter the default provider.

## Scope

Module:

- `frontend/src/lib/puter/freeModeChatMockedWiring.ts`

Tests:

- `frontend/src/lib/puter/freeModeChatMockedWiring.test.ts`

The module is pure and deterministic. It is not imported by normal chat code and is not mounted in UI.

## Composition

The mocked wiring layer composes Phase 8H:

```text
mocked wiring flag
-> Phase 8H Free Chat wiring harness
-> Phase 7P pilot flag contract
-> Phase 7Q pilot mock
-> Phase 7K chat bridge mock through the pilot mock path
```

The module intentionally does not compose the Phase 7S allowlisted real module because that path can reach the Phase 7R internal real pilot. Phase 8I remains mock-only.

## Feature Flag

The mocked wiring flag is default-disabled:

```env
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_MOCKED_WIRING=false
```

All related Puter/Free flags also remain default-disabled in `frontend/.env.example`:

```env
VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED=false
VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=false
```

## Behavior

When the mocked wiring flag is false:

- result mode is `normal_chat`
- `should_use_normal_chat=true`
- no mock provider is attempted
- no real provider is attempted
- no user-visible behavior change is expected

When the mocked wiring flag is true and gates deny:

- result mode is `mocked_free_chat`
- fail closed with a safe reason
- no real provider is attempted
- no mock success is recorded
- raw provider payload remains unexposed

When all mock gates pass:

- result mode is `mocked_free_chat`
- deterministic mock-only output is returned
- `provider_attempted=false`
- `provider_succeeded=false`
- `mock_provider_attempted=true`
- `mock_provider_succeeded=true`
- `raw_provider_payload_exposed=false`
- `sanitized_output_present=true`

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
mock_provider_attempted
mock_provider_succeeded
consent_state
sanitized_output_present
raw_provider_payload_exposed
should_use_normal_chat
```

Required invariants:

- `provider_attempted=false`
- `provider_succeeded=false`
- `raw_provider_payload_exposed=false`
- mock status is separate from real provider status
- `mock_provider_attempted=true` only on mocked success
- `mock_provider_succeeded=true` only on mocked success
- `should_use_normal_chat=true` only when the mocked wiring flag is false

## Deny And Fail-Closed Behavior

The mocked wiring layer denies safely for:

- rollback active
- allowlist missing
- allowlist mismatch
- quota denied or exceeded
- routing false
- wrong provider family
- consent/auth pending
- malformed input
- tools requested
- files requested
- function-calling requested
- long memory requested
- sensitive tools requested
- unsafe request fields, including camelCase, PascalCase, kebab-case, spaced, and mixed variants

Denied paths do not attempt a real provider and do not report mock success.

## Explicit Non-Integration

Phase 8I does not:

- modify normal chat components
- modify `sendOmniMessage`
- make Puter the default provider
- enable Puter by default
- call `puter.ai.chat`
- call the Phase 7L dev-real bridge
- call the Phase 7R internal real pilot
- call the manual Puter harness
- use `fetch`, `XMLHttpRequest`, `navigator.sendBeacon`, or `WebSocket`
- add BYOK, billing, tools, files, function-calling, or long memory behavior

## Test Coverage

Focused tests cover:

- flag false returns `should_use_normal_chat=true`
- flag false has no provider/mock attempt
- flag false documents normal chat behavior expected unchanged
- rollback active denies
- allowlist miss denies
- quota exceeded denies
- routing false denies
- wrong provider family denies
- consent pending maps to safe pending and no success
- unsafe key variants deny
- restricted capabilities deny
- mock success only when all gates pass
- exact public result key set
- exact runtime truth key set
- serialized output leak checks
- source guards for no `puter.ai.chat`
- source guards for no direct network path
- source guards for no dev-real/manual harness path
- source guard that `sendOmniMessage` is not modified

## Future Phase

Phase 8J should cover Internal Allowlisted Chat Wiring, still not default. It must preserve default-false flags, rollback, allowlist, Access Layer gates, consent/auth safety, result UX mapping, no raw payload exposure, and no default provider change.
