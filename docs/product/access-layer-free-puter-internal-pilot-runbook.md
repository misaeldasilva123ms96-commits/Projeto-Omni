# Access Layer Free/Puter Controlled Internal Pilot Runbook

Status: Phase 7X docs/runbook only. This runbook does not enable the pilot, change execution paths, connect Puter to normal chat, make Puter the default provider, or add provider/network calls.

## Purpose And Scope

This runbook describes how an internal operator may safely prepare, run, observe, stop, and report a controlled Free/Puter internal pilot. It is based on the current Access Layer contracts, regression matrix, runtime truth alignment, allowlisted pilot layer, internal-real pilot layer, and ops readiness documentation.

The only allowed real path remains:

`allowlisted pilot -> Phase 7R internal real pilot -> Phase 7L dev-real bridge -> existing gated manual harness`

This runbook must not be used to expose Puter to normal users. It must not be used to make Puter the default provider.

## Preconditions

Before any internal pilot attempt:

- Latest `origin/main` is fetched and the working branch is created from current `origin/main`.
- The worktree is clean except for known ignored/local-only files.
- CI is green for the target commit or PR.
- Backend Access Layer tests pass.
- Frontend typecheck, tests, build, and security regression pass.
- All Puter/Free flags in `frontend/.env.example` are reviewed and default to `false`.
- Rollback path is verified before the pilot starts.
- Allowlist marker or equivalent internal eligibility marker is reviewed.
- No normal-user exposure is planned.
- No default provider switch is present.
- Normal chat path is confirmed unchanged and still uses the Omni `sendOmniMessage` transport.
- The operator understands that consent/auth prompts must not be bypassed, hidden, auto-clicked, or auto-accepted.

## Required Flags

All flags default to `false` in `frontend/.env.example`:

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

For local/internal validation only, an operator may set the needed flags in an ignored `frontend/.env.local`. That file must remain untracked and must never contain secrets.

## Required Allowlist And Rollback State

Required before provider evaluation:

- `rollback_active=false`
- allowlist required when configured
- allowlist explicitly matched
- `plan_mode=free`
- quota allowed and not exceeded
- routing allowed
- selected provider family is `experimental_free_provider`
- consent/auth state is safe and not pending
- Puter runtime is available only when a real path is evaluated
- no tools, files, function-calling, long memory, or sensitive tools
- no public provider, adapter, policy, quota, credential, billing, debug, private endpoint, provider config, or raw provider payload overrides

Rollback must be tested before the pilot. Disabling pilot or allowlisted flags, removing the allowlist marker, or setting rollback active must deny new pilot attempts before provider execution.

## Required Checks Before Pilot

Git state:

```powershell
git fetch origin --prune
git branch --show-current
git status --short
git log --oneline origin/main -5
git status -sb .worktrees/consolidacao-main-stable
```

Backend Access Layer regression:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

Focused Puter runtime truth and pilot tests:

```powershell
cd frontend
npm.cmd exec vitest run src/lib/puter/freeModeChatBridgeContract.test.ts src/lib/puter/freeModeChatBridgeMock.test.ts src/lib/puter/freeModeChatBridgeDevReal.test.ts src/lib/puter/freeModePilotFlagContract.test.ts src/lib/puter/freeModePilotMock.test.ts src/lib/puter/freeModePilotInternalReal.test.ts src/lib/puter/freeModePilotAllowlisted.test.ts
```

Full frontend validation:

```powershell
cd frontend
npm.cmd run typecheck
$env:VITE_OMNI_EXPERIMENTAL_PUTER_FREE='false'
$env:VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE='false'
$env:VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE='false'
$env:VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK='false'
$env:VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL='false'
$env:VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE='false'
$env:VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT='false'
$env:VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL='false'
$env:VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED='false'
npm.cmd run test
npm.cmd run build
```

Root security regression:

```powershell
npm.cmd run test:security
```

GitHub PR checks when applicable:

```powershell
gh pr checks
gh pr status
```

If GitHub CLI is unavailable or not authenticated, record that limitation and rely on the visible CI result in GitHub.

## Required Local/Manual Validation Before Pilot

Before an internal pilot, validate the dev-only path locally:

1. Confirm `/dev/puter` is hidden when flags are false.
2. Enable only local ignored flags needed for `/dev/puter`.
3. Start the frontend dev server.
4. Open `/dev/puter`.
5. Confirm no Puter call happens on page load.
6. Confirm `Load Puter runtime` is a separate manual action.
7. Confirm the dev chat bridge action is a separate manual action.
8. Confirm normal chat is not involved.
9. Load the Puter runtime manually.
10. If consent/auth appears, do not bypass it.
11. If a manual call is attempted, use only a small safe prompt.
12. Record only public-safe status and sanitized result summary.

Do not upload files, enable tools, use function-calling, use long memory, paste secrets, or enter API keys.

## Consent/Auth Handling

Consent/auth behavior is user-controlled and provider-controlled. The operator must:

