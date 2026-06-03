# Access Layer Free Chat One-user Wiring Record

Status: PASS

## Purpose

Phase 8K records a controlled one-user execution check for the internal allowlisted Free Chat wiring path added in Phase 8J.

This record does not enable the pilot, does not expose Puter to normal users, does not make Puter the default provider, and does not change production chat behavior.

## Scope

Reviewed and validated:

- `frontend/src/lib/puter/freeModeChatInternalAllowlistedWiring.ts`
- `frontend/src/lib/puter/freeModeChatInternalAllowlistedWiring.test.ts`
- `frontend/src/lib/puter/freeModeChatMockedWiring.ts`
- `frontend/src/lib/puter/freeModeChatWiringHarness.ts`
- `frontend/src/lib/puter/freeModePilotAllowlisted.ts`
- `frontend/src/lib/puter/freeModePilotInternalReal.ts`
- `docs/product/access-layer-free-chat-internal-allowlisted-wiring.md`
- `docs/product/access-layer-free-chat-mocked-wiring.md`
- `docs/product/access-layer-free-chat-wiring-harness.md`
- `docs/product/access-layer-free-chat-activation-gate.md`
- `frontend/.env.example`
- current chat flow and `sendOmniMessage` source, read-only

## Git State

- Branch: `feature/access-layer-free-chat-one-user-wiring-record`
- Base: `origin/main`
- `origin/main` commit at validation: `f2e16ba Merge pull request #215 from misaeldasilva123ms96-commits/feature/access-layer-free-chat-internal-allowlisted-wiring`
- Current branch was created directly from current `origin/main`.
- Linked main worktree status was inspected read-only:
  - branch: `main`
  - local status: behind `origin/main` by 6 commits at inspection time
  - latest local linked-worktree commit: `731c052 Merge pull request #211 from misaeldasilva123ms96-commits/feature/access-layer-free-chat-activation-gate`
- No linked main worktree files were changed.

## Local State

- Pre-existing untracked local artifacts observed:
  - `.coverage`
  - `smoke.json`
- `frontend/.env.local` is ignored locally.
- No local env file, coverage file, smoke file, log file, screenshot, raw provider output, or secret is included in this record.
- Only this execution record document is intended to be tracked as changed.

## Committed Flag Defaults

`frontend/.env.example` keeps all Puter and Free pilot flags default-disabled:

```env
VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_MOCKED_WIRING=false
VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_INTERNAL_WIRING=false
VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=false
```

No committed file enables Puter by default.

## Wiring Behavior Record

Validated through focused Vitest with explicit default-false env overrides and safe mocked runtime inputs:

| Case | Result |
| --- | --- |
| Flags false | `should_use_normal_chat=true`; no provider attempt. |
| Allowlist miss | Denied safely; no provider attempt. |
| Rollback active | Denied safely; no provider attempt. |
| Quota denied or exceeded | Denied safely; no provider attempt. |
| Routing false | Denied safely; no provider attempt. |
| Wrong provider family | Denied safely; no provider attempt. |
| Consent pending | Safe pending state; not success; no provider attempt. |
| Unsafe fields | Denied safely, including camelCase, PascalCase, kebab-case, spaced, and mixed variants. |
| Restricted capabilities | Tools, files, function-calling, long memory, and sensitive tools denied. |
| Exact public output shape | Tested. |
| Exact runtime truth shape | Tested. |
| Serialized output safety | No raw IDs, secrets, or sensitive fragments in serialized public output. |
| Gated internal success path | Tested with a safe mocked runtime only. |
| `provider_attempted` | `true` only after the gated internal path invokes the mocked bridge. |
| `provider_succeeded` | `true` only on sanitized success. |
| `raw_provider_payload_exposed` | `false`. |
| Normal chat source | Unchanged by this record branch. |
| `sendOmniMessage` | Unchanged and not wired to the internal allowlisted module. |

No live Puter browser call was made as part of this record.

## Source Guard Record

Observed source guards:

- `freeModeChatInternalAllowlistedWiring.ts` imports the allowlisted pilot wrapper and does not directly import the dev-real bridge, internal-real pilot, or manual harness.
- No direct `puter.ai.chat` import or call was found in the internal allowlisted wiring module.
- No direct `fetch`, `XMLHttpRequest`, `navigator.sendBeacon`, or `WebSocket` provider path was found in the internal allowlisted wiring module.
- Chat components and `sendOmniMessage` do not import or call `runFreeModeChatInternalAllowlistedWiring`.
- The only permitted real path remains:

```text
internal allowlisted chat wiring
-> Phase 7S allowlisted pilot wrapper
-> Phase 7R internal real pilot
-> Phase 7L dev-real bridge
-> existing gated manual harness
```

## Validation Commands

Backend Access Layer:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

Result:

```text
83 passed, 82 subtests passed
```

Focused Puter wiring Vitest:

```powershell
cd frontend
npm.cmd exec -- vitest run src/lib/puter/freeModeChatInternalAllowlistedWiring.test.ts src/lib/puter/freeModeChatMockedWiring.test.ts src/lib/puter/freeModeChatWiringHarness.test.ts src/lib/puter/freeModePilotAllowlisted.test.ts src/lib/puter/freeModePilotInternalReal.test.ts src/lib/puter/freeModeChatBridgeDevReal.test.ts
```

Result:

```text
6 test files passed
76 tests passed
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

Note: Vite reported the existing chunk-size warning for the main bundle. This warning did not fail the build.

Root security regression:

```powershell
npm.cmd run test:security
```

Result:

```text
security regression suite: ok
```

Notes:

- Frontend validation commands were run with explicit Puter and Free flags set to `false` to avoid local ignored env interference.
- Security regression was run from the repository root, where `test:security` is defined.

## Data Policy Compliance

Recorded:

- safe constants
- booleans
- sanitized summaries
- command results
- test counts
- public-safe runtime truth summaries

Not recorded:

- raw Puter response
- raw provider payload
- tokens
- API keys
- environment variable values
- credentials
- cookies
- localStorage or sessionStorage contents
- provider config
- private endpoint
- billing or debug data
- stack traces
- sensitive prompts
- user secrets

## Stop Conditions

No stop condition was observed.

Specifically:

- no raw provider payload was observed
- no raw Puter response was observed
- no secret, token, env var, credential, provider config, private endpoint, billing, or debug data was recorded
- no stack trace was recorded in the execution record
- no normal chat source change was present
- no default provider change was present
- no tools, files, function-calling, or long memory behavior was enabled

## Result

PASS

The internal allowlisted Free Chat wiring decision layer is validated under controlled, test-only conditions. It remains disabled by default, not connected to normal chat, not the default provider, and guarded by flags, allowlist, rollback, Access Layer gates, quota/routing, consent/auth state, and sanitized output/runtime truth rules.

## Recommendation

Do not enable broad normal-user rollout from this record. Any next step must be a separately scoped, explicitly reviewed phase with default-false flags, rollback, allowlist, Access Layer gates, consent/auth handling, and PR validation.
