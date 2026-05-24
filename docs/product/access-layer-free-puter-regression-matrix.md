# Access Layer Free/Puter Regression Matrix

Status: Phase 7V docs/test-planning only. This matrix does not implement behavior, change execution paths, connect Puter to normal chat, make Puter default, or enable Puter by default.

## Purpose

This document consolidates regression coverage for the Free/Puter Access Layer work after Phase 7U. It covers backend Access Layer contracts, the Puter dev-only browser path, Free chat bridge contracts, pilot contracts, flags, rollback, allowlist, consent/auth handling, runtime truth, and public-safe output.

Normal chat remains the Omni chat transport through `sendOmniMessage`. Puter remains outside the normal chat send path unless a future reviewed phase explicitly changes that.

## Regression Matrix

| Category | Purpose | Critical invariants | Deny/fail-closed cases | Success/allowed cases | Existing tests | Recommended additions | Commands | Owner/phase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PlanPolicy | Define plan modes, Free limits, provider mode, and capability defaults. | Free disables files, tools, sensitive tools, and long memory; unknown plan fails; public policy has stable fields. | Unknown plan mode, invalid overrides, non-positive token limits, unsupported access modes. | Known plan resolves to public policy with expected provider mode and limits. | `tests/runtime/test_plan_policy.py` | Add matrix snapshot comparing all plan capability fields before pilot changes. | Backend access-layer pytest. | Phase 1 |
| TokenQuota | Compute usage totals, daily quota, and input/output limit checks. | Counts are non-negative; quota exceeded is deterministic; output is public-safe. | Negative token counts, invalid daily limit, exceeded quota, input/output over limit. | Valid token usage returns remaining quota and allowed limit checks. | `tests/runtime/test_token_quota.py` | Add boundary-value rows for exactly-at-limit and one-token-over cases across Free. | Backend access-layer pytest. | Phase 2 |
| ProviderRouter | Select provider family from plan/provider mode and quota state. | Free maps only to `experimental_free_provider`; routing requires quota, input, and output allowed. | Quota exceeded, input limit exceeded, output limit exceeded, unsupported policy state. | Free within quota routes to `experimental_free_provider`. | `tests/runtime/test_provider_router.py` | Add regression row confirming no Puter-specific default provider switch. | Backend access-layer pytest. | Phase 3 |
| ProviderRegistry | Publish public adapter metadata and validate router decisions. | Capabilities are explicit; unsupported provider family fails; public metadata excludes secrets. | Unknown provider family, provider mode mismatch. | Known provider family returns stable public adapter metadata. | `tests/runtime/test_provider_registry.py` | Add capability diff test for Free provider: no tools/files/long context/sensitive tools. | Backend access-layer pytest. | Phase 4 |
| PublicAccessSnapshot | Build public-safe Access Layer snapshot. | Exact public shape; fallback allowed on denial; selected provider/adapter are public metadata only. | Invalid plan, invalid token usage, registry mismatch, quota exceeded, routing denied. | Valid Free request within quota returns routing allowed and experimental provider family. | `tests/runtime/test_public_access_snapshot.py` | Add serialized-output scan for provider config/private endpoint/billing/debug terms. | Backend access-layer pytest. | Phase 5 |
| AccessSnapshotBoundary | Normalize public request input and enforce safe envelope shape. | Unsafe public input is rejected; exact keys required; subject IDs are opaque and safe. | Unsafe keys, malformed request, invalid token usage, unsafe subject ID, malformed snapshot. | Valid public input returns an exact boundary envelope. | `tests/runtime/test_access_snapshot_boundary.py` | Add unsafe-key variant coverage aligned with pilot contract key normalization. | Backend access-layer pytest. | Phase 6 |
| Puter client adapter | Define disabled-by-default Puter adapter selection contract. | Contract is deterministic; no browser/network/provider call; feature flag required; public-safe output. | Feature disabled, invalid snapshot, routing denied, non-Free, provider mode/family mismatch, unsafe options. | Valid snapshot plus experimental flag returns selection allowed. | `tests/runtime/test_puter_client_adapter.py` | Add backend-to-frontend adapter ID alignment check if adapter IDs evolve. | Backend access-layer pytest. | Phase 7A |
| Puter browser skeleton | Evaluate browser runtime eligibility for Puter. | Disabled by default; no `puter.ai.chat`; no network path; no tools/files/long context. | Flag false, invalid boundary, denied boundary, missing runtime, wrong provider family, unsafe options. | Valid Free boundary plus Puter runtime marker returns selection allowed. | `frontend/src/lib/puter/freeModePuterBrowserAdapter.test.ts` | Add source guard for future transport helpers if introduced. | Focused Puter Vitest. | Phase 7B |
| Puter manual harness | Provide explicit manual local Puter check. | Manual invocation only; existing adapter gates first; sanitized text only; no raw response. | Adapter denies, non-browser runtime, Puter unavailable, call failure, unsafe output. | Explicit invocation with valid runtime and safe prompt returns sanitized success. | `frontend/src/lib/puter/freeModePuterManualHarness.test.ts` | Add timeout-specific regression if harness timeout behavior is expanded. | Focused Puter Vitest. | Phase 7C |
| Puter script loader | Manually load fixed Puter runtime script for `/dev/puter`. | Fixed source only: `https://js.puter.com/v2/`; no duplicate script; no AI call; status is safe. | Flags false, non-browser runtime, source mismatch, unavailable after load, timeout/error. | Explicit load action injects one fixed script and reports loaded when runtime appears. | `frontend/src/lib/puter/puterScriptLoader.test.ts` | Add browser smoke row for script tag count after repeated clicks. | Focused Puter Vitest plus manual/browser runbook. | Phase 7G |
| `/dev/puter` route | Mount dev-only manual validation route. | Hidden unless Free and dev surface flags are true; no call on route load; outside normal chat. | Flags false, denied boundary, malformed state. | Flags true renders dev surface and optional dev toggle; manual actions remain separate. | `frontend/src/pages/PuterDevRoutePage.test.tsx` | Add route-level test that normal app routes still resolve without Puter imports. | Focused Puter Vitest. | Phase 7E/7M |
| Dev chat toggle | Manually invoke dev-real bridge from `/dev/puter`. | Hidden by default; requires all dev flags; manual click only; no direct `puter.ai.chat`; sanitized output. | Flags false, denied contract, missing runtime, unsafe fields, provider pending/failure. | All gates pass and manual click invokes Phase 7L bridge once. | `frontend/src/lib/puter/PuterFreeChatDevToggleSurface.test.tsx` | Add browser/manual row for consent dialog observed and stopped. | Focused Puter Vitest plus manual/browser runbook. | Phase 7M |
| Consent/auth pending handling | Keep real provider consent/auth states safe. | Never bypass auth; never auto-click; pending is not success; public reason only. | Pending timeout, auth/consent-like unresolved state, raw error, provider failure. | Mocked success remains sanitized; pending resolves to `provider_consent_or_auth_pending`. | `PuterFreeChatDevToggleSurface.test.tsx`, dev-real/harness tests. | Add manual browser checklist for exact visible pending copy. | Focused Puter Vitest plus manual/browser runbook. | Phase 7N |
| Free chat bridge contract | Decide future Free chat eligibility. | Pure deterministic contract; no Puter/chat/network import; exact output keys; sanitized runtime truth. | Non-Free, flags false, malformed/denied boundary, quota/routing denied, wrong provider, missing runtime, unsafe fields. | All gates pass returns allowed with provider not attempted and sanitized output null. | `frontend/src/lib/puter/freeModeChatBridgeContract.test.ts` | Add property-like unsafe string no-echo rows if new public fields are added. | Focused Puter Vitest. | Phase 7J |
| Free chat bridge mock | Prove bridge orchestration with deterministic mock output. | Composes contract; mock-only; no real provider; real provider attempted/succeeded remain false. | Flags false, contract denies, unsafe options, quota/routing denial, runtime missing. | Contract allowed returns mock-only sanitized output and mock success markers. | `frontend/src/lib/puter/freeModeChatBridgeMock.test.ts` | Add fixture comparison to keep mock runtime truth aligned with contract runtime truth. | Focused Puter Vitest. | Phase 7K |
| Dev-real bridge | Isolated real bridge through existing manual harness. | Calls contract first; no chat integration; direct `puter.ai.chat` not added; provider attempted only on explicit invocation. | Flags false, contract denied, runtime missing, unsafe fields, provider error, consent/auth pending. | All gates pass and explicit call invokes harness; sanitized success only. | `frontend/src/lib/puter/freeModeChatBridgeDevReal.test.ts` | Add guard that provider attempted stays false on every denial reason. | Focused Puter Vitest. | Phase 7L |
| Pilot flag contract | Decide future pilot eligibility with rollback and allowlist markers. | Pure; no Puter/chat/network path; flags default false; unsafe key variants denied; no raw IDs echoed. | Pilot flag false, rollback active, allowlist miss, non-Free, quota/routing denial, consent pending, unsafe fields. | All gates pass returns pilot eligible with provider attempted false. | `frontend/src/lib/puter/freeModePilotFlagContract.test.ts` | Add new key-normalization rows whenever new request fields are introduced. | Focused Puter Vitest. | Phase 7P |
| Pilot mock | Compose pilot contract and mock bridge. | Pilot contract runs first; mock bridge only after pilot allow; mock-only output; no dev-real/harness import. | Pilot denied, bridge denied, rollback active, allowlist miss, consent pending, unsafe fields. | Pilot and bridge allowed returns deterministic mock-only success. | `frontend/src/lib/puter/freeModePilotMock.test.ts` | Add runtime truth alignment test with allowlisted/internal layers. | Focused Puter Vitest. | Phase 7Q |
| Internal real pilot | Internal-only real pilot wrapper. | Pilot contract first; internal flag required; real path only through Phase 7L; no normal chat path. | Internal flag false, pilot denied, rollback, allowlist miss, consent pending, runtime missing, provider failure. | All internal gates pass and explicit call invokes dev-real bridge only. | `frontend/src/lib/puter/freeModePilotInternalReal.test.ts` | Add manual dry-run checklist before any internal real browser run. | Focused Puter Vitest. | Phase 7R |
| Allowlisted pilot | Allowlisted pilot layer on internal real pilot. | Allowlisted flag and match required; rollback inactive; real path only through Phase 7R; not default. | Flag false, allowlist missing/mismatch, rollback active, pilot/internal deny, runtime missing, unsafe fields. | All gates pass invokes internal real pilot and returns sanitized public-safe result. | `frontend/src/lib/puter/freeModePilotAllowlisted.test.ts` | Add stale-base guard in PR checklist to ensure Phase 7R files exist on base. | Focused Puter Vitest. | Phase 7S |
| Ops/readiness | Document rollout controls and readiness gates. | Docs/env only; flags default false; rollback and allowlist required; no production overclaim. | Missing rollback, missing allowlist, docs imply normal-user exposure, flag set true. | Docs confirm conservative rollout stages and rollback path. | Review and security regression suite. | Add docs lint/checklist to assert flag names appear once and default false. | Root `npm run test:security`; docs review. | Phase 7T |

