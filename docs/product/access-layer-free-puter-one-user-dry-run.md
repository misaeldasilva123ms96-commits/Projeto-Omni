# Access Layer Free/Puter One-User Allowlisted Pilot Dry Run

Status: Phase 7Y docs/runbook/validation record only. This document does not enable Puter for normal users, change execution paths, connect Puter to normal chat, make Puter the default provider, or add provider/network calls.

## Purpose And Scope

This document prepares a one-user allowlisted pilot dry run for the Free/Puter path using the current internal pilot runbook, regression matrix, runtime truth alignment, allowlisted pilot contract, and ops readiness guidance.

The dry run is operator-only and one-user scoped. It is a readiness rehearsal, not production rollout. It must verify that a single allowlisted/internal marker can be evaluated safely while rollback, Access Layer gates, and public-safe reporting remain intact.

The only allowed real path remains:

`allowlisted pilot -> Phase 7R internal real pilot -> Phase 7L dev-real bridge -> existing gated manual harness`

## Not Normal-User Enablement

This dry run is still not normal-user enablement because:

- all Puter/Free flags default to `false`
- an explicit allowlist marker/match is required
- rollback must be inactive and verified before the run
- normal chat behavior must remain unchanged
- Puter must not become the default provider
- tools, files, function-calling, long memory, BYOK, billing, and Pro behavior remain out of scope
- no broad user segment is included
- no raw provider payload or sensitive data may be recorded

## One-User / Operator-Only Assumption

The dry run assumes one internal operator or one explicitly allowlisted test session. The operator must not use real customer data, sensitive prompts, uploaded files, credentials, API keys, tokens, or private configuration.

If the test cannot be kept to a single allowlisted/operator context, stop and do not run the dry run.

## Required Flags

All flags are default `false` in `frontend/.env.example`:

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

For local dry-run preparation, flags may be set only in ignored local configuration such as `frontend/.env.local`. Do not commit local flag changes. Do not store secrets in env files.

## Required Dry-Run Gates

Before starting:

- latest `origin/main` is synced
- worktree is clean except known untracked local artifacts
- CI/checks are green
- backend Access Layer tests pass
- focused Puter tests pass
- frontend typecheck/test/build/security pass
- all flags are reviewed
- allowlist marker is reviewed
- rollback path is verified
- no normal chat behavior change is present
- no default provider switch is present
- no production chat integration is present

## Required Access Layer Gates

The dry run must deny before provider execution unless all are true:

- `plan_mode=free`
- quota allowed
- quota not exceeded
- routing allowed
- selected provider family is `experimental_free_provider`
- safe AccessSnapshotBoundary-style state is present
- selected adapter ID is allowlisted
- boundary and snapshot versions are expected
- no tools
- no files
- no function-calling
- no long memory
- no sensitive tools
- no public provider override
- no quota/policy override
- no sensitive fields

## Required Allowlist And Rollback State

Required state:

- allowlist marker exists for the one dry-run subject/session
- allowlist is explicitly matched
- allowlist miss denies
- rollback is inactive for the dry-run attempt
- rollback active denies before provider execution
- disabling pilot or allowlisted flags denies before provider execution

If allowlist miss still allows, stop immediately.

## Consent/Auth Safe Handling

Consent/auth must stay visible and user-controlled:

- do not bypass consent/auth
- do not auto-click or auto-accept prompts
- do not hide provider prompts
- do not simulate provider prompts
- unresolved consent/auth is a safe pending/denied state
- `provider_consent_or_auth_pending` is an acceptable safe state
- pending is not success

If Puter enters an unexpected consent/auth loop, stop and rollback.

## Safe Prompt Policy

Use only a simple smoke prompt:

```text
Reply with a short safe one-user dry run result.
```

Prompt rules:

- no secrets
- no API keys
- no access tokens
- no credentials
- no real user data
- no files
- no tools or function-calling
- no long memory
- no private project data
- no sensitive personal data

Do not record the full prompt if it contains sensitive data. Sensitive prompts must not be used.

## Data Policy

Allowed to record:

- safe constants
- booleans
- sanitized output summary
- command results
- consent/auth safe state
- `provider_attempted`
- `provider_succeeded`
- `fallback_triggered`
- `raw_provider_payload_exposed=false`
- `sanitized_output_present`
- branch and commit identifiers
- timestamps if needed

Forbidden to record:

- raw Puter response
- raw provider payload
- full sensitive prompt
- tokens
- API keys
- environment variables
- credentials
- `provider_config`
- `private_endpoint`
- billing/debug data
- stack traces
- raw user/session identifiers

## Validation Commands

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

Focused Puter Vitest group:

```powershell
cd frontend
npm.cmd exec vitest run src/lib/puter/freeModePuterBrowserAdapter.test.ts src/lib/puter/freeModePuterManualHarness.test.ts src/lib/puter/puterScriptLoader.test.ts src/lib/puter/PuterDevManualSurface.test.tsx src/pages/PuterDevRoutePage.test.tsx src/lib/puter/PuterFreeChatDevToggleSurface.test.tsx src/lib/puter/freeModeChatBridgeContract.test.ts src/lib/puter/freeModeChatBridgeMock.test.ts src/lib/puter/freeModeChatBridgeDevReal.test.ts src/lib/puter/freeModePilotFlagContract.test.ts src/lib/puter/freeModePilotMock.test.ts src/lib/puter/freeModePilotInternalReal.test.ts src/lib/puter/freeModePilotAllowlisted.test.ts
```

Frontend validation:

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

If `gh` is unavailable or unauthenticated, record that limitation and use visible GitHub CI status.

## Dry-Run Procedure

1. Confirm git state, branch, and current `origin/main`.
2. Confirm linked main worktree is read-only and not modified.
3. Run backend Access Layer regression.
4. Run focused Puter tests.
5. Run frontend typecheck/test/build/security.
6. Confirm `.env.example` flags default to `false`.
7. Confirm normal chat path still uses `sendOmniMessage`.
8. Configure local ignored flags only if browser/manual validation is part of the dry run.
9. Confirm allowlist marker/match for one operator/session.
10. Confirm rollback path denies before provider execution.
11. Confirm `/dev/puter` remains hidden when required flags are false.
12. Open `/dev/puter` only with local explicit flags.
13. Confirm no Puter call happens on page load.
14. Manually load Puter runtime only if needed for the dry run.
15. Stop if consent/auth behaves unexpectedly.
16. Use only the safe smoke prompt if a manual provider attempt is explicitly in scope.
17. Record only safe runtime truth and sanitized visible summary.
18. Disable local pilot/allowlisted flags and remove allowlist marker after the dry run.
19. Confirm no tracked files changed except intended docs for this phase.

## Stop Conditions

Stop immediately if:

- consent/auth enters an unexpected loop
- raw Puter response appears
- raw provider payload appears
- stack trace appears
- token, API key, environment variable, credential, or user secret appears
- `provider_config`, `private_endpoint`, billing, or debug data appears
- flags are not respected
- allowlist miss still allows
- rollback does not disable pilot
- quota denied but provider attempted
- routing denied but provider attempted
- normal chat behavior changes unexpectedly
- Puter becomes default provider
- tools, files, function-calling, or long memory become available

## Rollback Procedure

1. Disable `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT`.
2. Disable `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED`.
3. Disable `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL`.
4. Remove the allowlist marker.
5. Set rollback active when available.
6. Stop dev server/session.
7. Fall back to normal chat.
8. Do not delete user data.
9. Document only the safe rollback reason.
10. Confirm no new provider attempts can occur.

## Dry-Run Final Report Template

```markdown
# Free/Puter One-User Allowlisted Dry Run Report

- Date/time:
- Operator:
- Branch:
- Branch commit:
- origin/main commit:
- Worktree clean before run: yes/no
- Linked main read-only status:
- Flags used:
- `.env.local` used: yes/no
- `.env.local` ignored/untracked confirmed: yes/no
- Allowlist state:
- Allowlist matched: true/false
- Rollback state:
- Rollback verified before run: yes/no
- Access Layer tests:
- Focused Puter tests:
- Frontend typecheck/test/build/security:
- Route/path used:
- Normal chat behavior unchanged: yes/no
- Default provider unchanged: yes/no
- Consent/auth state:
- provider_attempted:
- provider_succeeded:
- provider_failed_reason:
- fallback_triggered:
- raw_provider_payload_exposed:
- sanitized_output_present:
- Sanitized output summary:
- Result: success / denied / pending / failed / stopped
- Issues found:
- Stop condition triggered: yes/no
- Rollback action:
- Sensitive data observed: no / yes-stop
- Recommendation:
```

## Recommendation Boundary

This dry-run document does not recommend broader rollout. The next phase should be Phase 7Z: Go/No-Go Review for broader pilot, and that phase should still require explicit review before any broader enablement.
