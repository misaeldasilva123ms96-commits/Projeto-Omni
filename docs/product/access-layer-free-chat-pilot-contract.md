# Omni Access Layer: Controlled Free Chat Pilot Contract

Phase 7O defines the contract for a future controlled Free chat pilot that may
exercise the Puter Free Mode path under strict gates. This is a docs/contract
phase only. It does not implement the pilot, connect Puter to normal production
chat, make Puter the default provider, add hidden provider execution, or change
runtime behavior.

## Pilot Goals

The controlled pilot should validate the Free Mode Puter path without changing
the default Omni chat experience.

Goals:

- validate Free Mode Puter routing with strict Access Layer gates
- preserve normal chat behavior by default
- prevent Omni server-side provider cost exposure for this experimental path
- keep the browser/user-pays experimental model explicit
- collect only public-safe runtime truth
- avoid tools, files, function-calling, long memory, and sensitive tools
- keep all rollout and rollback behavior reviewable

## Current Boundary

The current system already has separate contracts for:

- Free chat bridge design
- Free chat bridge contract decisions
- mocked bridge orchestration
- dev-only real bridge execution
- dev-only chat toggle surface
- Puter consent/auth safe state handling

The pilot must build on these boundaries. It must not bypass PlanPolicy,
TokenQuota, ProviderRouter, ProviderRegistry, PublicAccessSnapshot,
AccessSnapshotBoundary, PuterClientAdapter, the browser skeleton, the manual
harness, or the dev-real bridge contracts.

## Pilot Eligibility

A future pilot participant is eligible only when all conditions pass:

- `plan_mode=free`
- all Access Layer gates pass
- quota is allowed
- routing is allowed
- `selected_provider_family=experimental_free_provider`
- Puter runtime is available in the browser
- Puter consent/auth state is handled safely
- required feature flags are enabled
- the user, account, or session is explicitly included in a pilot allowlist, if
  a future implementation adds an allowlist
- no tools are requested
- no files are attached
- no function-calling is requested
- no long memory behavior is enabled
- no sensitive tools are enabled
- no public input attempts provider, adapter, policy, or quota overrides

Any missing eligibility condition means no Puter pilot call.

## Feature Flags

Existing flags remain disabled by default:

- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE=false`

Future pilot flag:

- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false`

All flags must default to false. A future pilot implementation should require
the pilot flag plus the required lower-level bridge flags before Puter can be
considered. Flag false means normal chat behavior remains unchanged.

## Deny And Fail-Closed Behavior

The future pilot must deny or fall back before provider execution when:

- the pilot flag is false
- the plan is not Free
- quota is denied or exceeded
- the AccessSnapshotBoundary state is denied, malformed, or unsafe
- routing is denied
- the selected provider family is not `experimental_free_provider`
- Puter runtime is unavailable
- consent or auth is pending
- provider execution fails
- public input attempts a provider, adapter, policy, or quota override
- sensitive request fields appear
- tools, files, function-calling, long memory, or sensitive tools are requested

Consent/auth pending must not be treated as success. It should return a safe
visible reason such as `provider_consent_or_auth_pending` and must not bypass,
hide, auto-click, or auto-accept provider consent/auth UI.

Provider failure must be sanitized. No raw exception, stack trace, raw provider
payload, raw request, credential, token, environment value, provider config,
private endpoint, billing data, or debug material may be exposed.

## Runtime Truth Fields

A future pilot result should expose an exact public-safe runtime truth shape
similar to:

- `pilot_enabled`
- `pilot_eligible`
- `pilot_denied_reason`
- `access_layer_plan_mode`
- `provider_family`
- `provider_attempted`
- `provider_succeeded`
- `provider_failed_reason`
- `fallback_triggered`
- `quota_allowed`
- `quota_exceeded`
- `routing_allowed`
- `consent_state`
- `selected_adapter_id`
- `boundary_version`
- `snapshot_version`
- `sanitized_output_present`
- `raw_provider_payload_exposed=false`

Runtime truth must support auditability without exposing raw prompts beyond
existing safe chat handling, raw provider payloads, provider internals, private
configuration, credentials, key material, billing data, stack traces, or debug
dumps.

## Observability Rules

Pilot observability must be public-safe only:

- no raw provider response
- no raw provider request
- no hidden debug dumps
- no stack traces
- no API keys, access tokens, credentials, or environment values
- no provider config or private endpoint data
- no billing configuration
- no tool, file, or function-calling payloads

Metrics should focus on safe booleans, stable reason codes, quota/routing state,
fallback state, consent state, and whether sanitized output was present.

## Rollout Stages

Recommended rollout:

- Stage 0: local dev only
- Stage 1: internal/dev pilot only
- Stage 2: small allowlisted Free pilot
- Stage 3: broader Free pilot, still behind flags
- Stage 4: production candidate only after explicit review

No stage should make Puter the default provider without a separate reviewed
promotion. Broader rollout should require passing security, public-boundary,
privacy, consent/auth, and fallback review.

## Rollback

Rollback should be simple and safe:

- disable `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT`
- keep or restore the normal chat path
- preserve no-data-loss behavior for user-visible conversation state
- do not delete user state
- do not depend on remote configuration unless a future phase adds it safely
- keep fallback reasons public-safe

Disabling the pilot flag must stop new Puter pilot attempts.

## Future Implementation Test Plan

Future pilot implementation should add tests proving:

- flags false means normal chat remains unchanged
- pilot flag false means no Puter call
- non-Free plans are denied
- quota denied means no Puter call
- routing denied means no Puter call
- malformed or denied boundary state means no Puter call
- consent/auth pending returns a safe state
- provider failure is sanitized
- unsupported tools, files, function-calling, long memory, and sensitive tools
  are denied
- suspicious public override fields are denied
- sensitive fields are denied
- runtime truth has an exact approved key set
- raw provider payload is never exposed
- rollback flag disables pilot
- default provider behavior remains unchanged

## Future Phase Path

Recommended next phases:

- Phase 7P: Pilot flag contract module, no chat integration.
- Phase 7Q: Pilot mocked chat integration.
- Phase 7R: Internal-only real pilot behind flags.
- Phase 7S: Allowlisted Free pilot, still not default.

Each phase should remain small, reviewed, and fail-closed. The pilot should not
be enabled for normal users by default.

## Non-Goals

This phase does not add:

- pilot runtime implementation
- normal chat integration
- production Puter routing
- default Puter provider behavior
- hidden provider execution
- BYOK storage
- billing
- tools
- files
- function-calling
- long memory
- public provider override support