- stop if Puter requires unexpected login/auth that cannot be completed through the ordinary visible user flow
- never bypass auth or consent
- never auto-click or auto-accept consent
- never hide or simulate provider prompts
- treat unresolved auth/consent as `provider_consent_or_auth_pending` or another safe pending/denied state
- record only safe public state, not provider internals

Consent/auth pending is not success.

## Safe Prompt Rules

Allowed prompts:

- short
- non-sensitive
- no personal data
- no credentials
- no API keys or tokens
- no proprietary payloads
- no uploaded files
- no tool, function-calling, long-memory, or file requests

Example safe prompt:

```text
Reply with a short safe internal pilot check result.
```

Do not record the full prompt if it contains sensitive data. Sensitive prompts must not be used.

## Data Recording Policy

Allowed to record:

- safe status constants
- boolean runtime truth fields
- sanitized output presence
- sanitized visible result summary
- test command results
- timestamps when needed
- branch/commit identifiers
- route/path used
- consent/auth state as a safe constant

Forbidden to record:

- raw provider payload
- raw Puter response
- full prompt if sensitive
- API keys
- access tokens
- environment variables
- credentials
- stack traces
- `provider_config`
- `private_endpoint`
- billing or debug data
- user secrets
- raw user/session identifiers

## Runtime Truth Fields To Inspect

Inspect these public-safe fields when present:

- `pilot_enabled`
- `pilot_eligible`
- `pilot_denied_reason`
- `allowlisted_pilot`
- `allowlist_required`
- `allowlist_matched`
- `rollback_active`
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
- `raw_provider_payload_exposed`

Required interpretation:

- `provider_attempted=true` only after explicit gated real invocation.
- `provider_succeeded=true` only after sanitized success.
- `raw_provider_payload_exposed` must be `false`.
- `sanitized_output_present` must be boolean only.
- Denied, pending, or failed states must set safe reason constants.

## Public Payload Fields To Inspect

Inspect only public-safe fields:

- `allowed`
- `denied`
- `reason`
- `fallback_required`
- `sanitized_output`
- `runtime_truth`
- `mock_*` fields where mock-only paths are being validated

Never inspect or store raw provider internals. If a UI or payload displays raw provider data, stop immediately.

## Success Criteria

An internal pilot attempt is successful only if:

- all required tests/checks passed before the attempt
- only internal or allowlisted markers were used
- rollback was verified
- flags were respected
- normal chat remained unchanged
- no automatic Puter call occurred on load
- no tools, files, function-calling, or long memory were enabled
- consent/auth was handled visibly and safely
- `provider_attempted` changed only after explicit gated manual action
- `provider_succeeded` is true only for sanitized success
- `raw_provider_payload_exposed=false`
- no sensitive data appeared
- final report contains only allowed data

## Stop And Rollback Criteria

Stop immediately if any of the following occurs:

- consent/auth enters an unexpected loop
- raw provider payload appears
- raw Puter response appears
- stack trace appears
- `provider_config`, `private_endpoint`, billing, or debug data appears
- API key, token, environment variable, credential, or user secret appears
- normal chat path changes unexpectedly
- flags are not respected
- allowlist miss still allows
- rollback does not disable pilot
- quota or routing is denied but provider is attempted
- tools, files, function-calling, or long memory become available
- any sensitive data appears

Rollback steps:

1. Disable pilot flags.
2. Disable allowlisted flag.
3. Remove the allowlist marker.
4. Set or verify rollback active when available.
5. Stop the dev server/session.
6. Fall back to the normal chat path.
7. Do not delete user data.
8. Document the safe stop reason.

## Incident Response

If a stop condition occurs:

1. Stop the run immediately.
2. Do not retry until the issue is reviewed.
3. Do not copy raw payloads, stack traces, tokens, or provider internals into tickets or docs.
4. Preserve only safe command results and safe status constants.
5. Record the branch, commit, timestamp, safe reason, flags used, and rollback action.
6. Confirm no further provider attempts can occur.
7. Confirm normal chat still works or falls back as expected.
8. Open a follow-up issue or PR using only sanitized details.

## Final Pilot Report Template

```markdown
# Free/Puter Internal Pilot Report

- Date/time:
- Operator:
- Environment:
- Branch/commit:
- Current main commit:
- Flags used:
- `.env.local` used: yes/no, ignored/untracked confirmed:
- Allowlist state:
- Rollback state:
- Tests run:
- Route/path used:
- Normal chat path unchanged: yes/no
- Consent/auth state:
- provider_attempted:
- provider_succeeded:
- provider_failed_reason:
- fallback_triggered:
- raw_provider_payload_exposed:
- sanitized_output_present:
- Sanitized visible result summary:
- Result: success / denied / pending / failed / stopped
- Stop/rollback action:
- Issues found:
- Sensitive data observed: no / yes-stop
- Recommendation:
```

## Non-Recommendation

This runbook does not recommend broad normal-user enablement. Any broader pilot must wait for a separate reviewed phase with regression evidence, runtime truth/public payload alignment, rollback proof, allowlist proof, and explicit go/no-go approval.
