# Access Layer Puter Auth/Consent Dev Flow

## Purpose

Phase 8O adds a dev-only Puter auth/consent action under the existing `/dev/puter` surface. It exists so an operator can explicitly request Puter browser auth/consent before retrying a controlled dev or internal pilot path.

This document does not enable normal chat, does not authorize broad rollout, and does not make Puter the default provider.

## Scope

- Dev-only auth/consent helper: `frontend/src/lib/puter/puterAuthConsent.ts`
- Dev-only UI surface: `frontend/src/lib/puter/PuterAuthConsentDevSurface.tsx`
- Existing `/dev/puter` route mount only
- Safe public result states and runtime truth only

No production chat execution path is changed.

## Required Controls

- Puter remains disabled by default.
- `/dev/puter` remains behind the existing dev and experimental flags.
- The auth/consent action requires an explicit user/operator click.
- The auth button is disabled until the Puter runtime is present.
- Auth/consent never runs on import, render, page load, or after runtime load.
- Completing auth/consent never automatically calls AI.
- The manual Puter check remains a separate explicit action.

## Safe States

The helper returns only these public states:

- `not_invoked`
- `runtime_not_loaded`
- `auth_api_unavailable`
- `consent_or_auth_pending`
- `consent_or_auth_completed`
- `consent_or_auth_cancelled`
- `consent_or_auth_failed_safe`

Pending consent/auth is not a provider success. It is also not a raw provider failure. It means the browser/user interaction must complete manually before any later retry.

## Runtime Truth

The auth/consent runtime truth is intentionally small and public-safe:

- `puter_runtime_loaded`
- `auth_api_available`
- `auth_attempted`
- `auth_completed`
- `auth_failed_reason`
- `consent_state`
- `raw_auth_payload_exposed=false`
- `provider_attempted=false`
- `provider_succeeded=false`
- `raw_provider_payload_exposed=false`

## Security Requirements

The dev auth/consent flow must never:

- bypass Puter auth or consent
- auto-accept consent
- hide or suppress Puter auth/consent UI
- call `puter.ai.chat`
- call provider APIs
- call `fetch`, `XMLHttpRequest`, `sendBeacon`, or `WebSocket`
- store credentials, tokens, cookies, `localStorage`, or `sessionStorage`
- return or display raw auth responses
- log raw auth responses
- expose secrets, env vars, provider config, private endpoints, billing data, debug data, raw provider payloads, or stack traces

## UX Guidance

The dev surface should show a clear manual action such as `Connect / Sign in with Puter`.

If Puter requires auth or consent, the operator must complete it in the browser. Omni must not ask for a Puter password, token, cookie, or credential. Retry remains manual and must still pass the relevant Access Layer, flag, allowlist, rollback, quota, routing, and consent gates.

## Relationship To Chat

This phase does not connect Puter to normal chat. It does not modify `sendOmniMessage`, does not change default provider behavior, and does not add any automatic provider path.

The auth/consent action only prepares the browser session for a later explicit dev/manual attempt. It does not trigger that attempt.

## Validation Expectations

Required tests cover:

- no auth call on import
- no auth call on render or mount
- button disabled when runtime is missing
- explicit click invokes `puter.auth.signIn` once
- success, cancellation, failure, and pending states are public-safe
- no `puter.ai.chat` during auth
- no direct network primitives
- no raw auth/provider payload exposure
- exact output and runtime truth key sets
- `/dev/puter` remains flag-gated
- normal chat and `sendOmniMessage` remain unchanged

## Future Phase

Next phase:

Phase 8P - Retry After Puter Consent/Auth
