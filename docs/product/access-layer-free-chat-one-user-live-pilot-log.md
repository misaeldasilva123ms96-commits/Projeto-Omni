# Access Layer Free Chat One-user Live Pilot Log

Status: PASS WITH LIMITATIONS

## Purpose

Phase 8N records a controlled one-user live pilot attempt for the internal allowlisted Free Chat wiring path using the Phase 8M plan.

This execution log is docs-only. It does not implement new behavior, does not change production chat behavior, does not make Puter the default provider, does not enable Puter by default in committed files, and does not expose the path to normal users.

## Branch And Main State

- Branch: `feature/access-layer-free-chat-one-user-live-pilot-log`
- Base: `origin/main`
- `origin/main` latest commit at execution: `549b39d Merge pull request #218 from misaeldasilva123ms96-commits/feature/access-layer-free-chat-one-user-live-pilot-plan`
- Current worktree before execution: clean except pre-existing untracked local artifacts:
  - `.coverage`
  - `smoke.json`
- Linked main worktree status was inspected read-only:
  - branch: `main`
  - latest commit: `549b39d Merge pull request #218 from misaeldasilva123ms96-commits/feature/access-layer-free-chat-one-user-live-pilot-plan`
  - no linked main worktree files were modified

## Local Environment State

- `frontend/.env.local`: present as ignored local config.
- `.env.local` was not committed.
- No secrets, API keys, tokens, credentials, or private data were added to committed files.
- The local dev server was started with process-only environment flags for the controlled attempt.
- The dev server was stopped during cleanup.

## Committed Flag Defaults

`frontend/.env.example` keeps all Puter and Free flags default-disabled:

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

No committed file enables Puter by default.

## Operator And Environment

- Operator: Codex local validation run.
- Date: 2026-05-25.
- Environment: local frontend dev server on `http://127.0.0.1:5173`.
- Route/path used: `/dev/puter`.
- Browser surface: Codex in-app browser.
- Normal chat path: not involved.
- `sendOmniMessage`: unchanged and not invoked by this attempt.

## Pre-flight Validation

Backend Access Layer:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

Result:

```text
83 passed, 82 subtests passed
```

Focused Puter/wiring Vitest:

```powershell
cd frontend
npm.cmd exec -- vitest run src/lib/puter/freeModeChatInternalAllowlistedWiring.test.ts src/lib/puter/freeModeChatMockedWiring.test.ts src/lib/puter/freeModeChatWiringHarness.test.ts src/lib/puter/freeModePilotAllowlisted.test.ts src/lib/puter/freeModePilotInternalReal.test.ts src/lib/puter/freeModeChatBridgeDevReal.test.ts src/lib/puter/freeModePuterManualHarness.test.ts
```

Result:

```text
7 test files passed
89 tests passed
```

Frontend typecheck:

```powershell
cd frontend
npm.cmd run typecheck
```

Result:

```text
passed
```

Frontend full tests:

```powershell
cd frontend
npm.cmd run test
```

Result:

```text
25 test files passed
230 tests passed
runtime console wiring checks passed
```

Frontend build:

```powershell
cd frontend
npm.cmd run build
```

Result:

```text
passed
```

Note: Vite emitted the existing chunk-size warning. It did not fail the build.

Root security regression:

```powershell
npm.cmd run test:security
```

Result:

```text
security regression suite: ok
```

Note: security tests emitted existing chart sizing stderr from `RuntimePanel` tests. The security suite passed.

## Route And Runtime Validation

Route:

- `/dev/puter` was reachable.
- The route displayed development-only Puter manual validation controls.
- Normal chat was not involved.
- Controls remained manual and dev/flag gated.

Page load:

- No Puter script loaded on page load.
- `window.puter` was not present on page load.
- No automatic provider call happened on page load.

Runtime load:

