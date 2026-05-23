# Omni Access Layer Puter Manual Harness

This document describes the Phase 7C Puter browser manual call harness. It is a
development-only frontend library helper for controlled Free Mode testing and is
not connected to the production chat flow.

## Location

- Harness: `frontend/src/lib/puter/freeModePuterManualHarness.ts`
- Tests: `frontend/src/lib/puter/freeModePuterManualHarness.test.ts`

## Boundary

The harness uses the existing disabled-by-default
`VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false` flag. It does not run on import, app
load, or any default path. A call can happen only through explicit manual
invocation after the Phase 7B browser skeleton accepts a safe
AccessSnapshotBoundary-style response.

The harness remains gated by PlanPolicy, TokenQuota, ProviderRouter,
ProviderRegistry, PublicAccessSnapshot, AccessSnapshotBoundary,
PuterClientAdapter, and the Phase 7B browser skeleton. It requires Free Mode and
`experimental_free_provider`.

## Not Included

This phase does not make Puter the default provider, does not add UI or chat flow
integration, does not add BYOK storage, billing, Pro provider behavior, tools,
files, function calling, or long memory.

The harness never accepts secrets, API keys, access tokens, env vars, provider
config, private endpoints, billing data, debug data, tools, files, function
calling, or raw provider payloads. Provider responses and errors are reduced to
public-safe output, and raw provider payloads are not returned.

Future production integration remains separate.
