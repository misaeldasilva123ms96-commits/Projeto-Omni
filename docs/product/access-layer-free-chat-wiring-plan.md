# Access Layer Free Chat Wiring Plan

Status: Proposed plan for future implementation

## Purpose

This document defines how a future phase may connect the allowlisted Free/Puter path to Omni chat safely. It is docs/plan only. It does not implement wiring, does not change execution paths, does not connect Puter to normal chat, does not make Puter the default provider, and does not enable Puter by default.

The plan exists to prevent accidental broad exposure while preserving the Access Layer safety model built through the Free/Puter phases.

## Scope

This plan applies to any future branch that proposes chat-adjacent or normal-chat wiring for the Free/Puter pilot path.

The future wiring may only be considered after the activation gate, consent/auth UX decision, result UX contract, pilot evidence checklist, and allowlisted pilot contracts are current and reviewed for the exact target commit.

The intended future shape is:

```text
normal chat request
-> plan/pilot eligibility check
-> AccessSnapshotBoundary/PublicAccessSnapshot check
-> Free/Puter pilot allowlisted gate
-> consent/auth/result UX contract
-> sanitized output only
-> fallback to normal chat path if denied/fails safely
```

## Non-Goals

This document does not:

- implement wiring
- change chat behavior
- connect Puter to normal chat
- make Puter the default provider
- enable Puter by default
- add network or provider calls
- bypass Puter consent/auth
- auto-accept consent
- hide auth or consent prompts
- remove rollback or allowlist controls
- bypass Access Layer gates
- enable BYOK, billing, tools, files, function-calling, or long memory
- authorize broad normal-user rollout

## Required Preconditions

Before any future implementation branch may wire Free/Puter into chat, all of the following must be true for the exact branch and commit:

- CI is green.
- Backend Access Layer tests are green.
- Focused Puter and pilot Vitest suites are green.
- Frontend `typecheck`, `test`, `build`, and `test:security` are green.
- `frontend/.env.example` keeps every Puter/Free flag defaulted to `false`.
- Any local `.env.local` used for validation remains ignored/untracked and contains no secrets.
- Activation gate evidence exists and is current.
- The result UX contract is implemented or explicitly planned in the same future phase before user-visible output is shown.
- Consent/auth pending is handled as a safe state and is not treated as success.
- Exact runtime truth key-set tests exist for any new public result shape.
- Exact public result key-set tests exist for any new public result shape.
- Serialized output leak tests exist.
- Normal chat behavior is unchanged when flags are false.
- Puter remains non-default.

## Required Feature Flags

All relevant flags must remain committed default `false`:

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

Future wiring must deny before provider execution unless the reviewed activation mode explicitly enables the required flag set. A future chat-specific flag may be added only if it defaults to `false` and is included in exact flag tests.

## Required Allowlist And Rollback Behavior

Future wiring must require allowlist and rollback gates before any Puter provider attempt.

Allowlist requirements:

- allowlist control exists
- allowlist marker or match is explicit
- allowlist miss denies before provider execution
- allowlist mismatch denies before provider execution
- raw user/session identifiers are not exposed in public output

Rollback requirements:

- rollback control exists
- rollback active denies before provider execution
- disabling pilot flags denies before provider execution
- disabling allowlisted/internal flags denies before provider execution
- removing the allowlist marker denies before provider execution
- rollback falls back to normal chat behavior
- rollback does not delete user data

## Required Access Layer Gates

The future chat wiring must rerun or compose the existing Access Layer and pilot gates before any provider attempt:

- `plan_mode=free`
- quota allowed
- quota not exceeded
- routing allowed
- selected provider family is `experimental_free_provider`
- selected adapter is approved for the Free/Puter path
- AccessSnapshotBoundary/PublicAccessSnapshot state is valid
- consent/auth state is safe
- requested capabilities exclude tools, files, function-calling, long memory, and sensitive tools
- request options contain no public provider overrides
- request options contain no quota overrides
- request options contain no credentials, API keys, tokens, env vars, provider config, private endpoint, billing, debug, raw provider payload, or raw provider response fields

If any gate denies, future wiring must not attempt Puter and must route to the safe result/fallback path.

## Required Consent/Auth UX Behavior

Future wiring must follow the Puter consent/auth UX decision record:

- Omni never bypasses Puter consent/auth.
- Omni never auto-clicks or auto-accepts consent.
- Omni never hides or suppresses Puter auth/consent UI.
- Consent/auth pending maps to `provider_consent_or_auth_pending` or a reviewed safe equivalent.
- Consent/auth pending is not provider success.
- Consent/auth pending is not a raw provider failure.
- Retry is manual only.
- Retry after consent/auth reruns flags, allowlist, rollback, quota, routing, provider family, boundary, runtime, and unsafe-field gates.
- Omni never asks for Puter passwords, credentials, tokens, cookies, localStorage, or sessionStorage contents.

## Required Result UX Mapping

Future chat wiring must map every provider and pilot outcome through the result UX contract before anything reaches UI or public payloads.

Required categories include:

