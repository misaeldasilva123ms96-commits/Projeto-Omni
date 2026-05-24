# Omni Access Layer: Free Pilot Flag Contract

Phase 7P adds a pure pilot flag contract module for future controlled Free chat
pilot eligibility. The module is deterministic and public-safe. It does not
implement the pilot, connect Puter to normal chat, call Puter, create network
paths, make Puter the default provider, or change production chat behavior.

## Module

- Location: `frontend/src/lib/puter/freeModePilotFlagContract.ts`
- Version: `free_mode_pilot_flag_contract_v1`
- Future pilot flag: `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false`

All related flags remain disabled by default:

- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false`

## Contract Scope

The contract decides whether a future controlled Free pilot may be considered
eligible. It consumes only safe markers:

- plan mode
- feature flag state
- rollback state
- allowlist-required and allowlist-matched markers
- Access Layer quota and routing markers
- provider family marker
- consent/auth state marker
- public-safe adapter, boundary, and snapshot version markers
- requested capabilities and request options

The module must not consume raw account identifiers, raw user identifiers,
credentials, provider configuration, raw provider payloads, or raw request
payloads. If future callers have user or session context, they should pass only
server-normalized boolean eligibility markers.

## Required Gates

The contract allows eligibility only when all gates pass:

- plan mode is Free
- Free Puter flag is enabled
- chat bridge flag is enabled
- dev-real bridge flag, or a future pilot-approved equivalent marker, is enabled
- pilot flag is enabled
- rollback is not active
- allowlist matches when allowlist is required
- quota is allowed
- quota is not exceeded
- routing is allowed
- selected provider family is `experimental_free_provider`
- consent state is safe, such as `ready`, `granted`, or `not_required`
- selected adapter id is the approved experimental Free adapter id
- boundary and snapshot versions are approved
- no tools, files, function-calling, long memory, or sensitive tools are requested
- no public provider, adapter, policy, quota, credential, billing, or debug
  override fields are present

Any failed gate returns a denied decision before any pilot or provider execution
could occur.

## Rollback Behavior

Rollback is a first-class deny condition. When rollback is active:

- `pilot_enabled=false`
- `pilot_eligible=false`
- `denied=true`
- the reason is `rollback_active`
- provider attempted remains false
- fallback is triggered

Disabling `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT` should also deny the pilot
and preserve normal chat behavior.

## Allowlist Model

The contract supports an allowlist-required marker and an allowlist-matched
marker. It does not inspect raw user, account, or session identifiers.

If a future implementation needs allowlisting, that check should happen outside
this public contract and pass only:

- `allowlistRequired=true`
- `allowlistMatched=true` or `false`

Allowlist required plus unmatched must deny with `allowlist_not_matched`.

## Consent/Auth Handling

Consent/auth states must be represented as safe constants. Allowed states are
limited to safe values such as:

- `ready`
- `granted`
- `not_required`

Pending consent/auth states deny with a safe public reason such as
`provider_consent_or_auth_pending`. The pilot contract must never bypass,
auto-click, hide, or auto-accept provider consent/auth UI.

## Runtime Truth

The decision exposes only public-safe runtime truth:

- `pilot_enabled`
- `pilot_eligible`
- `pilot_denied_reason`
- `access_layer_plan_mode`
- `provider_family`
- `provider_attempted=false`
- `provider_succeeded=false`
- `provider_failed_reason`
- `fallback_triggered`
- `quota_allowed`
- `quota_exceeded`
- `routing_allowed`
- `consent_state`
- `selected_adapter_id`
- `boundary_version`
- `snapshot_version`
- `sanitized_output_present=false`
- `raw_provider_payload_exposed=false`

Runtime truth must not expose raw prompts, raw provider payloads, raw requests,
stack traces, credentials, API keys, access tokens, environment values, provider
config, private endpoints, billing data, or debug payloads.

## Forbidden Fields

Public request options and requested capabilities must deny if they include:

- provider mode or provider family overrides
- adapter id or selected adapter id overrides
- policy overrides
- quota limits
- API keys
- access tokens
- credentials
- environment values
- provider config
- private endpoints
- billing fields
- debug fields
- tools
- files
- function-calling
- long memory
- sensitive tools
- raw provider request, response, or payload fields

Unknown string values in public output must be normalized to safe constants such
as `unknown`, `invalid`, or an empty string. The contract must not echo raw
caller-controlled plan, provider, adapter, version, user, session, or account
strings.

## Non-Goals

This phase does not add:

- pilot runtime implementation
- normal chat integration
- Puter calls
- `puter.ai.chat` usage
- network calls
- default Puter provider behavior
- hidden provider execution
- BYOK storage
- billing
- tools
- files
- function-calling
- long memory

## Future Path

Next phase:

- Phase 7Q: Pilot Mocked Chat Integration

That future phase should remain disabled by default, mocked first, and gated by
this contract before any real pilot behavior is considered.
