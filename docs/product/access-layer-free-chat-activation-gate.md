# Access Layer Free Chat Activation Gate

Status: Proposed final gate for future activation planning

## Purpose

This document defines the final gate that must be satisfied before any future phase may connect the Free/Puter path to normal chat or run a broader controlled Free Chat pilot.

This is a docs/gate artifact only. It does not activate Free Chat, does not implement pilot behavior, does not connect Puter to normal chat, does not make Puter the default provider, and does not enable Puter by default.

## Scope

This gate applies to any future Free/Puter activation mode:

- local/dev only
- internal-only
- one-user allowlisted
- small allowlisted pilot
- any future normal-chat-adjacent experiment

The gate must be evaluated against the exact branch, commit, environment, flags, allowlist state, rollback state, and runtime truth/public payload implementation under review.

## Non-Goals

This document does not:

- implement activation
- change execution paths
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

## Required Evidence

Activation cannot be considered until all evidence below is present and current for the exact target commit.

| Evidence | Required result |
| --- | --- |
| CI checks | Green for the exact branch/commit. |
| Backend Access Layer pytest | Green. |
| Focused Puter/pilot Vitest | Green. |
| Frontend validation | `typecheck`, `test`, `build`, and `test:security` green. |
| `.env.example` flag audit | Every Puter/Free flag defaults to `false`. |
| Local env handling | Any `.env.local` used for validation remains ignored/untracked and contains no secrets. |
| Allowlist miss | Denies before provider execution. |
| Rollback active | Denies before provider execution. |
| Quota denied or exceeded | Denies before provider execution. |
| Routing false | Denies before provider execution. |
| Wrong provider family | Denies before provider execution. |
| Consent/auth pending | Safe public state, not success, no bypass. |
| Result UX contract | All user-visible states map through safe result categories. |
| Runtime truth/public payload | Exact-key, public-safe, no raw provider payload. |
| Normal chat flags-false check | Normal chat unchanged when flags are false. |
| Default provider check | Puter is not the default provider. |

## Required Flags

All relevant committed defaults must remain `false` in `frontend/.env.example`:

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

Future activation may only use local, internal, or deployment-specific flags in a reviewed implementation phase. No committed default may flip to `true` as part of this gate.

## Required Allowlist State

For any internal, one-user, small pilot, or normal-chat-adjacent activation:

- allowlist control must exist
- allowlist must be required when configured
- allowlist marker or match must be explicit
- allowlist miss must deny before provider execution
- allowlist mismatch must deny before provider execution
- raw user/session identifiers must not be exposed in public output

Activation is blocked if an allowlist miss can reach provider execution.

## Required Rollback State

Rollback must be verified before activation:

- rollback control exists or an equivalent flag-off rollback process is documented
- rollback active denies before provider execution
- disabling pilot flags denies before provider execution
- disabling allowlisted/internal flags denies before provider execution
- removing allowlist marker denies before provider execution
- rollback process returns to normal Omni chat behavior
- rollback must not delete user data

Activation is blocked if rollback cannot stop new provider attempts.

## Required Access Layer Gates

The following gates must pass before any provider attempt:

- `plan_mode=free`
- quota allowed
- quota not exceeded
- routing allowed
- provider family is `experimental_free_provider`
- selected adapter is allowlisted for the Free/Puter path
- AccessSnapshotBoundary-style state is valid
- no tools
- no files
- no function-calling
- no long memory
- no sensitive tools
- no public provider override fields
- no quota override fields
- no credentials, API keys, tokens, env vars, provider config, private endpoint, billing, debug, or raw provider fields

Activation is blocked if provider execution can occur after any gate denies.

## Required Consent/Auth UX Handling

The consent/auth decision record must be implemented and tested before activation:

- Omni never bypasses Puter consent/auth.
- Omni never auto-clicks or auto-accepts consent.
- Omni never hides or suppresses Puter auth/consent UI.
- Consent/auth pending maps to `provider_consent_or_auth_pending` or a reviewed safe equivalent.
- Consent/auth pending is not provider success.
- Consent/auth pending is not raw provider failure.
- Retry after consent/auth is manual only.
- Retry reruns all Access Layer, quota, routing, allowlist, rollback, flag, runtime, and unsafe-field gates.
- Omni never asks for Puter password, credentials, tokens, cookies, localStorage, or sessionStorage contents.

Activation is blocked if consent/auth can be bypassed, hidden, auto-accepted, or treated as success.

## Required Result UX Handling

The result UX contract must be implemented and tested before activation:

- result categories are explicit and public-safe
- user-facing messages are Omni-authored safe text
- raw provider errors never reach UI
- `provider_consent_or_auth_pending` is a safe pending/aborted state
- `provider_failed_safe` exposes only safe constants
- `provider_succeeded_sanitized` exposes only sanitized output
- retry rules are manual and gate-aware
- exact public output key-set tests exist
- exact runtime truth key-set tests exist
- serialized output leak tests exist

