# Omni Access Layer: Controlled Free Chat Bridge Design

Phase 7I defines the contract for a future Free-mode chat bridge that may call
the browser Puter runtime. This is a docs/contract phase only. It does not
implement the bridge, connect Puter to the normal chat flow, make Puter the
default provider, or add any production provider execution path.

## Current Boundary

The normal chat flow remains server-backed through the existing chat transport.
The Puter work from earlier phases is isolated to the dev-only `/dev/puter`
surface and requires explicit local flags plus manual actions.

Existing foundations that must remain in the path before any future Free chat
bridge can call Puter:

- PlanPolicy
- TokenQuota
- ProviderRouter
- ProviderRegistry
- PublicAccessSnapshot
- AccessSnapshotBoundary
- PuterClientAdapter
- Puter browser skeleton
- Puter manual harness

The future bridge must compose these boundaries. It must not replace them with
client-side trust.

## Required Gates

Before a future Free chat bridge may attempt a Puter call, all of these gates
must pass:

- `plan_mode` is `free`.
- Daily quota allows the current request.
- Input token limit passes.
- Output token budget passes.
- AccessSnapshotBoundary returns `ok=true` and `denied=false`.
- The snapshot has `routing_allowed=true`.
- `selected_provider_family` is `experimental_free_provider`.
- The Puter adapter contract allows selection.
- Browser runtime is present.
- Puter runtime is present.
- The experimental Free Puter feature flag is enabled.
- No files are attached.
- No tools or function-calling options are present.
- No long memory behavior is enabled.
- No sensitive tools are enabled.
- No provider override is accepted from public input.

Any missing or failed gate means no Puter call.

## Feature Flags

Existing flag:

- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false`

Future optional bridge flag:

- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false`

Both flags must default to false. A future implementation should require both
flags before the normal Free chat path can even consider the bridge.

## Future Runtime Truth Fields

A future bridge result should expose only public-safe runtime truth fields:

- `access_layer_plan_mode`
- `provider_family`
- `provider_attempted`
- `provider_succeeded`
- `provider_failed_reason`
- `fallback_triggered`
- `quota_allowed`
- `quota_exceeded`
- `routing_allowed`
- `selected_adapter_id`
- `boundary_version`
- `snapshot_version`
- `sanitized_output`

These fields should support auditability without exposing raw provider data,
private configuration, or internal debug material.

## Fail-Closed Rules

The bridge must fail closed before any provider call in these cases:

- Quota is exceeded.
- Input token limit is exceeded.
- Output token budget is exceeded.
- The access snapshot is missing, malformed, denied, or fails exact key checks.
- Browser runtime is missing.
- Puter runtime is missing.
- Feature flags are disabled.
- The selected provider family is not `experimental_free_provider`.
- The selected adapter is not approved by the Puter adapter contract.
- Unsupported request options are present.
- Public input attempts to override provider, adapter, policy, or quota fields.

If Puter runtime is missing, production chat should not load it implicitly. A
dev-only path may report a safe missing-runtime reason and direct developers to
the manual `/dev/puter` loader flow.

If a provider error occurs after all gates pass, the bridge must return a
sanitized failure, trigger the approved fallback path, and avoid exposing raw
exception details.

## Forbidden Request Fields

Public chat input must not be allowed to set or override:

- `provider_mode`
- `provider_family`
- `adapter_id`
- `selected_adapter_id`
- `policy_overrides`
- quota limits
- API keys
- access tokens
- credentials
- environment variables
- `provider_config`
- `private_endpoint`
- billing fields
- debug fields
- tools
- files
- function-calling options
- raw provider payloads

Future code must reject these before adapter selection or provider execution.

## Output Sanitization

Future bridge output must not expose:

- raw provider response
- raw provider request
- stack trace
- internal debug payload
- private provider metadata
- credentials or key material
- environment values
- billing configuration

User-visible text must be sanitized before display. Public metadata should be
limited to approved access-layer and runtime truth fields.

## Future Testing Plan

Implementation phases after this design should add tests for:

- gate pass and fail cases
- no call when the feature flag is false
- no call when quota is denied
- no call when AccessSnapshotBoundary denies routing
- no call with tools, files, or function-calling options
- no call with provider or adapter override attempts
- no call when browser runtime is missing
- no call when Puter runtime is missing
- mocked successful Puter call
- mocked provider failure
- sanitized output
- runtime truth fields
- fallback behavior
- no chat call on app load
- no provider default switch

Tests should prove that provider execution can happen only after all gates pass.

## Staged Implementation Path

Recommended next phases:

- Phase 7J: Free Chat Bridge Contract Module, no real call.
- Phase 7K: Free Chat Bridge Mocked Integration, behind flags.
- Phase 7L: Real Puter Chat Bridge Dev-only, behind flags.
- Phase 7M: Controlled Free Mode pilot, still not default.

Each phase should preserve the existing dev-only Puter boundaries until a
reviewed production contract explicitly replaces them.

## Non-Goals

This design does not implement:

- production chat bridge execution
- default Puter routing
- BYOK storage
- billing
- tools
- files
- function-calling
- long memory
- hidden provider execution
- provider override from public input
