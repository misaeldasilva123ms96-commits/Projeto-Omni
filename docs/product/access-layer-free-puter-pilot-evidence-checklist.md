# Access Layer Free/Puter Pilot Evidence Checklist

Status: Phase 8B docs/checklist only. This checklist verifies that required evidence artifacts and operational controls exist before any controlled one-user Free/Puter pilot execution. It does not execute or enable the pilot, change execution paths, connect Puter to normal chat, make Puter the default provider, or add provider/network calls.

## Purpose

Use this checklist before a controlled one-user Free/Puter pilot. It is a pre-execution evidence gate that confirms the operator has the right artifacts, command outputs, rollback controls, allowlist controls, runtime truth fields, public payload checks, and stop conditions ready.

This checklist does not authorize broader rollout. It does not make Puter the default provider. It does not permit normal-user exposure, tools, files, function-calling, long memory, BYOK storage, billing, Pro behavior, raw provider payload exposure, or auth/consent bypass.

## Source Artifacts

Confirm these artifacts exist on the target branch or base:

- [ ] `docs/product/access-layer-free-puter-go-no-go.md`
- [ ] `docs/product/access-layer-free-puter-pilot-execution-record.md`
- [ ] `docs/product/access-layer-free-puter-one-user-dry-run.md`
- [ ] `docs/product/access-layer-free-puter-internal-pilot-runbook.md`
- [ ] `docs/product/access-layer-free-puter-regression-matrix.md`
- [ ] `docs/product/access-layer-free-puter-runtime-truth-alignment.md`
- [ ] `docs/product/access-layer-free-pilot-ops-readiness.md`
- [ ] `frontend/.env.example`
- [ ] `frontend/src/lib/puter/*`
- [ ] `backend/python/brain/runtime/access_layer/*`

## Pre-Execution Requirements

### Git And Branch State

- [ ] Latest `origin/main` fetched.
- [ ] Pilot branch created from current `origin/main`.
- [ ] Worktree clean except known ignored or local-only artifacts.
- [ ] Linked main worktree inspected read-only only.
- [ ] No merge into main performed.
- [ ] No direct push to main performed.

Command output placeholders:

```markdown
- git fetch origin --prune:
- git branch --show-current:
- git status --short:
- git log --oneline origin/main -5:
- linked main git status -sb:
```

### CI And Automated Validation

- [ ] CI green for the exact commit under review.
- [ ] Backend Access Layer pytest passes.
- [ ] Focused Puter/pilot Vitest passes.
- [ ] `npm.cmd run typecheck` passes.
- [ ] `npm.cmd run test` passes.
- [ ] `npm.cmd run build` passes.
- [ ] `npm.cmd run test:security` passes.

Command output placeholders:

```markdown
- CI checks:
- Backend Access Layer pytest:
- Focused Puter/pilot Vitest:
- npm.cmd run typecheck:
- npm.cmd run test:
- npm.cmd run build:
- npm.cmd run test:security:
```

Backend Access Layer command:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

Focused Puter/pilot command:

```powershell
cd frontend
npm.cmd exec vitest run src/lib/puter/freeModePuterBrowserAdapter.test.ts src/lib/puter/freeModePuterManualHarness.test.ts src/lib/puter/puterScriptLoader.test.ts src/lib/puter/PuterDevManualSurface.test.tsx src/pages/PuterDevRoutePage.test.tsx src/lib/puter/PuterFreeChatDevToggleSurface.test.tsx src/lib/puter/freeModeChatBridgeContract.test.ts src/lib/puter/freeModeChatBridgeMock.test.ts src/lib/puter/freeModeChatBridgeDevReal.test.ts src/lib/puter/freeModePilotFlagContract.test.ts src/lib/puter/freeModePilotMock.test.ts src/lib/puter/freeModePilotInternalReal.test.ts src/lib/puter/freeModePilotAllowlisted.test.ts
```

If local `frontend/.env.local` enables dev flags, run full frontend and focused Puter tests with explicit default-false env overrides before recording default behavior evidence.

