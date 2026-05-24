# Access Layer Free/Puter Runtime Truth and Public Payload Alignment

Status: Phase 7W audit/docs only. This document aligns public/runtime truth fields across the Free/Puter Access Layer stack before any broader pilot. It does not implement behavior, connect Puter to normal chat, make Puter default, enable Puter by default, or add provider/network calls.

## Scope

Reviewed surfaces:

- Backend Access Layer: `PlanPolicy`, `TokenQuota`, `ProviderRouter`, `ProviderRegistry`, `PublicAccessSnapshot`, `AccessSnapshotBoundary`, and Puter client adapter contract.
- Frontend Puter path: browser skeleton, manual harness, script loader, `/dev/puter` route, dev manual surface, and dev chat toggle.
- Free chat bridge/pilot modules: bridge contract, bridge mock, dev-real bridge, pilot flag contract, pilot mock, internal real pilot, and allowlisted pilot.
- Docs and config: checkpoint, regression matrix, ops readiness, and `frontend/.env.example`.
- Normal chat path read-only: normal chat still sends through `sendOmniMessage`; Puter pilot modules remain outside the normal chat send path.

## Canonical Runtime Truth Groups

These groups define the desired vocabulary for public-safe runtime truth. Not every layer emits every field. Lower-level Access Layer outputs use their existing public snapshot/envelope names; bridge and pilot layers translate those values into `runtime_truth`.

### Access Layer

- `access_layer_plan_mode`
- `quota_allowed`
- `quota_exceeded`
- `routing_allowed`
- `selected_adapter_id`
- `boundary_version`
- `snapshot_version`

### Provider

- `provider_family`
- `provider_attempted`
- `provider_succeeded`
- `provider_failed_reason`
- `fallback_triggered`
- `raw_provider_payload_exposed`

### Pilot

- `pilot_enabled`
- `pilot_eligible`
- `pilot_denied_reason`
- `allowlisted_pilot`
- `allowlist_required`
- `allowlist_matched`
- `rollback_active`
- `consent_state`

### Output

- `sanitized_output`
- `sanitized_output_present`

## Alignment Findings

| Surface | Public/runtime shape | Alignment status |
| --- | --- | --- |
| `PublicAccessSnapshot` | Public snapshot with `plan_mode`, quota fields, routing fields, `selected_provider_family`, `selected_adapter_id`, and `snapshot_version`. | Aligned as the source for Access Layer truth. It does not use the `runtime_truth` wrapper but exposes the canonical source values. |
| `AccessSnapshotBoundary` | Exact-key envelope with `ok`, `denied`, `reason`, `access_snapshot`, `snapshot_version`, and `boundary_version`. | Aligned as the public boundary. It enforces approved snapshot/envelope keys and fail-closed output. |
| Puter client adapter | Public adapter/selection payload with contract metadata, `selection_allowed`, `denied`, and `reason`. | Aligned as adapter selection metadata. It does not emit provider execution truth because it performs no provider execution. |
| Free chat bridge contract | Exact-key decision plus `runtime_truth` with Access Layer, provider, fallback, and `sanitized_output=null`. | Aligned. Provider attempted/succeeded are always false; missing runtime is denied/fallback; no raw payload field is emitted because no provider path exists. |
| Free chat bridge mock | Exact-key mock result plus bridge `runtime_truth`; mock status is represented by `mock_succeeded` outside real provider truth. | Aligned. Real provider attempted/succeeded remain false and mock success is separate. |
| Dev-real bridge | Exact-key result plus `runtime_truth` with `sanitized_output`. | Aligned for dev-only real path. Provider attempted becomes true only when the explicit exported function invokes the existing manual harness. |
| Pilot flag contract | Exact-key pilot decision plus `runtime_truth` with pilot, Access Layer, provider, consent, rollback, allowlist, and `raw_provider_payload_exposed=false`. | Aligned as the canonical pilot gate. Provider attempted/succeeded are false; sanitized output is represented as `sanitized_output_present=false`. |
| Pilot mock | Exact-key result plus pilot runtime truth with separate `mock_provider_attempted` and `mock_provider_succeeded`. | Aligned. Real provider status remains false while mock status is separate. |
| Internal real pilot | Exact-key result plus internal pilot runtime truth. | Aligned. Real provider status is copied only from the dev-real bridge after all internal gates pass. |
| Allowlisted pilot | Exact-key result plus allowlisted pilot runtime truth. | Aligned. Real provider status is copied only from the internal pilot after allowlisted gates pass. |

