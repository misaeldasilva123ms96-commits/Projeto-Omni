# Access Layer Puter Auth Status Dev Check

Status: Complete

## Purpose

Phase 8R adds a safe, dev-only Puter auth status check under `/dev/puter`.

Phase 8Q reached `consent_or_auth_pending`. Phase 8R gives the operator one explicit diagnostic button to check whether the browser Puter session reports signed in before any later manual retry attempt.

This phase does not connect Puter to normal chat, does not modify `sendOmniMessage`, does not make Puter the default provider, and does not enable Puter by default.

## Scope

Added:

```text
frontend/src/lib/puter/puterAuthStatus.ts
frontend/src/lib/puter/puterAuthStatus.test.ts
frontend/src/lib/puter/PuterAuthStatusDevSurface.tsx
frontend/src/lib/puter/PuterAuthStatusDevSurface.test.tsx
docs/product/access-layer-puter-auth-status-dev-check.md
```

Patched:

```text
frontend/src/pages/PuterDevRoutePage.tsx
```

The route page was patched to import and mount `PuterAuthStatusDevSurface`. It was not blindly replaced.

## Controls Preserved

- Dev-only under `/dev/puter`.
- `/dev/puter` remains flag-gated.
- No normal chat integration.
- No `sendOmniMessage` change.
- No default provider change.
- No `puter.ai.chat` call in the auth status check.
- No `fetch`, `XMLHttpRequest`, `sendBeacon`, or `WebSocket` path.
- No raw auth, user, or provider payload exposure.
- No token, cookie, localStorage, or sessionStorage storage or display.
- No auth status check on import, render, mount, or page load.
- Auth status check runs only after explicit operator click.
- Button remains disabled until the Puter runtime is loaded.

## Auth Status Helper

`checkPuterAuthStatus()` requires a trusted browser runtime:

- `globalThis.window` exists.
- `globalThis.document` exists.
- `window.document === document`.
- `window.puter` is present.
- `window.puter.auth.isSignedIn` is available.

It returns public-safe states only:

- `not_invoked`
- `runtime_not_loaded`
- `auth_api_unavailable`
- `auth_status_check_failed_safe`
- `signed_out`
- `signed_in_sanitized`
- `user_unavailable_safe`

If signed out, `getUser` is not called.

If signed in, `getUser` is called at most once. The raw user object is never returned. The only user output is presence booleans:

```ts
{
  user_present: boolean
  username_present: boolean
  email_present: boolean
  id_present: boolean
}
```

## Runtime Truth

The auth status output exposes only this exact public-safe runtime truth:

```ts
{
  puter_runtime_loaded: boolean
  auth_api_available: boolean
  auth_status_checked: boolean
  is_signed_in: boolean
  user_present: boolean
  sanitized_user_present: boolean
  raw_auth_payload_exposed: false
  provider_attempted: false
  provider_succeeded: false
  raw_provider_payload_exposed: false
}
```

The auth status check is not a provider request. Therefore:

- `provider_attempted=false`
- `provider_succeeded=false`
- `raw_provider_payload_exposed=false`

## Dev UI

The `/dev/puter` page now includes a separate button:

```text
Check Puter auth status
```

This remains separate from:

- `Load Puter runtime`
- `Connect / Sign in with Puter`
- `Run manual Puter check`
- `Retry manual Puter check after auth`

The button is disabled until the existing runtime detection reports that Puter is loaded.

The UI displays only:

- safe status
- `is_signed_in` boolean
- `user_present` boolean
- sanitized user presence booleans
- safe user message
- safe runtime truth booleans

## Security Requirements

This phase must never:

- call `puter.ai.chat`
- call provider APIs
- add direct network primitives
- store or display tokens
- store or display cookies
- inspect, store, or display localStorage/sessionStorage
- expose raw auth response
- expose raw user object
- expose raw provider payload
- expose stack traces
- expose provider config, private endpoint, billing, or debug data
- bypass or auto-accept Puter auth/consent
- connect Puter to normal chat

## Diagnostic Flow

1. Open `/dev/puter` with local ignored dev flags.
2. Click `Load Puter runtime`.
3. Click `Connect / Sign in with Puter`.
4. Complete Puter auth/consent manually if the browser/provider prompts the operator.
5. Click `Check Puter auth status`.
6. Interpret:
   - `signed_in_sanitized`: auth appears complete and sanitized.
   - `signed_out`: auth did not complete or user is signed out.
   - `auth_api_unavailable`: runtime loaded but auth status API is unavailable.
   - `runtime_not_loaded`: runtime is not present.
   - `user_unavailable_safe`: signed in but user details were unavailable safely.

## Validation Expectations

Tests cover:

- no status check on import/render/mount
- button disabled until runtime loaded
- runtime loaded plus click invokes `puter.auth.isSignedIn` once
- signed-out path does not call `getUser`
- signed-in path calls `getUser` at most once
- raw user object is not returned or displayed
- spoofed runtime is denied
- no `puter.ai.chat`
- no direct network primitives
- exact output key set
- exact runtime truth key set
- no raw auth/user/provider payload exposure
- `/dev/puter` remains flag-gated
- normal chat and `sendOmniMessage` remain unchanged

## Future Phase

Next phase:

```text
Phase 8S - One-user Real Response Retry With Auth Status
```

Phase 8S should use the safe `is_signed_in=true` status before manually retrying the existing safe Puter check. It must remain dev-only unless a later reviewed phase explicitly changes that.