- `Load Puter runtime` was clicked manually.
- Script source loaded: `https://js.puter.com/v2/`
- Exact Puter script count after load: `1`
- Loader visible state: `loaded`
- Script loading itself did not call AI.
- After script load in this local browser context, `window.puter.ai.chat` was not available.

## Live Pilot Attempt

Safe prompt classification: safe smoke prompt.

Prompt used:

```text
Reply with exactly: OMNI_ONE_USER_LIVE_PILOT_OK
```

Attempt:

- The existing manual dev Free chat bridge action was invoked once.
- No new production chat wiring was added.
- No direct `puter.ai.chat` call was made from chat components.
- No direct `fetch`, `XMLHttpRequest`, `navigator.sendBeacon`, or `WebSocket` provider path was added.

Observed result:

- Visible result state: `provider_consent_or_auth_pending`
- Provider output returned: no
- Sanitized output present: false
- Raw provider payload exposed: false
- Raw Puter response recorded: no
- Browser error console count during attempt: `0`
- Exact Puter script count after attempt: `1`

Consent/auth:

- No consent/auth bypass occurred.
- No auto-accept occurred.
- No auth/consent UI was hidden or suppressed.
- No Puter credentials, tokens, cookies, localStorage, or sessionStorage contents were requested or recorded.
- Because the provider remained unavailable/pending through the existing safe state, the attempt stopped without trying to bypass or force continuation.

## Runtime Truth Summary

Public-safe runtime summary:

```text
provider_attempted=true
provider_succeeded=false
provider_failed_reason=provider_consent_or_auth_pending
fallback_triggered=true
raw_provider_payload_exposed=false
sanitized_output_present=false
consent_state=provider_consent_or_auth_pending
```

Interpretation:

- `provider_attempted=true` means the existing gated manual bridge action was invoked.
- `provider_succeeded=false` because no sanitized provider output was returned.
- `provider_consent_or_auth_pending` is treated as safe pending, not success.

## Data Recording Policy Result

Recorded:

- safe constants
- booleans
- sanitized visible state summary
- command results
- test counts
- route/path used
- provider attempt/success booleans
- fallback and payload exposure states

Not recorded:

- raw Puter response
- raw provider payload
- raw provider request
- tokens
- API keys
- env var values
- credentials
- cookies
- localStorage/sessionStorage contents
- provider config
- private endpoint
- billing/debug data
- stack traces
- sensitive prompts
- user secrets
- raw user/session identifiers

## Stop Conditions

No unsafe stop condition was observed.

Checked conditions:

- raw provider payload appeared: no
- raw Puter response appeared: no
- stack trace appeared in visible output: no
- secret/env/debug/provider config/private endpoint/billing appeared: no
- normal chat behavior changed unexpectedly: no
- `sendOmniMessage` changed unexpectedly: no
- provider attempted when gates deny: no evidence
- allowlist miss allowed: no evidence
- rollback active allowed: no evidence
- quota/routing denied but provider attempted: no evidence
- Puter became default provider: no
- tools/files/function-calling/long memory appeared: no

## Cleanup

- Dev server/session stopped.
- `frontend/.env.local` remains ignored/untracked.
- `.coverage` and `smoke.json` remain untracked local artifacts and are not committed.
- No raw-output, screenshot, log, coverage, smoke, local env, or secret file is included.
- Only this execution log document is intended to be tracked as changed.

## Final Result

PASS WITH LIMITATIONS

The one-user live pilot attempt reached the existing safe pending state:

```text
provider_consent_or_auth_pending
```

No provider output returned. No raw provider payload appeared. Normal chat stayed untouched. `sendOmniMessage` stayed unchanged. Puter remained disabled by default in committed files and did not become the default provider.

## Recommendation

Do not broaden rollout from this result. Before any further live pilot step, review why the local browser context loaded `https://js.puter.com/v2/` but did not expose `window.puter.ai.chat`, and keep any continuation behind explicit flags, allowlist, rollback, Access Layer gates, consent/auth handling, and public-safe result reporting.
