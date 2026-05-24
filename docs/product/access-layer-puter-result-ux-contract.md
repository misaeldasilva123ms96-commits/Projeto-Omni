# Access Layer Puter Result UX Contract

Status: Proposed contract for pilot planning

## Purpose

This document defines how Omni should represent Free/Puter pilot result states safely before any broader pilot or normal-chat integration. It is docs/contract only. It does not implement new behavior, change execution paths, connect Puter to normal chat, make Puter the default provider, or enable Puter by default.

## Context

Phase 8C observed a controlled one-user dry run that reached `provider_consent_or_auth_pending`. No provider output returned, no raw provider payload appeared, and normal chat remained untouched.

Phase 8D decided that Omni must never bypass Puter consent/auth, never auto-accept consent, and never hide or suppress consent/auth prompts. Consent/auth pending is not success and is not raw provider failure. It must be represented as a safe public state.

This result contract defines the public UX vocabulary, runtime truth expectations, retry rules, and safety boundaries that future implementation must follow.

## Result Categories

| Category | User-facing label | Safe public reason | Runtime truth mapping | Retry allowed | Provider attempted can be true | Provider succeeded can be true | Sanitized output present can be true | Required UI action | Stop/rollback condition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `not_invoked` | Not started | `not_invoked` | `provider_attempted=false`, `provider_succeeded=false`, `fallback_triggered=false`, `sanitized_output_present=false` | Yes, manual start only | No | No | No | Show idle/manual start state. | None. |
| `denied_by_access_layer` | Not available for this request | `denied_by_access_layer` or exact safe gate reason | `provider_attempted=false`, `provider_succeeded=false`, `fallback_triggered=true`, `sanitized_output_present=false` | Only after inputs or gates change | No | No | No | Show safe denial reason and keep normal path available. | Stop if provider was attempted. |
| `denied_by_flag` | Feature disabled | `feature_disabled` or `pilot_disabled` | `provider_attempted=false`, `provider_succeeded=false`, `fallback_triggered=true`, `sanitized_output_present=false` | Only after explicit flag change and full gate recheck | No | No | No | Show disabled state. | Stop if any provider path runs while flags are false. |
| `denied_by_allowlist` | Not included in pilot | `allowlist_not_matched` | `allowlist_matched=false`, `provider_attempted=false`, `provider_succeeded=false`, `fallback_triggered=true` | Only after allowlist is explicitly updated and gates rerun | No | No | No | Show safe pilot eligibility denial. | Stop if allowlist miss allows. |
| `denied_by_rollback` | Pilot paused | `rollback_active` | `rollback_active=true`, `provider_attempted=false`, `provider_succeeded=false`, `fallback_triggered=true` | No until rollback is cleared by operator | No | No | No | Show paused/rollback message. | Stop if rollback active allows. |
| `denied_by_quota` | Daily limit reached | `quota_exceeded` | `quota_allowed=false` or `quota_exceeded=true`, `provider_attempted=false`, `provider_succeeded=false`, `fallback_triggered=true` | Only after quota state changes and gates rerun | No | No | No | Show quota-safe denial and fallback guidance. | Stop if quota denied still attempts provider. |
| `denied_by_routing` | Route not available | `routing_denied` | `routing_allowed=false`, `provider_attempted=false`, `provider_succeeded=false`, `fallback_triggered=true` | Only after routing state changes and gates rerun | No | No | No | Show safe routing denial. | Stop if routing denied still attempts provider. |
| `runtime_not_loaded` | Runtime not loaded | `runtime_not_loaded` | `provider_attempted=false`, `provider_succeeded=false`, `fallback_triggered=true`, `sanitized_output_present=false` | Yes, manual runtime load only on gated surfaces | No | No | No | Offer a manual load action only where allowed. | Stop if runtime loads automatically outside allowed surfaces. |
| `provider_unavailable` | Provider unavailable | `provider_unavailable` or `puter_unavailable` | `provider_attempted=false` unless a gated call reached the harness, `provider_succeeded=false`, `fallback_triggered=true` | Yes, manual retry after runtime availability changes and gates rerun | Maybe | No | No | Show safe unavailable message. | Stop if raw error or provider internals appear. |
| `provider_consent_or_auth_pending` | Consent or sign-in required | `provider_consent_or_auth_pending` | `consent_state=consent_or_auth_pending`, `provider_succeeded=false`, `fallback_triggered=true` or future `pending=true`, `raw_provider_payload_exposed=false`, `sanitized_output_present=false` | Manual retry only after user/operator completes visible browser consent/auth and gates rerun | Yes, only if the gated harness was reached | No | No | Explain Omni cannot complete consent/auth automatically. | Stop on auth loop, auto-accept, hidden consent, or raw auth data. |
| `provider_failed_safe` | Provider failed safely | `provider_failed_safe` or safe provider reason such as `puter_call_failed` | `provider_attempted=true` only after gated invocation, `provider_succeeded=false`, `fallback_triggered=true`, `raw_provider_payload_exposed=false` | Manual retry only after gates rerun and prompt is safe | Yes | No | No | Show safe failure message without raw error. | Stop if stack trace, raw payload, or debug data appears. |
| `provider_succeeded_sanitized` | Response ready | `ok` | `provider_attempted=true`, `provider_succeeded=true`, `fallback_triggered=false`, `raw_provider_payload_exposed=false`, `sanitized_output_present=true` | New manual request only; not automatic retry | Yes | Yes | Yes | Show sanitized response only. | Stop if raw provider output or sensitive prompt echo appears. |
| `aborted_by_operator` | Stopped by operator | `aborted_by_operator` | `provider_succeeded=false`, `fallback_triggered=true`, `sanitized_output_present=false` | Manual restart only after operator review and gates rerun | Maybe | No | No | Show stopped state. | Stop condition already triggered or operator chose to abort. |
| `fallback_used` | Returned to normal path | `fallback_used` | `fallback_triggered=true`, `provider_succeeded=false` unless fallback has its own separate success contract, `raw_provider_payload_exposed=false` | Future retry manual only | Maybe | No for Puter provider | No for Puter output | Show fallback-safe message. | Stop if fallback hides provider failure or exposes raw provider data. |

