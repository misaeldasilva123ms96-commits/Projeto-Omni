# Access Layer Puter Consent/Auth UX Decision

Status: Proposed for pilot planning

## Decision Title

Puter consent/auth in Omni Free Chat must remain explicit, user-controlled, public-safe, and non-bypassing.

## Context

The Free/Puter path is still disabled by default and outside normal chat. Current real-provider experimentation is limited to gated development, internal, and allowlisted surfaces that rely on Access Layer contracts, rollback controls, allowlist controls, and the existing Puter manual harness.

Phase 8C recorded a controlled one-user dry run with these safe observations:

- `/dev/puter` was reachable only with local ignored dev flags.
- No Puter script loaded on page load.
- No automatic provider call happened on page load.
- `Load Puter runtime` was a separate manual action.
- The Puter script source was exactly `https://js.puter.com/v2/`.
- Exactly one Puter script tag was loaded.
- A manual dev chat bridge attempt used the safe prompt `Reply with exactly: OMNI_ONE_USER_PILOT_OK`.
- The final visible state was `provider_consent_or_auth_pending`.
- No provider output returned.
- No raw provider payload, stack trace, API key, token, environment value, credential, provider config, private endpoint, billing data, or debug data appeared.
- Normal chat remained separate and unchanged.

Earlier consent-state documentation also recorded that Puter may display a consent/auth dialog and that validation must stop without bypassing auth or consent.

## Decision

Omni must never bypass Puter consent/auth.

Omni must never auto-accept consent, auto-click provider prompts, hide provider prompts, suppress consent/auth UI, or simulate consent/auth completion.

If Puter requires auth or consent, Omni should expose only a safe public state such as:

```text
provider_consent_or_auth_pending
```

Pending consent/auth is not a provider failure and not a successful response. It is a controlled pending or aborted state that may only continue after the user or operator explicitly completes the visible Puter consent/auth flow in the browser.

If consent/auth is not completed within a safe timeout, Omni should remain in a safe pending or aborted state. Omni must not retry automatically, must not send additional prompts automatically, and must not record raw provider output.

This decision applies before any broader pilot, normal-chat integration, or production Free/Puter exposure.

## UX States

The UX contract should use public-safe states only:

| State | Meaning | User/operator guidance |
| --- | --- | --- |
| `not_invoked` | No manual action has started. | Show idle state. |
| `runtime_not_loaded` | Puter runtime has not been manually loaded. | Offer manual runtime load only on allowed dev/pilot surfaces. |
| `runtime_loaded` | The Puter script loader completed. | Do not imply auth or AI readiness unless Puter chat is actually available. |
| `consent_or_auth_pending` | Consent/auth appears unresolved at the product state level. | Explain that user/browser action may be required. |
| `consent_or_auth_required` | Consent/auth is explicitly known or inferred as required. | Tell the user Omni cannot complete it automatically. |
| `provider_consent_or_auth_pending` | The provider attempt reached a pending timeout or unresolved auth/consent state. | Treat as pending or aborted, not success. |
| `provider_unavailable` | Puter runtime or chat capability is not available. | Show safe unavailable state and do not retry automatically. |
| `provider_failed_safe` | Provider call failed without exposed raw error. | Show safe failure reason only. |
| `provider_succeeded_sanitized` | Provider returned sanitized output after all gates passed. | Show sanitized result only. |
| `aborted_by_operator` | Operator stopped the flow. | Keep record public-safe. |
| `rollback_active` | Rollback gate blocks the pilot path. | Deny before provider attempt. |
| `denied_by_access_layer` | Plan, quota, routing, capability, provider, allowlist, or unsafe-field gate denied. | Deny before provider attempt. |

## Required UI Guidance

When consent/auth is pending or required, the UI should clearly communicate:

- Puter requires visible user/browser consent or authentication.
- Omni cannot complete consent/auth automatically.
- Omni will not ask for a Puter password, credential, token, API key, or cookie.
- Retry is manual only.
- The user/operator must complete consent/auth in the provider-controlled browser UI if continuing.
- Omni will not loop automatically.
- Omni will not send additional prompts automatically.
- Omni will not store Puter auth state.
- Omni will not collect or log tokens, cookies, credentials, localStorage, or sessionStorage contents.

The UI must not present pending consent/auth as provider success.

## Runtime Truth Mapping

For consent/auth pending:

| Field | Required value or convention |
| --- | --- |
| `provider_attempted` | `true` only if a real provider attempt reached the gated harness. Otherwise `false`. |
| `provider_succeeded` | `false` |
| `provider_failed_reason` | `provider_consent_or_auth_pending` or another reviewed safe equivalent |
| `fallback_triggered` | `true` where the current contract treats pending timeout as fallback, or `pending=true` in a future explicit pending convention |
| `raw_provider_payload_exposed` | `false` |
| `sanitized_output_present` | `false` |
| `consent_state` | `consent_or_auth_pending` |

