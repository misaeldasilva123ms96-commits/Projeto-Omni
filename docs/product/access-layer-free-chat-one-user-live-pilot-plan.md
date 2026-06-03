# Access Layer Free Chat One-user Live Pilot Plan

Status: Proposed plan/runbook, still not default

## Purpose And Scope

Phase 8M defines how a future one-user live pilot should be planned and run for the internal allowlisted Free Chat wiring path.

This document is docs/plan/runbook only. It does not execute the pilot, does not implement new behavior, does not change production chat behavior, does not connect Puter further into normal chat, does not make Puter the default provider, and does not enable Puter by default.

The planned pilot path remains constrained to:

```text
internal allowlisted chat wiring
-> allowlisted pilot wrapper
-> internal real pilot
-> dev-real bridge
-> existing gated manual harness
```

No future one-user pilot may bypass flags, allowlist, rollback, Access Layer gates, quota, routing, consent/auth, result UX handling, or public payload safety requirements.

## Why This Is Still Not Broad Release

This plan is for one controlled operator/user only. It does not approve broad normal-user rollout, default provider changes, production chat behavior changes, or silent activation.

The pilot remains:

- disabled by default
- allowlisted only
- rollback gated
- Access Layer gated
- quota and routing gated
- consent/auth non-bypassing
- public-safe only
- not default provider
- not connected more deeply into normal chat by this phase

## Operator And User Assumption

The pilot assumes a single authorized operator and one explicitly allowlisted user/session.

The operator must:

- understand the stop conditions
- verify flags and allowlist state before any live attempt
- use only the safe prompt policy
- avoid recording raw provider output
- stop immediately on any safety violation
- document only safe constants, booleans, sanitized summaries, and command results

The pilot user/session must be explicitly included through the reviewed allowlist mechanism. A missing or mismatched allowlist marker must deny before provider attempt.

## Required Branch And Main State

Before any live pilot execution:

- latest `origin/main` must be synced
- the pilot branch must be based on current `origin/main`
- worktree must be clean except ignored local env or explicitly documented local artifacts
- linked main worktree must not be modified
- CI must be green for the exact target commit
- no stale branch/base inconsistency may exist
- no unreviewed production chat wiring may be present

Required state checks:

```powershell
git fetch origin --prune
git branch --show-current
git status --short
git log --oneline origin/main -5
```

Linked main worktree read-only check:

```powershell
cd .worktrees/consolidacao-main-stable
git status -sb
git log --oneline -5
```

Return to the project root after inspection. Do not modify the linked main worktree.

## Required Flags

All relevant committed flags must remain default `false` in `frontend/.env.example`:

```env
VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false
VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_MOCKED_WIRING=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_INTERNAL_WIRING=false
```

For a future local pilot attempt, any enabled flags must be local, explicit, reviewed, and not committed. `frontend/.env.local` may be used only if it remains ignored/untracked and contains no secrets.

The pilot must stop if any committed file enables Puter by default.

## Required Allowlist State

The one-user live pilot requires:

- explicit allowlist marker or match
- exact target user/session inclusion through a reviewed mechanism
- allowlist miss denial before provider attempt
- allowlist mismatch denial before provider attempt
- no raw user/session identifier in public output
- test evidence proving allowlist miss denies

The pilot must not proceed if allowlist state is ambiguous.

## Required Rollback State

Rollback must be verified before any live attempt:

- rollback inactive for the approved pilot run
- rollback active denies before provider attempt
- disabling flags denies before provider attempt
- removing or mismatching the allowlist denies before provider attempt
- rollback procedure returns to normal chat behavior
- rollback does not delete user data

The operator must know how to disable local flags, remove the allowlist marker, enable the rollback marker if available, and stop the dev server/session.

## Required Access Layer Gates

All gates must pass before provider attempt:

- `plan_mode=free`
- quota allowed
- quota not exceeded
- routing allowed
- provider family is `experimental_free_provider`
- selected adapter is approved for the Free/Puter pilot path
- Access Snapshot Boundary style state is valid
- no public override fields
- no quota override fields
- no unsafe request fields
- no API keys, tokens, credentials, env vars, provider config, private endpoint, billing, debug, raw provider payload, or raw provider response fields
- no tools
- no files
- no function-calling
- no long memory
- no sensitive tools