## Flag Matrix

Every Puter/Free flag in `frontend/.env.example` must default to `false`.

| Flag | Expected default | Regression expectation |
| --- | --- | --- |
| `VITE_OMNI_EXPERIMENTAL_PUTER_FREE` | `false` | Puter Free browser skeleton is disabled unless explicitly enabled. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE` | `false` | Free chat bridge contract is disabled unless explicitly enabled. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK` | `false` | Mock bridge path is disabled unless explicitly enabled. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL` | `false` | Dev-real bridge path is disabled unless explicitly enabled. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE` | `false` | Dev chat toggle is hidden unless explicitly enabled. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT` | `false` | Free pilot is disabled unless explicitly enabled. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL` | `false` | Internal real pilot is disabled unless explicitly enabled. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED` | `false` | Allowlisted pilot is disabled unless explicitly enabled. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE` | `false` | `/dev/puter` manual surface is hidden unless explicitly enabled. |

Regression rule: full frontend tests should be run with explicit default-false overrides when a local `frontend/.env.local` enables dev validation flags.

## Security Regression Matrix

| Security invariant | Required coverage |
| --- | --- |
| No raw provider payload | Serialized decisions, runtime truth, UI output, and docs must never include raw provider request/response payloads. |
| No stack traces | Provider and runtime failures must expose safe reason constants only. |
| No API keys, tokens, credentials, or env vars | Unsafe fields and sensitive-looking values must be denied or redacted before public output. |
| No `provider_config`, `private_endpoint`, billing, or debug leakage | Unsafe option keys must be normalized across snake_case, camelCase, PascalCase, kebab-case, spaced, repeated-separator, and mixed-case variants. |
| No tools, files, function-calling, or long memory | Free/Puter contracts deny requested capabilities for tools, files, function-calling, long memory, and sensitive tools. |
| No public override fields | Public input cannot set provider mode/family, adapter ID, quota limits, policy overrides, selected adapter, or raw provider fields. |
| Unsafe key variants denied | Pilot flag contract coverage should remain the canonical reference for unsafe key normalization. |
| Output exact safe key sets | Contract, mock, pilot, and runtime truth outputs must keep exact public-safe key sets. |
| No hidden execution imports | Source guards should continue blocking `sendOmniMessage`, direct `puter.ai.chat`, `fetch`, `XMLHttpRequest`, `navigator.sendBeacon`, and `WebSocket` in modules that must not execute providers directly. |

