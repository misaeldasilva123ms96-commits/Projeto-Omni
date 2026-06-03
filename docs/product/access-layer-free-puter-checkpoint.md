# Access Layer Free/Puter Consolidated Checkpoint

Status: Phase 7U checkpoint/audit only. This document records the current Access Layer Free/Puter state after Phases 1 through 7T. It does not enable Puter, change chat behavior, add a provider path, or recommend normal-user rollout.

## Scope

This checkpoint is based on the existing Access Layer product docs, `backend/python/brain/runtime/access_layer/*`, `frontend/src/lib/puter/*`, `frontend/.env.example`, and a read-only inspection of the current chat path. The normal chat UI still sends through `sendOmniMessage` and the Omni API transport; Puter pilot modules remain outside the normal chat send path.

## Completed Phases

| Phase | Area | Checkpoint classification | Current status |
| --- | --- | --- | --- |
| Phase 1 | PlanPolicy | production-safe contract | Defines plan modes, Free limits, and disabled Free capabilities for files, tools, sensitive tools, and long memory. |
| Phase 2 | TokenQuota | production-safe contract | Computes token totals, daily quota, remaining quota, and input/output limit checks. |
| Phase 3 | ProviderRouter | production-safe contract | Maps plan/provider mode to provider family and denies routing when quota or token limits fail. |
| Phase 4 | ProviderRegistry | production-safe contract | Publishes adapter metadata and capability flags. Experimental Free remains capability-limited. |
| Phase 5 | PublicAccessSnapshot | production-safe contract | Builds public-safe snapshots and fails closed on invalid plan, policy, token, or registry state. |
| Phase 6 | AccessSnapshotBoundary | production-safe contract | Enforces exact public envelope/key shapes and rejects unsafe public inputs. |
| Phase 7A | Puter client adapter contract | production-safe contract, not default, disabled by default | Adds public-safe Puter client adapter metadata and selection rules without browser execution. |
| Phase 7B | Puter browser skeleton | production-safe contract, not default, disabled by default | Adds browser/runtime eligibility checks; no real provider call is made. |
| Phase 7C | Puter manual harness | dev-only, not default, disabled by default | Adds an explicit manual harness path for local Puter checks with sanitized output. |
| Phase 7D | Puter dev manual surface | dev-only, not default, disabled by default | Adds a manual UI surface gated by flags, with no chat wiring and no automatic call. |
| Phase 7E | Puter dev route | dev-only, not default, disabled by default | Mounts `/dev/puter` only when the Free and dev surface flags are enabled. |
| Phase 7F | Real Puter smoke runbook | docs-only | Documents local/manual smoke validation steps for `/dev/puter`. |
| Phase 7G | Puter script loader | dev-only, not default, disabled by default | Adds an explicit fixed-source loader for `https://js.puter.com/v2/`; loading is manual and does not call AI. |
| Phase 7H | Real Puter smoke result | docs-only | Records a sanitized local smoke result and confirms no normal chat integration. |
| Phase 7I | Free Chat Bridge design | docs/contract only | Defines future bridge gates and fail-closed behavior without implementation. |
| Phase 7J | Free Chat Bridge contract | production-safe contract, not default, disabled by default | Adds deterministic eligibility decisions and runtime truth; no Puter call or chat import. |
| Phase 7K | Free Chat Bridge mock | mock-only, not default, disabled by default | Composes the contract and returns deterministic mock output only. |
| Phase 7L | Dev-real Free Chat Bridge | dev-only, not default, disabled by default | Adds an isolated real bridge function that can invoke only the existing gated manual harness. |
| Phase 7M | Dev chat toggle | dev-only, not default, disabled by default | Adds a manual `/dev/puter` toggle surface; normal chat remains untouched. |
| Phase 7N | Consent/auth safe state | dev-only safety handling | Handles provider pending/consent/auth timeout states with safe public reasons. |
| Phase 7O | Controlled Free Chat Pilot contract | docs/contract only | Defines pilot boundaries, rollout stages, metrics, rollback, and runtime truth expectations. |
| Phase 7P | Pilot flag contract | production-safe contract, not default, disabled by default | Adds pure pilot eligibility, rollback, allowlist, and sanitization decisions. |
| Phase 7Q | Pilot mock | mock-only, not default, disabled by default | Composes pilot and bridge contracts with deterministic mock-only output. |
| Phase 7R | Internal real pilot | internal-only, not default, disabled by default | Composes pilot contract and dev-real bridge behind internal markers and flags. |
| Phase 7S | Allowlisted pilot | allowlisted-only, not default, disabled by default | Adds allowlisted pilot composition on top of the internal real pilot. |
| Phase 7T | Pilot ops/readiness | docs/env-example cleanup | Documents rollout readiness, rollback, allowlist, and observability controls. |

## Current Status By Area