## Public Output Shape Guidance

Future UI-facing result objects should expose only public-safe keys. A recommended shape is:

```ts
type PuterPilotUxResult = {
  ok: boolean
  status: string
  reason: string
  user_message: string
  sanitized_output: string | null
  retry_allowed: boolean
  manual_action_required: boolean
  fallback_triggered: boolean
  runtime_truth: PuterPilotUxRuntimeTruth
}
```

`status` must be one of the approved result categories or a reviewed safe extension. `reason` must be a safe constant. `user_message` must be written by Omni and must not include raw provider text, raw errors, stack traces, or secrets. `sanitized_output` must be `null` unless a provider or mock result has been sanitized through the approved wrapper.

Recommended runtime truth fields:

```ts
type PuterPilotUxRuntimeTruth = {
  access_layer_plan_mode: string
  pilot_enabled: boolean
  pilot_eligible: boolean
  pilot_denied_reason: string
  allowlisted_pilot: boolean
  allowlist_required: boolean
  allowlist_matched: boolean
  rollback_active: boolean
  quota_allowed: boolean
  quota_exceeded: boolean
  routing_allowed: boolean
  consent_state: string
  provider_family: string
  provider_attempted: boolean
  provider_succeeded: boolean
  provider_failed_reason: string
  fallback_triggered: boolean
  selected_adapter_id: string
  boundary_version: string
  snapshot_version: string
  sanitized_output_present: boolean
  raw_provider_payload_exposed: false
}
```

Implementation phases may define narrower exact-key shapes per module, but must preserve public-safety, exact-key tests, and serialized output leak tests.

## Strict Safety Requirements

Public result objects, runtime truth, UI text, docs, logs, screenshots, and tickets must never expose:

- raw Puter response
- raw provider payload
- raw provider request
- stack traces
- API keys
- access tokens
- credentials
- environment variables
- cookies
- localStorage contents
- sessionStorage contents
- `provider_config`
- `private_endpoint`
- billing data
- debug data
- hidden debug dumps
- raw user/session identifiers
- sensitive prompt echo

If any forbidden data appears, stop the pilot path, roll back if needed, and record only a safe stop reason.

## Messaging Examples

These examples are product guidance only. Future UI copy should keep the same safety posture.

### Consent/Auth Pending

```text
Puter needs browser consent or authentication before this pilot request can continue. Omni cannot complete this automatically. Complete the visible Puter flow if you choose to continue, then retry manually.
```

Reason: `provider_consent_or_auth_pending`

### Denied By Quota

```text
This Free pilot request is not available because the Access Layer quota gate denied it. No Puter provider call was made.
```

Reason: `quota_exceeded`

### Rollback Active

```text
The Free/Puter pilot is paused by rollback controls. No provider call was made.
```

Reason: `rollback_active`

### Allowlist Miss

```text
This session is not included in the Free/Puter pilot allowlist. No provider call was made.
```

Reason: `allowlist_not_matched`

### Provider Unavailable

```text
The Puter runtime is not available for this pilot request. Load the runtime manually on an allowed dev or pilot surface before retrying.
```

Reason: `provider_unavailable`

### Safe Provider Failure

```text
The provider request did not complete safely. Omni recorded only a safe failure state and did not expose provider internals.
```

Reason: `provider_failed_safe`

### Sanitized Success

```text
The pilot request completed and Omni is showing only sanitized output.
```

Reason: `ok`

## Retry Rules

Retries must be manual.

Every retry must rerun:

- Access Layer plan gate
- quota gate
- routing gate
- provider family gate
- capability restrictions
- unsafe-field checks
- flag checks
- rollback checks
- allowlist checks
- runtime availability checks
- consent/auth state checks

Retries must not:

- auto-submit the previous prompt
- auto-submit sensitive prompts
- bypass Puter consent/auth
- auto-click, auto-accept, hide, or suppress consent/auth prompts
- reuse stored credentials or tokens
- inspect cookies, localStorage, or sessionStorage
- bypass quota, routing, rollback, allowlist, or Access Layer gates
- make Puter the default provider

Retry after consent/auth is allowed only after the user or operator explicitly completes the visible browser consent/auth flow and all gates still pass.

Retry remains denied when rollback, allowlist, quota, routing, capability, provider family, or unsafe-field gates deny.

## Implementation Guidance

Future UI should consume contract states and safe reasons, not raw provider errors.

Future normal-chat integration, if ever proposed, must map every provider state through this result contract before anything reaches UI or public payloads.

Before implementation:

- Add exact public key-set tests.
- Add exact runtime truth key-set tests.
- Add serialized output leak tests.
- Add tests for every result category.
- Add tests proving retry is manual and reruns gates.
- Add tests proving consent/auth pending is not success.
- Add tests proving no raw provider payload, stack trace, token, API key, env var, cookie, storage value, provider config, private endpoint, billing, debug data, or sensitive prompt can leak.
- Add tests proving flags false leaves normal chat unchanged.
- Add tests proving Puter is not default provider.

This contract should be consumed only after an implementation phase explicitly defines the module boundary, exact key set, and tests.

## Non-Recommendation

Do not enable Puter for normal users yet. Do not connect Puter to normal chat yet. Do not broaden pilot access until Go/No-Go evidence is complete and reviewed.

## Future Phase

Next phase:

```text
Phase 8F - Final Free Chat Activation Gate
```

Phase 8F should define the activation gate before any future controlled pilot path can be considered for normal-chat adjacency. It must preserve disabled-by-default flags, rollback, allowlist, Access Layer gates, consent/auth safety, exact public output shapes, and no default-provider change.

## Explicit Non-Authorization

This contract does not enable Puter, does not execute Puter, does not implement pilot behavior, does not connect Puter to normal chat, and does not authorize broader rollout.