## Rollout/Ops Regression Matrix

| Scenario | Expected result |
| --- | --- |
| Rollback active | Pilot contracts deny before provider or mock success. |
| Allowlist missing | Allowlisted pilot denies. |
| Allowlist mismatch | Allowlisted pilot denies. |
| Consent/auth pending | Safe pending/denied state; no success and no bypass. |
| Quota exceeded | Access Layer and pilot contracts deny; no Puter call. |
| Routing false | Access Layer and bridge/pilot contracts deny; no Puter call. |
| Wrong provider family | Denied as provider family not allowed. |
| Flags false | Normal chat remains unchanged and Puter paths remain hidden/denied. |
| Puter not default provider | Provider registry/router/default behavior does not route normal chat to Puter. |
| Runtime missing | Browser/Puter runtime missing returns safe unavailable/fallback state. |
| Provider failure | Failure is sanitized and runtime truth marks fallback/failure safely. |
| Stale branch/base | PR review confirms expected dependency files exist on `origin/main`. |

## Automated Command Groups

Backend Access Layer regression:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

Focused Puter Vitest group:

```powershell
cd frontend
npm.cmd exec vitest run src/lib/puter/freeModePuterBrowserAdapter.test.ts src/lib/puter/freeModePuterManualHarness.test.ts src/lib/puter/puterScriptLoader.test.ts src/lib/puter/PuterDevManualSurface.test.tsx src/pages/PuterDevRoutePage.test.tsx src/lib/puter/PuterFreeChatDevToggleSurface.test.tsx
```

