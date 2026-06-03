# Access Layer Puter Retry After Auth

## Purpose

Phase 8P adds a dev-only manual retry path under `/dev/puter` after Puter auth/consent completes. It is meant for an operator validating the existing manual Puter dev flow after the browser consent/auth step has been completed.

This phase does not connect Puter to normal chat, does not make Puter the default provider, and does not enable Puter by default.

## Scope

- Dev-only retry state helper: `frontend/src/lib/puter/puterAuthRetryState.ts`
- Existing `/dev/puter` manual surface gets a separate retry button
- Existing auth/consent surface reports only safe public auth completion state to the dev route
- Existing manual harness remains the only retry execution path

No production chat execution path is changed.

## Required Controls

- Retry is manual only.
- Auth completion does not auto-run retry.
- Auth completion does not auto-submit any prompt.
- Retry is disabled until safe auth completion state is observed.
- Retry uses a fixed safe smoke prompt:
  `Reply with exactly: OMNI_PUTER_RETRY_AFTER_AUTH_OK`
- Retry does not reuse the editable manual prompt automatically.
- Retry still goes through the existing gated manual harness.
- Retry does not bypass Access Layer, quota, routing, allowlist, rollback, consent, or auth requirements.
- Retry does not call Puter from normal chat.
- Retry does not expose raw auth or provider payloads.

## Dev UI States

Safe retry states:

- `not_invoked`
- `runtime_not_loaded`
- `auth_required`
- `auth_completed`
- `retry_not_allowed`
- `retry_ready`
- `retry_invoked`
- `provider_consent_or_auth_pending`
- `provider_failed_safe`
- `provider_succeeded_sanitized`

The UI keeps these actions separate:

- `Connect / Sign in with Puter`
- `Run manual Puter check`
- `Retry manual Puter check after auth`

## Runtime Truth

The retry state exposes only public-safe runtime truth:

- `auth_completed`
- `retry_allowed`
- `retry_attempted`
- `provider_attempted`
- `provider_succeeded`
- `provider_failed_reason`
- `raw_auth_payload_exposed=false`
- `raw_provider_payload_exposed=false`
- `sanitized_output_present`

## Security Requirements

The retry flow must never:

- auto-run after auth
- auto-submit prompts after auth
- bypass Puter consent/auth
- auto-accept consent
- hide or suppress Puter consent/auth UI
- store credentials, tokens, cookies, `localStorage`, or `sessionStorage`
- log raw auth responses
- log raw provider responses
- expose secrets, env vars, raw provider payloads, stack traces, provider config, private endpoints, billing data, or debug data
- enable BYOK, billing, tools, files, function-calling, or long memory

## Relationship To Normal Chat

This phase does not touch normal chat and does not modify `sendOmniMessage`. The retry button is mounted only in the dev route and uses the existing manual harness path.

## Validation Expectations

Required tests cover:

- no retry on import, render, or mount
- auth completion does not auto-run manual check
- retry disabled before auth completion
- retry allowed after mocked auth completion
- retry invokes the existing manual harness only on explicit click
- retry uses the fixed safe smoke prompt
- retry has no direct `puter.ai.chat` call
- retry adds no `fetch`, `XMLHttpRequest`, `sendBeacon`, or `WebSocket` path
- retry handles sanitized success and safe failure
- exact retry output/runtime truth key sets
- no raw auth/provider payload exposure
- `/dev/puter` remains flag-gated
- normal chat and `sendOmniMessage` remain unchanged

## Future Phase

Next phase:

Phase 8Q - One-user Real Response Log
