# Access Layer Free/Puter Pilot Execution Record

Status: Phase 8A docs/record only. This document defines the official evidence record for a future controlled Free/Puter pilot execution. It does not execute or enable the pilot, change execution paths, connect Puter to normal chat, make Puter the default provider, or add provider/network calls.

## Purpose

This record is the template and evidence boundary for a controlled Free/Puter pilot execution. It must be completed when an approved local dev, internal-only, one-user allowlisted, or small allowlisted pilot is actually run.

The record exists to preserve public-safe evidence only: command results, safe status constants, boolean runtime truth fields, sanitized summaries, stop conditions, rollback actions, and the final operator recommendation.

## Scope

This record applies only to controlled pilot evidence gathering after the Go/No-Go review criteria have been satisfied for the exact target commit and environment.

It does not authorize broad rollout. It does not make Puter available to normal users. It does not make Puter the default provider. It does not permit tools, files, function-calling, long memory, BYOK storage, billing, Pro behavior, hidden provider execution, or raw provider payload exposure.

The only currently allowed real provider path remains:

`allowlisted pilot -> Phase 7R internal real pilot -> Phase 7L dev-real bridge -> existing gated manual harness`

## Pilot Type

Select exactly one:

- [ ] Local dev
- [ ] Internal-only
- [ ] One-user allowlisted
- [ ] Small allowlisted

Pilot type notes:

- Local dev is for `/dev/puter` and manual validation only.
- Internal-only requires internal markers and all pilot gates.
- One-user allowlisted is a single operator or explicitly allowlisted test session.
- Small allowlisted requires a separate Go decision and must still remain behind flags, rollback, and allowlist checks.

## Operator And Environment

```markdown
- Operator:
- Date/time:
- Timezone:
- Environment: local / internal / staging / other
- Browser/runtime used:
- Git branch:
- Git commit:
- PR reference:
- origin/main commit:
- Worktree clean before run: yes/no
- Linked main worktree read-only status:
- `.env.local` used: yes/no
- `.env.local` ignored/untracked confirmed: yes/no
```

## Flags Used

Record the value used for each flag. All defaults must remain `false` in `frontend/.env.example`.

```markdown
- VITE_OMNI_EXPERIMENTAL_PUTER_FREE:
- VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE:
- VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK:
- VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL:
- VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE:
- VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT:
- VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL:
- VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED:
- VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE:
```

Flag audit:

- [ ] `.env.example` reviewed.
- [ ] Every Puter/Free flag defaults to `false`.
- [ ] No committed env file enables Puter.
- [ ] No secrets are stored in local env files.

## Allowlist State

```markdown
- Allowlist required: true/false
- Allowlist marker present: true/false
- Allowlist matched: true/false
- Allowlist miss tested: yes/no
- Allowlist miss result:
- Allowlist mismatch tested: yes/no
- Allowlist mismatch result:
```

Required result: allowlist miss or mismatch must deny before provider execution.

## Rollback State

```markdown
- Rollback active before run: true/false
- Rollback denial tested: yes/no
- Rollback denial result:
- Pilot flag disable tested: yes/no
- Allowlisted flag disable tested: yes/no
- Internal flag disable tested, if applicable: yes/no
- Rollback owner:
```

Required result: rollback active, disabled pilot flags, removed allowlist marker, or disabled allowlisted flag must stop new pilot attempts before provider execution.

## Access Layer Gate State

Record public-safe values only:

```markdown
- plan_mode:
- quota_allowed:
- quota_exceeded:
- routing_allowed:
- selected_provider_family:
- selected_adapter_id:
- boundary_version:
- snapshot_version:
- tools requested: false/true-stop
- files requested: false/true-stop
- function-calling requested: false/true-stop
- long memory requested: false/true-stop
- sensitive tools requested: false/true-stop
- public override fields present: false/true-stop
- sensitive request fields present: false/true-stop
```

Required result: provider execution is allowed only when Free plan, quota/routing, provider family, adapter, boundary, snapshot, capability, and unsafe-field gates all pass.

## Consent/Auth State

```markdown
- Consent/auth prompt appeared: yes/no
- Consent/auth state:
- Consent/auth pending handled as safe state: yes/no
- Auth/consent bypass attempted: no / yes-stop
- Auto-click or auto-accept attempted: no / yes-stop
- Provider pending timeout observed: yes/no
- Safe visible reason:
```

Allowed safe states include:

- `not_required`
- `provider_consent_or_auth_pending`
- `provider_auth_required`
- `provider_pending_timeout`
- `provider_unavailable`
- `provider_failed`
- `provider_succeeded_sanitized`

Consent/auth pending is not success.

## Validation Commands And Results

### CI Checks

```markdown
- PR checks command/source:
- PR checks result:
- Link/reference:
```

### Backend Access Layer Pytest

Command:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

Result:

```markdown
- Passed: yes/no
- Summary:
```

### Focused Puter/Pilot Vitest

Command:

```powershell
cd frontend
npm.cmd exec vitest run src/lib/puter/freeModePuterBrowserAdapter.test.ts src/lib/puter/freeModePuterManualHarness.test.ts src/lib/puter/puterScriptLoader.test.ts src/lib/puter/PuterDevManualSurface.test.tsx src/pages/PuterDevRoutePage.test.tsx src/lib/puter/PuterFreeChatDevToggleSurface.test.tsx src/lib/puter/freeModeChatBridgeContract.test.ts src/lib/puter/freeModeChatBridgeMock.test.ts src/lib/puter/freeModeChatBridgeDevReal.test.ts src/lib/puter/freeModePilotFlagContract.test.ts src/lib/puter/freeModePilotMock.test.ts src/lib/puter/freeModePilotInternalReal.test.ts src/lib/puter/freeModePilotAllowlisted.test.ts
```

Result:

```markdown
- Passed: yes/no
- Summary:
- Explicit default-false env overrides used when local `.env.local` enabled flags: yes/no/not needed
```

### Frontend Typecheck

```markdown
- Command: npm.cmd run typecheck
- Passed: yes/no
- Summary:
```

### Frontend Test

```markdown
- Command: npm.cmd run test
- Passed: yes/no
- Summary:
- Explicit default-false env overrides used when local `.env.local` enabled flags: yes/no/not needed
```

### Frontend Build

```markdown
- Command: npm.cmd run build
- Passed: yes/no
- Summary:
```

### Security Regression

```markdown
- Command: npm.cmd run test:security
- Passed: yes/no
- Summary:
```

## Runtime Truth Observed

Record only public-safe fields. Do not paste raw provider payloads or raw provider responses.

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

- `provider_attempted=true` is allowed only after explicit gated invocation.
- `provider_succeeded=true` is allowed only after sanitized success.
- `raw_provider_payload_exposed` must be `false`.
- `sanitized_output_present` must be boolean only.

## Public Payload Observed

Record only public-safe payload fields:

```markdown
- allowed:
- denied:
- reason:
- fallback_required:
- sanitized_output present: yes/no
- sanitized_output summary:
- runtime_truth present: yes/no
- exact public key set verified: yes/no
- exact runtime truth key set verified: yes/no
```

Do not include raw request, raw response, provider internals, stack traces, debug dumps, credentials, tokens, env vars, or raw user/session identifiers.

## Sanitized Result Summary

Use a short sanitized summary only:

```markdown
- Result summary:
- User-visible safe status:
- User-visible safe reason:
- Sensitive data observed: no / yes-stop
```

## Stop Conditions Checked

Mark each before finalizing the record:

- [ ] No raw Puter response appeared.
- [ ] No raw provider payload appeared.
- [ ] No stack trace appeared.
- [ ] No API key, token, credential, env var, or user secret appeared.
- [ ] No `provider_config`, `private_endpoint`, billing, or debug data appeared.
- [ ] No sensitive prompt was recorded.
- [ ] Normal chat behavior remained unchanged when flags were false.
- [ ] Puter did not become the default provider.
- [ ] Tools, files, function-calling, and long memory remained unavailable in the Free/Puter path.
- [ ] Quota/routing denied states did not attempt provider execution.
- [ ] Allowlist miss did not allow provider execution.
- [ ] Rollback disabled new provider attempts.
- [ ] Consent/auth pending was not treated as success.

If any item fails, stop and classify the result as `FAIL` or `ABORTED`.

## Rollback Action Taken

```markdown
- Rollback needed: yes/no
- Pilot flags disabled: yes/no
- Allowlisted flag disabled: yes/no
- Internal flag disabled, if applicable: yes/no
- Allowlist marker removed: yes/no
- Rollback active set or verified: yes/no
- Dev server/session stopped: yes/no
- Normal chat fallback confirmed: yes/no
- User data deleted: no / yes-stop
- Safe rollback reason:
```

Rollback must not delete user data and must not expose raw provider data.

## Issues Found

```markdown
- Issues found: none / list safe summaries
- Stop condition triggered: yes/no
- Safety gap found: yes/no
- Follow-up issue/PR:
- Sanitized details only:
```

Never include raw provider payloads, stack traces, secrets, or debug internals in the issue summary.

## Required Forbidden Evidence

Never include these in this record, tickets, PR descriptions, screenshots, logs, or copied console output:

- raw Puter response
- raw provider payload
- raw provider request
- API keys
- access tokens
- environment variables
- credentials
- stack traces
- `provider_config`
- `private_endpoint`
- billing data
- debug data
- sensitive prompts
- user secrets
- raw user/session identifiers

If any forbidden evidence appears, stop the pilot, remove the unsafe material from public artifacts, and record only a safe stop reason.

## Decision Section

Select one result:

- [ ] PASS
- [ ] PASS WITH LIMITATIONS
- [ ] FAIL
- [ ] ABORTED

Select one recommendation:

- [ ] Proceed to next controlled step
- [ ] Repeat dry run
- [ ] Fix safety gap
- [ ] Rollback and stop

Decision details:

```markdown
- Final recommendation:
- Scope approved, if any:
- Max pilot population, if any:
- Required flags for any next step:
- Allowlist mechanism:
- Rollback owner:
- Observability owner:
- Stop conditions for next step:
- Next review date:
- Notes:
```

## Explicit Non-Authorization

This document does not enable the pilot. It does not authorize broad rollout. It does not connect Puter to normal chat. It does not make Puter the default provider. It does not permit bypassing rollback, allowlist, Access Layer gates, consent/auth, or public-safe output requirements.

Any future expansion beyond this record requires a separate reviewed phase with complete evidence and explicit approval.