| Area | Classification | Status |
| --- | --- | --- |
| Backend Access Layer contracts | production-safe contract | Plan policy, quota, routing, registry, public snapshot, boundary, and Puter adapter contracts are deterministic and tested. |
| Public snapshot/boundary | production-safe contract | Public output is exact-key, sanitized, and fail-closed on malformed or unsafe input. |
| Puter browser/dev flow | dev-only, not default, disabled by default | `/dev/puter`, manual surface, script loader, and manual harness require explicit flags and manual user action. |
| Free chat bridge contracts | production-safe contract, not default, disabled by default | Eligibility decisions are pure and do not call Puter or chat transport. |
| Mock bridge | mock-only, not default, disabled by default | Mock bridge returns deterministic mock-only output after contract allow. |
| Dev-real bridge | dev-only, not default, disabled by default | Real provider path is isolated and only reaches the existing gated manual harness. |
| Consent/auth pending handling | dev-only safety handling | Pending consent/auth states are treated as safe public pending/timeout states, not success. |
| Pilot flag contract | production-safe contract, not default, disabled by default | Pilot eligibility includes flags, rollback, allowlist markers, quota/routing, consent state, and unsafe-field denial. |
| Pilot mock | mock-only, not default, disabled by default | Pilot orchestration can be tested without real provider execution. |
| Internal real pilot | internal-only, not default, disabled by default | Internal path requires internal flag/marker and pilot contract allow before invoking the dev-real bridge. |
| Allowlisted pilot | allowlisted-only, not default, disabled by default | Allowlisted path requires explicit allowlist match, rollback inactive, and all pilot gates before internal composition. |
| Ops/readiness | docs/audit only | Defines rollout checklist, observability expectations, and rollback plan. |

## Flags Inventory

All Puter/Free pilot flags in `frontend/.env.example` default to `false`.

| Flag | Default | Classification |
| --- | --- | --- |
| `VITE_OMNI_EXPERIMENTAL_PUTER_FREE` | `false` | Enables the experimental Free/Puter family only when explicitly opted in. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE` | `false` | Future Free chat bridge contract gate. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK` | `false` | Mock bridge gate. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL` | `false` | Dev-real bridge gate. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE` | `false` | Dev-only chat toggle surface gate. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT` | `false` | Future controlled Free pilot gate. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL` | `false` | Internal-only real pilot gate. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED` | `false` | Allowlisted pilot gate. |
| `VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE` | `false` | Dev-only `/dev/puter` manual surface gate. |

## Safety Invariants

- Puter is not the default provider.
- Puter is not enabled by default.
- Normal chat remains unchanged unless a future phase explicitly changes it after review.
- The current normal chat path remains the Omni chat transport through `sendOmniMessage`, not a Puter bridge.
- Tools, files, function-calling, sensitive tools, and long memory remain disabled in the Free/Puter path.
- BYOK storage, billing, and Pro behavior are not implemented for the Free/Puter path.
- Raw provider payloads must not be exposed.
- Secrets, API keys, tokens, environment values, internal config, provider config, stack traces, and debug payloads must not be exposed.
- Rollback and allowlist controls are required before any pilot path can move beyond local/internal validation.
- Consent/auth pending states are handled as safe pending or timeout states, not hidden success.
- The only real Puter path that exists today is gated and manual: allowlisted/internal/dev pilot layers to the dev-real bridge to the existing manual harness.
- No layer should bypass PlanPolicy, TokenQuota, ProviderRouter, ProviderRegistry, PublicAccessSnapshot, AccessSnapshotBoundary, or the Puter adapter contracts.

## Known Limitations

- Puter consent/auth may require explicit user action in the browser.
- Production or user-facing pilot behavior is not enabled.
- The normal chat provider is not switched to Puter.
- Allowlist and rollback are contract-level or local markers unless a future ops config layer adds a safe remote control plane.
- Runtime truth is public-safe, but it should be revalidated before any broader rollout.
- Browser runtime and Puter runtime availability remain environment-dependent.
- The dev route and loader are suitable for local/manual validation only.

## Remaining Risks

- Accidental flag misconfiguration could expose a dev or pilot path unexpectedly.
- Accidental normal chat integration before readiness could bypass the staged rollout plan.
- Stale branch or base issues can hide missing dependencies between phases.
- Future modules could leak raw output if they bypass the existing sanitizing wrappers.
- Consent/auth UX still needs controlled handling before any real pilot.
- Production quota enforcement must remain authoritative and consistent with runtime truth.
- Remote ops controls are not yet defined; rollout currently depends on future safe configuration work.
- Source-level guards should continue checking for hidden provider, network, and chat-send imports.

## Recommended Next Phases

- Phase 7V: Free/Puter Regression Matrix.
- Phase 7W: Runtime Truth/Public Payload Alignment.
- Phase 7X: Controlled Internal Pilot Runbook.
- Phase 7Y: One-user Allowlisted Pilot Dry Run.
- Phase 7Z: Go/No-Go Review for broader pilot.

These phases should not enable Puter for normal users yet. They should keep Puter disabled by default, preserve rollback and allowlist controls, and continue proving public-safe runtime truth before any broader pilot decision.

## Checkpoint Conclusion

The Free/Puter work is currently a layered set of backend contracts, frontend contracts, dev-only/manual surfaces, mock-only paths, internal-only pilot preparation, allowlisted-only pilot preparation, and ops readiness documentation. The work is not a normal-user rollout, not a default provider switch, and not a production chat integration.