Provider execution must not occur after any gate denies.

## Required Consent/Auth Handling

The Phase 8D consent/auth decision remains mandatory:

- never bypass Puter consent/auth
- never auto-accept consent
- never hide or suppress Puter auth/consent UI
- never ask for Puter credentials, password, tokens, cookies, localStorage, or sessionStorage contents
- represent pending consent/auth as `provider_consent_or_auth_pending` or a reviewed safe equivalent
- treat consent/auth pending as not success
- retry manually only after visible user/operator consent/auth completion
- rerun all gates on retry

If Puter requires consent/auth and the operator does not explicitly complete the visible browser flow, stop and record only the safe pending state.

## Required Result UX Handling

Future live pilot result handling must follow the result UX contract:

- user-facing result state is a safe category
- safe reason is a constant
- user message is Omni-authored and public-safe
- `sanitized_output` is `null` unless sanitized success occurs
- retry is manual and gate-aware
- consent/auth pending is not success
- provider failure is sanitized
- raw provider errors never reach UI or records

Allowed result categories include:

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

## Required Runtime Truth Fields

The pilot report should capture only public-safe runtime truth fields:

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
should_use_normal_chat
internal_allowlisted_wiring_enabled
```

Required invariants:

- `raw_provider_payload_exposed=false`
- `provider_attempted=true` only after gated invocation
- `provider_succeeded=true` only after sanitized success
- `sanitized_output_present` is boolean only
- consent/auth pending is not success
- denied states use safe constants

## Required Public Payload Fields

The public payload should expose only safe fields such as:

```text
ok
mode
should_use_normal_chat
status
reason
user_message
sanitized_output
retry_allowed
manual_action_required
fallback_triggered
runtime_truth
```

No public payload may contain raw provider payload, raw Puter response, raw provider request, stack trace, API key, token, credential, env var, cookie, storage content, provider config, private endpoint, billing/debug data, sensitive prompt echo, or raw user/session identifier.

## Safe Prompt Policy

Use a simple deterministic prompt only:

```text
Reply with exactly: OMNI_ONE_USER_LIVE_PILOT_OK
```

The prompt must not include:

- secrets
- API keys
- credentials
- personal or private data
- files
- tool requests
- function-calling requests
- long memory requests
- sensitive business data
- user secrets

Do not automatically resubmit the prompt. Retry must be manual and must rerun every gate.

## Data Recording Policy

Allowed to record:

- safe constants
- booleans
- sanitized visible summary
- command results
- test counts
- consent/auth safe state
- `provider_attempted` and `provider_succeeded` booleans
- `fallback_triggered`
- `raw_provider_payload_exposed=false`
- sanitized output presence

Forbidden to record:

- raw Puter response
- raw provider payload
- raw provider request
- tokens
- API keys
- env vars
- credentials
- cookies
- localStorage or sessionStorage contents
- provider config
- private endpoint
- billing/debug data
- stack traces
- sensitive prompts
- user secrets
- raw user/session identifiers

If forbidden data appears, stop and record only a safe stop reason.

## Required Validation Before Execution

Backend Access Layer:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

Focused Puter/wiring tests:

```powershell
cd frontend
npm.cmd exec -- vitest run src/lib/puter/freeModeChatInternalAllowlistedWiring.test.ts src/lib/puter/freeModeChatMockedWiring.test.ts src/lib/puter/freeModeChatWiringHarness.test.ts src/lib/puter/freeModePilotAllowlisted.test.ts src/lib/puter/freeModePilotInternalReal.test.ts src/lib/puter/freeModeChatBridgeDevReal.test.ts
```

Frontend validation:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
cd ..
npm.cmd run test:security
```

When `frontend/.env.local` enables local flags, frontend tests must also be run with explicit default-false overrides to prove flags-false behavior.

## Required Preconditions

The pilot cannot start unless all are true:

- latest `origin/main` synced
- clean worktree
- CI green
- backend Access Layer tests pass
- focused Puter/wiring tests pass
- frontend typecheck/test/build/security pass
- `frontend/.env.example` flags default false
- local `.env.local` remains ignored/untracked
- normal chat unchanged when flags false
- `sendOmniMessage` unchanged unless a future phase explicitly modifies it
- Puter not default provider
- allowlist marker verified
- rollback marker verified
- quota/routing denial prevents provider attempt
- consent/auth pending handled safely
- `raw_provider_payload_exposed=false`

