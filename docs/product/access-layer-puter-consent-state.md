# Omni Access Layer: Puter Consent/Auth State

Phase 7N records and handles the observed Puter consent/auth pending state in
the dev-only `/dev/puter` flow.

## Observed Validation Result

During local Phase 7M validation:

- `/dev/puter` was reachable with explicit local dev flags enabled.
- The loader started at `idle`.
- `Load Puter runtime` loaded exactly one fixed script:
  `https://js.puter.com/v2/`
- The dev chat bridge was manually invoked once with a safe prompt.
- Puter displayed a consent/auth dialog.
- Validation stopped without bypassing auth or consent.
- The visible dev bridge result remained pending.
- No raw provider payload, stack trace, API key, token, environment value,
  credential, provider config, private endpoint, billing data, or debug data was
  displayed.

## Safe Handling

The dev-only toggle treats unresolved Puter consent/auth as a safe public state.
If the provider call does not settle within the dev toggle timeout, the UI shows
`provider_consent_or_auth_pending`.

This state means the dev flow is waiting on user-facing Puter consent/auth or an
equivalent unresolved provider state. It is intentionally not treated as
success, and it does not expose raw provider internals.

## Restrictions

The dev flow must never:

- bypass Puter consent/auth
- auto-click or auto-accept prompts
- hide consent/auth prompts
- make Puter the default provider
- connect Puter to normal chat
- make automatic Puter or provider calls on app load
- expose raw provider payloads, raw requests, stack traces, credentials, API
  keys, access tokens, environment values, provider config, private endpoints,
  billing data, or debug data

## Limitations

Exact Puter auth state is not reliably available through the current
public-safe contract. The UI therefore uses a stable safe reason for unresolved
pending state rather than attempting to inspect or classify provider internals.

## Future Path

The next phase should stay contract-first. A controlled Free Chat pilot should
only proceed after consent/auth behavior remains explicit, safe, and
non-bypassing under review.