## Field Mapping

| Canonical field | Backend source | Bridge source | Pilot source | Notes |
| --- | --- | --- | --- | --- |
| `access_layer_plan_mode` | `PublicAccessSnapshot.plan_mode` | Bridge `runtime_truth.access_layer_plan_mode` | Pilot `runtime_truth.access_layer_plan_mode` | Public values are normalized to safe plan modes before exposure. |
| `quota_allowed` | Snapshot quota field | Bridge runtime truth | Pilot runtime truth | Must remain false on denied quota. |
| `quota_exceeded` | Snapshot quota field | Bridge runtime truth | Pilot runtime truth | Must deny/fallback before provider execution. |
| `routing_allowed` | Snapshot routing field | Bridge runtime truth | Pilot runtime truth | Must deny/fallback before provider execution. |
| `selected_adapter_id` | Snapshot adapter field | Bridge runtime truth | Pilot runtime truth | Caller-controlled values must be allowlisted or replaced with safe empty values. |
| `boundary_version` | Boundary envelope | Bridge runtime truth | Pilot runtime truth | Unsafe or unknown versions must not be echoed. |
| `snapshot_version` | Boundary/snapshot version | Bridge runtime truth | Pilot runtime truth | Unsafe or unknown versions must not be echoed. |
| `provider_family` | `selected_provider_family` | Bridge runtime truth | Pilot runtime truth | Only `experimental_free_provider` is accepted for Free/Puter paths. |
| `provider_attempted` | Not applicable | False for contract/mock; conditional for dev-real | False for flag/mock; conditional for internal/allowlisted real paths | True only after an explicit, gated real invocation. |
| `provider_succeeded` | Not applicable | False for contract/mock; conditional for dev-real | False for flag/mock; conditional for internal/allowlisted real paths | True only on sanitized provider success. |
| `provider_failed_reason` | Snapshot/boundary reason equivalent | Safe reason constant | Safe reason constant | No raw errors or stack traces. |
| `fallback_triggered` | `fallback_allowed` equivalent | Bridge runtime truth | Pilot runtime truth | True on deny/failure. |
| `raw_provider_payload_exposed` | Not emitted | Not emitted for bridge contract/mock/dev-real | Always false in pilot runtime truth | Any future public provider payload field must remain explicit false. |
| `pilot_enabled` | Not applicable | Not applicable | Pilot runtime truth | Feature flags and rollback determine this. |
| `pilot_eligible` | Not applicable | Not applicable | Pilot runtime truth | True only after all pilot gates pass. |
| `pilot_denied_reason` | Not applicable | Not applicable | Pilot runtime truth | Safe reason constant only. |
| `allowlisted_pilot` | Not applicable | Not applicable | Allowlisted runtime truth | True only when allowlisted flag/marker passes. |
| `allowlist_required` | Not applicable | Not applicable | Pilot/allowlisted runtime truth | Missing or mismatched allowlist denies. |
| `allowlist_matched` | Not applicable | Not applicable | Pilot/allowlisted runtime truth | Public-safe boolean only. |
| `rollback_active` | Not applicable | Not applicable | Pilot/allowlisted runtime truth | True denies before provider execution. |
| `consent_state` | Not applicable | Not applicable | Pilot runtime truth | Pending/auth states deny or remain safe pending. |
| `sanitized_output` | Not applicable | Null for contract/mock deny; string only after sanitized mock/dev-real success | Result-level field for mock/internal/allowlisted outputs | Never raw provider payload. |
| `sanitized_output_present` | Not applicable | Not used by bridge contract/dev-real | Pilot runtime truth boolean | Boolean only, never text. |

