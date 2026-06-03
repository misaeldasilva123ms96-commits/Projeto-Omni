# Access Layer Free/Puter Go/No-Go Review

Status: Phase 7Z docs/review only. This document does not enable a broader pilot, change execution paths, connect Puter to normal chat, make Puter the default provider, or add provider/network calls.

## Purpose And Scope

This review defines the evidence and decision criteria required before any future broader Free/Puter pilot. It summarizes readiness after Phases 1 through 7Y, identifies what is still limited to contracts, development surfaces, mocks, internal-only paths, and allowlisted-only paths, and provides a safe decision template for a later rollout review.

This document is not approval to enable Puter for normal users. Any broader pilot requires explicit evidence that all Go criteria are satisfied and no No-Go criteria are present.

## Current Readiness Summary

The Free/Puter stack is staged and conservative:

- Backend Access Layer contracts are production-safe contracts for plan policy, quota, routing, registry, public snapshot, boundary, and Puter adapter selection.
- Frontend bridge and pilot contracts are deterministic, exact-key, public-safe, and disabled by default.
- Mock paths exist for orchestration testing without real provider execution.
- Real Puter execution remains limited to explicit, gated, dev/internal/allowlisted paths that flow through the existing manual harness.
- Consent/auth pending is treated as a safe pending/denied state, not success.
- Ops/readiness, regression matrix, runtime truth alignment, internal runbook, and one-user dry-run docs define the evidence required before broader pilot consideration.

Readiness is not the same as rollout approval. Broader normal-user enablement remains a No-Go unless the evidence checklist in this document is complete.

## Completed Phases

| Phase | Area | Current classification |
| --- | --- | --- |
| Phase 1 | PlanPolicy | Production-safe contract. |
| Phase 2 | TokenQuota | Production-safe contract. |
| Phase 3 | ProviderRouter | Production-safe contract. |
| Phase 4 | ProviderRegistry | Production-safe contract. |
| Phase 5 | PublicAccessSnapshot | Production-safe contract. |
| Phase 6 | AccessSnapshotBoundary | Production-safe contract. |
| Phase 7A | Puter client adapter contract | Production-safe contract, not default, disabled by default. |
| Phase 7B | Puter browser skeleton | Contract/browser eligibility only, not default, disabled by default. |
| Phase 7C | Puter manual harness | Dev-only, manual, not default, disabled by default. |
| Phase 7D | Puter dev manual surface | Dev-only, manual, not default, disabled by default. |
| Phase 7E | Puter dev route | Dev-only `/dev/puter`, not default, disabled by default. |
| Phase 7F | Real Puter smoke runbook | Docs-only. |
| Phase 7G | Puter script loader | Dev-only, fixed-source, manual, no AI call from loader. |
| Phase 7H | Real Puter smoke result | Docs-only sanitized validation record. |
| Phase 7I | Free chat bridge design | Docs/contract only. |
| Phase 7J | Free chat bridge contract | Production-safe contract, no Puter call, no chat integration. |
| Phase 7K | Free chat bridge mock | Mock-only, no real provider. |
| Phase 7L | Dev-real bridge | Dev-only real path through existing gated manual harness. |
| Phase 7M | Dev chat toggle | Dev-only `/dev/puter` manual surface, not normal chat. |
| Phase 7N | Consent/auth safe state | Dev-only safe pending/timeout handling. |
| Phase 7O | Controlled Free chat pilot contract | Docs/contract only. |
| Phase 7P | Pilot flag contract | Production-safe contract, rollback/allowlist aware, no Puter call. |
| Phase 7Q | Pilot mock | Mock-only pilot orchestration. |
| Phase 7R | Internal real pilot | Internal-only, disabled by default, real path only through Phase 7L. |
| Phase 7S | Allowlisted pilot | Allowlisted-only, disabled by default, real path only through Phase 7R. |
| Phase 7T | Pilot ops/readiness | Docs/env readiness only. |
| Phase 7U | Free/Puter checkpoint | Docs/audit checkpoint only. |
| Phase 7V | Regression matrix | Docs/test-planning only. |
| Phase 7W | Runtime truth alignment | Docs/audit only. |
| Phase 7X | Internal pilot runbook | Docs/runbook only. |
| Phase 7Y | One-user dry run | Docs/runbook/validation record only. |

## Layer Classification

### Production-Safe Contracts

- Backend `PlanPolicy`, `TokenQuota`, `ProviderRouter`, `ProviderRegistry`, `PublicAccessSnapshot`, and `AccessSnapshotBoundary`.
- Backend Puter client adapter selection contract.
- Frontend Free chat bridge contract.
- Frontend pilot flag contract.

These layers decide, normalize, deny, and expose public-safe state. They do not perform real Puter execution.

### Dev-Only

- `/dev/puter` route.
- Puter dev manual surface.
- Puter script loader for the fixed `https://js.puter.com/v2/` source.
- Puter manual harness.
- Dev chat toggle.
- Dev-real bridge.
- Consent/auth pending UI handling.

These layers require explicit flags and manual action. They are not normal-user chat paths.

### Mock-Only

- Free chat bridge mock.
- Pilot mock.

Mock-only layers return deterministic mock output and keep real provider status separate from mock status.

### Internal-Only