## Flag Evidence

Confirm every Puter/Free flag remains default `false` in `frontend/.env.example`:

- [ ] `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false`
- [ ] `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false`
- [ ] `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK=false`
- [ ] `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false`
- [ ] `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE=false`
- [ ] `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false`
- [ ] `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL=false`
- [ ] `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED=false`
- [ ] `VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=false`

Local config checks:

- [ ] `frontend/.env.local`, if used, remains ignored or untracked.
- [ ] No secrets are stored in local env files.
- [ ] No committed env file enables Puter.

## Control Evidence

### Rollback Control

- [ ] Rollback control exists.
- [ ] Rollback active denies before provider execution.
- [ ] Disabling pilot flag denies before provider execution.
- [ ] Disabling allowlisted pilot flag denies before provider execution.
- [ ] Removing allowlist marker denies before provider execution.

Placeholder:

```markdown
- Rollback active denial evidence:
- Pilot flag disabled evidence:
- Allowlisted flag disabled evidence:
- Rollback owner:
```

### Allowlist Control

- [ ] Allowlist control exists.
- [ ] Explicit allowlist marker or match is required.
- [ ] Allowlist miss denies before provider execution.
- [ ] Allowlist mismatch denies before provider execution.

Placeholder:

```markdown
- Allowlist marker reviewed:
- Allowlist matched:
- Allowlist miss denial evidence:
- Allowlist mismatch denial evidence:
```

### Access Layer Gates

- [ ] `plan_mode=free` required.
- [ ] Quota allowed required.
- [ ] Quota exceeded denies.
- [ ] Routing allowed required.
- [ ] Routing false denies.
- [ ] `selected_provider_family=experimental_free_provider` required.
- [ ] Safe AccessSnapshotBoundary-style state required.
- [ ] Unsupported options deny.
- [ ] Public override fields deny.
- [ ] Sensitive fields deny.

Placeholder:

```markdown
- Quota exceeded denial evidence:
- Routing false denial evidence:
- Wrong provider family denial evidence:
- Unsafe fields denial evidence:
```

### Consent/Auth Handling

- [ ] Consent/auth pending is handled safely.
- [ ] Pending is not treated as success.
- [ ] Auth/consent is never bypassed.
- [ ] No auto-click or auto-accept behavior is used.
- [ ] Safe pending reason is recorded when applicable.

Allowed safe pending reasons include:

- `provider_consent_or_auth_pending`
- `provider_auth_required`
- `provider_pending_timeout`
- `provider_unavailable`

Placeholder:

```markdown
- Consent/auth state:
- Safe visible reason:
- Bypass attempted: no / yes-stop
```

## Product Safety Invariants

Confirm before any one-user pilot execution:

- [ ] Normal chat is unchanged with flags false.
- [ ] Normal chat still uses the existing Omni chat path.
- [ ] Puter is not the default provider.
- [ ] No automatic Puter/network call happens on app load or normal route load.
- [ ] No tools are enabled in the Free/Puter path.
- [ ] No files are enabled in the Free/Puter path.
- [ ] No function-calling is enabled in the Free/Puter path.
- [ ] No long memory is enabled in the Free/Puter path.
- [ ] No BYOK behavior is added.
- [ ] No billing behavior is added.
- [ ] No Pro behavior is added.

Placeholder:

```markdown
- Normal chat unchanged evidence:
- Default provider unchanged evidence:
- Tools/files/function-calling/long memory evidence:
- BYOK/billing/Pro absent evidence:
```

## Runtime Truth Fields To Capture

Capture only public-safe fields:

```markdown
- pilot_enabled:
- pilot_eligible:
- pilot_denied_reason:
- allowlisted_pilot:
- allowlist_required:
- allowlist_matched:
- rollback_active:
- access_layer_plan_mode:
- provider_family:
- provider_attempted:
- provider_succeeded:
- provider_failed_reason:
- fallback_triggered:
- quota_allowed:
- quota_exceeded:
- routing_allowed:
- consent_state:
- selected_adapter_id:
- boundary_version:
- snapshot_version:
- sanitized_output_present:
- raw_provider_payload_exposed:
```

