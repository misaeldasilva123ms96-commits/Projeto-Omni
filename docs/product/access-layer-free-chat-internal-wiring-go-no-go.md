# Access Layer Free Chat Internal Wiring Go/No-Go Review

Status: Proposed review gate for internal wiring planning

## Purpose And Scope

Phase 8L defines the Go/No-Go review for the internal allowlisted Free Chat wiring path before any future phase touches production chat behavior.

This document is docs/review only. It does not implement new behavior, does not change production chat behavior, does not connect Puter more deeply into normal chat, does not make Puter the default provider, and does not enable Puter by default.

This review applies to:

- Phase 8H Free Chat wiring harness
- Phase 8I mocked chat wiring
- Phase 8J internal allowlisted chat wiring
- Phase 8K one-user wiring execution record
- any future step that considers chat-adjacent Free/Puter behavior

## Current Wiring Status

The current internal wiring path is a disabled-by-default, internal allowlisted decision layer:

```text
internal allowlisted chat wiring
-> Phase 7S allowlisted pilot wrapper
-> Phase 7R internal real pilot
-> Phase 7L dev-real bridge
-> existing gated manual harness
```

The Phase 8J module is not imported by normal chat code and is not mounted in UI. `sendOmniMessage` remains the normal chat send path.

The Phase 8K execution record reports PASS for controlled, test-only validation of the internal wiring layer. The record used safe mocked runtime inputs and did not execute a live Puter browser call.

## What Is Already Safe

- Flags remain default `false` in committed config.
- Flags-false behavior returns `should_use_normal_chat=true`.
- Flags-false behavior does not attempt a provider.
- Normal chat source remains unchanged by the internal wiring module.
- `sendOmniMessage` is not wired to the internal allowlisted module.
- Allowlist miss denies before provider attempt.
- Rollback active denies before provider attempt.
- Quota denied or exceeded denies before provider attempt.
- Routing false denies before provider attempt.
- Wrong provider family denies before provider attempt.
- Consent pending is safe pending, not success.
- Unsafe fields are denied, including common casing and separator variants.
- Tools, files, function-calling, long memory, and sensitive tools are denied.
- Public output and runtime truth exact key sets are tested.
- Serialized public output leak checks are tested.
- `raw_provider_payload_exposed=false`.
- Puter is not the default provider.

## What Is Still Not Enabled

- No broad normal-user rollout is enabled.
- No production chat behavior is changed.
- No direct Puter call is added to chat components.
- No direct `puter.ai.chat` call is added to chat components.
- No direct `fetch`, `XMLHttpRequest`, `navigator.sendBeacon`, or `WebSocket` provider path is added.
- No BYOK, billing, Pro behavior, tools, files, function-calling, or long memory behavior is added.
- No consent/auth bypass, auto-accept, hidden consent handling, or automatic retry is authorized.

## Required Flags

All related committed flags must remain default-disabled:

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
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_INTERNAL_WIRING=false
VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=false
```

No future review can approve a path where a committed default flips to `true`.

## GO Criteria

A GO decision requires current evidence for the exact target commit:

- CI green.
- Backend Access Layer tests green.
- Focused Puter/wiring tests green.
- Frontend typecheck, test, build, and security checks green.
- `frontend/.env.example` keeps all Puter and Free flags default `false`.
- Flags false keeps normal chat behavior unchanged.
- `sendOmniMessage` is unchanged or explicitly verified unchanged by the phase under review.
- Allowlist miss denies before provider attempt.
- Rollback active denies before provider attempt.
- Quota denied or exceeded prevents provider attempt.
- Routing false prevents provider attempt.
- Wrong provider family prevents provider attempt.
- Consent/auth pending is safe, public, manual, and not success.
- Runtime truth and public payloads are exact-key and public-safe.
- No raw provider payload is exposed.
- No stack trace, secret, token, API key, env var, credential, provider config, private endpoint, billing, or debug data is exposed.
- No direct Puter or direct network provider path is added.
- Puter is not the default provider.
- Tools, files, function-calling, and long memory remain disabled.
- BYOK, billing, and Pro behavior are not mixed into the Free/Puter path.

## NO-GO Criteria

Any of these conditions requires NO-GO:

- Any CI or security failure.
- Backend Access Layer tests fail.
- Focused Puter/wiring tests fail.
- Frontend typecheck, test, build, or security checks fail.
- `sendOmniMessage` changes unexpectedly.
- Normal chat behavior changes when flags are false.
- Puter becomes the default provider.
- Allowlist miss allows.
- Rollback active allows.
- Quota or routing denial still attempts a provider.
- Wrong provider family reaches provider execution.
- Consent/auth is bypassed, hidden, auto-accepted, or treated as success.
- Raw provider payload appears.
- Raw Puter response appears.
- Stack trace, secret, token, API key, env var, credential, cookie, storage content, provider config, private endpoint, billing, or debug data appears.
- Tools, files, function-calling, long memory, sensitive tools, BYOK, billing, or Pro behavior is enabled in the Free/Puter path.
- A stale branch/base inconsistency is found.

## Required Evidence

The review packet must include:

- Branch and commit under review.
- `origin/main` base commit.
- PR checks or local validation output.
- Backend Access Layer pytest output.
- Focused Puter/wiring Vitest output.
- Frontend `typecheck`, `test`, `build`, and root `test:security` output.
- `.env.example` flag audit showing default `false`.
- Source guard showing no direct `puter.ai.chat` from chat components.
- Source guard showing no direct provider network path in chat components.
- `sendOmniMessage` unchanged evidence.
- Flags false behavior evidence.
- Allowlist miss denial evidence.
- Rollback active denial evidence.
- Quota/routing/provider-family denial evidence.
- Consent/auth pending safe-state evidence.
- Runtime truth and public payload exact-key evidence.
- Serialized output leak-check evidence.
- Statement that no raw provider payload or sensitive data was recorded.

## Required Tests

Backend Access Layer:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

Focused Puter/wiring Vitest:

```powershell
cd frontend
npm.cmd exec -- vitest run src/lib/puter/freeModeChatInternalAllowlistedWiring.test.ts src/lib/puter/freeModeChatMockedWiring.test.ts src/lib/puter/freeModeChatWiringHarness.test.ts src/lib/puter/freeModePilotAllowlisted.test.ts src/lib/puter/freeModePilotInternalReal.test.ts src/lib/puter/freeModeChatBridgeDevReal.test.ts
```

Frontend validation:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
cd ..
npm.cmd run test:security
```

