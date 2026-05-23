# Omni Access Layer Puter Browser Skeleton

This document describes the Phase 7B Puter browser integration skeleton. It is
frontend-only structure for future Free Mode browser execution and does not make
Puter active by default.

## Location

- Skeleton: `frontend/src/lib/puter/freeModePuterBrowserAdapter.ts`
- Tests: `frontend/src/lib/puter/freeModePuterBrowserAdapter.test.ts`

## Boundary

The skeleton is disabled by default through
`VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false`. It performs no automatic network call,
does not switch the default provider, and does not invoke Puter on import, app
load, tests, typecheck, or default paths.

Selection requires an explicit experimental flag, browser runtime, available
Puter client shape, and a safe AccessSnapshotBoundary-style response proving
Free Mode routing is allowed. The skeleton remains gated by PlanPolicy,
TokenQuota, ProviderRouter, ProviderRegistry, PublicAccessSnapshot,
AccessSnapshotBoundary, and the PuterClientAdapter contract.

## Not Included

This phase does not add real Puter execution, provider calls, BYOK storage,
billing, Pro provider behavior, UI, tools, files, function calling, or long
memory. It does not accept secrets, API keys, access tokens, env vars, provider
config, private endpoints, billing data, debug data, or raw provider payloads.

`requestOptions` rejects every key in this skeleton phase. Benign client options
may be introduced only in a future phase with explicit allowlist tests.