- `not_invoked`
- `denied_by_access_layer`
- `denied_by_flag`
- `denied_by_allowlist`
- `denied_by_rollback`
- `denied_by_quota`
- `denied_by_routing`
- `runtime_not_loaded`
- `provider_unavailable`
- `provider_consent_or_auth_pending`
- `provider_failed_safe`
- `provider_succeeded_sanitized`
- `aborted_by_operator`
- `fallback_used`

Future user-facing text must be Omni-authored safe text. It must not include raw provider errors, raw provider payloads, stack traces, or secrets.

## Runtime Truth And Public Payload Mapping

Future wiring must expose only exact-key, public-safe runtime truth and public payload fields.

Recommended runtime truth fields:

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
consent_state
provider_family
provider_attempted
provider_succeeded
provider_failed_reason
fallback_triggered
selected_adapter_id
boundary_version
snapshot_version
sanitized_output_present
raw_provider_payload_exposed
```

Required invariants:

- `raw_provider_payload_exposed=false`
- `provider_attempted=true` only after explicit gated provider invocation
- `provider_succeeded=true` only after sanitized success
- denied states use safe reason constants
- consent/auth pending is not success
- sanitized output is absent unless sanitized through an approved wrapper
- mock provider status remains separate from real provider status

Recommended public result fields:

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

Public output must never expose raw Puter responses, raw provider payloads, raw provider requests, stack traces, API keys, access tokens, credentials, env vars, cookies, localStorage/sessionStorage contents, `provider_config`, `private_endpoint`, billing data, debug data, raw user/session identifiers, or sensitive prompt content.

## Fallback Behavior

Denied or failed Free/Puter pilot states must fall back safely.

Required fallback behavior:

- flags false returns to normal chat behavior without Puter attempt
- allowlist miss returns to normal chat behavior without Puter attempt
- rollback active returns to normal chat behavior without Puter attempt
- quota denied returns to normal chat behavior without Puter attempt
- routing denied returns to normal chat behavior without Puter attempt
- consent/auth pending remains a safe pending or aborted state and is not success
- provider failure returns a sanitized failure and fallback state
- fallback must not hide raw provider failures by logging or exposing raw data elsewhere
- fallback must not retry automatically
- fallback must not submit additional prompts automatically

## Explicitly Forbidden Future Wiring

Future implementation must not:

- call `puter.ai.chat` directly from chat components
- add direct `fetch`, `XMLHttpRequest`, `navigator.sendBeacon`, or `WebSocket` provider paths from chat source
- bypass existing Free/Puter wrappers
- bypass Access Layer gates
- bypass pilot flag, allowlist, or rollback gates
- store Puter auth credentials
- inspect or record cookies, localStorage, or sessionStorage contents
- log raw Puter or provider responses
- expose raw provider payloads in public output
- make Puter the default provider
- enable Puter for normal users without allowlist and Go/No-Go approval
- enable tools, files, function-calling, long memory, BYOK, billing, or Pro behavior in the Free/Puter path

## Test Strategy For Future Wiring

Any future wiring branch must add focused tests for:

- flags false means normal chat unchanged
- allowlist miss means no Puter attempt
- rollback active means no Puter attempt
- quota denied means no Puter attempt
- quota exceeded means no Puter attempt
- routing denied means no Puter attempt
- wrong provider family means no Puter attempt
- consent pending maps to a safe state and is not success
- provider failure maps to sanitized failure/fallback
- sanitized success exposes safe output only
- raw provider payload is never exposed
- normal chat fallback works
- exact public result shape
- exact runtime truth shape
- serialized output has no secrets or sensitive fragments
- chat source has no direct network/provider path
- chat source has no direct `puter.ai.chat`
- no tools, files, function-calling, or long memory can be requested
- unsafe field variants are denied before provider execution
- retry is manual and reruns all gates

Recommended command groups:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

```powershell
npm run typecheck
npm run test
npm run build
npm run test:security
```

Focused Vitest should cover the pilot flag contract, allowlisted pilot, internal real pilot, chat bridge contract, result UX mapping, and any future wiring harness.

## Rollback Strategy

Rollback must be available before any future wiring is merged:

- disable the pilot flag
- disable the internal pilot flag
- disable the allowlisted pilot flag
- remove the allowlist marker
- keep Puter non-default
- keep normal chat path available
- stop new Puter provider attempts immediately
- preserve user state
- record only safe rollback reason constants

If rollback cannot prevent new provider attempts, the future wiring must be a No-Go.

## Future Implementation Phases

Recommended next phases:

- Phase 8H: Free Chat Wiring Test Harness, no production chat behavior
- Phase 8I: Mocked Chat Wiring behind flags
- Phase 8J: Internal Allowlisted Chat Wiring, still not default
- Phase 8K: One-user Live Chat Pilot Execution Record

No future phase should enable broad normal-user access until activation evidence, Go/No-Go approval, rollback verification, allowlist verification, consent/auth UX handling, result UX mapping, runtime truth/public payload safety, and security tests are all complete for the exact implementation under review.