When local ignored env files may enable Puter flags, focused and full frontend validation must run with explicit default-false overrides.

## Rollback Requirements

Rollback must remain simple, explicit, and verifiable:

- Disable internal wiring flag.
- Disable mocked wiring flag if relevant.
- Disable allowlisted pilot flag.
- Disable internal pilot flag.
- Disable pilot flag.
- Disable chat bridge and Puter Free flags.
- Remove or mismatch allowlist marker.
- Set rollback active if a future ops control exists.
- Confirm no new provider attempts can occur.
- Confirm normal chat path remains available.
- Record only safe constants and sanitized summaries.

Rollback must not delete user data and must not expose raw provider or auth data.

## Allowlist Requirements

Any internal or one-user continuation must require:

- explicit allowlist marker or match
- fail-closed behavior when allowlist is missing
- fail-closed behavior when allowlist mismatches
- no raw user/session identifier exposure in public output
- tests proving allowlist miss denies before provider attempt

## Consent/Auth Requirements

Any future step must preserve the Phase 8D consent/auth decision:

- never bypass consent/auth
- never auto-accept consent
- never hide or suppress auth/consent prompts
- never ask users for Puter credentials, tokens, cookies, localStorage, or sessionStorage
- represent pending state as `provider_consent_or_auth_pending` or a reviewed safe equivalent
- keep pending state as not success
- retry manually only after visible user/operator consent/auth completion
- rerun all Access Layer, flag, rollback, allowlist, quota, routing, capability, unsafe-field, provider-family, and runtime gates on retry

## Runtime Truth And Public Payload Requirements

Public payloads and runtime truth must remain exact-key and public-safe.

Required invariants:

- `raw_provider_payload_exposed=false`
- `provider_attempted=true` only after gated invocation
- `provider_succeeded=true` only after sanitized success
- consent/auth pending is not success
- denied states expose only safe constants
- `sanitized_output_present` is boolean only
- normal chat fallback remains available

Forbidden in public output:

- raw Puter response
- raw provider payload
- raw provider request
- stack traces
- API keys
- tokens
- credentials
- env vars
- cookies
- localStorage/sessionStorage contents
- provider config
- private endpoint
- billing/debug data
- sensitive prompt echo
- raw user/session identifiers

## Decision Options

Allowed decisions:

- `NO-GO: stop and fix evidence gaps`
- `GO: continue with mocked chat path only`
- `GO: continue with internal allowlisted path only`
- `GO: prepare one-user live pilot plan`

This review must not approve broad normal-user rollout.

## Decision Template

```markdown
# Internal Chat Wiring Go/No-Go Decision

- Decision: NO-GO / GO: mocked chat path only / GO: internal allowlisted path only / GO: prepare one-user live pilot plan
- Target branch:
- Target commit:
- Base commit:
- Approved scope:
- Max users:
- Required flags:
- Allowlist mechanism:
- Rollback owner:
- Observability owner:
- Stop conditions:
- Backend Access Layer tests:
- Focused Puter/wiring tests:
- Frontend typecheck/test/build/security:
- `.env.example` flag audit:
- Flags-false normal chat behavior:
- `sendOmniMessage` unchanged:
- Allowlist miss denial:
- Rollback active denial:
- Quota/routing denial:
- Consent/auth pending safety:
- Runtime truth/public payload safety:
- Raw provider payload exposed: no / yes-stop
- Puter default provider: no / yes-stop
- Approval date:
- Next review:
- Notes:
```

## Future Phase Recommendation

If GO:

```text
Phase 8M - One-user Live Pilot Plan, still not default
```

If NO-GO:

```text
Phase 8M-blocked - Internal Wiring Evidence Gap Fixes
```

## Explicit Non-Authorization

This document does not enable Puter, does not connect Puter more deeply into normal chat, does not authorize broad normal-user rollout, does not make Puter the default provider, and does not permit bypassing flags, allowlist, rollback, quota, routing, consent/auth, or Access Layer gates.