## Public-Safety Invariants

- Mock-only modules keep real `provider_attempted=false` and `provider_succeeded=false`.
- Mock status is separate from real provider status with mock-specific fields or result-level markers.
- Real provider `provider_attempted=true` only after an explicit exported function call passes all gates.
- Real provider `provider_succeeded=true` only after sanitized success.
- `raw_provider_payload_exposed=false` everywhere it is public.
- `sanitized_output` is `null` unless intentionally safe mock/dev-real/internal/allowlisted output is returned.
- `sanitized_output_present` is a boolean only.
- No public output may include raw provider request/response payloads.
- No public output may include stack traces, API keys, tokens, credentials, environment variables, provider config, private endpoints, billing data, or debug data.
- Exact public key sets are tested for bridge contracts, mocks, pilot contracts, internal real pilot, allowlisted pilot, browser adapter, manual harness, and dev surfaces where practical.

## Existing Test Coverage

Existing frontend tests cover:

- Exact public decision/result key sets.
- Exact `runtime_truth` key sets.
- Serialized output scans for sensitive fragments.
- `provider_attempted=false` and `provider_succeeded=false` for contract/mock denial paths.
- Mock status separated from real provider status.
- `raw_provider_payload_exposed=false` for pilot layers.
- Provider failure sanitization.
- Source guards for hidden chat send, direct `puter.ai.chat`, and direct network paths.

Existing backend tests cover:

- Public Access Layer contract behavior across plan policy, quota, routing, registry, public snapshot, boundary, and Puter adapter selection.
- Fail-closed snapshot/boundary behavior.
- Public-safe Puter client adapter contract/selection behavior.

No public-safety gap requiring code behavior changes was found in this audit.

## Recommended Follow-Up Tests

These are future hardening tests, not blockers for this docs/audit phase:

- Add a generated snapshot test that compares every frontend `runtime_truth` key set to the canonical groups in this document.
- Add a backend/frontend adapter ID alignment test if adapter IDs evolve.
- Add a CI check that all Puter/Free flags in `frontend/.env.example` are present once and default to `false`.
- Add browser/manual consent flow assertions to the internal pilot runbook without storing raw provider payloads.
- Add stale-base guard checks to PR review templates for phases that compose newly merged pilot layers.

## Validation Guidance

Backend Access Layer regression:

```powershell
python -m pytest -q tests/runtime/test_plan_policy.py tests/runtime/test_token_quota.py tests/runtime/test_provider_router.py tests/runtime/test_provider_registry.py tests/runtime/test_public_access_snapshot.py tests/runtime/test_access_snapshot_boundary.py tests/runtime/test_puter_client_adapter.py
```

Focused frontend runtime truth group:

```powershell
cd frontend
npm.cmd exec vitest run src/lib/puter/freeModeChatBridgeContract.test.ts src/lib/puter/freeModeChatBridgeMock.test.ts src/lib/puter/freeModeChatBridgeDevReal.test.ts src/lib/puter/freeModePilotFlagContract.test.ts src/lib/puter/freeModePilotMock.test.ts src/lib/puter/freeModePilotInternalReal.test.ts src/lib/puter/freeModePilotAllowlisted.test.ts
```

Full frontend validation should use explicit default-false overrides when local `frontend/.env.local` enables dev flags.

## Conclusion

The current Free/Puter runtime truth stack is aligned for public-safe audit purposes. Backend snapshots and boundaries provide the Access Layer source of truth. Frontend bridge and pilot modules expose exact-key public decisions/results and sanitized runtime truth. Mock-only modules keep mock status separate from real provider status. Real provider status is limited to dev/internal/allowlisted paths and only after explicit gated invocation. Puter remains disabled by default, non-default, and outside normal chat.