Activation is blocked if UI consumes raw provider errors or raw provider payloads.

## Required Runtime Truth And Public Payload Safety

Runtime truth and public payloads must remain exact-key and public-safe.

Required runtime truth fields, where applicable:

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
- `sanitized_output_present` is boolean only
- denied states use safe reason constants
- pending consent/auth is not success
- mock provider status remains separate from real provider status

Forbidden in public output:

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
- sensitive prompt echo
- raw user/session identifiers

## Required Tests

Before activation, these tests or equivalent CI checks must pass:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

Focused Puter/pilot Vitest must cover:

- Puter browser adapter
- Puter manual harness
- Puter script loader
- Puter dev manual surface
- `/dev/puter` route
- dev chat toggle surface
- Free chat bridge contract
- Free chat bridge mock
- dev-real bridge
- pilot flag contract
- pilot mock
- internal real pilot
- allowlisted pilot
- result UX contract implementation when it exists
- activation gate implementation when it exists

Full frontend validation must pass:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
```

Root security regression must pass:

```powershell
npm.cmd run test:security
```

When local `frontend/.env.local` enables dev flags, full frontend and focused Puter/pilot tests must also run with explicit default-false overrides to prove flags-false behavior.

## Required Operator Approval

Activation requires explicit operator approval recorded in a decision artifact.

Approval must include:

- target branch and commit
- activation mode
- approved scope
- maximum users
- required flags
- allowlist mechanism
- rollback owner
- observability owner
- stop conditions
- evidence links or command outputs
- approval date
- next review date

No implicit approval is allowed from this document.

## Required Stop Conditions

Activation must stop immediately if any condition appears:

- any required test fails
- CI is not green
- raw provider payload appears
- raw Puter response appears
- stack trace appears
- API key, token, env var, credential, cookie, provider config, private endpoint, billing, or debug data appears
- sensitive prompt is echoed
- consent/auth is bypassed
- consent/auth is hidden or auto-accepted
- rollback fails
- allowlist miss allows
- quota or routing denied but provider attempted
- wrong provider family reaches provider execution
- Puter becomes default provider
- normal chat changes when flags are false
- tools, files, function-calling, or long memory are enabled
- BYOK, billing, or Pro behavior is mixed into the Free/Puter path
- stale branch/base inconsistency exists

Stop records must use safe constants and sanitized summaries only.

## Required Rollback Process

Rollback must be documented for the target environment. Minimum rollback:

1. Disable `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT`.
2. Disable `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED`.
3. Disable `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL` if used.
4. Disable `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL` if used.
5. Disable `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE`.
6. Disable `VITE_OMNI_EXPERIMENTAL_PUTER_FREE`.
7. Remove or mismatch allowlist marker.
8. Set or verify rollback active if a future ops control exists.
9. Stop the pilot session or dev server.
10. Confirm normal Omni chat path remains available.
11. Confirm no new provider attempts can occur.
12. Record only a safe rollback reason.

Rollback must not delete user data and must not expose raw provider or auth data.

## Activation Modes

The gate may produce only one of these decisions:

- `NO-GO`
- `GO: local/dev only`
- `GO: internal-only`
- `GO: one-user allowlisted`
- `GO: small allowlisted pilot`

No activation mode authorizes broad normal-user rollout. No activation mode makes Puter the default provider. Any normal-chat integration requires a future explicit implementation phase with tests, PR checks, review, and manual merge.

## Decision Result Template

```markdown
# Free/Puter Activation Gate Decision

- Decision: NO-GO / GO: local-dev only / GO: internal-only / GO: one-user allowlisted / GO: small allowlisted pilot
- Approved scope:
- Max users:
- Target branch:
- Target commit:
- Required flags:
- Allowlist mechanism:
- Rollback owner:
- Observability owner:
- Stop conditions:
- Evidence links/commands:
- CI result:
- Backend Access Layer pytest:
- Focused Puter/pilot Vitest:
- Frontend typecheck/test/build/security:
- `.env.example` flag audit:
- Local env ignored/untracked:
- Allowlist miss denial:
- Rollback active denial:
- Quota/routing/provider-family denial:
- Consent/auth pending safety:
- Result UX contract compliance:
- Runtime truth/public payload safety:
- Normal chat unchanged with flags false:
- Puter default provider: no / yes-stop
- Approval date:
- Next review:
- Notes:
```

## Future Phase Recommendation

If this gate is satisfied:

```text
Phase 8G - Controlled Free Chat Pilot Wiring Plan
```

If this gate is not satisfied:

```text
Phase 8G-blocked - Activation Evidence Gap Fixes
```

Phase 8G must still be explicit, reviewed, tested, disabled by default, rollback-safe, allowlisted when applicable, and manually merged only by the project owner.

## Explicit Non-Authorization

This document does not activate Free Chat. It does not authorize broad normal-user rollout. It does not make Puter the default provider. It does not connect Puter to normal chat. Any activation must happen in a future phase with explicit implementation, tests, PR checks, review, and manual merge.