## Stop Conditions

Stop immediately if any of these occur:

- any CI or security failure
- raw provider payload appears
- raw Puter response appears
- secret, token, API key, env var, credential, cookie, provider config, private endpoint, billing, or debug data appears
- stack trace appears
- consent/auth bypass appears
- consent/auth auto-accept appears
- consent/auth UI is hidden or suppressed
- provider is attempted when gates deny
- allowlist miss allows
- rollback active allows
- quota or routing denied but provider attempted
- normal chat changes unexpectedly
- Puter becomes default provider
- tools, files, function-calling, long memory, or sensitive tools appear
- BYOK, billing, or Pro behavior appears in the Free/Puter path

After a stop condition, do not copy unsafe material into docs, tickets, logs, screenshots, or public records.

## Rollback Procedure

Minimum rollback:

1. Disable local pilot flags.
2. Disable local internal wiring flag.
3. Disable local allowlisted/internal pilot flags.
4. Remove or mismatch the allowlist marker.
5. Enable rollback marker if a future ops control exists.
6. Stop the dev server or pilot session.
7. Fall back to normal chat.
8. Confirm no new provider attempts can occur.
9. Document only a safe rollback reason.
10. Do not delete user data.
11. Do not record raw provider output.

## Success Criteria

The one-user live pilot may be considered PASS only if:

- all preflight tests pass
- flags and allowlist are explicit and local/reviewed
- rollback path is verified
- normal chat remains unchanged when flags are false
- `sendOmniMessage` remains unchanged unless a future approved wiring phase explicitly changes it
- Puter is not default provider
- safe prompt policy is followed
- consent/auth is not bypassed
- provider is attempted only after all gates pass
- provider success, if any, is sanitized
- `raw_provider_payload_exposed=false`
- no forbidden data is recorded
- final report is complete and public-safe

## Failure Criteria

The pilot is FAIL or ABORTED if:

- any stop condition occurs
- required evidence is missing
- consent/auth cannot be handled safely
- any provider call occurs after a deny gate
- raw provider payload or sensitive data appears
- normal chat behavior changes unexpectedly
- rollback fails
- allowlist miss allows
- Puter becomes default provider

Use `PASS WITH LIMITATIONS` only when no safety violation occurred but the pilot could not complete because of an expected safe state, such as unresolved consent/auth pending.

## Final Execution Report Template

```markdown
# One-user Live Free Chat Pilot Execution Report

- Result: PASS / PASS WITH LIMITATIONS / FAIL / ABORTED
- Branch:
- Target commit:
- Base `origin/main` commit:
- Operator:
- Date/time:
- Environment:
- Local env used: yes/no
- Local env ignored/untracked: yes/no
- Flags used:
- Allowlist state:
- Rollback state:
- Access Layer gate state:
- Quota state:
- Routing state:
- Provider family:
- Prompt used: safe deterministic prompt only / not recorded if sensitive
- Consent/auth state:
- Provider attempted:
- Provider succeeded:
- Provider failed reason:
- Fallback triggered:
- Raw provider payload exposed:
- Sanitized output present:
- Public payload shape verified:
- Runtime truth shape verified:
- Backend Access Layer tests:
- Focused Puter/wiring tests:
- Frontend typecheck:
- Frontend test:
- Frontend build:
- Security test:
- Normal chat unchanged with flags false:
- `sendOmniMessage` unchanged:
- Puter default provider:
- Stop conditions checked:
- Issues found:
- Rollback action:
- Recommendation:
```

## Future Phase Recommendation

If this plan is accepted:

```text
Phase 8N - One-user Live Pilot Execution Log
```

If blocked:

```text
Phase 8N-blocked - Live Pilot Evidence Gap Fixes
```

## Explicit Non-Authorization

This plan does not execute or enable the pilot. It does not authorize broad normal-user rollout. It does not make Puter the default provider. It does not connect Puter further into normal chat. Any execution must happen in a future phase with explicit operator approval, current evidence, default-false committed flags, rollback, allowlist, Access Layer gates, consent/auth safety, and public-safe reporting.
