# Omni Access Layer: Puter Dev Toggle

Phase 7D adds a dev-only manual test surface for the experimental Free Mode Puter path. It is a frontend library surface only; it is not mounted by default, not connected to chat, and not a default provider.

## Scope

- Uses the existing `invokePuterFreeModeManualHarness(...)` contract from Phase 7C.
- Requires both `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=true` and `VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=true`.
- Defaults both feature flags to `false`.
- Requires a safe AccessSnapshotBoundary-style envelope before any manual invocation can pass.
- Requires an explicit developer button/action; no call happens on import, render, mount, or app load.
- Shows only sanitized public-safe output and stable denial reasons.

## Non-Goals

- No production chat flow integration.
- No default Puter provider behavior.
- No automatic network calls.
- No tools, files, function-calling, or long memory in Free mode.
- No BYOK storage, billing, Pro behavior, or provider credential handling.
- No raw request, raw response, stack trace, environment values, provider internals, private endpoint, billing detail, or debug payload exposure.

The production user flow remains a future phase. This surface exists only to make controlled browser testing possible while preserving the PlanPolicy, TokenQuota, ProviderRouter, ProviderRegistry, PublicAccessSnapshot, AccessSnapshotBoundary, PuterClientAdapter, browser skeleton, and manual harness gates.