Pending consent/auth should be observable only through safe constants and booleans. Runtime truth must not include raw provider errors, raw request/response data, stack traces, cookies, tokens, localStorage, sessionStorage, or debug payloads.

## Security Requirements

The consent/auth UX must preserve these invariants:

- No consent/auth bypass.
- No auto-click or auto-accept.
- No hidden consent handling.
- No automatic provider call on import, render, mount, app load, route load, or default path.
- No normal-chat integration until separately reviewed.
- No Puter default provider behavior.
- No rollback or allowlist bypass.
- No Access Layer gate bypass.
- No tools, files, function-calling, long memory, BYOK, billing, or Pro behavior in the Free/Puter path.
- No raw provider payload exposure.
- No secrets, API keys, access tokens, environment values, credentials, cookies, provider config, private endpoint, billing, debug data, or stack traces in public output, docs, tickets, logs, screenshots, or runtime truth.

## Data Handling Rules

Allowed to record:

- safe state constants
- booleans
- sanitized visible summaries
- command and test results
- whether consent/auth was required or pending
- route/path used
- branch and commit identifiers
- rollback and allowlist state as safe booleans/constants

Forbidden to record:

- raw Puter response
- raw provider payload
- raw provider request
- Puter tokens
- credentials
- API keys
- environment variables
- cookies
- localStorage contents
- sessionStorage contents
- provider config
- private endpoint
- billing data
- debug data
- stack traces
- sensitive prompts
- user secrets
- raw user/session identifiers

If forbidden data appears, the run must stop, unsafe material must not be copied into public artifacts, and only a safe stop reason may be recorded.

## Retry Rules

Retries must be manual.

A retry is allowed only after all of the following are true:

- The user or operator explicitly completes any visible Puter consent/auth flow.
- Access Layer gates are re-evaluated.
- Quota and routing still allow the request.
- Rollback is inactive.
- Required allowlist or internal markers still match.
- Provider family remains `experimental_free_provider`.
- No tools, files, function-calling, long memory, or sensitive tools are requested.
- No public override, quota override, credential, token, provider config, private endpoint, billing, debug, raw payload, or unsafe key field is present.
- The prompt is safe for the pilot or dry run.

Retries must not:

- automatically resubmit sensitive prompts
- use stored auth credentials
- inspect cookies, localStorage, or sessionStorage
- bypass consent/auth
- bypass quota, routing, allowlist, rollback, or Access Layer gates
- make Puter the default provider

## Stop Conditions

Stop immediately if any of these occur:

- repeated consent/auth loop
- raw provider payload appears
- raw Puter response appears
- credential, token, cookie, API key, or environment value appears
- stack trace appears
- `provider_config`, `private_endpoint`, billing, or debug data appears
- provider is attempted when Access Layer gates deny
- provider is attempted when quota or routing denies
- allowlist miss allows
- rollback active allows
- normal chat path is unexpectedly involved
- Puter becomes the default provider
- automatic provider call appears
- tools, files, function-calling, or long memory appear
- any sensitive prompt or user secret is present

After a stop condition, record only safe constants, booleans, command results, and a sanitized summary.

## Rollback Behavior

Rollback for consent/auth UX issues should:

1. Disable pilot and Puter flags.
2. Disable allowlisted and internal pilot flags when present.
3. Remove allowlist marker or set allowlist mismatch.
4. Set or verify rollback active when the future implementation supports it.
5. Stop the dev server or pilot session.
6. Return to the normal Omni chat path.
7. Preserve user data.
8. Record only a safe reason.

Rollback must not delete user data and must not expose raw provider or auth data.

## Open Questions

- Can the Puter browser runtime expose a public-safe auth-required state without revealing provider internals?
- Should future UI distinguish `consent_or_auth_required` from `provider_consent_or_auth_pending`, or keep one conservative pending state?
- What is the appropriate timeout for normal pilot UI versus `/dev/puter` manual validation?
- Should retry be a distinct action after consent/auth completion, or should the operator restart the whole gated flow?
- What public-safe telemetry is sufficient to prove consent/auth was required without recording provider UI contents?
- How should accessibility copy describe provider-controlled consent without implying Omni owns the auth flow?

## Future Implementation Guidance

Phase 8E should define the result handling and UX contract for these states before normal-chat integration.

Phase 8F should define the activation gate for any future controlled pilot path.

Do not implement normal-chat integration until UX state handling is explicitly implemented, tested, reviewed, and supported by Go/No-Go evidence.

Broader pilot work requires current Go/No-Go evidence, rollback proof, allowlist proof, consent/auth pending proof, runtime truth/public payload validation, and confirmation that Puter remains disabled by default and not the default provider.

## Explicit Non-Authorization

This decision record does not enable Puter, does not connect Puter to normal chat, does not implement new behavior, does not authorize broader rollout, and does not make Puter the default provider.