- Internal real pilot.

The internal real pilot requires internal flags/markers and composes the dev-real bridge only after pilot gates pass.

### Allowlisted-Only

- Allowlisted pilot.
- One-user dry-run process.

Allowlisted paths require explicit allowlist match, rollback inactive, pilot gates, safe consent state, and all Access Layer gates.

### Still Not Default

Puter is not the default provider. Normal chat remains the Omni chat transport through `sendOmniMessage` unless a future reviewed phase explicitly changes it.

### Still Disabled By Default

All Puter/Free flags in `frontend/.env.example` remain default `false`:

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

## Go Criteria

A broader Free/Puter pilot may be considered only if all criteria are true:

| Criterion | Required evidence |
| --- | --- |
| CI green | PR checks pass for the exact commit under review. |
| Backend Access Layer tests green | Access Layer pytest command passes. |
| Frontend validation green | `npm run typecheck`, `npm run test`, `npm run build`, and `npm run test:security` pass. |
| Focused Puter/pilot tests green | Focused Vitest group passes for bridge, dev-real, pilot flag, pilot mock, internal real, allowlisted, dev route, loader, and harness coverage. |
| Runtime truth/public payload safe | Exact-key public output and runtime truth checks pass. |
| No raw provider payload exposure | Runtime truth shows `raw_provider_payload_exposed=false` where present. |
| No secret/env/debug leakage | Serialized output scans show no API keys, tokens, credentials, env vars, provider config, private endpoints, billing, debug data, or stack traces. |
| Rollback verified | Disabling pilot/allowlisted flags, removing allowlist, or setting rollback active denies before provider execution. |
| Allowlist verified | Allowlist miss and mismatch deny before provider execution. |
| Consent/auth pending handled safely | Pending/auth state is denied or safe pending; it is never success and never bypassed. |
| Quota/routing gates verified | Quota denied/exceeded and routing false deny before provider execution. |
| Normal chat unchanged with flags false | Normal chat still uses the existing Omni chat path and does not call Puter. |
| Puter not default provider | Provider defaults and normal routing do not select Puter by default. |

## No-Go Criteria

Any single item below makes broader pilot approval a No-Go:

- Any failing CI or security test.
- Raw provider payload exposure.
- Raw Puter response exposure.
- Stack trace exposure.
- Token, API key, credential, environment variable, provider config, private endpoint, billing, or debug leakage.
- Rollback failure.
- Allowlist bypass.
- Quota or routing denied while provider is attempted.
- Consent/auth loop or unsafe pending state.
- Normal chat behavior changes unexpectedly.
- Puter becomes the default provider.
- Tools, files, function-calling, or long memory are enabled in the Free/Puter path.
- BYOK, billing, or Pro behavior appears in the Free/Puter path.
- Stale branch/base inconsistency hides missing dependency files or phase work.

## Required Evidence Checklist

Collect only public-safe evidence:

- PR checks output for the target commit.
- Backend pytest output.
- Focused Puter Vitest output.
- `npm run typecheck`, `npm run test`, `npm run build`, and `npm run test:security` output.
- `.env.example` flag audit confirming every Puter/Free flag defaults to `false`.
- Safe dry-run report from the one-user allowlisted dry-run process.
- Runtime truth sample with no secrets and no raw provider payload.
- Rollback verification showing provider execution stops before attempt.
- Allowlist miss verification showing denial before provider execution.
- Consent/auth state evidence using safe constants only.
- Confirmation that normal chat remains unchanged with flags false.

Do not collect raw provider payloads, raw Puter responses, sensitive prompts, tokens, API keys, credentials, env vars, stack traces, provider config, private endpoints, billing data, debug payloads, or raw user/session identifiers.

## Decision Template

```markdown
# Free/Puter Broader Pilot Go/No-Go Decision

- Decision: GO / NO-GO
- Date/time:
- Reviewer(s):
- Target branch/commit:
- Scope approved:
- Max pilot population:
- Required flags:
- Allowlist mechanism:
- Rollback owner:
- Observability owner:
- Stop conditions:
- Next review date:
- CI result:
- Backend Access Layer tests:
- Focused Puter/pilot tests:
- Frontend typecheck/test/build/security:
- Runtime truth sample reviewed: yes/no
- Raw provider payload exposed: no / yes-stop
- Secrets/env/debug leakage observed: no / yes-stop
- Rollback verified: yes/no
- Allowlist miss verified: yes/no
- Consent/auth pending handling verified: yes/no
- Normal chat unchanged with flags false: yes/no
- Puter default provider: no / yes-stop
- Notes:
```

## Recommendation

Do not recommend broad normal-user enablement yet unless all evidence above is present for the exact commit and environment under review.

If the evidence is complete and all Go criteria pass, the next controlled step should be:

- Phase 8A - Controlled Pilot Execution Record.

If any evidence is incomplete, stale, unsafe, or failing, the next step should be:

- Phase 8A-blocked - Fix evidence gaps first.

## Review Conclusion

The current Free/Puter stack is ready for continued controlled review and evidence gathering, not broad default rollout. Puter remains disabled by default, not the default provider, outside normal chat by default, and constrained by Access Layer gates, rollback, allowlist, consent/auth safety, and public-safe runtime truth.
