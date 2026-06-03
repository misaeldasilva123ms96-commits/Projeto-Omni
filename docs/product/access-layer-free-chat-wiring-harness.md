# Access Layer Free Chat Wiring Harness

Status: Test harness only

## Purpose

Phase 8H adds an isolated Free Chat wiring test harness for future Free/Puter chat wiring. The harness proves the intended orchestration shape without changing normal chat behavior.

This phase does not wire Puter into normal chat, does not change `sendOmniMessage`, does not call real Puter, does not add a provider or network path, and does not make Puter the default provider.

## Scope

Module:

- `frontend/src/lib/puter/freeModeChatWiringHarness.ts`

Tests:

- `frontend/src/lib/puter/freeModeChatWiringHarness.test.ts`

The harness is a pure deterministic TypeScript module. It has no React UI and is not mounted anywhere.

## Composition

The harness composes only safe contract/mock layers:

- Phase 7P pilot flag contract
- Phase 7Q pilot mock
- Phase 7K chat bridge mock through the pilot mock path
- Phase 8E result UX contract as output-shape guidance

The harness enforces allowlisted pilot markers locally for test planning. It does not import the Phase 7S real allowlisted module because that module is intentionally connected to the internal real pilot path. Phase 8H remains mock-only.

## Explicit Non-Integration

The harness must not:

- import or call `sendOmniMessage`
- import normal chat components
- call `puter.ai.chat`
- call the Phase 7L dev-real bridge
- call the Phase 7R internal real pilot
- call the manual Puter harness
- use `fetch`, `XMLHttpRequest`, `navigator.sendBeacon`, or `WebSocket`
- add a route, UI, render path, mount path, or app-load behavior
- alter default provider selection

## Required Flags

All committed defaults remain `false` in `frontend/.env.example`:

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

The harness succeeds only when all test inputs explicitly represent enabled experimental flags, matched allowlist, inactive rollback, allowed quota/routing, safe consent state, and the experimental Free provider family.

## Input Contract

The harness input may include:

- prompt or message summary
- plan mode
- feature flags
- allowlist marker
- rollback marker
- quota and routing markers
- provider family marker
- consent state marker
- requested capabilities
- request options

Prompt and message summaries are not echoed into public output. They are accepted only as safe summaries for future wiring tests.

## Output Shape

The public result shape is exact-key:

```text
ok
status
reason
user_message
sanitized_output
retry_allowed
manual_action_required
fallback_triggered
runtime_truth
```

Success uses deterministic mock-only output:

```text
Omni Free chat wiring harness mock response.
```

No raw provider payload, raw prompt, raw user/session identifier, stack trace, API key, token, env var, provider config, private endpoint, billing data, or debug data may appear.

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
```

Required invariants:

- `provider_attempted=false`
- `provider_succeeded=false`
- `raw_provider_payload_exposed=false`
- mock status is separate from real provider status
- `mock_provider_attempted=true` only on mock success
- `mock_provider_succeeded=true` only on mock success
- `sanitized_output_present=true` only on deterministic mock success

## Deny And Fail-Closed Behavior

The harness denies safely for:

- flags false
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

Denied paths never attempt a real provider and never attempt a mock provider success.

## Test Coverage

Focused tests cover:

- flags false denies
- rollback active denies
- allowlist miss denies
- quota exceeded denies
- routing false denies
- wrong provider family denies
- consent pending maps to safe pending and no success
- unsafe field variants deny
- tools/files/function-calling/long memory deny
- mock success only when all gates pass
- exact public result key set
- exact runtime truth key set
- serialized output leak checks
- source guards for no chat send imports
- source guards for no `puter.ai.chat`
- source guards for no direct network path
- source guards for no dev-real/internal-real/manual harness imports

## Future Phase

Phase 8I should add mocked chat wiring behind flags. It must still avoid production chat behavior, real Puter calls, direct provider/network paths, default provider changes, consent/auth bypass, tools, files, function-calling, long memory, BYOK, and billing behavior.