Focused bridge and pilot Vitest group:

```powershell
cd frontend
npm.cmd exec vitest run src/lib/puter/freeModeChatBridgeContract.test.ts src/lib/puter/freeModeChatBridgeMock.test.ts src/lib/puter/freeModeChatBridgeDevReal.test.ts src/lib/puter/freeModePilotFlagContract.test.ts src/lib/puter/freeModePilotMock.test.ts src/lib/puter/freeModePilotInternalReal.test.ts src/lib/puter/freeModePilotAllowlisted.test.ts
```

Frontend full validation:

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

Expected PR CI checks:

- Backend Access Layer pytest group passes.
- Focused Puter/bridge/pilot Vitest groups pass.
- Frontend `typecheck`, `test`, and `build` pass.
- Root `test:security` passes.
- Review confirms docs do not recommend normal-user enablement.
- Review confirms no chat execution path changed unless a future phase explicitly scopes that work.

## Future Test Gaps

- Runtime truth/public payload alignment across backend Access Layer, bridge contracts, pilot contracts, and UI-visible state.
- One-user allowlisted dry run with explicit rollback criteria and sanitized evidence capture.
- Browser/manual consent flow runbook that records only safe visible state and never bypasses auth.
- Production-safe rollback drill proving flags and allowlist removal stop new pilot attempts.
- Stale branch/base guard for phase dependencies, especially when a phase composes the previous real-pilot layer.
- Public payload snapshot tests for every runtime truth object that may eventually be surfaced in normal chat.
- CI assertion that all Puter/Free pilot flags in `.env.example` remain `false`.

## Non-Recommendation

This matrix does not recommend enabling Puter for normal users. The next phases should continue strengthening regression coverage, runtime truth alignment, runbooks, rollback readiness, and dry-run evidence before any broader pilot decision.