Required interpretation:

- [ ] `provider_attempted=true` only after explicit gated invocation.
- [ ] `provider_succeeded=true` only after sanitized success.
- [ ] `raw_provider_payload_exposed=false`.
- [ ] `sanitized_output_present` is boolean only.
- [ ] Denied or pending states use safe reason constants only.

## Public Payload Fields To Inspect

Inspect only public-safe payload fields:

```markdown
- allowed:
- denied:
- reason:
- fallback_required:
- sanitized_output present:
- sanitized_output summary:
- runtime_truth present:
- exact public key set verified:
- exact runtime truth key set verified:
```

Required:

- [ ] No raw request.
- [ ] No raw response.
- [ ] No provider internals.
- [ ] No stack traces.
- [ ] No debug dumps.
- [ ] No credentials, tokens, API keys, or env vars.
- [ ] No raw user/session identifiers.

## Stop-Condition Checks

Stop immediately if any item is not satisfied:

- [ ] No raw Puter response appeared.
- [ ] No raw provider payload appeared.
- [ ] No stack trace appeared.
- [ ] No API key appeared.
- [ ] No token appeared.
- [ ] No credential appeared.
- [ ] No env var appeared.
- [ ] No user secret appeared.
- [ ] No `provider_config` appeared.
- [ ] No `private_endpoint` appeared.
- [ ] No billing/debug data appeared.
- [ ] No sensitive prompt was recorded.
- [ ] Normal chat behavior remained unchanged when flags were false.
- [ ] Puter did not become the default provider.
- [ ] Tools/files/function-calling/long memory remained unavailable in the Free/Puter path.
- [ ] Quota denied or routing denied did not attempt provider execution.
- [ ] Allowlist miss did not allow provider execution.
- [ ] Rollback disabled new provider attempts.
- [ ] Consent/auth pending was not treated as success.

If any stop condition fails, classify the result as `FAIL` or `ABORTED`, roll back, and record only safe details.

## Rollback Verification

Required rollback evidence:

```markdown
- Pilot flags disabled:
- Allowlisted flag disabled:
- Internal flag disabled, if applicable:
- Allowlist marker removed:
- Rollback active set or verified:
- Dev server/session stopped, if applicable:
- Normal chat fallback confirmed:
- User data deleted: no / yes-stop
- Safe rollback reason:
```

Rollback must not delete user data and must not expose raw provider data.

## Safe Result Summary

Use only sanitized summaries:

```markdown
- Safe status:
- Safe reason:
- Sanitized output present:
- Sanitized visible summary:
- Sensitive data observed: no / yes-stop
- Raw provider payload exposed: false / true-stop
```

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

## Forbidden Evidence

Never record:

- raw Puter response
- raw provider payload
- raw provider request
- API keys
- access tokens
- env vars
- credentials
- stack traces
- `provider_config`
- `private_endpoint`
- billing/debug data
- user secrets
- sensitive prompts
- raw user/session identifiers

If forbidden evidence appears, stop, remove unsafe material from public artifacts, roll back, and record only a safe stop reason.

## Final Decision

Select one:

- [ ] PASS
- [ ] PASS WITH LIMITATIONS
- [ ] FAIL
- [ ] ABORTED

Select one recommendation:

- [ ] Proceed to controlled pilot execution record
- [ ] Repeat dry run
- [ ] Fix safety gap
- [ ] Rollback and stop

Decision details:

```markdown
- Final decision:
- Final recommendation:
- Evidence complete: yes/no
- Known limitations:
- Required follow-up:
- Next review date:
- Reviewer/operator:
```

## Explicit Non-Authorization

This checklist does not execute the pilot, does not enable Puter, does not authorize broader rollout, does not connect Puter to normal chat, and does not make Puter the default provider.

Any future pilot execution must use the controlled execution record and must keep Puter disabled by default, allowlisted, rollback-safe, Access Layer gated, consent/auth safe, and public-output safe.
