# Access Layer Free/Puter One-user Execution Log

## Purpose

This document records the Phase 8C controlled one-user Free/Puter pilot dry-run evidence. It does not enable the pilot, does not authorize broader rollout, does not connect Puter to normal chat, and does not make Puter the default provider.

## Scope

- Branch: `feature/access-layer-free-puter-one-user-execution-log`
- Base: `origin/main` at `6752b93`
- Pilot type: local dev / one-user dry run
- Normal chat path: unchanged; no normal chat validation path was used
- Committed config: `frontend/.env.example` keeps all Puter and pilot flags default `false`
- Local ignored config: `frontend/.env.local` was used for dev-route flags only and remained ignored/untracked

## Git And Worktree Evidence

| Check | Result |
| --- | --- |
| `git fetch origin --prune` | Passed |
| Current branch | `feature/access-layer-free-puter-one-user-execution-log` |
| `git status --short` before validation | Only pre-existing untracked `.coverage` and `smoke.json` |
| `git log --oneline origin/main -5` | Latest `origin/main` commit `6752b93` |
| Linked main worktree status | Read-only check only; `main` was behind `origin/main` and not modified |
| Linked main worktree touched | No writes, no checkout, no merge |

## Committed Defaults

`frontend/.env.example` was inspected and kept these committed defaults:

```text
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

No committed file was changed to enable Puter by default.

## Local Ignored Env

`frontend/.env.local` existed before the dry run and was confirmed ignored by `.gitignore`.

Local values used:

```text
VITE_OMNI_EXPERIMENTAL_PUTER_FREE=true
VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=true
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=true
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=true
VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE=true
```

No secrets, API keys, access tokens, credentials, or provider configuration were placed in `.env.local`.

## Validation Commands

| Command | Result |
| --- | --- |
| `python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py` | Passed: 83 tests and 82 subtests |
| `npm.cmd run typecheck` from `frontend` | Passed |
| `npm.cmd run test` from `frontend` with explicit default-false Puter/pilot env overrides | Passed: 22 files, 190 tests |
| `npm.cmd run build` from `frontend` | Passed |
| `npm.cmd run test:security` from repo root | Passed |
| Focused Puter/pilot Vitest group with explicit default-false Puter/pilot env overrides | Passed: 13 files, 170 tests |

The focused Puter/pilot Vitest group included the Puter browser adapter, manual harness, script loader, dev manual surface, dev route page, dev chat toggle surface, chat bridge contract/mock/dev-real modules, and pilot flag/mock/internal-real/allowlisted modules.

## Manual Route Validation

| Check | Result |
| --- | --- |
| Dev server URL | `http://127.0.0.1:5173` |
| Route | `/dev/puter` |
| Route reachable | Yes |
| Dev controls visible with local flags | Yes |
| Normal chat involved | No |
| Puter script on page load | No |
| Automatic provider call on page load | No evidence observed |
| Initial visible result states | `not_invoked` |

Initial page inspection showed no `https://js.puter.com/v2/` script tag and no Puter runtime marker before the manual loader action.

## Runtime Loader Validation

| Check | Result |
| --- | --- |
| Manual action used | `Load Puter runtime` |
| Script source | `https://js.puter.com/v2/` |
| Script tag count after load | Exactly 1 |
| Loader visible status | `loaded` |
| AI call from loader | No visible AI result; manual and dev chat results remained `not_invoked` |
| Runtime marker in browser inspection | Unavailable |

The loader added the expected script exactly once. No provider text or raw payload appeared from the loader action.

## One-user Dry-run Attempt

Safe prompt used:

```text
Reply with exactly: OMNI_ONE_USER_PILOT_OK
```

No secrets, user data, files, tools, API keys, tokens, credentials, environment variables, or sensitive data were included.

| Check | Result |
| --- | --- |
| Manual dev chat bridge action attempted | Yes |
| Visible result | `provider_consent_or_auth_pending` |
| Consent/auth state | Safe pending state |
| Provider output returned | No |
| Raw provider payload appeared | No |
| Stack trace appeared | No |
| Secret/env/debug/provider config/private endpoint/billing fragments appeared | No |
| Normal chat path changed or used | No |

The dry-run did not bypass consent/auth and did not auto-accept any prompt. The visible result remained a safe public state.

## Runtime Truth Summary

The dev surface exposes a sanitized visible result rather than raw runtime truth JSON. Based on the public-safe dev toggle timeout contract and the observed visible state:

| Field | Observed/Safe Value |
| --- | --- |
| `provider_attempted` | `true` for the manual dev bridge invocation timeout path |
| `provider_succeeded` | `false` |
| `fallback_triggered` | `true` |
| `provider_failed_reason` | `provider_consent_or_auth_pending` |
| `raw_provider_payload_exposed` | `false` by visible-output inspection |
| `sanitized_output_present` | `false` |

## Stop Conditions

| Stop Condition | Result |
| --- | --- |
| Raw provider payload appears | Not observed |
| Stack trace appears | Not observed |
| Secret/env/debug/provider config/private endpoint/billing appears | Not observed |
| Normal chat path changes unexpectedly | Not observed |
| Provider attempted despite quota/routing denial | Not observed |
| Allowlist miss allows | Not exercised in UI dry run |
| Rollback active still allows | Not exercised in UI dry run |
| Tools/files/function-calling/long memory appear | Not observed |

## Cleanup

- Dev server stopped.
- Port `5173` cleared after stopping the Vite/node process.
- `frontend/.env.local` remained ignored/untracked.
- No local env, coverage, smoke files, screenshots, logs, raw provider output, or secrets were committed.
- Tracked files changed only for this execution log document.

## Result

Result: `PASS WITH LIMITATIONS`

The dry run validated the local dev route, manual loader behavior, single expected Puter script source, no automatic provider call on page load, and safe consent/auth pending handling. It did not produce a provider completion and did not validate a completed one-user output because the run settled into `provider_consent_or_auth_pending`.

## Recommendation

Do not broaden rollout and do not enable Puter for normal users. Keep Puter disabled by default. Before any broader pilot, repeat this dry run with explicit operator consent/auth completion only if authorized, and record only sanitized evidence in the pilot execution record.
